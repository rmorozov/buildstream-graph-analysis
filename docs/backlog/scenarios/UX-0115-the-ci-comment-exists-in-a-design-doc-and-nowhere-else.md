# UX-115: the CI comment exists in a design doc and nowhere else

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-79 (marginal gate + element diff), UX-96 (baseline helper), UX-75 (findings as data)

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
