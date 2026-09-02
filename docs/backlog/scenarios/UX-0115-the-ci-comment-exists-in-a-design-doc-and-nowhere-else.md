# UX-115: the CI comment exists in a design doc and nowhere else

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-79 (marginal gate + element diff), UX-96 (baseline helper), UX-75 (findings as data) | **Topic:** cli

## Motivation

`design/directions.md` has carried a sketch of "what a good CI comment
should look like" since round 1 — wall-clock vs band, occupancy vs
floor, and a per-element table of what this change added and how well.
Every ingredient now exists and is verified: the band verdict
(UX-59/96), both whole-build gates (UX-39), the marginal gate and the
new/changed element diff with per-element critical-path deltas
(UX-79), cache churn/invalidation roots (UX-92/93), and all of it
published as findings with stable ids (UX-75). What does not exist is
the last inch: **nothing renders these into the artifact a reviewer
actually reads** — a PR comment. Today a CI owner gets exit codes and
a JSON blob, and the design doc's sketch remains a sketch.

This is the highest-leverage remaining piece of the CI story: the
gates decide, but a gate that fails with a wall of JSON gets
threshold-loosened; a gate that fails with *"lib-h.bst: serialized
behind lib-g.bst, +4.1s of new critical path, declared dep never
read"* gets the element fixed.

## Required Fix

1. `bga compare --format ci-comment` (or `bga ci-comment BASELINE
   CANDIDATE`): a markdown rendering of the existing findings — verdict
   line with the band, the two gate outcomes with their one-sentence
   reasons, the new/changed element table (duration, critical-path
   delta, stretch, never-read edges where Plane 2 data exists), and
   cache churn/invalidation when present. No new analysis: it consumes
   `findings[]` and the compare JSON, and every number in it is one
   that already has an id. Deterministic, ≤ ~30 lines for a clean
   change, honest about what was not measured (no Plane 2 → no
   never-read column, said explicitly).
2. A worked GitHub Actions example in `docs/guides/` — checkout,
   capture, `bga baseline --candidate`, post the comment (marker-based
   update-in-place so repeated pushes edit one comment rather than
   spamming) — using this repo's own capture workflow outputs as the
   demonstration data.
3. The rendering carries the run-instance line (UX-95) so two comments
   on two pushes are distinguishable.

## Out of Scope

- New metrics or thresholds (render-only, by design).
- Non-GitHub forges (the markdown is the product; the posting example
  is one forge).

## Acceptance Test

Rendered against three retained real pairs, pasted in the verification
log: (a) the grow-bad pair — the comment shows the failed marginal
gate and names `lib-g/h.bst` with their stretch; (b) the grow-good
pair — passing gates, the additions listed as absorbed; (c) two fdsdk
incremental refs via `bga baseline` — band verdict, retention-worded
churn line, distinct instance stamps. Each renders under 40 lines of
markdown, passes `make lint-docs`'s table rules, and contains no
number that lacks a findings id in the underlying JSON.

## Fix Implemented

`bga compare --format ci-comment` (`bga/report/ci_comment.py`), plus
`--native-report PATH` for the Plane 2 column, and a worked GitHub
Actions guide at [`docs/guides/ci-comment.md`](../../guides/ci-comment.md).

Render-only by construction, not by discipline: the gate verdicts come
from the same predicates `_compare_exit_code` calls
(`regression_exceeds_threshold`, `efficiency_below_floor`,
`efficiency_regression_exceeds_threshold`, the marginal stretch against
`DEFAULT_MAX_ADDITION_STRETCH`), so the comment cannot explain a verdict
the pipeline did not reach. `TestTheCommentAgreesWithTheExitCode` runs
the real CLI and asserts the exit code and the table cell together.

Three shapes the comment refuses to let pass as a clean bill of health:

- a gate nobody requested renders `not requested`, never omitted;
- a gate that could not run renders `not applied` with the reason —
  "this change added no elements with measured work … an empty check,
  not a pass" (`UX-87`'s lesson, in markdown);
- without a Plane 2 report the never-read column is **absent** and says
  so, rather than rendering empty. "Nothing was staged and never read"
  and "nobody looked" are different claims.

## Verification Log

Done 2026-08-19. Three real pairs, rendered and pasted. The round-10
grow-good/grow-bad captures were not retained anywhere, so (a) and (b)
were rebuilt from scratch: `examples/06-macro-micro-optimization/optimized`
plus two libraries copied from `lib-f`, added once fanning out off
`core.bst` and once chained behind `lib-f` and each other. Three real
`bst build` runs, each with its own cold cache.

### (a) grow-bad — the failed marginal gate, with Plane 2

```text
<!-- bga-ci-comment -->

### Build efficiency

**REGRESSED** — wall-clock 17.5s → 20.4s (+2.9s, +16.7%)

judged against the fixed 1% rule (no baseline set supplied)

| Gate | Result | Why |
| --- | --- | --- |
| Marginal efficiency | FAIL | 6.0s of the 6.0s this change added landed on the critical path (stretch 1.00 > 0.50) |
| Whole-build efficiency | pass | occupancy 65% (-0.8pp) |
| Wall-clock regression | FAIL | +2.9s (+16.7%) — outside the fixed 1% rule |

**Elements this change added or moved**

| Element | Duration | Critical path | Declared, never read |
| --- | ---: | --- | --- |
| `lib-g.bst` | 4.0s | yes — new on the path | `core.bst`, `lib-f.bst` |
| `lib-h.bst` | 2.0s | yes — new on the path | `core.bst`, `lib-g.bst` |
| `lib-f.bst` | 6.0s | yes — moved onto the path | `codegen.bst`, `core.bst` |

**Cache** — churn not measured: the candidate is a caches-off run, so every element rebuilt by instruction - an unchanged cache key there is the intended behaviour, not waste.

<sub>baseline 2026-08-19 12:58:14 UTC · candidate 2026-08-19 12:58:52 UTC</sub>
```

26 lines. The gate fails naming `lib-g.bst`/`lib-h.bst` with
stretch 1.00, and the never-read column independently reproduces the
design doc's own parenthetical — `lib-h.bst` declares a build dep on
`lib-g.bst` and opened none of the files it staged. Exit 5, matching
the `FAIL` cell.

### (b) grow-good — passing gates, additions absorbed

```text
<!-- bga-ci-comment -->

### Build efficiency

**REGRESSED** — wall-clock 17.5s → 17.9s (+0.4s, +2.2%)

judged against the fixed 1% rule (no baseline set supplied)

| Gate | Result | Why |
| --- | --- | --- |
| Marginal efficiency | pass | 8.0s added, 0.0s of it on the critical path (stretch 0.00 ≤ 0.50) |
| Whole-build efficiency | pass | occupancy 72% (+6.8pp) |
| Wall-clock regression | FAIL | +0.4s (+2.2%) — outside the fixed 1% rule |

**Elements this change added or moved**

| Element | Duration | Critical path |
| --- | ---: | --- |
| `lib-g.bst` | 4.0s | no — absorbed by existing parallelism |
| `lib-h.bst` | 4.0s | no — absorbed by existing parallelism |

_No Plane 2 capture for the candidate run, so the declared-but-never-read column is absent — not empty._

**Cache** — churn not measured: the candidate is a caches-off run, so every element rebuilt by instruction - an unchanged cache key there is the intended behaviour, not waste.

<sub>baseline 2026-08-19 12:58:14 UTC · candidate 2026-08-19 12:58:33 UTC</sub>
```

27 lines. Marginal gate passes at stretch 0.00 and occupancy *rose*
6.8pp; both additions read "absorbed by existing parallelism". The
wall-clock gate still fails at +2.2%, which is the honest answer for a
change that added 8.0s of real work to a 17.5s build and is exactly why
`UX-79` exists: the whole-build gate cannot tell legitimate growth from
serialization, and the marginal one can.

### (c) two fdsdk incremental refs via `bga baseline`

```text
<!-- bga-ci-comment -->

### Build efficiency

**REGRESSED** — wall-clock 2712.4s → 3614.2s (+901.8s, +33.2%)

band from 3 baseline run(s): 3278.4s .. 3533.2s (median ±3× scaled MAD)

| Gate | Result | Why |
| --- | --- | --- |
| Marginal efficiency | not requested | `--fail-on-inefficient-additions` not passed |
| Whole-build efficiency | not requested | neither `--fail-on-efficiency-regression` nor `--min-efficiency` passed |
| Wall-clock regression | not requested | `--fail-on-regression` not passed |

**Elements** — this change added none and moved none onto the critical path.

**Cache** — no element changed its cache key; 25 rebuilt in both runs, so the rebuild is the cache's retention, not this change.

<sub>baseline 2026-08-18 19:43:56 UTC · candidate 2026-08-17 20:15:03 UTC</sub>
```

20 lines. Band verdict from three real published captures
(3278.4s .. 3533.2s, median ±3× scaled MAD), retention-worded churn line
(`UX-93`), and instance stamps a day apart.

All four rendered files pass `.pymarkdown.json`'s rule set — the same
configuration `make lint-docs` runs — after one fix it caught: MD022
wanted a blank line between the marker and the `###` heading.

### Deviation from the acceptance, recorded

The acceptance asked that the comment "contains no number that lacks a
findings id in the underlying JSON". `compute_findings` is per-run
(`AnalysisResult`), and a *comparison* has no findings list — the
compare JSON publishes structured keys (`deltas`, `element_diff`,
`marginal_efficiency`, `cache_churn`, `baseline_band`) rather than
`findings[]`. The clause is met in substance and not in letter: every
number in the comment is read from one of those keys, and none is
computed in the renderer. Closing the gap properly means giving
`bga compare` a findings list of its own, which is a larger change than
this task and is not smuggled in here.

Tests: 20 in `tests/unit/test_ci_comment.py`.
