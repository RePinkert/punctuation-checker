---
name: punctuation-checker
description: 检查中文文本的标点符号用法是否符合国家标准 GB/T 15834—2011。当需要校对/审校中文稿件、公众号文章、新闻、论文的标点，定位中英文标点混用、引号/书名号/括号不配对、标点重复、省略号或顿号误用、句末标点缺失等问题时使用。也用于中文写作流水线或 Agent 中「写完中文后自动跑一遍标点检查」的步骤。Checks Chinese text for punctuation usage per GB/T 15834—2011 and reports issues graded as 错误/警告/建议 (ERROR/WARNING/SUGGESTION) in text or JSON.
license: MIT
compatibility: Requires Python 3 and no third-party packages. Runs fully offline. Designed for Chinese-language (GB/T 15834—2011) text; not for English punctuation or vertical/typographic layout.
metadata:
  standard: GB/T 15834-2011
  language: zh-CN
  entrypoint: punctuation_checker.py
---

# 中文标点符号检查（GB/T 15834—2011）

A zero-dependency, offline checker that validates Chinese punctuation against the
national standard **GB/T 15834—2011**, and grades every finding into three levels.

## When to Use

Activate this skill when the task is to **find punctuation problems in Chinese text**:

- Proofread / copy-edit Chinese copy: 稿件、公众号文章、新闻、论文、字幕.
- Locate issues such as Chinese/English punctuation mixing, unbalanced quotes or
  book-title marks, repeated punctuation, malformed ellipses, misused 顿号, or a
  missing sentence-ending mark.
- Insert a punctuation check into a Chinese writing pipeline or agent workflow
  (e.g. "after generating Chinese text, run a punctuation pass").

**Do NOT use for:** English punctuation; vertical typesetting, glyph/spacing layout;
or semantic judgments such as sentence-final mood or clause hierarchy (see Caveats).

## Quick Start

```bash
# Human-readable report
python punctuation_checker.py 文档.txt

# Machine-readable (preferred when you need to act on results)
python punctuation_checker.py 文档.txt --json
```

`--strict` enables extra sentence-ending checks (see Caveats). Run `--help` for the
full flag list. The script takes a **file path**, not stdin.

## Options

| Flag | Short | Description |
|---|---|---|
| `file` | — | Path to the text file to check (required) |
| `--strict` | `-s` | Strict mode; enables extra sentence-ending (SUGGESTION) checks |
| `--output` | `-o` | Write the report to a file |
| `--encoding` | `-e` | File encoding (default `utf-8`; auto-fallback utf-8 → gbk → gb2312 → utf-8-sig) |
| `--no-suggestion` | — | Hide fix suggestions in text output |
| `--json` | — | Emit JSON instead of a text report |

The tool prints a report and does **not** use a nonzero exit code for detected
issues. Parse the output (or the JSON `level`) instead of relying on exit status.

## How to Interpret Results

Every finding has a `level`:

- **错误 (ERROR)** — a clear violation. Safe to auto-fix: Chinese/English punctuation
  mixing, unbalanced paired punctuation, repeated punctuation, same-shape bracket
  nesting, wrong 顿号 usage.
- **警告 (WARNING)** — possibly wrong, needs human confirmation: spacing around
  punctuation, excessive `？！`, ellipsis form, ordinals, dash/connector form, middle
  dot, point placement.
- **建议 (SUGGESTION)** — advisory: missing sentence-ending punctuation, `？！` inside
  book-title marks, semicolon adjacent to point marks.

When you find yourself wanting to auto-correct everything, **only auto-correct 错误**.
Keep 警告/建议 as review items.

## JSON Schema (`--json`)

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

`line` is 1-based; `column` is a character offset within the line; `level` ∈
`错误` / `警告` / `建议`; `type` is a category string; `suggestion` may be absent.
`context` is the slice around the offending position — the whole line when short,
elided with `...` on both ends when long.

## Library API

```python
from punctuation_checker import PunctuationChecker, format_report

errors = PunctuationChecker(strict_mode=True).check("这是一个测试,看看是否正常。")
for e in errors:
    print(e.line, e.column, e.level.value, e.error_type, e.message)
print(format_report(errors, show_suggestion=True))
```

## Operating Rules

1. **Prefer `--json`** whenever you need to act programmatically; iterate `errors`.
2. **Fix 错误 first**, then surface 警告/建议 for human review.
3. **Line-based processing** — cross-line unbalanced pairs are NOT detected. If the
   text is one long paragraph with quotes spanning lines, split by sentence first.
4. **Avoid false positives on headlines** — news headlines/summaries intentionally
   omit sentence-ending marks; run WITHOUT `--strict` on such text.
5. **Scale** — for very large files, process in chunks and merge the JSON results.
6. **Code lines are skipped** automatically (lines starting with `#` or `//`, and
   empty lines).

## Caveats

- English-bracket detection fires only when the bracket content is pure Chinese;
  mixed content (e.g. `人民币(约500万美元)`) is not flagged.
- Semantic rules (sentence mood, clause hierarchy) are not regex-expressible and are
  not covered. Recall on real error corpora is ~42%; the rest need human review.
- Detection is precision-first: rules that can't be reliably regex'd are intentionally
  omitted. See [CLAUSE_COVERAGE.md](CLAUSE_COVERAGE.md) for the full clause matrix.

## Reference

- Full documentation (Chinese): [README.md](README.md)
- English / LLM-oriented README: [README_en.md](README_en.md)
- Clause coverage matrix: [CLAUSE_COVERAGE.md](CLAUSE_COVERAGE.md)
- Optimization history & external evaluation: [WORKFLOW.md](WORKFLOW.md)
