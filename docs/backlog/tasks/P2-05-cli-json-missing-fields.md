# P2-05: CLI `--format json` silently omits most of `AnalysisResult`

**Priority:** P2 | **Status:** 🟢 Fixed & Verified (found and fixed 2026-08-13 via `tests/test_synthetic_multi_subproject.py`) | **Depends on:** none

## Spec Reference
`sed -n '1513,1628p' docs/spec/specification.md` (Part 32.4 — `analysis/v9` data contract) describes the full output shape: `attribution`, `occupancy`, `timeline`, `floors`, `signals`, `utilisation`, `model`, `confidence`, `violations`. This is a completeness/robustness gap, not a spec-nuance one — the JSON output should reflect the whole `AnalysisResult`, not a hand-picked subset.

## Current Broken Behavior
File: `bga/cli.py:124-178`, function `format_json`.
- Line 175-176: `if hasattr(result, 'structural_metrics') and result.structural_metrics: data['structural'] = result.structural_metrics` — **typo**. The real dataclass field (`bga/ingest/models.py:240`) is `result.structural`, not `result.structural_metrics`. `hasattr` always returns `False`, so `'structural'` is **always** silently absent from JSON output, no matter what `--diagnostics`/other flags are passed.
- `utilisation`, `confidence`, `violations`, and `model` — all real fields on `AnalysisResult` — are **never referenced anywhere in `format_json`** at all, not even attempted. They are unconditionally missing from every JSON report.
- Line 143-152: `if hasattr(result, 'critical_path') and result.critical_path: ...` — dead code. `AnalysisResult` has no `critical_path` attribute at all (the actual critical path lives at `result.signals['critical_path']`, a plain list of element UID strings) — this `hasattr` is always `False`, so this whole block never executes and can be removed or fixed to read from the right place.

**Confirmed empirically**, not just by reading code: running `bga analyze <run> --format json --diagnostics` against `tests/fixtures/synthetic_multi_subproject/` produces a JSON object with only `run_id`, `total_duration_us`, `floors`, `attribution`, `occupancy`, `signals` — `structural`, `utilisation`, `confidence`, and `violations` are absent even though the analyzer computed all of them (verify directly against the Python `AnalysisResult` object from the same run, e.g. via `bga.analyze_run`, to see they're populated but simply never serialized). Reproduce with `tests/test_synthetic_multi_subproject.py::test_cli_json_includes_full_analysis_result` (currently `xfail`-marked pointing at this task).

## Required Fix
1. Fix the typo: `result.structural_metrics` → `result.structural`.
2. Add `utilisation`, `confidence`, and `violations` to the output dict (`model` too, if it's meant to be user-facing — check whether `model` is internal-only scaffolding or a real reportable field per Part 32.4 before including it; the spec lists it, so include it unless there's a reason found during implementation not to).
3. Either fix or remove the dead `critical_path` block (lines 143-152) — since `result.signals['critical_path']` is already included via the `signals` dict a few lines below, the cleanest fix is likely to just delete this dead block rather than duplicate the data under a second top-level key.
4. Consider whether hand-picking fields at all is the right long-term shape here versus serializing the whole `AnalysisResult` generically (e.g. via `dataclasses.asdict` with a custom JSON encoder for enums) — that would make this entire class of "forgot to add a new field" bug structurally impossible going forward. Not required for this task, but worth a one-line note in the tracker if you decide not to do it here, so a future session can pick it up (this ties naturally into `P1-15`'s `bga/report/json.py` extraction).

## Out of Scope
- Don't touch `format_text`/`format_csv` — this task is scoped to `format_json` only; if they have similar gaps, log a new tracker row rather than expanding scope here.

## Acceptance Test
Remove the `@pytest.mark.xfail` from `tests/test_synthetic_multi_subproject.py::test_cli_json_includes_full_analysis_result` and confirm it passes: `PYTHONPATH=. python3 -m pytest tests/test_synthetic_multi_subproject.py::test_cli_json_includes_full_analysis_result -v`. Also run `PYTHONPATH=. python3 -m pytest tests/test_cli.py tests/test_e2e.py -v` for regression safety (the existing CLI JSON test only checks for `floors`/`attribution`/`occupancy` presence, so this shouldn't break it, but confirm).

## Verification Log
Fixed `bga/cli.py::format_json`: corrected `result.structural_metrics` → `result.structural`; added `utilisation`, `confidence`, and `model` (same `hasattr(...) and result.x` pattern as the existing fields); added `violations` unconditionally (an empty list is a meaningful "checked, none found" signal, not the same as the key being absent); removed the dead `hasattr(result, 'critical_path')` block (no such attribute exists - the same data is already present via `signals['critical_path']`).
```
$ PYTHONPATH=. python3 -m pytest tests/test_synthetic_multi_subproject.py::test_cli_json_includes_full_analysis_result -v
XPASS (mark removed, now a plain passing assertion)

$ PYTHONPATH=. python3 -m pytest tests/ -v
24 passed, 1 xfailed
```
No regression on `tests/test_cli.py`'s existing JSON-format assertions (`floors`/`attribution`/`occupancy` presence).
