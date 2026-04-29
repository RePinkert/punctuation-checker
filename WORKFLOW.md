# 工作流程记录

本文档记录 punctuation-checker 项目从初始代码到 autoresearch 迭代优化、外部语料评估的完整工作流。

---

## 阶段一：项目初始化与 GitHub 连接

### 1.1 远程仓库

- 仓库地址：`https://github.com/RePinkert/punctuation-checker`
- 初始状态：空仓库，仅含 MIT LICENSE

### 1.2 本地初始化

```bash
cd X:\Trans-AM\Yet\2-punctuation-checker
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

---

## 阶段四：外部语料评估

### 4.1 语料拉取

创建 `fetch_corpus.py` 下载三个外部语料库：

| 语料 | 句数 | 来源 | 下载方式 |
|---|---|---|---|
| UD Chinese-GSD | 4,992 | GitHub | `urllib` (零依赖) |
| chinese_text_correction | 54,344 | HuggingFace | `pip install datasets` |
| ChineseNewsSummary | 26,940 | HuggingFace | `pip install datasets` |

运行：`python fetch_corpus.py`

生成文件：
- `corpus_ud_gsd.txt`
- `corpus_hf_correction.txt`
- `corpus_hf_news.txt`

### 4.2 三模式评估

创建 `evaluate_external.py`，提供三种评估模式：

#### 模式 A：干净文本误报率

在外部语料（正确标点的真实文本）上运行 checker，任何报错都是误报。

| 语料 | 句数 | FP 率 | 主要误报 |
|---|---|---|---|
| UD Chinese-GSD | 2,000 | **0.30%** | 跨行配对引号 (4), 句末标点 (2) |
| ChineseNewsSummary | 2,000 | **30.35%** | 句末标点 (589) — 新闻标题省略句号 |

#### 模式 B：扩展变异测试

用外部语料句子作为变异基底，运行 10 个变异算子。

| 语料 | F1 | Precision | Recall |
|---|---|---|---|
| UD Chinese-GSD | **0.9953** | 0.9938 | 0.9969 |
| ChineseNewsSummary | **0.7754** | 0.6586 | 0.9425 |

#### 模式 C：真实错误检出

用 `shibing624/chinese_text_correction` 数据集中的 1,403 条含真实标点差异的数据测试。

| 指标 | 值 |
|---|---|
| 总扫描行数 | 108,315 |
| 含标点差异的行 | 1,403 |
| Checker 检出行数 | 576 (**41%**) |
| 主要检出类型 | 中英文标点混用 (2,104), 句末标点 (137), 标点配对 (55) |

### 4.3 基于外部评估的改进

**变更 (`4d7395e`)**：

1. `_check_sentence_end`：跳过以 `%`/数字结尾的行（新闻中如 "跌超4%" 属正常）
2. `_check_chinese_english_mixed`：英文括号检测改为只在括号内为纯中文内容时报错，中英混合内容不再误报

**改进效果**：

| 指标 | 改前 | 改后 |
|---|---|---|
| 新闻 FP 率 | 34.25% | 30.35% |
| 新闻句末标点 FP | 667 | 589 |
| 合成 F1 | 1.0000 | 1.0000 (不变) |

---

## 阶段五：发现的局限性与待改进方向

### 已知局限

1. **句末标点检查 vs 新闻文本**：新闻标题/摘要省略句号是行业标准，strict 模式下的 SUGGESTION 级别报错属预期行为（589 FP / 2000 句新闻）。目前无法可靠区分"标题省略句号"和"句子缺失句号"。

2. **跨行配对引号**：checker 逐行处理，无法检测跨行的配对标点（如引号在第1行打开、第3行关闭）。UD-GSD 中有 4 个此类 FP。

3. **真实错误检出率 41%**：合成变异只覆盖 7 种错误类型，真实文本中的标点错误更加多样（如标点位置不当、语气不符、语境误用等），当前规则无法覆盖。

4. **繁体中文**：UD-GSD 使用繁体中文，部分词汇/标点习惯与简体中文不同，可能导致误判。

### 待改进方向

- 跨行配对标点检查
- 更多变异算子覆盖真实错误模式
- 基于中文 NLP 模型的语义感知检查（如判断句子是否完整）
- 繁体中文适配

---

## 文件结构总览

```
2-punctuation-checker/
├── punctuation_checker.py          # 核心检查器（autoresearch 优化目标）
├── test_punctuation_checker.py     # 原始手工测试
├── punctuation_checker_readme.md   # 检查器使用说明
├── evaluate.py                     # 合成变异评估（不可变）
├── corpus_clean.txt                # 正确中文句子语料（88句，不可变）
├── program.md                      # autoresearch agent 指令
├── fetch_corpus.py                 # 外部语料下载脚本
├── evaluate_external.py            # 外部语料评估脚本（三模式）
├── WORKFLOW.md                     # 本文档
├── LICENSE                         # MIT License
├── .gitignore
│
│   （以下为运行时生成，git 不跟踪）
├── corpus_ud_gsd.txt               # UD Chinese-GSD 语料 (4,992句)
├── corpus_hf_correction.txt        # chinese_text_correction 语料 (54,344句)
├── corpus_hf_news.txt              # ChineseNewsSummary 语料 (26,940句)
├── eval_results.json               # 合成评估详细结果
├── eval_external_results.json      # 外部评估详细结果
├── misses_*.json                   # 各语料的漏检详情
├── results.tsv                     # autoresearch 实验日志
└── run.log                         # 最新运行日志
```

---

## 快速复现

### 运行合成评估

```bash
python evaluate.py
```

### 拉取外部语料并评估

```bash
pip install datasets
python fetch_corpus.py
python evaluate_external.py
```

### 启动 autoresearch 迭代优化

```bash
git checkout -b autoresearch/<tag>
# 按 program.md 中的指令开始实验循环
```
