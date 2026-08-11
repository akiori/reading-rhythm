# Reading Rhythm

An experimental, customizable typography renderer for long-form reading.

Reading Rhythm turns long-form Chinese, English, or mixed-language writing into a calm, self-contained webpage. It does not summarize or rewrite text. Instead, it preserves the original structure and introduces visual rhythm, re-entry points, and a small number of visual anchors.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)

## What it does

- Turns plain text or Markdown into a standalone HTML reading page.
- Uses Songti-family fonts for Chinese and Charter-style serif fonts for English.
- Keeps Chinese words intact with deterministic `jieba` segmentation; it never uses arbitrary character chunks such as `法部分` or `么独`.
- Styles complete English words rather than individual letters, with an English UI for English-dominant documents.
- Supports Markdown headings, lists, quotes, fenced code blocks, and responsive GFM pipe tables.
- Includes font-size controls and a focus-highlights toggle. No account, network request, or frontend framework is required at reading time.

## Scope

This is a personal, experimental reading interface—not a diagnostic, therapeutic, or accessibility claim. Typography preferences vary: some readers find visual rhythm engaging, while others prefer conventional typesetting. The renderer is therefore designed to be adjustable and evaluated by the reader, not presented as a universal reading intervention.

## Quick start

```bash
git clone https://github.com/akiori/reading-rhythm.git
cd reading-rhythm
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt

python3 scripts/make_reading_page.py \
  --input examples/english-demo.md \
  --title "Focused Reading" \
  --keywords "visual rhythm,working memory,re-entry point" \
  --output reading-page.html
```

Open `reading-page.html` in any modern browser.

## English support

English is a first-class rendering path, not a Chinese page with English pasted into it:

- The page switches its interface, typography, and `lang` attribute to English when Latin text predominates.
- Every English word is kept intact and receives a deterministic position in the type rhythm.
- Multi-word keywords such as `visual rhythm` and `working memory` can be used as stronger visual anchors.

The current renderer does not attempt full syntactic phrase parsing for English. The deliberate tradeoff is stable, dependency-light rendering: use `--keywords` to tell it which multi-word ideas should become anchors.

Try the included [English Markdown example](examples/english-demo.md).

## Chinese / 中文说明

这个项目把中文长文、基金申请书或 Markdown 转成可直接打开的专注阅读网页。它不摘要、不改写，而是保留原文结构，通过字体层级、留白和少量视觉锚点帮助重新进入阅读。

中文采用 `jieba` 精确分词，只对完整词语应用样式；科研或课题术语可以逐行加入 `assets/research_terms.txt`，防止专有词被误拆。关键词建议使用 2–4 个汉字，例如「图像副本」「相似异章」「可信度」「人工复核」。

## Codex skill installation

Clone or copy this repository to `~/.codex/skills/reading-rhythm`. In a new Codex task, ask:

> Turn the following research proposal into a focused reading page with visual rhythm: …

The bundled `SKILL.md` contains the interaction workflow and rendering constraints.

## Development

```bash
python3 tests/test_make_reading_page.py
```

Tests cover plain text, English UI selection, GFM tables, escaped pipes, and common Markdown blocks.

## License

Choose a license before the first public release. The repository currently has no license grant.
