# autoresearch: punctuation-checker optimization

This is an experiment to have the LLM autonomously optimize a Chinese punctuation checker.

## Setup

To set up a new experiment:

1. **Agree on a run tag**: propose a tag based on today's date (e.g. `apr29`).
2. **Create the branch**: `git checkout -b autoresearch/<tag>` from current main.
3. **Read the in-scope files**:
   - `evaluate.py` — fixed evaluation harness with synthetic corpus generation. Do not modify.
   - `corpus_clean.txt` — source of correct Chinese sentences used for mutation testing. Do not modify.
   - `punctuation_checker.py` — the file you modify. All checking rules and logic.
4. **Initialize results.tsv**: Create `results.tsv` with just the header row.
5. **Establish baseline**: Run `python evaluate.py > run.log 2>&1` and record the baseline f1_score.
6. **Confirm and go**: Confirm setup looks good.

## Experimentation

**What you CAN do:**
- Modify `punctuation_checker.py` — this is the only file you edit. Everything is fair game: regex patterns, new check methods, improved edge case handling, new error types, etc.

**What you CANNOT do:**
- Modify `evaluate.py`. It is read-only. It contains the fixed evaluation corpus, mutation operators, and metric computation.
- Modify `corpus_clean.txt`.
- Install new packages. Only Python standard library is available.
- Modify the evaluation metric. The f1_score computed by evaluate.py is the ground truth.

**The goal is simple: get the highest f1_score.** The metric combines precision (no false positives on clean text) and recall (detecting injected errors). Both matter equally.

**Simplicity criterion**: All else being equal, simpler is better. A tiny improvement that adds ugly complexity is not worth it. Conversely, removing code and getting equal or better results is a great outcome.

**The first run**: Your very first run should always be the baseline.

## Output format

The evaluate.py script prints output like:

```
---
f1_score:          0.954907
precision:         1.000000
recall:            0.913706
total_cases:       246
total_mutated:     197
total_clean:       49
detected_mutated:  180
false_positive_cases: 0
total_fp_errors:   0
```

You can extract the key metric:
```
grep "^f1_score:" run.log
```

## Logging results

Log each experiment to `results.tsv` (tab-separated):

```
commit	f1_score	precision	recall	status	description
```

1. git commit hash (short, 7 chars)
2. f1_score achieved (e.g. 0.954907) — use 0.000000 for crashes
3. precision — use 0.000000 for crashes
4. recall — use 0.000000 for crashes
5. status: `keep`, `discard`, or `crash`
6. short text description

## The experiment loop

The experiment runs on a dedicated branch (e.g. `autoresearch/apr29`).

LOOP FOREVER:

1. Look at the git state: current branch/commit
2. Tune `punctuation_checker.py` with an experimental idea
3. git commit
4. Run experiment: `python evaluate.py > run.log 2>&1`
5. Read results: `grep "^f1_score:\|^precision:\|^recall:" run.log`
6. If grep is empty → crash. Read `tail -n 50 run.log` for the stack trace, attempt fix.
7. Record results in results.tsv (do NOT commit results.tsv)
8. If f1_score improved (higher) → keep the commit
9. If f1_score is equal or worse → git reset back to previous commit
10. REPEAT

**Crashes**: If a run crashes, fix simple bugs (typos, import errors) and re-run. If the idea is fundamentally broken, log "crash" and move on.

**NEVER STOP**: Once the experiment loop has begun, do NOT pause to ask the human if you should continue. The loop runs until the human interrupts you.

## Analysis tips

After each run, check `eval_results.json` for per-type recall to identify which categories need improvement. Focus your experiments on the weakest categories first.

## External corpus evaluation

After the synthetic evaluation reaches F1=1.0, validate on real-world data:

```bash
# Download external corpora (requires: pip install datasets)
python fetch_corpus.py

# Run three-mode external evaluation
python evaluate_external.py
```

Three evaluation modes:
1. **FP Analysis** — Run checker on clean external text, measure false positive rate
2. **Extended Mutation Test** — Use external sentences as mutation base, measure F1
3. **Real Error Detection** — Test against real punctuation errors from chinese_text_correction

Key finding: news headlines/summaries frequently omit sentence-ending periods. The sentence-end check (SUGGESTION level in strict mode) will have elevated FP rates on news text — this is expected behavior.

See `WORKFLOW.md` for the complete optimization history and external evaluation results.
