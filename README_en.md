<p align="center">
  <a href="README.md"><img src="https://img.shields.io/badge/%E6%96%87%E6%A1%A3-%E4%B8%AD%E6%96%87_Main-6BCB77?style=flat-square" alt="Switch to Chinese README (primary)" /></a>
  <img src="https://img.shields.io/badge/Docs-English-1F6FEB?style=flat-square" alt="doc: en" />
  <a href="https://skills.sh/RePinkert/punctuation-checker/punctuation-checker"><img src="https://skills.sh/b/RePinkert/punctuation-checker?style=flat-square" alt="skills.sh" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="MIT License" /></a>
  <img src="https://img.shields.io/badge/python-3%2B-3776AB?style=flat-square" alt="python 3+" />
  <img src="https://img.shields.io/badge/deps-none-4B8B3F?style=flat-square" alt="zero dependencies" />
</p>

# Punctuation Checker (GB/T 15834—2011)

A Chinese punctuation checker that validates text against the national standard **《标点符号用法》 GB/T 15834—2011**. Usable as a CLI, as a Python library, or packaged as an **Agent Skill**.

> This is the English / LLM-oriented companion to the **primary** Chinese documentation: **[README.md](README.md)**.
> Clause-level coverage matrix: [CLAUSE_COVERAGE.md](CLAUSE_COVERAGE.md). Optimization history: [WORKFLOW.md](WORKFLOW.md).

---

## TL;DR for agents

- **What it does:** finds Chinese punctuation misuse in Chinese text, graded into 3 levels (`错误` ERROR / `警告` WARNING / `建议` SUGGESTION).
- **How to run:** `python punctuation_checker.py <file> [--strict] [--json]`
- **Machine output:** always prefer `--json`; the schema is stable (see below).
- **Requirements:** Python 3, standard library only, no network, no `pip install`.
- **Do not** use it for English punctuation, vertical/typesetting layout, or semantic judgments (sentence-final mood, clause hierarchy).
- **Precision over coverage:** rules that cannot be reliably regex'd are intentionally not implemented.

---

## Requirements

Python 3 (developed/tested on 3.13). Zero third-party dependencies — only `re`, `argparse`, `json`, `dataclasses`, `typing`, `enum`. Runs fully offline.

```bash
git clone https://github.com/RePinkert/punctuation-checker.git
cd punctuation-checker
python punctuation_checker.py --help
```

---

## CLI usage

```bash
python punctuation_checker.py 文档.txt              # basic check
python punctuation_checker.py 文档.txt --strict      # strict mode (adds sentence-end checks)
python punctuation_checker.py 文档.txt -o report.txt # write report to file
python punctuation_checker.py 文档.txt -e gbk        # specify encoding (default utf-8)
python punctuation_checker.py 文档.txt --json        # JSON output (recommended for agents)
python punctuation_checker.py 文档.txt --no-suggestion
```

| Flag | Short | Description |
|---|---|---|
| `file` | — | Path to the text file to check (required) |
| `--strict` | `-s` | Strict mode; enables extra sentence-ending checks |
| `--output` | `-o` | Write the report to a file |
| `--encoding` | `-e` | File encoding (default `utf-8`; auto-fallback utf-8 → gbk → gb2312 → utf-8-sig) |
| `--no-suggestion` | — | Hide fix suggestions |
| `--json` | — | Emit JSON instead of a text report |

Exit behavior: the tool prints a report and does not set a nonzero exit code for detected issues; parse the output (or JSON `level`) rather than relying on exit status.

---

## Library usage

```python
from punctuation_checker import PunctuationChecker, format_report

checker = PunctuationChecker(strict_mode=True)
errors = checker.check("这是一个测试,看看标点检测是否正常。")  # -> List[PunctuationError]

for err in errors:
    print(err.line, err.column, err.level.value, err.error_type, err.message)

print(format_report(errors, show_suggestion=True))
```

`PunctuationError` fields: `line`, `column`, `level` (`ErrorLevel`), `error_type`, `message`, `context`, `suggestion` (optional).

---

## Output formats

### Text report

```text
============================================================
标点符号检查报告 (基于 GB/T 15834-2011)
============================================================
统计: 错误 1 个, 警告 0 个, 建议 0 个

第1行, 第6列 [错误]
  类型: 中英文标点混用
  问题: 中文标点后使用了英文逗号
  上下文: 这是中文句子,用了英文逗号。
  建议: 应使用中文标点「，」
```

### JSON output (`--json`)

```json
{
  "file": "文档.txt",
  "total_errors": 1,
  "errors": [
    {
      "line": 1,
      "column": 6,
      "level": "错误",
      "type": "中英文标点混用",
      "message": "中文标点后使用了英文逗号",
      "context": "这是中文句子,用了英文逗号。",
      "suggestion": "应使用中文标点「，」"
    }
  ]
}
```

`line` is 1-based; `column` is a character offset within the line; `level` is one of `错误` / `警告` / `建议`.

> `context` is the slice around the offending position; it is the whole line when the
> line is short, and is elided with `...` on both ends when the line is long.

---

## What it checks

1. **Chinese/English punctuation mixing** — English `, . : ; ? ! ( )` used in Chinese text (or after Chinese paired punctuation).
2. **Spacing around punctuation** — extra spaces adjacent to Chinese punctuation.
3. **Paired punctuation** — balance of quotes `“”‘’`, brackets `（）【】〔〕`, title marks `「」『』`, book-title marks `《》`.
4. **Repeated punctuation** — `，。；：、）【】》` used more than once.
5. **Ellipsis form** — non-standard `...` / `。。。`, over-long runs (>12 dots), co-occurrence with “等”.
6. **Enumeration comma (顿号)** — followed directly by sentence-final punctuation, followed by “等”-type words, misused for approximate numbers, and in date/ordinal contexts.
7. **Sentence-ending punctuation** — strict mode only; missing end punctuation (skips headings, list items, lines ending in digits/percentages).
8. **Clause-level rules from the standard** — dash/connector forms, ordinals, point placement, quote/bracket nesting, book-title nesting, middle dot, semicolon forms, etc.

### Severity levels

- **`错误` (ERROR)** — clear violations (mixed punctuation, unbalanced pairs, repeated marks, same-shape bracket nesting, wrong 顿号 use).
- **`警告` (WARNING)** — possibly wrong, needs human confirmation (spacing, excessive `？！`, ellipsis form, ordinals, dash form, connectors, middle dot, point placement).
- **`建议` (SUGGESTION)** — advisory extras (missing sentence end, `？！` inside book-title marks, semicolon adjacent to point marks).

---

## Standard coverage

GB/T 15834—2011 has 101 clauseable clauses:

| Status | Count | Meaning |
|---|---|---|
| **R implemented** | **37** | 27 fully + 10 partially |
| **G regex-able, unimplemented** | 4 | Formalizable but not done |
| **H heuristic, unimplemented** | 18 | Needs word lists/context (e.g., “说/道” followed by colon) |
| **S semantic** | 27 | Not regex-expressible (sentence mood, clause hierarchy) |
| **T typography/layout** | 14 | Glyphs/spacing/vertical text — out of scope for plain text |

i.e. **55 clauses (54%)** are regex-expressible; **37** are currently covered. Full matrix: [CLAUSE_COVERAGE.md](CLAUSE_COVERAGE.md).

---

## Evaluation

```bash
# Synthetic mutation evaluation (447 cases, 10 mutation operators)
python evaluate.py

# External corpora (stdlib only; downloads data over the network)
python fetch_corpus.py
python evaluate_external.py
```

- **Synthetic:** F1 = 1.0 / Precision = 1.0 / Recall = 1.0 (447 cases; 7 error types fully covered).
- **External:**
  - UD Chinese-GSD false-positive rate: **0.30%** (6/2000)
  - UD Chinese-GSD extended mutation F1: **0.9984**
  - Real-error detection recall (shibing624/chinese_text_correction): **41.87%** (587/1,402)

Recall on real errors is bounded because most true errors are semantic. See [WORKFLOW.md](WORKFLOW.md).

---

## Using it as an Agent Skill

This project is publishable to [skills.sh](https://www.skills.sh/) and follows the Agent Skills specification. The skill directory contains a `SKILL.md` with this frontmatter:

```yaml
---
name: punctuation-checker           # lowercase, hyphens, ≤64 chars
description: 检查中文文本的标点符号用法是否符合 GB/T 15834—2011，检测中英文标点混用、配对缺失、重复标点、省略号/顿号误用等，并按 错误/警告/建议 三级输出，支持文本或 JSON 报告。适用于中文稿件校对与写作流水线中的标点检查。
license: MIT
compatibility: Python 3，仅需标准库，离线可用
---
```

Discovery: a `SKILL.md` at the repo root or at `skills/<name>/` is auto-discovered by `npx skills add owner/repo`; the `description` determines when the agent loads the skill.

Operational contract for agents:

1. **Run:** `python punctuation_checker.py <file> [--strict] [--json]`.
2. **Consume:** prefer `--json`; fix `错误` first, then review `警告`/`建议` manually.
3. **Line-based:** cross-line paired punctuation is not detected; pre-split text by sentence if needed.
4. **Avoid FPs:** disable `--strict` for news headlines/summaries (missing sentence-end marks are expected there).
5. **Scale:** for very large files, process in chunks and merge the JSON results.

Install (once published):

```bash
npx skills add RePinkert/punctuation-checker
```

---

## Caveats

1. Encoding is auto-detected (UTF-8 / GBK / GB2312 / UTF-8-SIG); override with `-e`.
2. Lines starting with `#` or `//` and empty lines are skipped.
3. Sentence-ending checks run only under `--strict`, and skip headings, list items, and lines ending in digits/percentages.
4. English-bracket detection fires only when the bracket content is **pure Chinese**; mixed content (e.g. `人民币(约500万美元)`) is not flagged.
5. **Line-by-line processing** — cross-line unbalanced pairs are not detected.
6. On news headlines/summaries, missing sentence-ending punctuation is expected (≈94% of news-corpus FPs); disable `--strict`.
7. Semantic rules (sentence mood, clause hierarchy) are not regex-expressible and are not covered; precision is prioritized over coverage.
8. ~41.87% recall on real error corpora; the rest need human review.

---

## Documents

| File | Description |
|---|---|
| [README.md](README.md) | Primary Chinese documentation |
| [README_en.md](README_en.md) | This file (English / LLM-oriented) |
| [SKILL.md](SKILL.md) | Agent Skill definition and usage contract |
| [CLAUSE_COVERAGE.md](CLAUSE_COVERAGE.md) | GB/T 15834—2011 clause coverage matrix |
| [WORKFLOW.md](WORKFLOW.md) | Optimization history and external evaluation results |
| [program.md](program.md) | autoresearch experiment workflow notes |
| [LICENSE](LICENSE) | MIT |

## License

[MIT](LICENSE)
