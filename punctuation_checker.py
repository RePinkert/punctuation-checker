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

# GB/T 15834-2011 第 1 章：适用于汉语书面语（含汉语和外文混合排版时的汉语部分）。
# 汉字判定范围 = CJK Unified Ideographs 基本区 U+4E00–9FFF + 扩展 A U+3400–4DBF。
# 兼容区 F900–FAFF 与扩展 B 起的表意平面不在本范围内。
CJK_TEXT = r'\u4e00-\u9fff\u3400-\u4dbf'
CJK_TEXT_RE = re.compile(f'[{CJK_TEXT}]')

# 中文标点所在区：CJK 符号和标点区 U+3000–303F、全角区 U+FF01–FF1F/FF08/FF09/
# FF0C/FF1A/FF1B、弯引号区 U+2018–201F 以及书名号/篇号/题号 (《》〈〉「」『』【】〔〕) 专用
CJK_PUNCT = r'\u3001\u3002\u300a\u300b\u300c\u300d\u300e\u300f\u3010\u3011\u3014\u3015\u2018-\u201f\uff01\uff08\uff09\uff0c\uff1a\uff1b\uff1f'
CJK_CONTEXT_RE = re.compile(f'[{CJK_TEXT}{CJK_PUNCT}]')


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
        '\u3014': '\u3015',  # 中文六角括号 〔〕
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
        self._check_line_start_point(line, line_num)
        self._check_ordinal_conjunction(line, line_num)
        self._check_date_dunhao(line, line_num)
        self._check_numeric_range_dash(line, line_num)
        self._check_dash_form(line, line_num)
        self._check_gbt_matrix(line, line_num)
        self._check_ellipsis_run(line, line_num)
        self._check_ordinal_bracket(line, line_num)
        self._check_arabic_ordinal(line, line_num)
        self._check_narrow_clauses(line, line_num)

    def _check_narrow_clauses(self, line: str, line_num: int):
        """低误报风险的窄规则集（全部对照标准原文核实）

        - 4.15.3.5 书名号中还需要书名号时，里面一层用单书名号
        - B.3.6   用于章节、条款的序次语后宜用空格表示停顿

        注：B.3.5（下脚点章节序次语末尾不用任何点号）已尝试但**撤回**——
        正文中的小数（“7.9公分”“都是0.4。”）与章节号无法用正则区分，
        UD-GSD 语料上直接产生误报，故不实现。
        """
        rules = [
            # 4.15.3.5 嵌套书名号应为外双内单：《…〈…〉…》；内层误用双书名号即报
            (r'《[^《》〈〉]{0,60}《', ErrorLevel.ERROR, "书名号使用",
             "书名号中还需要书名号时，里面一层应用单书名号",
             "内层改用单书名号「〈〉」（4.15.3.5）"),
            # B.3.6 章节/条款序次语后宜用空格表示停顿（第一课 春天来了）
            # 只认行首的序次语（章节/条款标题位置），避免行文中「第三课的内容」等误报
            (r'^\s*(第[一二三四五六七八九十百千零〇\d]{1,3}[章节课编部篇])(?![\s])(?=\S)',
             ErrorLevel.SUGGESTION, "序次语",
             "用于章节、条款的序次语后宜用空格表示停顿",
             "序次语后加一个空格（B.3.6）"),
        ]
        for pattern, level, etype, msg, sugg in rules:
            for match in re.finditer(pattern, line):
                col = match.start()
                self.errors.append(PunctuationError(
                    line=line_num,
                    column=col + 1,
                    level=level,
                    error_type=etype,
                    message=msg,
                    context=self._get_context(line, col),
                    suggestion=sugg
                ))

    def _check_line_start_point(self, line: str, line_num: int):
        """GB/T 15834-2011 5.1.1：点号应置于文字之后，居左下，不出现在一行之首"""
        stripped = line.strip()
        if stripped and stripped[0] in '，。、；：？！':
            self.errors.append(PunctuationError(
                line=line_num,
                column=1,
                level=ErrorLevel.WARNING,
                error_type="点号位置",
                message=f"点号「{stripped[0]}」不应出现在一行之首",
                context=self._get_context(line, 0, width=20),
                suggestion="删除该点号或移动到上一行句末"
            ))

    def _check_ordinal_conjunction(self, line: str, line_num: int):
        """GB/T 15834-2011 B.3.1：序次语（"首先"、"其次"、"再次"、"最后"）之后用逗号"""
        for match in re.finditer(r'(首先|其次|再次|最后)、', line):
            col = match.start()
            self.errors.append(PunctuationError(
                line=line_num,
                column=col + 1,
                level=ErrorLevel.WARNING,
                error_type="顿号使用",
                message=f"序次语「{match.group(1)}」之后应用逗号，不用顿号",
                context=self._get_context(line, col),
                suggestion="顿号改为逗号"
            ))

    def _check_date_dunhao(self, line: str, line_num: int):
        """GB/T 15834-2011 A.4.4.2 / 4.13.3.1：数字年月日的简写形式用短横线连接号，不用顿号"""
        for match in re.finditer(r'\d{4}、\d{1,2}、\d{1,2}', line):
            col = match.start()
            self.errors.append(PunctuationError(
                line=line_num,
                column=col + 1,
                level=ErrorLevel.ERROR,
                error_type="连接号",
                message="数字年月日简写中不应使用顿号",
                context=self._get_context(line, col),
                suggestion="改为短横线连接号，如「2010-03-02」"
            ))

    def _check_numeric_range_dash(self, line: str, line_num: int):
        r"""GB/T 15834-2011 4.13.3.2：数值起止应用一字线「—」或浪纹线「～」，
        4.13.3.1(b) 的短横线仅用于序号/电话/年月日。窄定义：允许数值后
        紧接 %（如 3.75%-4.00%）；纯整数段（电话、门牌、序号）以及连用段
        不报"""
        candidate = r'\d(?:[\d,.]{0,10}\d)?\s*%?\s*-\s*%?\s*\d(?:[\d,.]{0,10}\d)?\s*%?'
        for match in re.finditer(candidate, line):
            if not re.search(r'[.%]', match.group(0)):
                continue
            before = line[:match.start()]
            after = line[match.end():]
            if re.match(r'\s*-\s*\d', after) or before.rstrip().endswith('-'):
                continue
            col = match.start()
            self.errors.append(PunctuationError(
                line=line_num,
                column=col + 1,
                level=ErrorLevel.WARNING,
                error_type="连接号",
                message="数值区间不应使用短横线",
                context=self._get_context(line, col),
                suggestion="改为一字线「—」或浪纹线「～」，如「3.75%—4.00%」"
            ))

    def _check_dash_form(self, line: str, line_num: int):
        """GB/T 15834-2011 4.10.2：破折号形式「——」为两个一字线；
        破折号位置的单个一字线为形式错误。一字线作为连接号连接数字
        （4.13.3.2 时间/数值起止）属合法，不查"""
        for match in re.finditer(r'—', line):
            start, end = match.start(), match.end()
            if start > 0 and line[start - 1] == '—':
                continue
            if end < len(line) and line[end] == '—':
                continue
            before = line[:start].rstrip()
            after = line[end:].lstrip()
            # 一字线紧邻数字（如 1031—1095、2月3日—10日）视为连接号
            if before and after and (before[-1].isdigit() or after[0].isdigit()):
                continue
            # 成语/合成词中作连接号且两侧为汉字的情况无法与破折号区分，
            # 仅当一侧是标点/行首行尾等非文字边界时保守不报；两侧均为
            # 汉字或引号/书名号上下文才按破折号形式错误处理
            if before and after and self._has_chinese(before[-1]) and self._has_chinese(after[:1]):
                col = start
                self.errors.append(PunctuationError(
                    line=line_num,
                    column=col + 1,
                    level=ErrorLevel.WARNING,
                    error_type="破折号形式",
                    message="破折号「——」应占两个一字线位置，不应单用",
                    context=self._get_context(line, col),
                    suggestion="改为双字线「——」；若此处为数值/时间起止的连接号则应保留单线"
                ))

    def _check_gbt_matrix(self, line: str, line_num: int):
        """coverage matrix 中标记为 G 的剩余条款（见 CLAUSE_COVERAGE.md）"""
        rules = [
            # B.2.4 省略号前后点号为语义判断（分句中点号可保留），归 S 类不实现
            # G6 A.12：并列标题已用间隔号，不再用"和"
            (r'《[^《》]{1,40}·[^《》]{0,20}》\s*(和|及)', ErrorLevel.SUGGESTION, "间隔号使用",
             "并列标题间已用间隔号，不应再用「和」", "删去连接词（A.12）"),
            # G7 A.13.5：篇名末尾的？！应在书名号内
            (r'《[^《》]{1,60}》\s*([？！])', ErrorLevel.SUGGESTION, "书名号使用",
             "篇名末尾的问号/叹号应放在书名号内", "将「\\1」移入《》（A.13.5）"),
            # G8 A.14：分隔号前后不贴点号
            (r'[、，；：。]\s*/|/\s*[、，；：。]', ErrorLevel.SUGGESTION, "分隔号使用",
             "分隔号前后通常不用点号", "删除紧贴的分隔点号（A.14）"),
            # G9/G14 4.8.3.4：同向双引号不可嵌套（外双内单）
            (r'\u201c[^“”]{1,50}\u201c', ErrorLevel.ERROR, "引号使用",
             "双引号内不可再嵌套双引号", "内层改用单引号「''」（4.8.3.4）"),
            # G9b 4.9.3.6：同形括号不可嵌套
            (r'\u3010[^【】]{1,50}\u3010', ErrorLevel.ERROR, "括号使用",
             "同形括号不应嵌套套用", "内层换用其他形式括号（4.9.3.6）"),
            (r'（[^（）]{1,50}（', ErrorLevel.ERROR, "括号使用",
             "同形括号不应嵌套套用", "内层换用其他形式括号（4.9.3.6）"),
            # G10 A.9.1 省略号连用改为 _check_ellipsis_run 单独计数

            # 4.5.3.5 引号/书名号间顿号为「通常不用」软规则（语料 FP 10/2000），归 H 类
            # G12 B.1.2：并列成分末尾用"等"类词时，"等"类词前不用顿号
            (r'、\s*(等等?)', ErrorLevel.SUGGESTION, "顿号使用",
             "「等」类词之前不用顿号", "删去顿号；若并列停顿改用逗号则前改用逗号（B.1.2）"),
            # G13a 4.14.3.5：事件年月日的间隔号应用半角「·」
            (r'\d{1,2}\s*[・•]\s*\d{1,2}', ErrorLevel.WARNING, "间隔号使用",
             "间隔号不应使用「・」「•」", "改用半角「·」（4.14.3.5）"),
            # G13b 4.14.3.5：间隔号两侧不应有空格
            (r'\d{1,2}\s+·\s+\d{1,2}', ErrorLevel.WARNING, "间隔号使用",
             "事件年月日间隔号两侧不应有空格", "紧凑书写如「9·11」（4.14.3.5）"),
        ]
        for pattern, level, etype, msg, sugg in rules:
            for match in re.finditer(pattern, line):
                col = match.start()
                self.errors.append(PunctuationError(
                    line=line_num,
                    column=col + 1,
                    level=level,
                    error_type=etype,
                    message=msg,
                    context=self._get_context(line, col),
                    suggestion=sugg
                ))

    def _check_ellipsis_run(self, line: str, line_num: int):
        """GB/T 15834-2011 A.9.1：不能多于两个省略号（即十二点以上）连用"""
        if line.count('……') > 2:
            self.errors.append(PunctuationError(
                line=line_num,
                column=1,
                level=ErrorLevel.ERROR,
                error_type="省略号格式",
                message="省略号连用不应超过两个（十二点）",
                context=self._get_context(line, 0, width=20),
                suggestion="删减连用数量（A.9.1）"
            ))

    def _check_ordinal_bracket(self, line: str, line_num: int):
        """GB/T 15834-2011 B.3.4：加括号的序次语（（一）、(1)）后面不用任何点号
        （B.3.2 对不带括号的汉字序次语才是顿号）"""
        for match in re.finditer(r'[（(][\d一二三四五六七八九十]{1,3}[）\)]\s*[、，。；]', line):
            col = match.start()
            self.errors.append(PunctuationError(
                line=line_num,
                column=col + 1,
                level=ErrorLevel.WARNING,
                error_type="序次语",
                message="带括号的序次语后面不用点号",
                context=self._get_context(line, col),
                suggestion="删除序次语后的点号（B.3.4）"
            ))

    def _check_arabic_ordinal(self, line: str, line_num: int):
        """GB/T 15834-2011 B.3.3：不带括号的阿拉伯数字做行首序次语时，
        后面用下脚点「.」，不用顿号（「1、」应为「1.」）"""
        m = re.match(r'^\s*(\d{1,3})\s*、', line)
        if m:
            self.errors.append(PunctuationError(
                line=line_num,
                column=1,
                level=ErrorLevel.SUGGESTION,
                error_type="序次语",
                message="阿拉伯数字序次语后应用下脚点「.」，不用顿号",
                context=self._get_context(line, 0, width=20),
                suggestion=f"「{m.group(1)}、」应为「{m.group(1)}.」"
            ))
    
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
        """判断是否为汉字字符（CJK 基本区 + 扩展 A）"""
        return bool(CJK_TEXT_RE.match(char))

    def _has_chinese(self, text: str) -> bool:
        """判断文本是否包含汉字"""
        return bool(CJK_TEXT_RE.search(text))

    def _check_chinese_english_mixed(self, line: str, line_num: int):
        """检测中英文标点混用"""
        if not self._has_chinese(line):
            return

        cn_ctx = rf'[{CJK_TEXT}{CJK_PUNCT}]'

        patterns = [
            (fr'{cn_ctx},', '，', '中文标点后使用了英文逗号'),
            (fr'{cn_ctx}\.(?![a-zA-Z0-9])', '。', '中文标点后使用了英文句号'),
            (fr'{cn_ctx}:', '：', '中文标点后使用了英文冒号'),
            (fr'{cn_ctx};', '；', '中文标点后使用了英文分号'),
            (fr'{cn_ctx}\?', '？', '中文标点后使用了英文问号'),
            (fr'{cn_ctx}!', '！', '中文标点后使用了英文感叹号'),
        ]
        
        paren_pattern = r'\(([^\)]*)\)'
        for match in re.finditer(paren_pattern, line):
            content = match.group(1)
            has_cn_inside = bool(CJK_TEXT_RE.search(content))
            has_en_inside = any(c.isascii() and c.isalpha() for c in content)
            if has_cn_inside and not has_en_inside:
                before = line[:match.start()]
                if before and (bool(CJK_TEXT_RE.match(before[-1])) or before[-1] in '\uff0c\u3002\uff1b\uff1a\u201c\u201d'):
                    col = match.start() + 1
                    self.errors.append(PunctuationError(
                        line=line_num,
                        column=col,
                        level=ErrorLevel.ERROR,
                        error_type="中英文标点混用",
                        message="中文句子中使用了英文括号",
                        context=self._get_context(line, col),
                        suggestion="应使用中文括号「（）」"
                    ))

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
                    '\u3014': '六角括号',
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

        # GB/T 15834-2011 A.9.2：省略号和"等"、"等等"等词语不能同时使用
        for match in re.finditer(r'……\s*(等等?)', line):
            col = match.start()
            self.errors.append(PunctuationError(
                line=line_num,
                column=col + 1,
                level=ErrorLevel.WARNING,
                error_type="省略号格式",
                message=f"省略号与「{match.group(1)}」不能同时使用",
                context=self._get_context(line, col),
                suggestion="删除省略号或删除「等」类词语"
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

        # GB/T 15834-2011 B.3.3/B.3.4：只有真正的序次语列表项才免检句末，
        # 如 "1. " "1、" "1) " "(1)" "（一）"；以数字开头的普通句子（如年份）仍需检查
        if re.match(r'^[#*\-]', stripped):
            return
        if re.match(r'^\d+\s*[.、)\]）]\s*\S', stripped):
            return
        if re.match(r'^[（\(][\d一二三四五六七八九十]+[）\)]', stripped):
            return
        # 点号开头的行由 5.1.1 点号位置检查负责，避免重复报
        if stripped[0] in '，。、；：？！':
            return

        last_char = stripped[-1]

        close_marks = '"\u201d\u2019\'\u300f》）】」\u3009\u3015\u3017\u300d'
        if last_char in close_marks:
            if len(stripped) > 1:
                last_char = stripped[-2]
            else:
                return

        if last_char not in self.SENTENCE_END_PUNCS:
            if last_char in '：；;:%％':
                return
            effective_end = stripped.rstrip('"\'\u201d\u2019\u300f》）】」\u3009\u3015\u3017\u300d')
            if effective_end and re.search(r'[\d%％]$', effective_end):
                return
            if self._has_chinese(stripped):
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
