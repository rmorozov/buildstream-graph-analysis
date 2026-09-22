# UX-899: "this PR made the build N seconds slower" needs a band, not a pair

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-898 (the class), UX-234 (the store as a distribution), the baseline set | **Found by:** the 2026-09-20 rollout brief ([`continuous-build-improvement.md`](../../design/continuous-build-improvement.md), section 1) — the owner wants the review gate to say seconds, not only the diff-only verdict | **Serves:** R4 (the gate), R6 (a contributor who will read the verdict) | **Topic:** analysis | **Area:** bga | **Shape:** judgement

## Motivation

The gate the tool ships for a growing project judges the diff alone
(`--fail-on-inefficient-additions`), and it does so precisely because a
whole-build number is noisy: the README pastes five captures of one
unchanged `freedesktop-sdk` commit spanning **33%** (3614.2s → 2712.4s)
against a 1% significance default. A seconds claim made from one PR
build against one previous build is therefore a coin toss with a
decimal point on it, and a gate that cries wolf is the failure mode R4's
row names.

The rollout asks for the seconds anyway, and it is right to: a reviewer
cannot act on "inefficient additions" alone. What makes it honest is the
instrument the tool already has for exactly this — a baseline *set* and
its noise band — pointed at the review population rather than at a
nightly.

## Required Fix

A gate mode that compares a candidate run against the band of the N most
recent runs **of its own class** (`UX-898`), not against a single
predecessor:

- the verdict carries the delta in seconds, the band, and the number of
  runs the band was computed from;
- inside the band, the verdict is "within the band" and the gate passes
  — and that sentence is the deliverable, not a failure to answer;
- below the minimum baseline count, the gate refuses rather than
  guessing, with an exit code of its own;
- the CI comment says which runs formed the band, so a reviewer can see
  why a number is or is not believed.

The band arithmetic is `bga.compare.compute_band` — reused, not
reimplemented, the rule `cache_trend` already follows.

## Decomposition

surfaces: `bga/compare.py` (the mode and its verdict), the CLI flag and its exit code, `docs/guides/ci-comment.md`, and the `compare/v2` document's verdict keys
guards: a candidate inside the band, one above it, one with too few baselines (refusal), and one whose baselines are of a different class (refused by `UX-898`)
gap: the population is **several hundred review builds a day** (the owner, 2026-09-20), so the band is not starved and the open question is the opposite one — how far back a window may reach before it is describing a different tree; the first cut states the window and the reason
track: `implementer` once the band population is decided; deciding it is the session's
gate: after `UX-898`

## Out of Scope

Per-element blame for the delta — `compare` already names culprits and
this row does not change that. Any change to the diff-only gate, which
keeps its exit code and its meaning.

## Acceptance Test

On a synthetic store of same-class runs, a candidate 1s from the median
reports "within the band" and exits 0; one well outside reports the
delta in seconds, names the band, and exits with the regression code; a
store of two runs refuses with the too-few-baselines code. The CI
comment carries the band's run count. Mutations: widen the band (the
outside case becomes inside), drop the run count from the verdict (the
guard names it), compare against runs of another class (refused, not
silently pooled).

## Outcome

**Premise:** held. The gate said seconds from a pair; the band the tool
already owned was never pointed at the review population.

### The gap, measured

A synthetic store of five review builds at 98..102s, a candidate 3s
above the median — inside the spread those five runs themselves
reached:

```text
$ bga compare BASE CAND --fail-on-regression
Verdict: REGRESSED  (total duration +3.00s, +3.0%, 100.01s -> 103.01s)
Regression gate FAILED: candidate run's total duration regressed beyond
the default significance threshold (verdict: regressed).
exit 4
```

Three seconds inside a population that spans four is a regression to the
fixed 1% rule: `UX-180`'s open seam — the verdict judged against a band,
the gate judged a percentage — fired several hundred times a day.

### After

```text
$ bga compare BASE CAND --band-from-class --fail-on-regression
Verdict: NO SIGNIFICANT CHANGE  (total duration +3.00s, +3.0%, 100.01s -> 103.01s)
  Judged against a noise band from 5 baseline run(s): 95.56s .. 104.46s
  - median 100.01s +/- 3x1.48s (scaled MAD)
exit 0
```

The band is selected, not supplied: the last `N` (default 10) runs of
this store declaring the candidate's own `build_class` (`UX-898`),
newest first, both principals excluded so neither votes on the band it
is judged against. The delta in seconds is unchanged and still printed —
what moved is which rule decides. Below three runs of that class the
gate refuses on its own code rather than falling back:

```text
Band gate REFUSED: the candidate declares review · arch=x86_64 ·
sanitizer=address and this store holds 2 other run(s) of that class
within the last 10, below the 3 a measured band needs. ...
exit 8
```

The CI comment names the members, not only the count, so a window that
reached back across a toolchain bump is visible rather than hidden
inside an `n`.

### Mutations verified red and reverted (8)

`tests/unit/test_the_band_comes_from_the_class.py`, 12 clauses, each
mutation applied alone and reverted:

| # | mutation | reddened |
|---|---|---|
| A1 | `DEFAULT_BAND_K = 30.0` — widen the band | 1: the outside case becomes inside |
| A2 | `_band_name` drops `{band['n']}` | 2: both clauses that name the count |
| A3 | `_band_members` prints "some runs" | 1: which five formed it |
| A4 | `runs_of_class` skips the class test | 2: nightlies and the coverage variant pooled |
| A5 | the shortfall falls back instead of refusing | 3: the refusal, its wording, the class separation |
| A6 | `exclude=()` — the principals vote on their own band | 5 |
| A7 | `regression_gate_failed` ignores `against_band` | 1: the fixed rule decides again |
| A8 | `same_class` compares the type alone | 1: the coverage variant pools |

### Deviation from the Required Fix

The band gate closes `UX-180`'s seam **for this flag only**. Closing it
for `--baseline-run` would change the exit code of every existing
pipeline that supplies a baseline set, which this row was not asked to
do; `test_the_band_decides_the_gate_where_the_fixed_rule_would_not`
pins both halves. The window's default of 10 is reasoned, not measured —
several hundred review builds a day (the owner, 2026-09-20) puts ten
runs under an hour — and the flag takes an argument so a pipeline can
state its own. A store of real review builds is what would settle it.
