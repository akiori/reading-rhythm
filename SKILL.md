---
name: reading-rhythm
description: Create a calm, attention-supportive HTML reading page from Chinese or mixed Chinese-English prose or Markdown, including responsive tables, lists, quotes, and code blocks. Use when the user asks to turn a passage, draft, long article, technical document, report, pasted text, or Markdown document into a focused reading experience with visual hierarchy, varied word emphasis, Songti Chinese typography, and an elegant serif English font.
---

# Reading Rhythm / 阅读节律

将用户提供的文字转成一个可直接打开的单页 HTML。交付成品链接，不要只提供代码片段。

## 工作流

1. 保持用户的段落和论证顺序；不要改写原意。
2. 选出 5–12 个确实承载论证的词或短语，每项控制在 2–4 个汉字，例如「核心问题」「因果机制」「关键变量」。不要把一整句或 5 字以上的长概念标成重点。
3. 前 2–3 个为最强视觉锚点，接着 3–4 个为中等重点，其余为轻提示。脚本使用随 skill 安装的 `jieba` 精确模式先做确定性中文分词；只把完整词语应用视觉样式，绝不按字拆开词。单字虚词保持普通样式。将短语用逗号传给脚本的 `--keywords`。
4. 输入是 Markdown 时直接传入 `.md`，不要先用 Pandoc 转成 plain text，否则 pipe table 会丢失结构。脚本原生渲染 GFM pipe tables、heading、list、blockquote 和 fenced code block；普通纯文本仍保持兼容。
5. 运行脚本，输出到当前 task 的 `outputs/`。标题简洁，默认从正文或用户说明中推断。

```bash
python3 /Users/thor/.codex/skills/reading-rhythm/scripts/make_reading_page.py \
  --input work/source.txt \
  --title "阅读标题" \
  --keywords "关键结论,核心概念,实际案例,后续行动,重要限制,下一步" \
  --output outputs/reading-page.html
```

也可用 `--text` 传入短文字。生成后用浏览器或本地预览检查：中文应显示为 Songti/STSong，英文为 Charter；核心短语必须明显但不刺眼；一屏不应出现大面积加粗。如有表格，确认生成了 `<table>` 而不是连字符；宽表应在单元内横向滚动，首列保持可见。

## 排版约束

- 优先保留留白、较大行距和单栏。不要使用高饱和背景、自动滚动、闪烁或复杂动画。
- 一个自然段是一个阅读单元。必要时仅按完整句子拆分超长段落，不要切断中文短语。
- 表格整体作为一个阅读单元。保留表头、行列对齐和原始数值；不把数据行转成普通段落，不在单元外造成页面横向滚动。
- 对 2–4 字的完整词语持续产生克制的字号、字重变化；不要把「方法部分」切成「法部分」或把「什么独特」切成「么独」。正文的字号起伏保持在约 ±6%，以接近稳定的基线为主；层次主要由少量中等偏粗词语形成，最细字不能被压成灰字，最粗字也不能让其余文字失去可读性。
- 对用户反复出现的专有词、产品名或领域术语，在 `assets/custom_terms.txt` 每行追加一个词；脚本会把它交给 jieba 的用户词典，防止专有词被错误拆开。
- 生成页面自带 `A− / A+` 和「聚焦重点」开关；不要为简单阅读再引入登录、菜单或外部依赖。
