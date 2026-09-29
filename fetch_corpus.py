#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Download external Chinese corpora for punctuation checker evaluation.
All three corpora are fetched with the Python standard library only (urllib);
no `datasets` package required.

- UD Chinese-GSD: raw .conllu from GitHub -> ~5K sentences (clean text)
- shibing624/chinese_text_correction: plain .tsv files on HuggingFace ->
  writes corpus_hf_correction.txt (unique corrected targets, clean text) and
  corpus_hf_pairs.tsv (source<TAB>target error/correction pairs for mode C)
- feilongfl/ChineseNewsSummary: plain train.json on HuggingFace -> titles/summaries
"""

import os
import sys
import json
import urllib.request
import tempfile

_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

UD_GSD_BASE = "https://raw.githubusercontent.com/UniversalDependencies/UD_Chinese-GSD/master/"
UD_GSD_FILES = [
    "zh_gsd-ud-train.conllu",
    "zh_gsd-ud-dev.conllu",
    "zh_gsd-ud-test.conllu",
]

HF_CORRECTION_BASE = "https://huggingface.co/datasets/shibing624/chinese_text_correction/resolve/main/"
HF_CORRECTION_FILES = [
    "lemon_enc.tsv",
    "lemon_new.tsv",
    "lemon_nov.tsv",
    "lemon_car.tsv",
    "lemon_cot.tsv",
    "lemon_gam.tsv",
    "lemon_mec.tsv",
    "TextProofreadingCompetition.tsv",
    "grammar.tsv",
    "ec_law.tsv",
    "ec_med.tsv",
    "ec_odw.tsv",
    "cscd_ns.tsv",
    "medical_csc.tsv",
]

HF_NEWS_BASE = "https://huggingface.co/datasets/feilongfl/ChineseNewsSummary/resolve/main/"
HF_NEWS_FILE = "train.json"


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
    """Download shibing624/chinese_text_correction as plain TSVs (stdlib only).

    Produces two files:
      - corpus_hf_correction.txt : unique corrected `target` sentences (clean text, modes A/B)
      - corpus_hf_pairs.tsv      : every `source<TAB>target` row (mode C real-error test)
    """
    print("\n=== Fetching shibing624/chinese_text_correction (TSV via urllib) ===")
    sentences = set()
    pairs = []
    for fname in HF_CORRECTION_FILES:
        url = HF_CORRECTION_BASE + fname
        data = download_file(url)
        if not data:
            continue
        count = 0
        lines = data.split("\n")
        for i, line in enumerate(lines):
            if i == 0 and line.lower().startswith("source"):
                continue  # header
            parts = line.split("\t")
            if len(parts) < 2:
                continue
            source = parts[0].strip()
            target = parts[1].strip()
            if not source or not target:
                continue
            count += 1
            pairs.append((source, target))
            if 5 < len(target) < 500:
                cn_puncs = "\u3002\uff0c\uff1f\uff01"
                if any(p in target for p in cn_puncs):
                    sentences.add(target)
        print(f"  {fname}: {count} rows")

    # Clean-text corpus (modes A/B)
    out_path = os.path.join(_SCRIPT_DIR, "corpus_hf_correction.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        for s in sorted(sentences):
            f.write(s + "\n")
    print(f"  Saved {len(sentences)} clean sentences to {out_path}")

    # Error/correction pairs (mode C). TSV-escape newlines/tabs defensively.
    pairs_path = os.path.join(_SCRIPT_DIR, "corpus_hf_pairs.tsv")
    with open(pairs_path, "w", encoding="utf-8", newline="\n") as f:
        for source, target in pairs:
            f.write(source.replace("\t", " ").replace("\n", " ")
                    + "\t" + target.replace("\t", " ").replace("\n", " ") + "\n")
    print(f"  Saved {len(pairs)} source/target pairs to {pairs_path}")
    return len(sentences)


def fetch_hf_news():
    """Download feilongfl/ChineseNewsSummary as a plain JSON array (stdlib only)."""
    print("\n=== Fetching feilongfl/ChineseNewsSummary (train.json via urllib) ===")
    url = HF_NEWS_BASE + HF_NEWS_FILE
    raw = download_file(url)
    if not raw:
        print("  SKIP: could not download train.json")
        return 0
    try:
        rows = json.loads(raw)
    except Exception as e:
        print(f"  ERROR parsing train.json: {e}")
        return 0

    sentences = set()
    cn_puncs = "\u3002\uff0c\uff1f\uff01"
    for row in rows:
        output_str = (row.get("output") or "").strip()
        if not output_str:
            continue
        try:
            data = json.loads(output_str)
        except Exception:
            continue
        for field in ["summary", "title"]:
            text = (data.get(field) or "").strip()
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
