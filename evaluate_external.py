#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
External corpus evaluation for punctuation checker.
Three evaluation modes:
  A. Clean text FP rate on external corpora
  B. Extended mutation test using external sentences
  C. Real error detection (if HF correction corpus available)
"""

import sys
import os
import json
import random
import re
from typing import List, Dict, Tuple, Optional
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from punctuation_checker import PunctuationChecker, ErrorLevel

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SEED = 42
random.seed(SEED)


def load_corpus(filename: str) -> List[str]:
    path = os.path.join(_SCRIPT_DIR, filename)
    if not os.path.exists(path):
        print(f"  WARNING: {path} not found, skipping")
        return []
    sentences = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and len(line) > 3:
                sentences.append(line)
    return sentences


def run_fp_analysis(checker: PunctuationChecker, sentences: List[str], corpus_name: str) -> Dict:
    print(f"\n--- FP Analysis: {corpus_name} ({len(sentences)} sentences) ---")
    fp_cases = []
    total = 0
    skipped = 0
    error_type_counts = Counter()
    error_messages = Counter()

    for sent in sentences:
        errors = checker.check(sent)
        if errors:
            fp_cases.append({"text": sent, "errors": errors})
            for e in errors:
                error_type_counts[e.error_type] += 1
                error_messages[e.message] += 1
        total += 1

    fp_rate = len(fp_cases) / total if total > 0 else 0.0
    total_errors = sum(len(c["errors"]) for c in fp_cases)

    print(f"  Total sentences: {total}")
    print(f"  FP sentences: {len(fp_cases)} ({fp_rate:.2%})")
    print(f"  Total FP errors: {total_errors}")
    print(f"  Error types:")
    for etype, count in error_type_counts.most_common():
        print(f"    {etype}: {count}")

    return {
        "corpus": corpus_name,
        "total_sentences": total,
        "fp_sentences": len(fp_cases),
        "fp_rate": round(fp_rate, 6),
        "total_fp_errors": total_errors,
        "error_type_counts": dict(error_type_counts),
        "top_fp_cases": [
            {"text": c["text"][:100], "errors": [
                {"type": e.error_type, "message": e.message}
                for e in c["errors"][:3]
            ]}
            for c in fp_cases[:30]
        ],
    }


ENGLISH_PUNC_MAP = {
    "\uff0c": ",",
    "\u3002": ".",
    "\uff1a": ":",
    "\uff1b": ";",
    "\uff1f": "?",
    "\uff01": "!",
}

SPACE_AFTER_PUNCS = "\uff0c\u3002\uff1b\uff1a\uff1f\uff01\u3001\uff09\u300b\u3011\u300d\u300f"
SPACE_BEFORE_PUNCS = "\uff0c\u3002\uff1b\uff1a\uff1f\uff01\u3001\uff08\u300a\u3010\u300c\u300e"

CLOSING_PUNCTS = {
    "\u201c": "\u201d",
    "\u2018": "\u2019",
    "\uff08": "\uff09",
    "\u3010": "\u3011",
    "\u300a": "\u300b",
    "\u300c": "\u300d",
    "\u300e": "\u300f",
}

REPEATABLE_PUNCS = [
    "\uff0c", "\u3002", "\uff1b", "\uff1a", "\u3001",
    "\uff09", "\u3011", "\u300b",
]


def mutate_to_english_punc(text: str) -> Optional[Tuple[str, List[str]]]:
    candidates = [i for i, ch in enumerate(text) if ch in ENGLISH_PUNC_MAP]
    if not candidates:
        return None
    idx = random.choice(candidates)
    old = text[idx]
    new = ENGLISH_PUNC_MAP[old]
    return text[:idx] + new + text[idx + 1:], ["\u4e2d\u82f1\u6587\u6807\u70b9\u6df7\u7528"]


def mutate_add_space_after(text: str) -> Optional[Tuple[str, List[str]]]:
    candidates = [i for i, ch in enumerate(text)
                  if ch in SPACE_AFTER_PUNCS and i + 1 < len(text) and text[i + 1] not in " \t"]
    if not candidates:
        return None
    idx = random.choice(candidates)
    return text[:idx + 1] + " " + text[idx + 1:], ["\u6807\u70b9\u7a7a\u683c\u95ee\u9898"]


def mutate_add_space_before(text: str) -> Optional[Tuple[str, List[str]]]:
    candidates = [i for i, ch in enumerate(text)
                  if ch in SPACE_BEFORE_PUNCS and i > 0 and text[i - 1] not in " \t"]
    if not candidates:
        return None
    idx = random.choice(candidates)
    return text[:idx] + " " + text[idx:], ["\u6807\u70b9\u7a7a\u683c\u95ee\u9898"]


def mutate_remove_closing(text: str) -> Optional[Tuple[str, List[str]]]:
    candidates = []
    for left, right in CLOSING_PUNCTS.items():
        if right in text:
            for i, ch in enumerate(text):
                if ch == right:
                    candidates.append((i, left))
    if not candidates:
        return None
    idx, _ = random.choice(candidates)
    return text[:idx] + text[idx + 1:], ["\u6807\u70b9\u914d\u5bf9\u95ee\u9898"]


def mutate_duplicate_punc(text: str) -> Optional[Tuple[str, List[str]]]:
    candidates = []
    for punc in REPEATABLE_PUNCS:
        for i, ch in enumerate(text):
            if ch == punc:
                candidates.append((i, punc))
    if not candidates:
        return None
    idx, punc = random.choice(candidates)
    return text[:idx + 1] + punc + text[idx + 1:], ["\u6807\u70b9\u91cd\u590d"]


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
    candidates = [i for i, ch in enumerate(text)
                  if ch == "\u3001" and i + 1 < len(text) and text[i + 1] not in "\u3002\uff1f\uff01"]
    if not candidates:
        return None
    idx = random.choice(candidates)
    end = random.choice(["\u3002", "\uff1f", "\uff01"])
    return text[:idx + 1] + end + text[idx + 1:], ["\u987f\u53f7\u4f7f\u7528"]


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


MUTATORS = [
    mutate_to_english_punc,
    mutate_add_space_after,
    mutate_add_space_before,
    mutate_remove_closing,
    mutate_duplicate_punc,
    mutate_ellipsis,
    mutate_dunhao_before_end,
    mutate_remove_sentence_end,
]


def run_mutation_test(checker: PunctuationChecker, sentences: List[str],
                      corpus_name: str, n_per_mutator: int = 50) -> Dict:
    print(f"\n--- Mutation Test: {corpus_name} ({len(sentences)} base sentences) ---")

    cases = []
    for sent in sentences:
        cases.append({"text": sent, "expected": []})

    for mutator in MUTATORS:
        count = 0
        attempts = 0
        while count < n_per_mutator and attempts < n_per_mutator * 5:
            attempts += 1
            sent = random.choice(sentences)
            result = mutator(sent)
            if result is not None:
                mutated, expected = result
                cases.append({"text": mutated, "expected": expected})
                count += 1

    total_mutated = 0
    detected = 0
    total_clean = 0
    fp_errors = 0
    type_recall = {}
    type_total = {}
    misses = {}

    for case in cases:
        errors = checker.check(case["text"])
        found_types = set(e.error_type for e in errors)

        if case["expected"]:
            total_mutated += 1
            expected_set = set(case["expected"])
            hit = bool(found_types & expected_set)
            if hit:
                detected += 1
            else:
                for et in expected_set:
                    if et not in misses:
                        misses[et] = []
                    misses[et].append(case["text"][:80])
            for et in expected_set:
                type_total[et] = type_total.get(et, 0) + 1
                if et in found_types:
                    type_recall[et] = type_recall.get(et, 0) + 1
        else:
            total_clean += 1
            if errors:
                fp_errors += len(errors)

    recall = detected / total_mutated if total_mutated > 0 else 0.0
    precision = detected / (detected + fp_errors) if (detected + fp_errors) > 0 else 1.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    per_type = {k: round(type_recall.get(k, 0) / type_total[k], 3) for k in type_total}

    print(f"  F1={f1:.4f}  P={precision:.4f}  R={recall:.4f}")
    print(f"  Cases: {len(cases)} (clean={total_clean}, mutated={total_mutated})")
    print(f"  Per-type recall:")
    for etype, r in sorted(per_type.items()):
        print(f"    {etype}: {r:.3f}")

    if misses:
        miss_path = os.path.join(_SCRIPT_DIR, f"misses_{corpus_name}.json")
        with open(miss_path, "w", encoding="utf-8") as f:
            json.dump(misses, f, ensure_ascii=False, indent=2)
        print(f"  Miss details saved to {miss_path}")

    return {
        "corpus": corpus_name,
        "f1_score": round(f1, 6),
        "precision": round(precision, 6),
        "recall": round(recall, 6),
        "total_cases": len(cases),
        "total_mutated": total_mutated,
        "total_clean": total_clean,
        "detected": detected,
        "fp_errors": fp_errors,
        "per_type_recall": per_type,
    }


def run_real_error_test(checker: PunctuationChecker) -> Optional[Dict]:
    correction_path = os.path.join(_SCRIPT_DIR, "corpus_hf_correction.txt")
    if not os.path.exists(correction_path):
        print("\n--- Real Error Test: SKIPPED (no HF correction corpus) ---")
        return None

    print("\n--- Real Error Test: shibing624/chinese_text_correction ---")
    try:
        from datasets import load_dataset
    except ImportError:
        print("  SKIP: `datasets` not installed")
        return None

    ds = load_dataset("shibing624/chinese_text_correction", split="train", trust_remote_code=True)

    punct_diff_lines = []
    total_lines = 0
    detected = 0
    error_type_counts = Counter()

    for row in ds:
        source = row.get("source", "").strip()
        target = row.get("target", "").strip()
        if not source or not target:
            continue
        total_lines += 1

        source_puncs = set(i for i, ch in enumerate(source) if ch in
                           "\uff0c\u3002\uff1b\uff1a\uff1f\uff01\u3001\u201c\u201d\uff08\uff09\u3010\u3011\u300a\u300b")
        target_puncs = set(i for i, ch in enumerate(target) if ch in
                           "\uff0c\u3002\uff1b\uff1a\uff1f\uff01\u3001\u201c\u201d\uff08\uff09\u3010\u3011\u300a\u300b")

        has_punct_diff = False
        if len(source) > 0 and len(target) > 0:
            if source != target:
                for i in range(min(len(source), len(target))):
                    if source[i] != target[i]:
                        sc = source[i]
                        tc = target[i]
                        s_is_punc = sc in "\uff0c\u3002\uff1b\uff1a\uff1f\uff01\u3001\u201c\u201d\uff08\uff09\u3010\u3011\u300a\u300b,.:;?!)\"'("
                        t_is_punc = tc in "\uff0c\u3002\uff1b\uff1a\uff1f\uff01\u3001\u201c\u201d\uff08\uff09\u3010\u3011\u300a\u300b,.:;?!)\"'("
                        if s_is_punc or t_is_punc:
                            has_punct_diff = True
                            break

        if not has_punct_diff:
            continue

        punct_diff_lines.append((source, target))
        errors = checker.check(source)
        if errors:
            detected += 1
            for e in errors:
                error_type_counts[e.error_type] += 1

    total = len(punct_diff_lines)
    recall = detected / total if total > 0 else 0.0

    print(f"  Total lines scanned: {total_lines}")
    print(f"  Lines with punctuation diffs: {total}")
    print(f"  Checker detected errors in: {detected} ({recall:.2%})")
    print(f"  Error types found:")
    for etype, count in error_type_counts.most_common():
        print(f"    {etype}: {count}")

    return {
        "corpus": "chinese_text_correction",
        "total_scanned": total_lines,
        "punct_diff_lines": total,
        "detected": detected,
        "recall": round(recall, 6),
        "error_type_counts": dict(error_type_counts),
    }


def main():
    checker = PunctuationChecker(strict_mode=True)
    all_results = {"fp_analysis": [], "mutation_test": [], "real_error_test": None}

    corpora = [
        ("corpus_ud_gsd.txt", "UD Chinese-GSD"),
        ("corpus_hf_news.txt", "HF ChineseNewsSummary"),
    ]

    print("=" * 60)
    print("MODE A: Clean Text False Positive Analysis")
    print("=" * 60)
    for filename, name in corpora:
        sentences = load_corpus(filename)
        if sentences:
            # sample up to 2000 to keep runtime reasonable
            if len(sentences) > 2000:
                random.seed(SEED)
                sentences = random.sample(sentences, 2000)
            result = run_fp_analysis(checker, sentences, name)
            all_results["fp_analysis"].append(result)

    print("\n" + "=" * 60)
    print("MODE B: Extended Mutation Test")
    print("=" * 60)
    for filename, name in corpora:
        sentences = load_corpus(filename)
        if sentences:
            random.seed(SEED)
            # use up to 500 sentences as mutation base
            if len(sentences) > 500:
                sentences = random.sample(sentences, 500)
            result = run_mutation_test(checker, sentences, name, n_per_mutator=50)
            all_results["mutation_test"].append(result)

    print("\n" + "=" * 60)
    print("MODE C: Real Error Detection")
    print("=" * 60)
    real_result = run_real_error_test(checker)
    if real_result:
        all_results["real_error_test"] = real_result

    results_path = os.path.join(_SCRIPT_DIR, "eval_external_results.json")
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)
    print(f"\nResults saved to {results_path}")


if __name__ == "__main__":
    main()
