# UX-95: the report's `Run:` header names the identity, not the run

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-07 (done)

## Motivation

`bga analyze` and `bga compare` label runs with the run-identity hash —
which is *deliberately* stable across captures of the same project,
targets and graph, because its job is comparability (UX-07). But it is
the only identifier the reports print, so two different fdsdk captures
— taken 100 minutes apart, 3434s vs 3406s, different workflow runs —
both display `Run: f12a845e2327de7a…` (observed on the round-11 per-run
refs). In a directory of accumulated baseline captures, or a CI comment
trail, the one printed identifier cannot tell any two same-config runs
apart, which is precisely the situation the UX-81 baseline history now
creates routinely.

The instance-level facts exist in every run directory (`run-context`'s
capture timestamp; in CI, the workflow run id is even in the ref name)
— they are just not surfaced next to the identity.

## Required Fix

Print both, labeled for what they are: keep the identity hash (it says
"these are comparable"), add a run-instance line (capture start
timestamp from run-context, plus the log/source path or CI run id when
known) in `analyze`'s header and in `compare`'s Baseline/Candidate
lines. JSON gains the same fields additively.

## Out of Scope

- Changing the identity hash's definition or any comparability logic.

## Acceptance Test

`bga compare` over two same-config fdsdk captures from the per-run
refs shows identical identity hashes *and* two distinct, human-readable
instance lines (timestamps differing by the real 100 minutes). Golden
tests updated; JSON adds fields without renaming existing ones.

---

## Fix Implemented

An `Instance:` line beside `Run:`, and a `run_instance` object beside
`run_id` in JSON. Additive throughout: `run_id` keeps its meaning and
its value, because comparability logic reads it and nothing about
comparability changed.

`bga analyze`:

```text
Run: f12a845e2327de7a0101a227aaf602b15b8b45a3cfc78185af3485d3472cace8
Instance: 2026-08-18 09:48:55 UTC  /…/set/00-32122941503/run
```

`bga compare`, over two real per-run refs — same identity, two
instances:

```text
Baseline:  f12a845e2327de7a0101a227aaf602b15b8b45a3cfc78185af3485d3472cace8
           2026-08-17 20:15:03 UTC  /…/set/02-32064333551/run
Candidate: f12a845e2327de7a0101a227aaf602b15b8b45a3cfc78185af3485d3472cace8
           2026-08-18 09:48:55 UTC  /…/set/00-32122941503/run
```

Three small decisions, each of which had a tempting wrong answer:

- **UTC, stated.** The capture was taken on a CI runner in a zone this
  process knows nothing about; rendering it in the reader's local time
  would be a fiction dressed as precision.
- **Absent, not "unknown".** A run directory that recorded no wall clock
  has no capture time, and a placeholder beside a real path reads worse
  than the path alone. The JSON omits the key entirely rather than
  emitting an empty object.
- **A zero wall clock is absent too.** Most fixtures in this suite set
  `wall_start_us=0`, and no real capture starts at the epoch; printing
  `1970-01-01` would put a confidently wrong date in every synthetic
  report.

### Two tests it broke, and why neither was a reason to weaken it

- `test_section_stage_gating` renders one topology from two directories
  and asserts identical output. The instance line correctly
  distinguishes them — the feature working — so the test normalises that
  one line out rather than the feature losing the path.
- The golden snapshot compares the whole JSON payload, and
  `run_instance` holds a wall-clock stamp and an absolute path: both are
  properties of the machine that ran it, not of the analysis, so they
  cannot live in a committed snapshot. Stripped in the harness, with the
  identity hash — which is what a snapshot is about — still compared.

Tests: 7 new in `tests/unit/test_run_instance.py`. Suite: 1292 → 1299.

## Verification Log

Done 2026-08-18. The `compare` output above is a real run over two of
the published per-run capture refs: identical identity hashes, two
distinct instance lines, 13.5 hours apart.
