# P1-07: No `--cold`/`--allow-partial-cold` CLI flags; cold publication gate unimplemented

**Priority:** P1 | **Status:** 🔴 Not Started | **Depends on:** `P1-06` (needs the underlying `T∞,cold` computation to exist first)

## Spec Reference
Read only: `sed -n '2133,2182p' docs/specification.md` (Part 37 — CLI, esp. 37.1 Cold Analysis flags) and `sed -n '904,996p' docs/specification.md` (Part 15.3 — Cold Publication Gate).
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
4. If `--allow-partial-cold` is passed without `--cold`, treat it as a no-op or a usage error (your call, but be consistent and document it in `docs/cli.md`) — don't silently enable cold analysis from that flag alone.

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
_(append real command + output here once run, before marking 🟢)_
