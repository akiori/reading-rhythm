#!/usr/bin/env python3
"""Create a self-contained focused-reading HTML page without external dependencies."""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

READING_TOKEN = re.compile(r"[\u3400-\u9fff]+|[A-Za-z][A-Za-z0-9+.#/:'’_-]*")
HAN_CHARACTER = re.compile(r"[\u3400-\u9fff]")
LATIN_CHARACTER = re.compile(r"[A-Za-z]")
TABLE_SEPARATOR_CELL = re.compile(r"^:?-{3,}:?$")
LIST_ITEM = re.compile(r"^\s*(?:[-+*]|\d+[.)])\s+(.+)$")
HEADING = re.compile(r"^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$")
PULSE_CLASSES = ("pulse-2", "pulse-4", "pulse-1", "pulse-3", "pulse-0", "pulse-2", "pulse-4", "pulse-1")
VENDOR_DIR = Path(__file__).resolve().parent.parent / "vendor"
USER_DICT = Path(__file__).resolve().parent.parent / "assets" / "custom_terms.txt"

if VENDOR_DIR.exists():
    sys.path.insert(0, str(VENDOR_DIR))

try:
    import jieba
except ModuleNotFoundError:  # Keep the page usable if the skill was copied without its vendor directory.
    jieba = None

if jieba and USER_DICT.exists():
    jieba.load_userdict(str(USER_DICT))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate an ADHD-friendly reading webpage.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="UTF-8 plain-text or Markdown input file")
    source.add_argument("--text", help="Text to render")
    parser.add_argument("--title", default="专注阅读", help="Page title")
    parser.add_argument("--keywords", default="", help="Comma-separated emphasis phrases")
    parser.add_argument("--output", type=Path, required=True, help="HTML output path")
    return parser.parse_args()


def emphasis_rules(raw: str) -> list[tuple[str, str]]:
    phrases = []
    for item in re.split(r"[,，\n]", raw):
        phrase = item.strip()
        if phrase and phrase not in phrases:
            phrases.append(phrase)
    rules = []
    for index, phrase in enumerate(phrases[:12]):
        level = "anchor" if index < 3 else "focus" if index < 7 else "hint"
        rules.append((phrase, level))
    return rules


def render_plain(text: str, pulse: list[int]) -> str:
    """Wrap short Chinese/English reading units in a deterministic visual rhythm."""
    result: list[str] = []
    cursor = 0
    for match in READING_TOKEN.finditer(text):
        result.append(html.escape(text[cursor:match.start()]))
        token = match.group(0)
        if "\u3400" <= token[0] <= "\u9fff":
            # jieba precise mode is deterministic and keeps semantic words intact.
            words = jieba.lcut(token, cut_all=False) if jieba else [token]
            for word in words:
                if len(word) == 1:
                    result.append(html.escape(word))
                    continue
                rhythm = pulse[0] % len(PULSE_CLASSES)
                result.append(f'<span class="pulse {PULSE_CLASSES[rhythm]}">{html.escape(word)}</span>')
                pulse[0] += 1
        else:
            rhythm = pulse[0] % len(PULSE_CLASSES)
            result.append(f'<span class="en pulse {PULSE_CLASSES[rhythm]}">{html.escape(token)}</span>')
            pulse[0] += 1
        cursor = match.end()
    result.append(html.escape(text[cursor:]))
    return "".join(result)


def render_keyword(phrase: str, level: str) -> str:
    english_class = " en" if LATIN_CHARACTER.search(phrase) else ""
    return f'<span class="{level}{english_class}">{html.escape(phrase)}</span>'


def render_text(text: str, rules: list[tuple[str, str]]) -> str:
    pulse = [0]
    if not rules:
        return render_plain(text, pulse)
    mapping = {phrase: level for phrase, level in rules}
    pattern = re.compile("|".join(re.escape(p) for p, _ in sorted(rules, key=lambda r: len(r[0]), reverse=True)))
    parts: list[str] = []
    cursor = 0
    for match in pattern.finditer(text):
        parts.append(render_plain(text[cursor:match.start()], pulse))
        phrase = match.group(0)
        parts.append(render_keyword(phrase, mapping[phrase]))
        cursor = match.end()
    parts.append(render_plain(text[cursor:], pulse))
    return "".join(parts)


def normalize_inline_markdown(text: str) -> str:
    """Remove common inline Markdown markers while preserving their readable text."""
    text = re.sub(r"!\[([^]]*)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"\[([^]]+)\]\([^)]+\)", r"\1", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\*\*([^*]+)\*\*|__([^_]+)__", lambda m: m.group(1) or m.group(2), text)
    text = re.sub(r"(?<!\w)\*([^*]+)\*(?!\w)|(?<!\w)_([^_]+)_(?!\w)", lambda m: m.group(1) or m.group(2), text)
    return text.strip()


def split_pipe_row(line: str) -> list[str]:
    """Split a GFM pipe-table row, preserving escaped pipes inside cells."""
    value = line.strip()
    if value.startswith("|"):
        value = value[1:]
    if value.endswith("|") and not value.endswith(r"\|"):
        value = value[:-1]
    return [cell.strip().replace(r"\|", "|") for cell in re.split(r"(?<!\\)\|", value)]


def table_alignment(cell: str) -> str:
    cell = cell.strip()
    if cell.startswith(":") and cell.endswith(":"):
        return "center"
    if cell.endswith(":"):
        return "right"
    return "left"


def is_table_separator(line: str) -> bool:
    cells = split_pipe_row(line)
    return len(cells) >= 2 and all(TABLE_SEPARATOR_CELL.fullmatch(cell.replace(" ", "")) for cell in cells)


def is_table_start(lines: list[str], index: int) -> bool:
    if index + 1 >= len(lines) or "|" not in lines[index]:
        return False
    header = split_pipe_row(lines[index])
    separator = split_pipe_row(lines[index + 1])
    return len(header) >= 2 and len(header) == len(separator) and is_table_separator(lines[index + 1])


def parse_blocks(text: str) -> list[dict[str, object]]:
    """Parse calm-reading blocks with native support for GFM pipe tables."""
    text = text.replace("\\r\\n", "\n").replace("\\n", "\n")
    lines = text.strip().splitlines()
    blocks: list[dict[str, object]] = []
    paragraph: list[str] = []

    def flush_paragraph() -> None:
        if paragraph:
            value = re.sub(r"\s+", " ", " ".join(paragraph)).strip()
            if value:
                blocks.append({"kind": "paragraph", "text": normalize_inline_markdown(value)})
            paragraph.clear()

    index = 0
    while index < len(lines):
        line = lines[index]
        if not line.strip():
            flush_paragraph()
            index += 1
            continue

        if is_table_start(lines, index):
            flush_paragraph()
            header = split_pipe_row(lines[index])
            separators = split_pipe_row(lines[index + 1])
            width = len(header)
            rows: list[list[str]] = []
            index += 2
            while index < len(lines) and lines[index].strip() and "|" in lines[index]:
                row = split_pipe_row(lines[index])
                if len(row) != width:
                    break
                rows.append(row)
                index += 1
            blocks.append({
                "kind": "table",
                "header": header,
                "rows": rows,
                "align": [table_alignment(cell) for cell in separators],
            })
            continue

        if line.strip().startswith("```"):
            flush_paragraph()
            language = line.strip()[3:].strip()
            code_lines: list[str] = []
            index += 1
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            if index < len(lines):
                index += 1
            blocks.append({"kind": "code", "text": "\n".join(code_lines), "language": language})
            continue

        heading = HEADING.match(line)
        if heading:
            flush_paragraph()
            blocks.append({"kind": "heading", "text": normalize_inline_markdown(heading.group(1))})
            index += 1
            continue

        list_item = LIST_ITEM.match(line)
        if list_item:
            flush_paragraph()
            items: list[str] = []
            while index < len(lines):
                item = LIST_ITEM.match(lines[index])
                if not item:
                    break
                items.append(normalize_inline_markdown(item.group(1)))
                index += 1
            blocks.append({"kind": "list", "items": items})
            continue

        if line.lstrip().startswith(">"):
            flush_paragraph()
            quote_lines: list[str] = []
            while index < len(lines) and lines[index].lstrip().startswith(">"):
                quote_lines.append(lines[index].lstrip()[1:].lstrip())
                index += 1
            blocks.append({"kind": "quote", "text": normalize_inline_markdown(" ".join(quote_lines))})
            continue

        paragraph.append(line.strip())
        index += 1

    flush_paragraph()
    return blocks


def render_table(block: dict[str, object], rules: list[tuple[str, str]], index: int) -> str:
    header = block["header"]
    rows = block["rows"]
    align = block["align"]

    def cell_tag(tag: str, value: str, column: int) -> str:
        alignment = align[column] if column < len(align) else "left"
        content = render_text(normalize_inline_markdown(value), rules)
        return f'<{tag} class="align-{alignment}">{content}</{tag}>'

    head_html = "".join(cell_tag("th", value, column) for column, value in enumerate(header))
    row_html = "".join(
        "<tr>" + "".join(cell_tag("td", value, column) for column, value in enumerate(row)) + "</tr>"
        for row in rows
    )
    return (
        f'      <section class="unit table-unit" data-index="{index}">'
        f'<div class="table-scroll" tabindex="0" aria-label="Scrollable data table">'
        f'<table><thead><tr>{head_html}</tr></thead><tbody>{row_html}</tbody></table>'
        f'</div></section>'
    )


def render_block(block: dict[str, object], rules: list[tuple[str, str]], index: int) -> str:
    kind = block["kind"]
    if kind == "table":
        return render_table(block, rules, index)
    if kind == "code":
        language = html.escape(str(block.get("language", "")))
        return f'      <pre class="unit code-unit" data-index="{index}"><code data-language="{language}">{html.escape(str(block["text"]))}</code></pre>'
    if kind == "list":
        items = "".join(f"<li>{render_text(str(item), rules)}</li>" for item in block["items"])
        return f'      <section class="unit list-unit" data-index="{index}"><ul>{items}</ul></section>'
    class_name = "heading-unit" if kind == "heading" else "quote-unit" if kind == "quote" else ""
    classes = f"unit {class_name}".strip()
    return f'      <p class="{classes}" data-index="{index}">{render_text(str(block["text"]), rules)}</p>'


def make_html(title: str, text: str, rules: list[tuple[str, str]]) -> str:
    article = "\n".join(render_block(block, rules, i) for i, block in enumerate(parse_blocks(text), 1))
    keyword_note = " · ".join(html.escape(p) for p, _ in rules) or "按自己的节奏读"
    english_page = len(LATIN_CHARACTER.findall(text)) > len(HAN_CHARACTER.findall(text))
    ui = (
        {
            "lang": "en",
            "body_class": "lang-en",
            "controls": "Reading controls",
            "focus": "Focus highlights",
            "guide": f"Visual anchors: {keyword_note}. Read one block at a time.",
            "footer": "Leave a little room for attention.",
        }
        if english_page
        else {
            "lang": "zh-CN",
            "body_class": "lang-zh",
            "controls": "阅读控制",
            "focus": "聚焦重点",
            "guide": f"视觉锚点：{keyword_note}。每次只读一个色块，读完再进入下一段。",
            "footer": "给注意力留一点空白。",
        }
    )
    return f'''<!doctype html>
<html lang="{ui["lang"]}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
    :root {{ --base: 28px; --ink: #29282a; --paper: #fbfaf7; --mist: #e7edf8; --accent: #55538f; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; color: var(--ink); background: #f1efe9; font-family: "Songti SC", "STSong", SimSun, serif; }}
    body.lang-en, body.lang-en h1 {{ font-family: Charter, Baskerville, Georgia, "Times New Roman", serif; }}
    .shell {{ width: min(100%, 980px); min-height: 100vh; margin: auto; padding: 42px 54px 88px; background: var(--paper); }}
    header {{ display: flex; justify-content: space-between; gap: 24px; align-items: flex-start; margin-bottom: 46px; }}
    .eyebrow {{ margin: 0 0 8px; color: var(--accent); font-family: Charter, Georgia, serif; font-size: 14px; letter-spacing: .08em; }}
    h1 {{ margin: 0; font-size: clamp(30px, 5vw, 47px); line-height: 1.18; font-weight: 700; }}
    .controls {{ display: flex; gap: 7px; flex-wrap: wrap; justify-content: flex-end; }}
    button {{ border: 1px solid #d8d4ca; border-radius: 999px; padding: 7px 11px; color: #4e4b4c; background: #fffefd; font: 14px Charter, Georgia, serif; cursor: pointer; }}
    button:hover, button.active {{ background: #deddf9; border-color: #aaa8e7; }}
    .guide {{ margin: 0 0 30px; padding: 13px 17px; color: #5a5a68; border-left: 3px solid #a9b7dc; background: #f2f5fb; font-size: 16px; line-height: 1.65; }}
    article {{ counter-reset: section; }}
    .unit {{ position: relative; margin: 0 0 30px; padding: 20px 26px 21px; border-radius: 11px; font-size: var(--base); line-height: 1.92; letter-spacing: .025em; text-wrap: pretty; }}
    .unit:nth-child(even) {{ background: var(--mist); }}
    .unit::before {{ content: counter(section, decimal-leading-zero); counter-increment: section; position: absolute; top: 9px; left: -4px; color: #a19fab; font: 12px Charter, Georgia, serif; letter-spacing: .05em; }}
    .pulse {{ display: inline; }}
    .pulse-0 {{ font-size: .96em; font-weight: 460; }}
    .pulse-1 {{ font-size: .98em; font-weight: 500; }}
    .pulse-2 {{ font-size: 1.00em; font-weight: 560; }}
    .pulse-3 {{ font-size: 1.03em; font-weight: 630; }}
    .pulse-4 {{ font-size: 1.06em; font-weight: 700; color: #29283a; }}
    .anchor {{ font-size: 1.12em; font-weight: 780; color: #24233c; text-shadow: 0 .3px 0 #d5d3ea; }}
    .focus {{ font-size: 1.08em; font-weight: 690; color: #29283e; }}
    .hint {{ font-size: 1.04em; font-weight: 600; text-decoration: underline; text-decoration-color: #b8c6e6; text-decoration-thickness: .09em; text-underline-offset: .12em; }}
    .en {{ font-family: Charter, Baskerville, Georgia, "Times New Roman", serif; letter-spacing: .01em; }}
    .heading-unit {{ color: #29283e; font-weight: 720; line-height: 1.45; }}
    .quote-unit {{ border-left: 4px solid #a9b7dc; color: #50505d; background: #f2f5fb; }}
    .list-unit ul {{ margin: 0; padding-left: 1.25em; }}
    .list-unit li + li {{ margin-top: .58em; }}
    .code-unit {{ overflow-x: auto; white-space: pre; font: 500 .64em/1.65 ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; letter-spacing: 0; background: #f1f3f7; }}
    .table-scroll {{ width: 100%; overflow-x: auto; overscroll-behavior-inline: contain; border: 1px solid #d9dfeb; border-radius: 9px; background: rgba(255,255,255,.58); }}
    .table-unit table {{ width: 100%; min-width: max(560px, 100%); border-collapse: collapse; color: #35343a; font: 500 .62em/1.45 Charter, Baskerville, Georgia, serif; letter-spacing: 0; font-variant-numeric: tabular-nums; }}
    .table-unit th, .table-unit td {{ padding: 12px 14px; border-bottom: 1px solid #d9dfeb; vertical-align: top; white-space: nowrap; }}
    .table-unit th {{ color: #55536b; background: rgba(231,237,248,.76); font-weight: 680; }}
    .table-unit th:first-child, .table-unit td:first-child {{ position: sticky; left: 0; background: #f8f8f6; box-shadow: 1px 0 0 #d9dfeb; }}
    .table-unit thead th:first-child {{ background: #edf1f8; }}
    .table-unit tbody tr:last-child td {{ border-bottom: 0; }}
    .align-left {{ text-align: left; }}
    .align-center {{ text-align: center; }}
    .align-right {{ text-align: right; }}
    body.focus-mode .unit:not(:has(.anchor, .focus)) {{ opacity: .62; }}
    body.focus-mode .unit:has(.anchor, .focus) {{ box-shadow: inset 4px 0 0 #8c89cf; }}
    footer {{ margin-top: 56px; color: #8a8785; font-size: 14px; text-align: center; }}
    @media (max-width: 640px) {{ .shell {{ padding: 28px 18px 60px; }} header {{ margin-bottom: 28px; }} .unit {{ padding: 18px 15px; font-size: calc(var(--base) - 4px); line-height: 1.83; }} .guide {{ font-size: 14px; }} .table-unit table {{ min-width: 540px; font-size: .67em; }} .table-unit th, .table-unit td {{ padding: 10px 11px; }} }}
  </style>
</head>
<body class="{ui["body_class"]}">
  <main class="shell">
    <header>
      <div><p class="eyebrow">FOCUSED READING</p><h1>{html.escape(title)}</h1></div>
      <div class="controls" aria-label="{ui["controls"]}"><button id="smaller">A−</button><button id="larger">A+</button><button id="focus">{ui["focus"]}</button></div>
    </header>
    <p class="guide">{ui["guide"]}</p>
    <article>
{article}
    </article>
    <footer>{ui["footer"]}</footer>
  </main>
  <script>
    let size = 28;
    const root = document.documentElement;
    document.querySelector('#smaller').onclick = () => {{ size = Math.max(20, size - 2); root.style.setProperty('--base', size + 'px'); }};
    document.querySelector('#larger').onclick = () => {{ size = Math.min(40, size + 2); root.style.setProperty('--base', size + 'px'); }};
    document.querySelector('#focus').onclick = (event) => {{ document.body.classList.toggle('focus-mode'); event.currentTarget.classList.toggle('active'); }};
  </script>
</body>
</html>'''


def main() -> None:
    args = parse_args()
    text = args.text if args.text is not None else args.input.read_text(encoding="utf-8")
    if not text.strip():
        raise SystemExit("Input text is empty.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(make_html(args.title, text, emphasis_rules(args.keywords)), encoding="utf-8")
    print(f"Created {args.output}")


if __name__ == "__main__":
    main()
