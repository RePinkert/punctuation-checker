#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download external Chinese corpora for punctuation checker evaluation.
- UD Chinese-GSD: zero-dependency (urllib), ~5K gold-annotated sentences
- HuggingFace datasets: requires `pip install datasets`
"""

import os
import sys
import urllib.request
import tempfile

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

UD_GSD_BASE = "https://raw.githubusercontent.com/UniversalDependencies/UD_Chinese-GSD/master/"
UD_GSD_FILES = [
    "zh_gsd-ud-train.conllu",
    "zh_gsd-ud-dev.conllu",
    "zh_gsd-ud-test.conllu",
]


def download_file(url: str) -> str:
    print(f"  Downloading {url}...")
    try:
        with urllib.request.urlopen(url, timeout=60) as resp:
            return resp.read().decode("utf-8")
    except Exception as e:
        print(f"  ERROR downloading {url}: {e}")
        return ""


def parse_conllu_sentences(data: str) -> list:
    sentences = []
    current_text = None
    in_tokens = False
    has_punct = False

    for line in data.split("\n"):
        line = line.strip()
        if line.startswith("# text ="):
            current_text = line[len("# text ="):].strip()
            in_tokens = False
            has_punct = False
        elif line.startswith("#"):
            continue
        elif line == "":
            if current_text and in_tokens:
                cn_puncs = "\u3002\uff0c\uff1f\uff01\u2026\u3001\uff1b\uff1a\u201c\u201d\u300a\u300b"
                if any(p in current_text for p in cn_puncs):
                    sentences.append(current_text)
            current_text = None
            in_tokens = False
            has_punct = False
        elif "\t" in line and current_text is not None:
            in_tokens = True
            parts = line.split("\t")
            if len(parts) >= 4 and parts[3] == "PUNCT":
                has_punct = True

    return sentences


def fetch_ud_gsd():
    print("=== Fetching UD Chinese-GSD ===")
    all_sentences = []
    for fname in UD_GSD_FILES:
        url = UD_GSD_BASE + fname
        data = download_file(url)
        if data:
            sents = parse_conllu_sentences(data)
            print(f"  {fname}: {len(sents)} sentences")
            all_sentences.extend(sents)

    out_path = os.path.join(_SCRIPT_DIR, "corpus_ud_gsd.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        for s in all_sentences:
            f.write(s + "\n")
    print(f"  Saved {len(all_sentences)} sentences to {out_path}")
    return len(all_sentences)


def fetch_hf_correction():
    print("\n=== Fetching shibing624/chinese_text_correction ===")
    try:
        from datasets import load_dataset
    except ImportError:
        print("  SKIP: `datasets` not installed. Run: pip install datasets")
        return 0

    ds = load_dataset("shibing624/chinese_text_correction", split="train")
    sentences = set()
    for row in ds:
        target = row.get("target", "").strip()
        if target and len(target) > 5 and len(target) < 500:
            cn_puncs = "\u3002\uff0c\uff1f\uff01"
            if any(p in target for p in cn_puncs):
                sentences.add(target)

    out_path = os.path.join(_SCRIPT_DIR, "corpus_hf_correction.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        for s in sorted(sentences):
            f.write(s + "\n")
    print(f"  Saved {len(sentences)} sentences to {out_path}")
    return len(sentences)


def fetch_hf_news():
    print("\n=== Fetching feilongfl/ChineseNewsSummary ===")
    try:
        from datasets import load_dataset
    except ImportError:
        print("  SKIP: `datasets` not installed.")
        return 0

    ds = load_dataset("feilongfl/ChineseNewsSummary", split="train")
    sentences = set()
    cn_puncs = "\u3002\uff0c\uff1f\uff01"
    for row in ds:
        output_str = row.get("output", "").strip()
        if not output_str:
            continue
        try:
            import json as _json
            data = _json.loads(output_str)
        except Exception:
            continue
        for field in ["summary", "title"]:
            text = data.get(field, "").strip()
            if text and 8 < len(text) < 500:
                if any(p in text for p in cn_puncs):
                    sentences.add(text)

    out_path = os.path.join(_SCRIPT_DIR, "corpus_hf_news.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        for s in sorted(sentences):
            f.write(s + "\n")
    print(f"  Saved {len(sentences)} sentences to {out_path}")
    return len(sentences)


def main():
    total = 0
    total += fetch_ud_gsd()
    total += fetch_hf_correction()
    total += fetch_hf_news()
    print(f"\n=== Total: {total} sentences fetched ===")


if __name__ == "__main__":
    main()
