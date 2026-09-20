# UX-899: "this PR made the build N seconds slower" needs a band, not a pair

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-898 (the class), UX-234 (the store as a distribution), the baseline set | **Found by:** the 2026-09-20 rollout brief ([`continuous-build-improvement.md`](../../design/continuous-build-improvement.md), section 1) — the owner wants the review gate to say seconds, not only the diff-only verdict | **Serves:** R4 (the gate), R6 (a contributor who will read the verdict) | **Topic:** analysis | **Area:** bga | **Shape:** judgement

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
