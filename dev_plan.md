# Dev Plan: Robustness Improvements for `backtest_hh_hl.py`

---

## Overview

**Goal:** Make the backtester resilient to bad inputs, malformed data, and edge cases so it can run reliably across many CSV files in batch.

**Scope:** `python_script/backtest_hh_hl.py` only. No changes to strategy logic or output format.

---

## Phase 1 — CSV Input Hardening ✅ Complete

| # | Task | Details |
|---|---|---|
| 1.1 | **Validate CSV columns** | Before parsing, confirm all required columns (`time`, `open`, `high`, `low`, `close`) exist in `read_csv`. If missing, print a clear error listing which columns are missing and return empty list. |
| 1.2 | **Skip malformed rows** | Wrap each row's `float()` conversion in `try/except (ValueError, KeyError)`. Print a warning with row number and reason, skip the row, continue. |
| 1.3 | **Handle empty input** | After `read_csv`, if `rows` is empty, print `"No valid data. Exiting."` and return 1 from `main()` (avoids `IndexError` on `rows[0]['time']`). |
| 1.4 | **Handle unreadable files** | Wrap `open()` in `try/except (IOError, PermissionError)`. Print error and return empty list. |

**Target location:** `read_csv` (line 261), `main` (line 294)

---

## Phase 2 — Argument Validation

| # | Task | Details |
|---|---|---|
| 2.1 | **Validate `--length`** | Reject values `< 2` (a pivot needs at least 1 bar on each side). Use `parser.error()` for clean argparse-style exit. |
| 2.2 | **Validate `--sl-buffer`** | Reject negative values. A zero buffer is valid (SL = HL), but negative makes no sense. |
| 2.3 | **Validate `--output` / `--report` paths** | Check parent directory exists before writing. If not, warn and skip the write instead of crashing. |

**Target location:** `main` (line 290), after `parser.parse_args()`

---

## Phase 3 — Runtime Safety

| # | Task | Details |
|---|---|---|
| 3.1 | **Replace `raise SystemExit` with `sys.exit`** | Consistent with Python conventions and the other script in the folder. |
| 3.2 | **Add tolerance for float comparisons** | Introduce a module-level epsilon (e.g., `EPS = 1e-9`) and use it in TP/SL checks, or add a comment acknowledging the intentional strict comparison. |
| 3.3 | **Remove dead parameter** | Drop unused `swings` parameter from `export_trades_csv`. Update the call site. |
| 3.4 | **Fix truthiness edge case** | Change `'LH' if prev_sh else 'SH'` → `'LH' if prev_sh is not None else 'SH'` (same for `prev_sl`). Price of 0.0 would misclassify. |

**Target location:** Throughout

---

## Phase 4 — Logging Infrastructure

| # | Task | Details |
|---|---|---|
| 4.1 | **Add `logging` module** | Replace `print()` status messages with `logging.info()`. Keep `print()` only for the final report output. |
| 4.2 | **Add `--verbose` flag** | Optional `-v`/`--verbose` flag to increase log level to DEBUG for detailed row-level diagnostics during batch runs. |

**Target location:** `main` (line 290), top-level imports

---

## Phase 5 — Edge-Case Testing

| # | Task | Details |
|---|---|---|
| 5.1 | **Create test fixtures** | Add CSV fixtures to `python_script/tests/fixtures/`: (a) normal data, (b) malformed rows, (c) empty file, (d) fewer rows than pivot length. |
| 5.2 | **Write unit tests** | Use `pytest` to verify: `read_csv` skips bad rows gracefully, `main` exits cleanly on empty data, `--length=0` is rejected, `detect_pivots` returns correct values for a known sequence. |
| 5.3 | **Regression test** | Run with a real CSV from `data/` to confirm no behavioral change. |

**Target location:** New `python_script/tests/` directory

---

## Verification Checklist

```bash
# After implementation, all should pass without crashes:
python3 python_script/backtest_hh_hl.py data/empty.csv
python3 python_script/backtest_hh_hl.py data/malformed.csv
python3 python_script/backtest_hh_hl.py nonexistent.csv
python3 python_script/backtest_hh_hl.py data/normal.csv --length 0
python3 python_script/backtest_hh_hl.py data/normal.csv --sl-buffer -1
python3 python_script/backtest_hh_hl.py data/normal.csv -o /tmp/trades.csv -r /tmp/report.txt
python3 python_script/backtest_hh_hl.py data/normal.csv --verbose
```

---

## Suggested Order of Execution

1. **Phase 1** — highest impact; prevents crashes on real-world data (done)
2. **Phase 2** — quick wins; prevents invalid usage
3. **Phase 3** — cleanup; reduces subtle bug surface
4. **Phase 4** — nice-to-have for batch usability
5. **Phase 5** — validates all of the above
