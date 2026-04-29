# 标点符号用法检测脚本

## 基于《GB/T 15834—2011 标点符号用法》

### 功能特性

1. **中英文标点混用检测** - 检测中文文本中使用的英文标点
2. **标点空格问题** - 检测标点前后多余的空格
3. **配对标点检查** - 检测引号、括号、书名号是否成对
4. **标点重复检测** - 检测不应重复的标点
5. **冒号使用检查** - 检测冒号后是否有内容
6. **顿号使用检查** - 检测顿号和逗号的混用
7. **引号内标点** - 检测引号内标点位置问题
8. **省略号/破折号** - 检测省略号和破折号的格式
9. **句末标点** - 检测句子末尾是否缺少标点
10. **标点与数字/英文** - 检测标点与数字、英文之间的空格

### 使用方法

```bash
# 基本用法
python punctuation_checker.py 文档.txt

# 严格模式（更多警告）
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
标点符号检查报告
============================================================
统计：错误 2 个，警告 1 个，建议 1 个

❌ 第3行，第15列 [错误]
   类型：中英文标点混用
   问题：中文句子中使用了英文逗号
   上下文：这是一个测试,看看标点检测
   建议：应使用中文标点「，」

⚠️ 第5行，第8列 [警告]
   类型：标点空格问题
   问题：中文标点后不应有空格
   上下文：这是测试， 后面有空格
   建议：删除标点后的空格
```

### 作为库使用

```python
from punctuation_checker import PunctuationChecker, format_report

# 创建检查器
checker = PunctuationChecker(strict_mode=True)

# 检查文本
text = "这是一个测试,看看标点检测是否正常。"
errors = checker.check(text)

# 格式化报告
print(format_report(errors))

# 或者处理错误列表
for error in errors:
    print(f"第{error.line}行: {error.message}")
```

### 错误等级

- **错误** ❌ - 明显违反规范的用法
- **警告** ⚠️ - 可能存在问题，需要人工确认
- **建议** 💡 - 严格模式下的额外检查，可参考

### 注意事项

1. 脚本会自动检测文件编码（支持 UTF-8, GBK, GB2312）
2. 代码行和空行会被自动跳过
3. 某些检查需要上下文判断，建议人工复核
4. 严格模式会产生更多建议，适合正式文档
