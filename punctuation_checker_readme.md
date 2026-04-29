# 标点符号用法检测脚本

## 基于《GB/T 15834—2011 标点符号用法》

### 功能特性

1. **中英文标点混用检测** - 检测中文文本及中文配对标点后使用的英文标点（逗号、句号、冒号、分号、问号、感叹号、括号）
2. **标点空格问题** - 检测中文标点前后多余的空格
3. **配对标点检查** - 检测引号（`""` `''` `「」` `『』`）、括号（`（）` `【】`）、书名号（`《》`）等是否成对
4. **标点重复检测** - 检测不应重复的标点（`，` `。` `；` `：` `、` `）` `】` `》`）
5. **省略号格式** - 检测非标准的省略号形式（`...`、`。。。`）
6. **顿号使用检查** - 检测顿号后直接跟句末标点的情况
7. **句末标点** - 严格模式下检测句子末尾是否缺少标点（跳过标题、列表项、以数字/百分比结尾的行）

### 使用方法

```bash
# 基本用法
python punctuation_checker.py 文档.txt

# 严格模式（启用句末标点检查等额外建议）
python punctuation_checker.py 文档.txt --strict

# 输出到文件
python punctuation_checker.py 文档.txt -o 报告.txt

# 指定编码
python punctuation_checker.py 文档.txt -e gbk

# JSON格式输出
python punctuation_checker.py 文档.txt --json

# 不显示修改建议
python punctuation_checker.py 文档.txt --no-suggestion
```

### 输出示例

```
============================================================
标点符号检查报告 (基于 GB/T 15834-2011)
============================================================
统计: 错误 2 个, 警告 1 个, 建议 1 个

第1行, 第9列 [错误]
  类型: 中英文标点混用
  问题: 中文句子中使用了英文逗号
  上下文: ...这是中文句子,用了英文逗号...
  建议: 应使用中文标点「，」
```

### 作为库使用

```python
from punctuation_checker import PunctuationChecker, format_report

checker = PunctuationChecker(strict_mode=True)
text = "这是一个测试,看看标点检测是否正常。"
errors = checker.check(text)

for error in errors:
    print(f"第{error.line}行: {error.message}")
```

### 错误等级

- **错误** - 明显违反规范的用法（中英文标点混用、配对缺失、重复标点、顿号误用）
- **警告** - 可能存在问题，需要人工确认（标点空格、问号感叹号连用过多、省略号格式）
- **建议** - 严格模式下的额外检查，可参考（句末标点缺失）

### 评估

项目包含基于合成变异测试的评估管线（`evaluate.py`）和外部语料评估管线（`evaluate_external.py`）。

```bash
# 合成变异评估（447个测试用例，10个变异算子）
python evaluate.py

# 外部语料评估（需先运行 fetch_corpus.py）
python evaluate_external.py
```

当前合成评估指标：**F1=1.0** / Precision=1.0 / Recall=1.0（447个测试用例）。

详见 [WORKFLOW.md](WORKFLOW.md) 了解完整的优化历史和外部评估结果。

### 注意事项

1. 脚本会自动检测文件编码（支持 UTF-8, GBK, GB2312, UTF-8-SIG）
2. 代码行（以 `#` 或 `//` 开头）和空行会被自动跳过
3. 句末标点检查仅在 strict 模式下启用，且会跳过标题、列表项、以数字/百分比结尾的行
4. 英文括号检测仅在括号内为纯中文内容时触发，中英混合内容（如 `人民币(约500万美元)`）不会误报
5. 检查器逐行处理，无法检测跨行的配对标点
