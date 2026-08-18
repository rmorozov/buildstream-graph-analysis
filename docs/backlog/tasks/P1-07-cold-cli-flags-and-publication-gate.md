# P1-07: No `--cold`/`--allow-partial-cold` CLI flags; cold publication gate unimplemented

**Priority:** P1 | **Status:** 🟢 Fixed & Verified (2026-08-13) | **Depends on:** `P1-06` (needs the underlying `T∞,cold` computation to exist first)

## What was fixed
- Added `--cold` (store_true) and `--allow-partial-cold` (store_true) to the `analyze` subcommand.
- Added `--history-dir PATH` (repeatable via `action='append'`), a CLI addition beyond the spec's literal flag list - spec Part 37.1 documents `--cold`/`--allow-partial-cold` but never specifies *where* historical data comes from, and the feature is unusable without a way to point at it. Judged the most natural mechanism given `P1-06`'s file-directory-based `load_historical_runs`; documented in `docs/guides/cli.md`.
- `cmd_analyze` loads historical runs (only when both `--cold` and at least one `--history-dir` are given) and passes `cold`/`allow_partial_cold`/`historical_runs` through to `BuildEfficiencyAnalyzer`, which only attempts cold-floor computation when `cold=True` - default behavior (no flags) is completely unchanged.
- The publication gate itself (Part 15.3) is implemented in `_compute_cold_floor` (`P1-06`): by default, if any element on the resolved cold critical path has no resolvable duration, `t_infinity_cold` is `None`; with `--allow-partial-cold`, it publishes a value with `cold_partial=True`/`cold_confidence='low'`.
- `--allow-partial-cold` without `--cold`: treated as a documented no-op with a logged warning (`--allow-partial-cold has no effect without --cold; ignoring`), not a hard usage error - consistent with the CLI's general style of warning rather than failing on redundant flag combinations.
- `format_text`'s Certified Floors section now shows a `T∞,cold (advisory)` line (with a `(partial, confidence=low)` suffix when applicable) only when `t_infinity_cold` is not `None` - no change to output when `--cold` isn't passed. `format_json` already serializes the entire `floors` dict, so the new keys flow through with no formatter change needed.

## Spec Reference
Read only: `sed -n '2133,2182p' docs/spec/specification.md` (Part 37 — CLI, esp. 37.1 Cold Analysis flags) and `sed -n '904,996p' docs/spec/specification.md` (Part 15.3 — Cold Publication Gate).
Key requirements (quoted):
- Default: `bga floors RUN` reports `T∞,observed` only.
- `--cold` — "enables trustworthy historical cold analysis."
- `--cold --allow-partial-cold` — "enables explicitly heuristic partial estimation," output must be flagged `partial=true`, `confidence=low`.
- Publication gate: by default, if any task on the cold critical path has unavailable duration, `T∞,cold = unavailable`.

## Current Broken Behavior
- `bga/cli.py` has no `--cold` or `--allow-partial-cold` flags at all (check `create_parser()`/`cmd_analyze` — confirm current flag list before adding).
- Cold analysis, once `P1-06` makes it computable, is still unreachable from the CLI without these flags.

## Required Fix
1. Add `--cold` (store_true) and `--allow-partial-cold` (store_true) flags to the `analyze` subcommand's argparse setup.
2. Wire them through to `BuildEfficiencyAnalyzer` so `.analyze()` only attempts cold-floor computation (from `P1-06`) when `--cold` is passed — keep it off by default to avoid surprising users who haven't supplied historical data.
3. Implement the publication gate exactly as specified: if `--cold` is set but any task on the cold critical path has an unavailable duration, `T∞,cold` reports as `unavailable` **unless** `--allow-partial-cold` is also set, in which case it reports a value with `partial=true` and `confidence=low` attached (don't just print a note — these should be structured fields matching whatever shape `AnalysisResult`/the JSON formatter already uses for similar flags, check `bga/ingest/models.py` for the pattern before inventing a new one).
4. If `--allow-partial-cold` is passed without `--cold`, treat it as a no-op or a usage error (your call, but be consistent and document it in `docs/guides/cli.md`) — don't silently enable cold analysis from that flag alone.

## Out of Scope
- Don't touch the actual cold-duration-resolution logic — that's `P1-06`, already done by the time you start this.
- Don't add the other missing subcommands (`graph`/`floors`/etc.) — that's the separate, product-decision-gated `P1-14`. This task only adds flags to the existing `analyze` subcommand.

## Acceptance Test
1. Run `python3 -m bga.cli analyze <fixture-without-history>` (no `--cold`) → output has no cold-floor section, no crash.
2. Run the same with `--cold` and no historical data supplied → `T∞,cold` reports `unavailable`, no crash, exit code 0.
3. Run with `--cold --allow-partial-cold` and partial historical data (some but not all critical-path tasks have history) → `T∞,cold` reports a value with `partial=true`/`confidence=low` visible in the output.
4. Run with `--cold` and full historical coverage → `T∞,cold` reports a real value, no `partial` flag.

Run each variant manually and paste the relevant output section into the Verification Log. Also run `PYTHONPATH=. python3 tests/test_e2e.py` for regression safety.

## Verification Log
```
# 1. No --cold -> no cold-floor section, no crash
$ PYTHONPATH=. python3 -m bga.cli analyze <fixture>
(Certified Floors section has no T∞,cold line)
exit: 0

# 2. --cold, no --history-dir -> unavailable, no crash
$ PYTHONPATH=. python3 -m bga.cli analyze <fixture> --cold --format json
floors: {..., 't_infinity_cold': None, 'cold_partial': False, 'cold_confidence': None, ...}
exit: 0

# 3. --cold --allow-partial-cold, partial historical coverage (one element
#    genuinely unresolvable) -> value with partial=true/confidence=low
$ PYTHONPATH=. python3 -m bga.cli analyze <fixture> --cold --allow-partial-cold --history-dir <hist>
floors: {..., 't_infinity_cold': 40000, 'cold_partial': True, 'cold_confidence': 'low', ...}
text format: "T∞,cold (advisory):          0.04s (partial, confidence=low)"

# 4. --cold, full historical coverage -> real value, no partial flag
$ PYTHONPATH=. python3 -m bga.cli analyze <fixture> --cold --history-dir <hist>
floors: {..., 't_infinity_cold': 40000, 'cold_partial': False, 'cold_confidence': 'high', ...}

# --allow-partial-cold without --cold -> warned, no-op, no crash
$ PYTHONPATH=. python3 -m bga.cli analyze <fixture> --allow-partial-cold
--allow-partial-cold has no effect without --cold; ignoring
(report proceeds normally)

$ PYTHONPATH=. python3 -m pytest tests/ -q
76 passed

$ PYTHONPATH=. python3 tests/test_e2e.py
Results: 7 passed, 0 failed
```
