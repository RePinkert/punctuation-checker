#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Punctuation checker evaluation script (immutable).
Generates synthetic mutated corpus and evaluates punctuation_checker.py.
Outputs a single metric f1_score for the autoresearch framework.
"""

import sys
import os
import json
import random
import re
from typing import List, Dict, Tuple, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from punctuation_checker import PunctuationChecker, ErrorLevel

SEED = 42
random.seed(SEED)

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_clean_sentences() -> List[str]:
    corpus_path = os.path.join(_SCRIPT_DIR, "corpus_clean.txt")
    sentences = []
    with open(corpus_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n").rstrip("\r")
            if line.strip():
                sentences.append(line)
    return sentences


ENGLISH_PUNC_MAP = {
    "\uff0c": ",",   # fullwidth comma -> ASCII comma
    "\u3002": ".",   # ideographic period -> ASCII dot
    "\uff1a": ":",   # fullwidth colon -> ASCII colon
    "\uff1b": ";",   # fullwidth semicolon -> ASCII semicolon
    "\uff1f": "?",   # fullwidth question mark -> ASCII ?
    "\uff01": "!",   # fullwidth exclamation -> ASCII !
}

SPACE_AFTER_PUNCS = "\uff0c\u3002\uff1b\uff1a\uff1f\uff01\u3001\uff09\u300b\u3011\u300d\u300f"
SPACE_BEFORE_PUNCS = "\uff0c\u3002\uff1b\uff1a\uff1f\uff01\u3001\uff08\u300a\u3010\u300c\u300e"

CLOSING_PUNCTS = {
    "\u201c": "\u201d",  # left/right double curly quotes
    "\u2018": "\u2019",  # left/right single curly quotes
    "\uff08": "\uff09",  # fullwidth parens
    "\u3010": "\u3011",  # black lenticular brackets
    "\u300a": "\u300b",  # double angle brackets
    "\u300c": "\u300d",  # left/right corner bracket
    "\u300e": "\u300f",  # left/right white corner bracket
}

REPEATABLE_PUNCS = [
    "\uff0c",  # fullwidth comma
    "\u3002",  # ideographic period
    "\uff1b",  # fullwidth semicolon
    "\uff1a",  # fullwidth colon
    "\u3001",  # ideographic comma
    "\uff09",  # fullwidth right paren
    "\u3011",  # right black lenticular bracket
    "\u300b",  # right double angle bracket
]


def mutate_to_english_punc(text: str) -> Optional[Tuple[str, List[str]]]:
    candidates = []
    for i, ch in enumerate(text):
        if ch in ENGLISH_PUNC_MAP:
            candidates.append(i)
    if not candidates:
        return None
    idx = random.choice(candidates)
    old_punc = text[idx]
    new_punc = ENGLISH_PUNC_MAP[old_punc]
    mutated = text[:idx] + new_punc + text[idx + 1:]
    return mutated, ["\u4e2d\u82f1\u6587\u6807\u70b9\u6df7\u7528"]


def mutate_add_space_after(text: str) -> Optional[Tuple[str, List[str]]]:
    candidates = []
    for i, ch in enumerate(text):
        if ch in SPACE_AFTER_PUNCS and i + 1 < len(text) and text[i + 1] not in " \t":
            candidates.append(i)
    if not candidates:
        return None
    idx = random.choice(candidates)
    mutated = text[:idx + 1] + " " + text[idx + 1:]
    return mutated, ["\u6807\u70b9\u7a7a\u683c\u95ee\u9898"]


def mutate_add_space_before(text: str) -> Optional[Tuple[str, List[str]]]:
    candidates = []
    for i, ch in enumerate(text):
        if ch in SPACE_BEFORE_PUNCS and i > 0 and text[i - 1] not in " \t":
            candidates.append(i)
    if not candidates:
        return None
    idx = random.choice(candidates)
    mutated = text[:idx] + " " + text[idx:]
    return mutated, ["\u6807\u70b9\u7a7a\u683c\u95ee\u9898"]


def mutate_remove_closing(text: str) -> Optional[Tuple[str, List[str]]]:
    candidates = []
    for left, right in CLOSING_PUNCTS.items():
        if right in text:
            for i, ch in enumerate(text):
                if ch == right:
                    candidates.append((i, left))
    if not candidates:
        return None
    idx, left_punc = random.choice(candidates)
    mutated = text[:idx] + text[idx + 1:]
    return mutated, ["\u6807\u70b9\u914d\u5bf9\u95ee\u9898"]


def mutate_duplicate_punc(text: str) -> Optional[Tuple[str, List[str]]]:
    candidates = []
    for punc in REPEATABLE_PUNCS:
        for i, ch in enumerate(text):
            if ch == punc:
                candidates.append((i, punc))
    if not candidates:
        return None
    idx, punc = random.choice(candidates)
    mutated = text[:idx + 1] + punc + text[idx + 1:]
    return mutated, ["\u6807\u70b9\u91cd\u590d"]


def mutate_ellipsis(text: str) -> Optional[Tuple[str, List[str]]]:
    ellipsis = "\u2026\u2026"
    if ellipsis not in text:
        return None
    variant = random.choice(["english", "chinese_short"])
    if variant == "english":
        mutated = text.replace(ellipsis, "...", 1)
    else:
        mutated = text.replace(ellipsis, "\u3002\u3002\u3002", 1)
    return mutated, ["\u7701\u7565\u53f7\u683c\u5f0f"]


def mutate_dunhao_before_end(text: str) -> Optional[Tuple[str, List[str]]]:
    candidates = []
    for i, ch in enumerate(text):
        if ch == "\u3001" and i + 1 < len(text) and text[i + 1] not in "\u3002\uff1f\uff01":
            candidates.append(i)
    if not candidates:
        return None
    idx = random.choice(candidates)
    end_punc = random.choice(["\u3002", "\uff1f", "\uff01"])
    mutated = text[:idx + 1] + end_punc + text[idx + 1:]
    return mutated, ["\u987f\u53f7\u4f7f\u7528"]


def mutate_remove_sentence_end(text: str) -> Optional[Tuple[str, List[str]]]:
    stripped = text.rstrip()
    if not stripped:
        return None
    last_char = stripped[-1]
    in_bracket = False
    if last_char not in "\u3002\uff1f\uff01\u2026":
        if last_char in "\u201d\u2019\uff09\u3011\u300b\u300d\u300f\"\')":
            if len(stripped) > 1:
                last_char = stripped[-2]
                in_bracket = True
            else:
                return None
        else:
            return None
    if last_char not in "\u3002\uff1f\uff01\u2026":
        return None
    base = len(stripped) - 1
    if in_bracket:
        base = len(stripped) - 2
    remove_len = 1
    if last_char == "\u2026" and base > 0 and stripped[base - 1] == "\u2026":
        remove_len = 2
        base -= 1
    mutated = text[:base] + text[base + remove_len:]
    if len(mutated.rstrip()) >= 5:
        return mutated, ["\u53e5\u672b\u6807\u70b9"]
    return None


def mutate_to_english_punc_midquote(text: str) -> Optional[Tuple[str, List[str]]]:
    puncs = {
        "\uff0c": ",",
        "\u3002": ".",
        "\uff1a": ":",
        "\uff1b": ";",
    }
    quote = "\u201d"
    if quote not in text:
        return None
    candidates = []
    for i, ch in enumerate(text):
        if ch in puncs and i > 0:
            prev = text[i - 1]
            if "\u4e00" <= prev <= "\u9fff" or prev in "\u201c\u201d\u2018\u2019":
                candidates.append(i)
    if not candidates:
        return None
    idx = random.choice(candidates)
    old = text[idx]
    new = puncs[old]
    mutated = text[:idx] + new + text[idx + 1:]
    return mutated, ["\u4e2d\u82f1\u6587\u6807\u70b9\u6df7\u7528"]


def mutate_double_close(text: str) -> Optional[Tuple[str, List[str]]]:
    closers = {
        "\u201d": "\u201c",
        "\uff09": "\uff08",
        "\u3011": "\u3010",
        "\u300b": "\u300a",
    }
    candidates = []
    for close, open_c in closers.items():
        for i, ch in enumerate(text):
            if ch == close:
                candidates.append((i, open_c))
    if not candidates:
        return None
    idx, open_c = random.choice(candidates)
    mutated = text[:idx + 1] + open_c
    return mutated, ["\u6807\u70b9\u914d\u5bf9\u95ee\u9898"]


MUTATORS = [
    mutate_to_english_punc,
    mutate_add_space_after,
    mutate_add_space_before,
    mutate_remove_closing,
    mutate_duplicate_punc,
    mutate_ellipsis,
    mutate_dunhao_before_end,
    mutate_remove_sentence_end,
    mutate_to_english_punc_midquote,
    mutate_double_close,
]

ERROR_TYPE_LABELS = {
    "mutate_to_english_punc": "\u4e2d\u82f1\u6587\u6807\u70b9\u6df7\u7528",
    "mutate_add_space_after": "\u6807\u70b9\u7a7a\u683c\u95ee\u9898",
    "mutate_add_space_before": "\u6807\u70b9\u7a7a\u683c\u95ee\u9898",
    "mutate_remove_closing": "\u6807\u70b9\u914d\u5bf9\u95ee\u9898",
    "mutate_duplicate_punc": "\u6807\u70b9\u91cd\u590d",
    "mutate_ellipsis": "\u7701\u7565\u53f7\u683c\u5f0f",
    "mutate_dunhao_before_end": "\u987f\u53f7\u4f7f\u7528",
    "mutate_remove_sentence_end": "\u53e5\u672b\u6807\u70b9",
    "mutate_to_english_punc_midquote": "\u4e2d\u82f1\u6587\u6807\u70b9\u6df7\u7528",
    "mutate_double_close": "\u6807\u70b9\u914d\u5bf9\u95ee\u9898",
}


def generate_test_cases(n_per_mutator: int = 30) -> List[Dict]:
    correct_sentences = load_clean_sentences()
    cases = []

    for sent in correct_sentences:
        cases.append({
            "text": sent,
            "expected_error_types": [],
            "category": "clean",
        })

    for mutator in MUTATORS:
        count = 0
        attempts = 0
        while count < n_per_mutator and attempts < n_per_mutator * 5:
            attempts += 1
            sent = random.choice(correct_sentences)
            result = mutator(sent)
            if result is not None:
                mutated, expected = result
                cases.append({
                    "text": mutated,
                    "expected_error_types": expected,
                    "category": "mutated",
                })
                count += 1

    return cases


def evaluate(checker_strict: bool = False) -> Dict:
    cases = generate_test_cases(n_per_mutator=40)
    checker = PunctuationChecker(strict_mode=checker_strict)

    total_mutated = 0
    detected_mutated = 0
    total_clean = 0
    false_positive_cases = 0
    total_fp_errors = 0
    type_recall = {}
    type_total = {}

    for case in cases:
        errors = checker.check(case["text"])
        found_types = set(e.error_type for e in errors)

        if case["expected_error_types"]:
            total_mutated += 1
            expected_set = set(case["expected_error_types"])
            hit = bool(found_types & expected_set)
            if hit:
                detected_mutated += 1
            for et in expected_set:
                type_total[et] = type_total.get(et, 0) + 1
                if et in found_types:
                    type_recall[et] = type_recall.get(et, 0) + 1
        else:
            total_clean += 1
            if errors:
                false_positive_cases += 1
                total_fp_errors += len(errors)

    recall = detected_mutated / total_mutated if total_mutated > 0 else 0.0
    precision = detected_mutated / (detected_mutated + total_fp_errors) if (detected_mutated + total_fp_errors) > 0 else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "f1_score": round(f1, 6),
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "total_cases": len(cases),
        "total_mutated": total_mutated,
        "total_clean": total_clean,
        "detected_mutated": detected_mutated,
        "false_positive_cases": false_positive_cases,
        "total_fp_errors": total_fp_errors,
        "type_recall": {k: round(type_recall.get(k, 0) / type_total[k], 3) for k in type_total},
    }


def main():
    results = evaluate(checker_strict=True)

    print("---")
    for key in ["f1_score", "precision", "recall", "total_cases", "total_mutated",
                "total_clean", "detected_mutated", "false_positive_cases", "total_fp_errors"]:
        val = results[key]
        if isinstance(val, float):
            print(f"{key}: {val:.6f}")
        else:
            print(f"{key}: {val}")

    print("\nper-type recall:")
    for etype, r in sorted(results["type_recall"].items()):
        print(f"  {etype}: {r:.3f}")

    json_path = os.path.join(_SCRIPT_DIR, "eval_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
