# -*- coding: utf-8 -*-
"""
标点符号检测脚本测试用例
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')

from punctuation_checker import PunctuationChecker, ErrorLevel, format_report

def test_checker():
    checker = PunctuationChecker(strict_mode=True)
    
    # 测试用例
    test_cases = [
        # 中英文标点混用
        ("这是中文句子,用了英文逗号。", "中英文标点混用"),
        ("这是中文句子.用了英文句号。", "中英文标点混用"),
        
        # 标点空格问题
        ("这是句子， 后面有空格。", "标点空格问题"),
        ("前面有空格 。这是句子。", "标点空格问题"),
        
        # 配对标点 - 缺少后引号（使用中文引号）
        ('他说：\u201c你好。', "标点配对问题"),
        
        # 配对标点 - 缺少后括号
        ("（这是括号内容", "标点配对问题"),
        
        # 配对标点 - 缺少后书名号
        ("《书名号未闭合", "标点配对问题"),
        
        # 标点重复
        ("这是句子，，重复逗号。", "标点重复"),
        ("这是句子。。重复句号。", "标点重复"),
        
        # 省略号格式
        ("这是省略号......不对", "省略号格式"),
        ("这是省略号。。。不对", "省略号格式"),
    ]
    
    print("=" * 60)
    print("标点符号检测测试")
    print("=" * 60)
    
    for text, expected_type in test_cases:
        errors = checker.check(text)
        found = False
        if errors:
            for err in errors:
                if expected_type in err.error_type:
                    print(f"[PASS] {text[:20]}...")
                    print(f"   检测到: [{err.level.value}] {err.error_type} - {err.message}")
                    found = True
                    break
        if not found:
            print(f"[FAIL] 未检测到预期错误类型 '{expected_type}': {text[:30]}...")
        print()
    
    # 测试正确的文本
    print("-" * 60)
    print("测试正确文本（应无错误）:")
    print("-" * 60)
    
    correct_texts = [
        "这是正确的中文句子，使用了中文标点。",
        '他说："你好！"',
        "《红楼梦》是一部伟大的作品。",
        "苹果、香蕉、橘子都是水果。",
        "这是省略号……表示省略。",
    ]
    
    checker_normal = PunctuationChecker(strict_mode=False)
    for text in correct_texts:
        errors = checker_normal.check(text)
        if not errors:
            print(f"[PASS] 正确: {text[:30]}...")
        else:
            print(f"[WARN] 误报: {text[:30]}...")
            for err in errors:
                print(f"   [{err.level.value}] {err.error_type}: {err.message}")
    
    print()
    print("=" * 60)
    print("完整报告示例")
    print("=" * 60)
    
    # 完整报告示例
    sample_text = '''这是一个测试文档,用来检测标点符号问题。
第二行有标点空格问题 ，这里有问题。
第三行"引号不配对。
这是省略号....格式不对。'''
    
    checker2 = PunctuationChecker(strict_mode=False)
    errors = checker2.check(sample_text)
    print(format_report(errors))


if __name__ == '__main__':
    test_checker()
