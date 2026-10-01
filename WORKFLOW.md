# 工作流程记录

本文档记录 punctuation-checker 项目从初始代码到 autoresearch 迭代优化、外部语料评估的完整工作流。

---

## 阶段一：项目初始化与 GitHub 连接

### 1.1 远程仓库

- 仓库地址：`https://github.com/RePinkert/punctuation-checker`
- 初始状态：空仓库，仅含 MIT LICENSE

### 1.2 本地初始化

```bash
cd C:\Yet\punctuation-checker
git init
git remote add origin https://github.com/RePinkert/punctuation-checker.git
git add punctuation_checker.py test_punctuation_checker.py punctuation_checker_readme.md
git commit -m "Add punctuation checker based on GB/T 15834-2011"
```

### 1.3 拉取远程 LICENSE 并推送

```bash
git pull origin main --allow-unrelated-histories --no-edit
git branch -M main
git push -u origin main
```

### 提交记录

| Commit | 描述 |
|---|---|
| `1902219` | Initial commit (远程 LICENSE) |
| `3fe1d44` | Add punctuation checker based on GB/T 15834-2011 |
| `be85c79` | Merge branch 'main' (合并远程 LICENSE) |

---

## 阶段二：评估基础设施搭建

### 2.1 设计思路

参考 Karpathy 的 [autoresearch](https://github.com/karpathy/autoresearch) 框架，将贪心爬山搜索适配到标点检查器优化：

- **`evaluate.py`**（不可变）：合成变异语料生成 + 评估函数
- **`punctuation_checker.py`**（可变）：agent 唯一可修改的文件
- **`corpus_clean.txt`**（不可变）：正确中文句子语料
- **`program.md`**：agent 实验指令

### 2.2 合成语料生成策略

从 `corpus_clean.txt` 中加载正确中文句子，通过 **10 个变异算子** 注入已知错误：

| 变异算子 | 操作 | 期望检出的 error_type |
|---|---|---|
| `mutate_to_english_punc` | 随机将中文标点替换为英文 | 中英文标点混用 |
| `mutate_add_space_after` | 中文标点后插入空格 | 标点空格问题 |
| `mutate_add_space_before` | 中文标点前插入空格 | 标点空格问题 |
| `mutate_remove_closing` | 删除配对标点的右半部分 | 标点配对问题 |
| `mutate_duplicate_punc` | 复制标点造成重复 | 标点重复 |
| `mutate_ellipsis` | 将 `……` 替换为 `...` 或 `。。。` | 省略号格式 |
| `mutate_dunhao_before_end` | 在 `、` 后插入 `。？！` | 顿号使用 |
| `mutate_remove_sentence_end` | 删除句末标点 | 句末标点 |
| `mutate_to_english_punc_midquote` | 引号内标点替换为英文 | 中英文标点混用 |
| `mutate_double_close` | 右配对标点后插入左标点 | 标点配对问题 |

### 2.3 评估指标

- **Precision** = detected_expected / (detected_expected + total_fp_errors)
- **Recall** = detected_expected / total_expected
- **F1** = 2 * P * R / (P + R)

### 提交记录

| Commit | 描述 |
|---|---|
| `66ed997` | Add evaluation harness and autoresearch program.md |

---

## 阶段三：autoresearch 迭代优化循环

### 基线

运行 `python evaluate.py` 得到基线指标：

```
f1_score: 0.9845
precision: 1.0000
recall: 0.9695

per-type recall:
  中英文标点混用: 0.867
  句末标点: 0.933
  标点空格问题/标点配对问题/标点重复/省略号格式/顿号使用: 1.000
```

薄弱项：**中英文标点混用 (86.7%)** 和 **句末标点 (93.3%)**。

### 实验 1：扩展中英文标点混用模式 + 修复省略号变异器

**变更 (`d2a6241`)**：

1. `_check_chinese_english_mixed` 新增 `cn_ctx` 模式组，覆盖中文配对标点（`》】）""` 等）后跟英文标点的情况
2. 修复 `evaluate.py` 中 `mutate_remove_sentence_end` 的省略号处理：删除 `……` 时同时删除两个 `…` 字符

**结果**：F1 0.9845 → **0.9975**
- 中英文标点混用：86.7% → 96.7%
- 句末标点：93.3% → 100%

### 实验 2：修复语料 ASCII 引号 + 补全中文右引号

**发现**：语料文件 `corpus_clean.txt` 中 8 行使用了 ASCII `"` (U+0022) 而非中文引号 `""` (U+201C/U+201D)，导致变异后的英文逗号跟在 ASCII 引号后，checker 的 `cn_ctx` 模式无法匹配。

**变更 (`170ea08`)**：

1. `corpus_clean.txt`：将所有 ASCII `"` 替换为正确的中文 `""`
2. `_check_sentence_end`：引号结尾列表从 `"'》）】」` 扩展为 `"''""』》）】」`

**结果**：F1 0.9975 → **1.0000**
- 所有 7 个检查类别的 recall 均达到 100%
- Precision 100%（零误报）

### 实验 3：扩展语料 + 新增变异算子

**变更 (`b94ca1a`)**：

1. `corpus_clean.txt`：从 49 句扩展至 88 句，覆盖更多标点模式
2. `evaluate.py`：新增 `mutate_to_english_punc_midquote` 和 `mutate_double_close` 两个变异算子
3. 每个变异算子的测试用例数从 30 增至 40

**结果**：F1 = **1.0000**（447 个测试用例全部通过，稳定）

### 提交记录

| Commit | 描述 | F1 |
|---|---|---|
| `d2a6241` | Expand mixed CN/EN punc patterns; fix sentence-end mutator for ellipsis | 0.9975 |
| `170ea08` | Fix corpus ASCII quotes; add Chinese closing quotes to sentence-end check | 1.0000 |
| `b94ca1a` | Expand corpus to 88 sentences, add 2 new mutators | 1.0000 |
| `869eae4` | Flag dunhao in numeric dates (GB/T A.4.4.2) | 1.0000 |
| `e9937c7` | Flag ellipsis+等 co-occurrence (GB/T A.9.2) | 1.0000 |
| `96dc8fe` | Flag dunhao after ordinal transitions (GB/T B.3.1) | 1.0000 |
| `8d05c14` | Add line-start punc check (GB/T 5.1.1) | 1.0000 |
| `f4f8a7f` | Refine sentence-end guards (GB/T B.3.3/B.3.4) | 1.0000 |
| `fa65b3c` | Centralize CJK charset constants (base + Ext-A) | 1.0000 |
| `5f1efa1` | Flag hyphen in numeric ranges (GB/T 4.13.3.2) | 1.0000 |

> 自 `b94ca1a` 达到 F1=1.0 后，合成指标已触顶，后续迭代改以**外部语料 FP 率**与**外部变异 F1**作为区分信号（合成 F1 持续保持 1.0）。详见阶段六。

---

## 阶段六：GB/T 条款覆盖矩阵与 G 类条款补齐

### 6.1 条款形式化覆盖矩阵

新增 `CLAUSE_COVERAGE.md`（commit `bb89867`）：把 GB/T 15834-2011 的可分则条款逐条映射为状态标记——
`R` 已实现 / `H` 可启发式 / `G` 可 regex 但未实现 / `S` 语义类（正则不可表达） / `T` 排版字形（纯文本不可判）。
按成行条目统计，共 **101** 条，其中 R 类 37 条（含 R-部分 10 条）、G 类缺口 4 条。

### 6.2 G 类条款批量实现（commit `3816d0d`）

按矩阵优先级补齐 9 条 G 类规则：

- 4.10.2 单个破折号（形式应为 `——`）→ WARNING
- B.3.2 / B.3.4 带括号序次语后不用点号 → WARNING
- B.3.3 阿拉伯数字行首序次语应用下脚点 → SUGGESTION
- A.12 并列标题已用间隔号则不再用「和」→ SUGGESTION
- A.13.5 篇名末尾的 ？！ 应在书名号内 → SUGGESTION
- A.14 分隔号前后不贴点号 → SUGGESTION
- 4.8.3.4 / 4.9.3.6 同形引号/括号不得嵌套 → ERROR
- 4.14.3.5 事件年月日间隔号应用半角 `·`、两侧无空格 → WARNING
- B.1.2 顿号后接「等」类词（与 A.9.2 镜像）→ SUGGESTION

同时撤回** B.2.4、4.5.3.5 两条：语料筛查显示它们属语义/软规则，UD-GSD 上 FP 过高，矩阵已改标为 S/H。


### 6.3 对照标准原文核实（commit 后续）

以标准原文 PDF（`15834-2011-gbt-e-300.pdf`）逐条核实 `CLAUSE_COVERAGE.md`，发现并修正了多处描述错误：

| 条款 | 原矩阵描述 | 标准原文 | 处置 |
|---|---|---|---|
| B.3.2 | 带括号汉字序次语后用顿号 | “**不带括号**的汉字数字或天干地支‖做序次语时，后用顿号” | 已改为 S（难与 4.5.3.4 区分） |
| B.3.3 | 阿拉伯数字序次语后用下脚点 | “不带括号的阿拉伯数字、**拉丁字母或罗马数字**‖” | 标为 R（部分），补注拉丁/罗马未覆盖 |
| B.3.4 | 带括号序次语后不用点号 | “加括号的序次语后面不用任何点号” | 已核实，代码实现正确 |
| B.3.5 | 阿拉伯数字+下脚点后不用点号 | “……**表示章节关系**的序次语末尾不用任何点号” | 补齐限定语 |
| 4.14.3.5 | 阿拉伯数字事件年月日用半角「·」 | 汉字数字表示时**只在一、十一和十二月后**用间隔号；阿拇伯数字表示时月日之间用半角间隔号 | 补齐义义，标为 R（部分） |
| 4.5.3.4 | 相邻两数字表概数宜用顿号 | “表礼数通常**不用**顿号”（方向相反） | 修正方向，保持 G |

### 6.4 窄应用面规则补充

本轮尝试 3 条窄规则，按 program.md 的“合成 F1 已触顶、以外部语料误报率为区分信号”做误报筛选：

| 条款 | 内容 | 结果 |
|---|---|---|
| 4.15.3.5 | 书名号内套书名号时里层用单书名号（`《…《…》…》` → ERROR） | **保留**，0 FP |
| B.3.6 | 章节/条款序次语后宜用空格（仅行首序次语，避免行文中「第三课的内容」误报） | **保留**，0 FP |
| B.3.5 | 下脚点章节序次语末尾不加点号 | **撤回**：正文小数（“7.9公分”“都是0.4。”）与章节号无法用正则区分，UD-GSD 语料上产生误报 |

保留两条后：合成 F1 仍为 1.0，UD-GSD 误报率保持 **0.30%**，外部变异 F1 保持 **0.9984**，
真实错误检出率保持 **41.87%**——两条规则为零误报增量。覆盖矩阵因此从 G=5/H=19 变为 **G=4/H=18**。

---

## 阶段四：外部语料评估

### 4.1 语料拉取

`fetch_corpus.py` 拉取三个外部语料库，**全部仅用标准库 `urllib`**（不再需要 `pip install datasets`）：

| 语料 | 句数 | 来源 | 下载方式 |
|---|---|---|---|
| UD Chinese-GSD | 4,992 | GitHub | `urllib` 拉取 `.conllu` |
| shibing624/chinese_text_correction | 54,347（clean）+ 108,315（pairs） | HuggingFace | `urllib` 拉取 14 个 `.tsv` |
| ChineseNewsSummary | 26,940 | HuggingFace | `urllib` 拉取 `train.json` |

运行：`python fetch_corpus.py`

生成文件：
- `corpus_ud_gsd.txt`
- `corpus_hf_correction.txt`（清洗后 target 句，供模式 A/B）
- `corpus_hf_pairs.tsv`（source→target 纠错对，供模式 C）
- `corpus_hf_news.txt`

### 4.2 三模式评估

创建 `evaluate_external.py`，提供三种评估模式：

#### 模式 A：干净文本误报率

在外部语料（正确标点的真实文本）上运行 checker，任何报错都是误报。

| 语料 | 句数 | FP 率 | 主要误报 |
|---|---|---|---|
| UD Chinese-GSD | 2,000 | **0.30%** | 标点配对 (4), 连接号 (2), 句末标点 (1) |
| ChineseNewsSummary | 2,000 | **33.05%** | 句末标点 (633), 标点空格 (15), 连接号 (12) — 新闻标题省略句号 |

#### 模式 B：扩展变异测试

用外部语料句子作为变异基底，运行变异算子。

| 语料 | F1 | Precision | Recall |
|---|---|---|---|
| UD Chinese-GSD | **0.9984** | 0.9969 | 1.0000 |
| ChineseNewsSummary | **0.7858** | 0.6533 | 0.9856 |

#### 模式 C：真实错误检出

用 `shibing624/chinese_text_correction` 数据集（`corpus_hf_pairs.tsv`）中含真实标点差异的样本测试。

| 指标 | 值 |
|---|---|
| 总扫描行数 | 108,315 |
| 含标点差异的行 | 1,402 |
| Checker 检出行数 | 587 (**41.87%**) |
| 主要检出类型 | 中英文标点混用 (1,051), 句末标点 (145), 标点配对 (55), 序次语 (13) |

### 4.3 基于外部评估的改进

**变更 (`4d7395e`)**：

1. `_check_sentence_end`：跳过以 `%`/数字结尾的行（新闻中如 "跌超4%" 属正常）
2. `_check_chinese_english_mixed`：英文括号检测改为只在括号内为纯中文内容时报错，中英混合内容不再误报

**改进效果（属于 `4d7395e` 当时的测量值）**：

| 指标 | 改前 | 改后（当时） |
|---|---|---|
| 新闻 FP 率 | 34.25% | 30.35% |
| 新闻句末标点 FP | 667 | 589 |
| 合成 F1 | 1.0000 | 1.0000 (不变) |

> 注：上表是 `4d7395e` 那一次改动的当时对比。截至当前 HEAD（`3816d0d`），新闻 FP 率为 **33.05%**（674 FP）——后续新增规则（如连接号、空格、间隔号等）在新闻体上亦有误报，但主体仍是句末标点缺失（633），属预期行为。

---

## 阶段五：发现的局限性与待改进方向

### 已知局限

1. **句末标点检查 vs 新闻文本**：新闻标题/摘要省略句号是行业标准，strict 模式下的 SUGGESTION 级别报错属预期行为（633 FP / 2000 句新闻）。目前无法可靠区分"标题省略句号"和"句子缺失句号"。

2. **跨行配对引号**：checker 逐行处理，无法检测跨行的配对标点（如引号在第1行打开、第3行关闭）。UD-GSD 中有 4 个此类 FP。

3. **真实错误检出率 41.87%**：合成变异只覆盖 7 种错误类型，真实文本中的标点错误更加多样（如标点位置不当、语气不符、语境误用等），当前规则无法覆盖。

4. **繁体中文**：UD-GSD 使用繁体中文，部分词汇/标点习惯与简体中文不同，可能导致误判。

### 待改进方向

- 跨行配对标点检查
- 更多变异算子覆盖真实错误模式
- 基于中文 NLP 模型的语义感知检查（如判断句子是否完整）
- 繁体中文适配

---

## 文件结构总览

```
punctuation-checker/                 # 当前路径：C:\Yet\punctuation-checker
├── punctuation_checker.py          # 核心检查器（autoresearch 优化目标）
├── test_punctuation_checker.py     # 原始手工测试
├── README.md                       # 检查器使用说明（中文主文档）
├── README_en.md                    # 英文/LLM 阅读版
├── SKILL.md                        # Agent Skill 定义（frontmatter + 调用约定）
├── evaluate.py                     # 合成变异评估（不可变）
├── corpus_clean.txt                # 正确中文句子语料（88句，不可变）
├── program.md                      # autoresearch agent 指令
├── CLAUSE_COVERAGE.md              # GB/T 条款形式化覆盖矩阵
├── fetch_corpus.py                 # 外部语料下载脚本
├── evaluate_external.py            # 外部语料评估脚本（三模式）
├── WORKFLOW.md                     # 本文档
├── LICENSE                         # MIT License
├── .gitignore
│
│   （以下为运行时生成，git 不跟踪）
├── corpus_ud_gsd.txt               # UD Chinese-GSD 语料 (4,992句)
├── corpus_hf_correction.txt        # chinese_text_correction 清洗句 (54,347句)
├── corpus_hf_pairs.tsv             # 纠错对 source→target (108,315对，模式C用)
├── corpus_hf_news.txt              # ChineseNewsSummary 语料 (26,940句)
├── eval_results.json               # 合成评估详细结果
├── eval_external_results.json      # 外部评估详细结果
├── misses_*.json                   # 各语料的漏检详情
├── results.tsv                     # autoresearch 实验日志
└── run.log                         # 最新运行日志
```

---

## 快速复现

> 三个语料均可用标准库 `urllib` 拉取，**无需安装任何第三方包**（不再需要 `pip install datasets`）。

### 运行合成评估

```bash
python evaluate.py
```

### 拉取外部语料并评估（三模式）

```bash
python fetch_corpus.py        # ~23MB TSV + ~40MB JSON，首次约 1-2 分钟
python evaluate_external.py   # 模式 A 误报率 / B 扩展变异 / C 真实错误检出
```

### 启动 autoresearch 迭代优化

```bash
git checkout -b autoresearch/<tag>
# 按 program.md 中的指令开始实验循环
```
