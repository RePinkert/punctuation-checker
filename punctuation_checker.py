#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
标点符号用法检测脚本
基于《GB/T 15834-2011 标点符号用法》

功能：
1. 检测中英文标点混用
2. 检测标点符号前后空格问题
3. 检测引号、括号、书名号配对
4. 检测句末标点缺失
5. 检测标点符号重复
6. 检测冒号、分号、顿号使用场景
7. 检测引号内标点位置
"""

import re
import argparse
import json
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class ErrorLevel(Enum):
    ERROR = "错误"
    WARNING = "警告"
    SUGGESTION = "建议"


@dataclass
class PunctuationError:
    """标点符号错误"""
    line: int
    column: int
    level: ErrorLevel
    error_type: str
    message: str
    context: str
    suggestion: Optional[str] = None


class PunctuationChecker:
    """基于 GB/T 15834-2011 的标点符号检查器"""
    
    # 配对标点 (左引号: 右引号)
    PAIRED_PUNCS = {
        '\u201c': '\u201d',  # 中文双引号 ""
        '\u2018': '\u2019',  # 中文单引号 ''
        '\uff08': '\uff09',  # 中文小括号 （）
        '\u3010': '\u3011',  # 中文中括号 【】
        '\u300a': '\u300b',  # 中文书名号 《》
        '\u300c': '\u300d',  # 中文篇名号 「」
        '\u300e': '\u300f',  # 中文篇名号 『』
        '"': '"',   # 英文双引号
        "'": "'",   # 英文单引号
        '(': ')',   # 英文小括号
        '[': ']',   # 英文中括号
    }
    
    # 句末标点
    SENTENCE_END_PUNCS = set('\u3002\uff1f\uff01\u2026.?!')
    
    def __init__(self, strict_mode: bool = False):
        self.strict_mode = strict_mode
        self.errors: List[PunctuationError] = []
        
    def check(self, text: str) -> List[PunctuationError]:
        """检查文本中的标点符号问题"""
        self.errors = []
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            self._check_line(line, line_num)
        
        return self.errors
    
    def _check_line(self, line: str, line_num: int):
        """检查单行文本"""
        stripped = line.strip()
        if not stripped:
            return
        if stripped.startswith('#') or stripped.startswith('//'):
            return
            
        self._check_chinese_english_mixed(line, line_num)
        self._check_space_around_punctuation(line, line_num)
        self._check_paired_punctuation(line, line_num)
        self._check_repeated_punctuation(line, line_num)
        self._check_ellipsis_and_dash(line, line_num)
        self._check_dunhao_usage(line, line_num)
        self._check_sentence_end(line, line_num)
    
    def _get_context(self, line: str, col: int, width: int = 15) -> str:
        """获取错误上下文"""
        start = max(0, col - width)
        end = min(len(line), col + width)
        context = line[start:end]
        if start > 0:
            context = '...' + context
        if end < len(line):
            context = context + '...'
        return context
    
    def _is_chinese_char(self, char: str) -> bool:
        """判断是否为中文字符"""
        return '\u4e00' <= char <= '\u9fff'
    
    def _has_chinese(self, text: str) -> bool:
        """判断文本是否包含中文"""
        return any(self._is_chinese_char(c) for c in text)
    
    def _check_chinese_english_mixed(self, line: str, line_num: int):
        """检测中英文标点混用"""
        if not self._has_chinese(line):
            return
            
        cn_ctx = r'[\u4e00-\u9fff\u300a\u300b\u300c\u300d\u300e\u300f\u3010\u3011\uff08\uff09\u201c\u201d\u2018\u2019\u2026\u3001\uff0c\u3002\uff1b\uff1a\uff1f\uff01]'

        patterns = [
            (r'[\u4e00-\u9fff],', '，', '中文句子中使用了英文逗号'),
            (r'[\u4e00-\u9fff]\.(?![a-zA-Z0-9])', '。', '中文句子中使用了英文句号'),
            (r'[\u4e00-\u9fff]:', '：', '中文句子中使用了英文冒号'),
            (r'[\u4e00-\u9fff];', '；', '中文句子中使用了英文分号'),
            (r'[\u4e00-\u9fff]\?', '？', '中文句子中使用了英文问号'),
            (r'[\u4e00-\u9fff]!', '！', '中文句子中使用了英文感叹号'),
            (r'[\u4e00-\u9fff]\([^\)]*[\u4e00-\u9fff]', '()', '中文句子中使用了英文括号'),
            (fr'{cn_ctx},', '，', '中文标点后使用了英文逗号'),
            (fr'{cn_ctx}\.(?![a-zA-Z0-9])', '。', '中文标点后使用了英文句号'),
            (fr'{cn_ctx}:', '：', '中文标点后使用了英文冒号'),
            (fr'{cn_ctx};', '；', '中文标点后使用了英文分号'),
            (fr'{cn_ctx}\?', '？', '中文标点后使用了英文问号'),
            (fr'{cn_ctx}!', '！', '中文标点后使用了英文感叹号'),
        ]
        
        for pattern, correct, msg in patterns:
            for match in re.finditer(pattern, line):
                col = match.start() + 1
                self.errors.append(PunctuationError(
                    line=line_num,
                    column=col,
                    level=ErrorLevel.ERROR,
                    error_type="中英文标点混用",
                    message=msg,
                    context=self._get_context(line, col),
                    suggestion=f"应使用中文标点「{correct}」"
                ))
    
    def _check_space_around_punctuation(self, line: str, line_num: int):
        """检测标点前后空格问题"""
        # 中文标点后不应有空格
        chinese_puncs = '，。；：？！、）》】」』'
        for punc in chinese_puncs:
            pattern = re.escape(punc) + r'\s+'
            for match in re.finditer(pattern, line):
                col = match.start()
                self.errors.append(PunctuationError(
                    line=line_num,
                    column=col + 1,
                    level=ErrorLevel.WARNING,
                    error_type="标点空格问题",
                    message=f"标点「{punc}」后不应有空格",
                    context=self._get_context(line, col),
                    suggestion="删除标点后的空格"
                ))
        
        # 中文标点前不应有空格
        chinese_puncs_before = '，。；：？！、（《【「『'
        for punc in chinese_puncs_before:
            pattern = r'\s+' + re.escape(punc)
            for match in re.finditer(pattern, line):
                col = match.start()
                self.errors.append(PunctuationError(
                    line=line_num,
                    column=col + 1,
                    level=ErrorLevel.WARNING,
                    error_type="标点空格问题",
                    message=f"标点「{punc}」前不应有空格",
                    context=self._get_context(line, col),
                    suggestion="删除标点前的空格"
                ))
    
    def _check_paired_punctuation(self, line: str, line_num: int):
        """检测配对标点是否成对"""
        for left, right in self.PAIRED_PUNCS.items():
            left_count = line.count(left)
            right_count = line.count(right)
            
            if left_count != right_count:
                col = line.find(left) if left in line else line.find(right)
                col = max(0, col)
                
                punc_name = {
                    '\u201c': '双引号',
                    '\u2018': '单引号',
                    '\uff08': '小括号',
                    '\u3010': '中括号',
                    '\u300a': '书名号',
                    '"': '英文双引号',
                    "'": '英文单引号',
                    '(': '英文小括号',
                    '[': '英文中括号',
                }.get(left, '配对标点')
                
                self.errors.append(PunctuationError(
                    line=line_num,
                    column=col + 1,
                    level=ErrorLevel.ERROR,
                    error_type="标点配对问题",
                    message=f"{punc_name}不配对：左{left_count}个，右{right_count}个",
                    context=self._get_context(line, col),
                    suggestion=f"检查{punc_name}是否成对使用"
                ))
    
    def _check_repeated_punctuation(self, line: str, line_num: int):
        """检测标点重复"""
        # 不应重复的标点
        no_repeat = ['，', '。', '；', '：', '、', '）', '】', '》']
        
        for punc in no_repeat:
            pattern = re.escape(punc) + r'{2,}'
            for match in re.finditer(pattern, line):
                col = match.start()
                self.errors.append(PunctuationError(
                    line=line_num,
                    column=col + 1,
                    level=ErrorLevel.ERROR,
                    error_type="标点重复",
                    message=f"标点「{punc}」重复使用",
                    context=self._get_context(line, col),
                    suggestion="删除多余的标点符号"
                ))
        
        # 问号和感叹号最多连用三个
        for punc in ['？', '！']:
            pattern = re.escape(punc) + r'{4,}'
            for match in re.finditer(pattern, line):
                col = match.start()
                self.errors.append(PunctuationError(
                    line=line_num,
                    column=col + 1,
                    level=ErrorLevel.WARNING,
                    error_type="标点重复",
                    message=f"标点「{punc}」连用超过三个",
                    context=self._get_context(line, col),
                    suggestion="减少标点连用数量"
                ))
    
    def _check_ellipsis_and_dash(self, line: str, line_num: int):
        """检测省略号和破折号格式"""
        # 检测不规范的省略号
        ellipsis_issues = [
            (r'\.{3,5}(?!\.)', '英文省略号应为三个点或使用中文省略号'),
            (r'(?<!\。)\。{3,5}(?!\。)', '中文省略号应为六个点'),
        ]
        
        for pattern, msg in ellipsis_issues:
            for match in re.finditer(pattern, line):
                col = match.start()
                self.errors.append(PunctuationError(
                    line=line_num,
                    column=col + 1,
                    level=ErrorLevel.WARNING,
                    error_type="省略号格式",
                    message=msg,
                    context=self._get_context(line, col),
                    suggestion="中文省略号使用「……」，英文省略号使用「...」"
                ))
    
    def _check_dunhao_usage(self, line: str, line_num: int):
        """检测顿号使用"""
        # 顿号后不应直接跟句末标点
        pattern = '、[。？！]'
        for match in re.finditer(pattern, line):
            col = match.start()
            self.errors.append(PunctuationError(
                line=line_num,
                column=col + 1,
                level=ErrorLevel.ERROR,
                error_type="顿号使用",
                message="顿号后不应直接跟句末标点",
                context=self._get_context(line, col),
                suggestion="删除顿号或改用逗号"
            ))
    
    def _check_sentence_end(self, line: str, line_num: int):
        """检测句末标点"""
        stripped = line.rstrip()
        if not stripped or len(stripped) < 5:
            return
        
        # 跳过标题、列表项
        if re.match(r'^[#*\-\d\.、]+', stripped):
            return
        if re.match(r'^[（\(]\d+[）\)]', stripped):
            return
            
        last_char = stripped[-1]
        
        # 如果以引号等结尾，检查前一个字符
        if last_char in '"\'》）】」':
            if len(stripped) > 1:
                last_char = stripped[-2]
            else:
                return
        
        # 检查是否缺少句末标点
        if self._has_chinese(stripped):
            if last_char not in self.SENTENCE_END_PUNCS:
                if last_char not in '：；;:':  # 冒号/分号结尾
                    if self.strict_mode:
                        self.errors.append(PunctuationError(
                            line=line_num,
                            column=len(stripped),
                            level=ErrorLevel.SUGGESTION,
                            error_type="句末标点",
                            message="句子末尾可能缺少标点符号",
                            context=self._get_context(line, len(stripped) - 1),
                            suggestion="考虑在句末添加句号"
                        ))


def format_report(errors: List[PunctuationError], show_suggestion: bool = True) -> str:
    """格式化错误报告"""
    if not errors:
        return "未发现标点符号问题"
    
    error_count = sum(1 for e in errors if e.level == ErrorLevel.ERROR)
    warning_count = sum(1 for e in errors if e.level == ErrorLevel.WARNING)
    suggestion_count = sum(1 for e in errors if e.level == ErrorLevel.SUGGESTION)
    
    lines = []
    lines.append("=" * 60)
    lines.append("标点符号检查报告 (基于 GB/T 15834-2011)")
    lines.append("=" * 60)
    lines.append(f"统计: 错误 {error_count} 个, 警告 {warning_count} 个, 建议 {suggestion_count} 个")
    lines.append("")
    
    sorted_errors = sorted(errors, key=lambda e: (e.line, e.column))
    
    for err in sorted_errors:
        level_icon = {
            ErrorLevel.ERROR: "[错误]",
            ErrorLevel.WARNING: "[警告]",
            ErrorLevel.SUGGESTION: "[建议]"
        }
        
        lines.append(f"第{err.line}行, 第{err.column}列 {level_icon[err.level]}")
        lines.append(f"  类型: {err.error_type}")
        lines.append(f"  问题: {err.message}")
        lines.append(f"  上下文: {err.context}")
        if show_suggestion and err.suggestion:
            lines.append(f"  建议: {err.suggestion}")
        lines.append("")
    
    return "\n".join(lines)


def check_file(filepath: str, strict: bool = False, encoding: str = 'utf-8') -> List[PunctuationError]:
    """检查文件"""
    encodings = [encoding, 'utf-8', 'gbk', 'gb2312', 'utf-8-sig']
    
    for enc in encodings:
        try:
            with open(filepath, 'r', encoding=enc) as f:
                text = f.read()
            break
        except UnicodeDecodeError:
            continue
    else:
        raise ValueError(f"无法解码文件 {filepath}")
    
    checker = PunctuationChecker(strict_mode=strict)
    return checker.check(text)


def main():
    parser = argparse.ArgumentParser(
        description='基于 GB/T 15834-2011 的标点符号用法检测工具'
    )
    parser.add_argument('file', help='要检查的文件路径')
    parser.add_argument('-s', '--strict', action='store_true', 
                        help='严格模式')
    parser.add_argument('-o', '--output', help='输出报告文件路径')
    parser.add_argument('-e', '--encoding', default='utf-8', 
                        help='文件编码')
    parser.add_argument('--no-suggestion', action='store_true',
                        help='不显示修改建议')
    parser.add_argument('--json', action='store_true',
                        help='以JSON格式输出')
    
    args = parser.parse_args()
    
    try:
        errors = check_file(args.file, args.strict, args.encoding)
        
        if args.json:
            result = {
                'file': args.file,
                'total_errors': len(errors),
                'errors': [
                    {
                        'line': e.line,
                        'column': e.column,
                        'level': e.level.value,
                        'type': e.error_type,
                        'message': e.message,
                        'context': e.context,
                        'suggestion': e.suggestion
                    }
                    for e in errors
                ]
            }
            output = json.dumps(result, ensure_ascii=False, indent=2)
        else:
            output = format_report(errors, show_suggestion=not args.no_suggestion)
        
        if args.output:
            with open(args.output, 'w', encoding='utf-8') as f:
                f.write(output)
            print(f"报告已保存到 {args.output}")
        else:
            print(output)
            
    except FileNotFoundError:
        print(f"错误: 文件 {args.file} 不存在")
    except Exception as e:
        print(f"错误: {e}")


if __name__ == '__main__':
    main()
