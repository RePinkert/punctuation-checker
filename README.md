<p align="center">
  <img src="https://img.shields.io/badge/%E6%96%87%E6%A1%A3-%E4%B8%AD%E6%96%87_Main-6BCB77?style=flat-square" alt="doc: zh-CN main" />
  <a href="README_en.md"><img src="https://img.shields.io/badge/English-README-1F6FEB?style=flat-square" alt="Switch to English README" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue?style=flat-square" alt="MIT License" /></a>
  <img src="https://img.shields.io/badge/python-3%2B-3776AB?style=flat-square" alt="python 3+" />
  <img src="https://img.shields.io/badge/%E4%BE%9D%E8%B5%96-%E9%9B%B6%E4%BE%9D%E8%B5%96-4B8B3F?style=flat-square" alt="zero dependencies" />
</p>

# 标点符号用法检测（GB/T 15834—2011）

一个基于《标点符号用法》（GB/T 15834—2011）的**中文标点符号检查器**，可用作命令行工具、Python 库，或打包为 **Agent Skill** 供大模型调用。

> 规则已逐条对照标准原文核实，覆盖矩阵见 [CLAUSE_COVERAGE.md](CLAUSE_COVERAGE.md)。
> 完整优化历史与外部评估见 [WORKFLOW.md](WORKFLOW.md)。
> 英文/LLM 阅读版见 [README_en.md](README_en.md)。

---

## 特性速览

- **零依赖**：仅用 Python 标准库（`re`/`argparse`/`json`），离线可用，无需 `pip install`。
- **两种用法**：命令行（CLI）或作为 Python 库导入。
- **三级提示**：错误 / 警告 / 建议，区分“必然违规”与“需人工确认”。
- **JSON 输出**：便于 Agent 或流水线消费。
- **可作为 Skill**：附带 `SKILL.md` 前置元数据与调用约定，见下文「作为 Agent Skill 使用」。

---

## 何时使用（Skill 激活场景）

当任务涉及**中文文本的标点校对、规范检查、错误定位**时启用本技能，例如：

- 校对/审校中文稿件、公众号文章、新闻、论文，检查标点是否符合 GB/T 15834—2011；
- 定位中文文本中的中英文标点混用、引号/书名号不配对、省略号/顿号误用等问题；
- 在写作流水线或 Agent 中，作为“写完中文后自动跑一遍标点检查”的步骤。

**不适用**：英文标点排版、竖排/字形/字距问题、语义层面的语气与分句判断（见「边界与注意事项」）。

---

## 安装

无依赖，直接克隆或下载后使用：

```bash
git clone https://github.com/RePinkert/punctuation-checker.git
cd punctuation-checker
python punctuation_checker.py --help
```

要求：Python 3（开发与测试环境为 3.13）。

---

## 使用方法

### 命令行

```bash
# 基本用法
python punctuation_checker.py 文档.txt

# 严格模式（额外启用句末标点缺失等建议级检查）
python punctuation_checker.py 文档.txt --strict

# 输出到文件
python punctuation_checker.py 文档.txt -o 报告.txt

# 指定编码（默认 utf-8；无法解码时会自动回退 utf-8 → gbk → gb2312 → utf-8-sig）
python punctuation_checker.py 文档.txt -e gbk

# JSON 输出（供程序/Agent 消费）
python punctuation_checker.py 文档.txt --json

# 不显示修改建议
python punctuation_checker.py 文档.txt --no-suggestion
```

| 参数 | 简写 | 说明 |
|---|---|---|
| `file` | — | 待检查的文本文件路径（必填） |
| `--strict` | `-s` | 严格模式，启用句末标点等额外建议 |
| `--output` | `-o` | 将报告写入文件 |
| `--encoding` | `-e` | 指定文件编码（默认 `utf-8`） |
| `--no-suggestion` | — | 不显示修改建议 |
| `--json` | — | 以 JSON 格式输出结果 |

### 作为 Python 库

```python
from punctuation_checker import PunctuationChecker, format_report

checker = PunctuationChecker(strict_mode=True)
text = "这是一个测试,看看标点检测是否正常。"
errors = checker.check(text)          # -> List[PunctuationError]

for err in errors:
    print(f"第{err.line}行 第{err.column}列 [{err.level.value}] {err.error_type}: {err.message}")

# 或直接生成文本报告
print(format_report(errors, show_suggestion=True))
```

`PunctuationError` 字段：`line`、`column`、`level`、`error_type`、`message`、`context`、`suggestion`（可选）。

---

## 输出格式

### 文本报告示例

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

### JSON 输出结构（`--json`）

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

> `line` 为 1 起始的行号；`column` 为该行内的字符偏移；`level` 取值为 `错误` / `警告` / `建议`。
> `context` 为出错位置前后的片段：以出错列为中心截取，该行较短时为整行原文，过长时两端用 `...` 省略。

---

## 检查项

1. **中英文标点混用** — 中文文本（含中文配对标点后）使用英文 `, . : ; ? ! ( )`。
2. **标点空格** — 中文标点前后多余空格。
3. **配对标点** — 引号 `“”‘’`、括号 `（）【】〔〕`、篇名号 `「」『』`、书名号 `《》` 是否成对。
4. **标点重复** — `，。；：、）【】》` 等不应重复的标点。
5. **省略号格式** — 非标准形式 `...`、`。。。`，以及省略号叠用超限（>12 点）、与“等”共现。
6. **顿号使用** — 顿号后直接接句末标点、顿号后接“等”类词、概数误用顿号、日期/序次语境。
7. **句末标点** — 严格模式下检测句末缺失（跳过标题、列表项、以数字/百分比结尾的行）。
8. **GB/T 条款形式化规则** — 破折号/连接号形式、序次语、点号位置、引号与括号嵌套、书名号嵌套、间隔号、分隔号等窄模式规则。

### 错误等级

- **错误** — 明显违反规范（中英文标点混用、配对缺失、重复标点、括号同形嵌套、顿号误用）。
- **警告** — 可能有问题，需人工确认（标点空格、问号/叹号连用过多、省略号格式、序次语、破折号形式、连接号、间隔号、点号位置）。
- **建议** — 额外参考（句末标点缺失、书名号内 `？！`、分隔号前贴点号等）。

---

## 规则覆盖范围

按 GB/T 15834—2011 可分则条款统计（共 101 条）：

| 状态 | 数量 | 说明 |
|---|---|---|
| **R 已实现** | **37** | 27 条完全实现 + 10 条部分实现 |
| **G 可 regex 未实现** | 4 | 可形式化但尚未实现 |
| **H 启发式未实现** | 18 | 需词表/上下文，如“说”“道”后用冒号 |
| **S 语义类** | 27 | 原则不可 regex 化（句末语气、分句层次等） |
| **T 排版字形** | 14 | 字位/字距/竖排，纯文本不可判（out of scope） |

即 **55 条（54%）** 条款可形式化为 regex 规则，目前覆盖其中 37 条。逐条矩阵见 [CLAUSE_COVERAGE.md](CLAUSE_COVERAGE.md)。

---

## 评估

项目包含合成变异评估（`evaluate.py`）与外部语料评估（`fetch_corpus.py` + `evaluate_external.py`）。

```bash
# 合成变异评估（447 用例，10 个变异算子）
python evaluate.py

# 外部语料评估（仅用标准库，无需安装第三方包；需联网下载语料）
python fetch_corpus.py
python evaluate_external.py
```

**合成评估**：F1 = 1.0 / Precision = 1.0 / Recall = 1.0（447 用例，7 类错误全覆盖）。

**外部语料评估**：

| 指标 | 值 |
|---|---|
| UD Chinese-GSD 误报率 | **0.30%**（6/2000） |
| UD Chinese-GSD 扩展变异 F1 | **0.9984** |
| 真实错误检出率（shibing624/chinese_text_correction） | **41.87%**（587/1,402） |

误报率优先于覆盖率：未能可靠形式化的规则宁可不做。历史与实验记录见 [WORKFLOW.md](WORKFLOW.md)。

---

## 作为 Agent Skill 使用

本项目可发布为 [skills.sh](https://www.skills.sh/) / Agent Skills 标准的技能。技能目录以 `SKILL.md` 描述，并遵循如下前置元数据（Agent Skills 规范）：

```yaml
---
name: punctuation-checker           # 小写、连字符、≤64 字符
description: 检查中文文本的标点符号用法是否符合 GB/T 15834—2011，检测中英文标点混用、配对缺失、重复标点、省略号/顿号误用等，并按 错误/警告/建议 三级输出，支持文本或 JSON 报告。适用于中文稿件校对与写作流水线中的标点检查。
license: MIT
compatibility: Python 3，仅需标准库，离线可用
---
```

技能发现：仓库根目录或 `skills/<name>/` 下的 `SKILL.md` 会被 `npx skills add owner/repo` 自动发现；`description` 决定 Agent 何时加载该技能。

给 Agent / 使用者的调用约定：

1. **执行检查**：`python punctuation_checker.py <文件> [--strict] [--json]`。
2. **消费结果**：需要程序化处理时优先用 `--json`，按 `level` 分级处理（先修“错误”，再人工确认“警告/建议”）。
3. **逐行处理**：检查器按行扫描，无法检测跨行的配对标点；必要时先按语义分行。
4. **控制误报**：新闻标题/摘要应关闭 `--strict`（句末缺标点在该场景属预期）。
5. **性能**：文本很大时可分块后合并 JSON 结果。

安装（发布后）：

```bash
npx skills add RePinkert/punctuation-checker
```

---

## 边界与注意事项

1. 自动检测文件编码（UTF-8 / GBK / GB2312 / UTF-8-SIG），`-e` 可手动指定。
2. 以 `#` 或 `//` 开头的代码行与空行会被跳过。
3. 句末标点检查仅在 `--strict` 下启用，且跳过标题、列表项、以数字/百分比结尾的行。
4. 英文括号检测仅在括号内为**纯中文**时触发；中英混合内容（如 `人民币(约500万美元)`）不误报。
5. **逐行处理**，不检测跨行配对标点（引号第 1 行开、第 3 行关的场景需自行预处理）。
6. 新闻标题/摘要上，句末标点缺失属预期行为（占新闻语料误报的 94%），建议关闭 `--strict`。
7. 语义类规则（句末语气、分句层次）本质无法 regex 化，当前不覆盖；误报率优先于覆盖率。
8. 检出“真实错误”语料时召回约 41.87%，因多数真实错误属语义类，需人工复核。

---

## 文档索引

| 文件 | 说明 |
|---|---|
| [README.md](README.md) | 本文件（中文主文档） |
| [README_en.md](README_en.md) | 英文/LLM 阅读版 |
| [SKILL.md](SKILL.md) | Agent Skill 定义与调用约定 |
| [CLAUSE_COVERAGE.md](CLAUSE_COVERAGE.md) | GB/T 15834—2011 条款形式化覆盖矩阵 |
| [WORKFLOW.md](WORKFLOW.md) | 完整优化历史与外部评估结果 |
| [program.md](program.md) | 自动优化实验流程（autoresearch）说明 |
| [LICENSE](LICENSE) | MIT |

## 许可

[MIT](LICENSE)
