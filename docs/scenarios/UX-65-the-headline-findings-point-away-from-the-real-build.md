# UX-65: on the only real build we have, both headline rankings point away from the answer — the tool leads with 3.47s and never names the element that is 43% of the build

**Priority:** High | **Status:** 🔴 Open | **Depends on:** — (blocks calling the tool an MVP)

## Motivation

The question this project keeps asking is *"is the tool what it claims to
be — would a real user find real low-hanging fruit with it?"* Round 7 is
the first capture good enough to answer that, and the answer is **the
engine yes, the report no**.

Here is what `bga analyze` told a user about a real 3587.6-second
`freedesktop-sdk` build, verbatim:

```
  Biggest Opportunity: 0.1% of wall-clock time is UNTRACKED HEAD (3.47s)
  Elements Most Worth Optimizing First (by blast radius):
    1. bootstrap/base-sdk/binary-seed-x86_64.bst (124 downstream) [structural: import]
    2. bootstrap/base-sdk/binary-seed.bst (123 downstream) [structural: compose]
    3. bootstrap/gnu-config.bst (118 downstream)
  Efficiency Score: 1.00 (scheduling is near the certified floor...)
```

Here is what the same run's own Critical Path block says, further down:

```
    components/_private/cmake-stage1.bst     1558.75s ( 43.5% of path)
    components/openssl.bst                    679.90s ( 19.0% of path)
    components/python3.bst                    625.75s ( 17.5% of path)
    components/doxygen.bst                    503.55s ( 14.1% of path)
```

**Four elements are 3367.95s of a 3583.90s critical path — 94.0% of the
entire build.** None of them appears in either headline ranking.

The tool leads a user toward **3.47 seconds** and a list topped by two
elements it simultaneously labels *"structural: may not reflect real
compute work"*.

## Why each ranking fails, specifically

**"Biggest Opportunity" is `max(non_execution_category)`.** That is a
sound question — *where did time go that was not useful work?* — and this
build's answer is "nowhere": attribution is **99.9% EXECUTION_ON_CHAIN**,
with dependency wait, resource wait, scheduler wait, idle and retry all
exactly 0.00s. So the maximum over the remaining categories is
UNTRACKED_HEAD at 0.1%, and the headline degenerates to noise.

This is not a mis-computation. It is a question that has no useful answer
for an execution-bound build, asked as if it always does.

**Blast radius is the wrong ranking for this build's shape.** It measures
how many elements depend on you, which matters when the graph is the
problem. Here the graph is *not* the problem: `T∞ = LB = T_C = 3583.90s`
against a 3587.6s wall clock, so the build is entirely critical-path-
bound and only 33.8% of dispatch capacity is used. What matters is *how
long you take*, and `cmake-stage1` — 43.5% of the path on its own — has a
blast radius too small to make the list.

## What the tool gets right, and it is most of it

This is a presentation failure, not an analysis one, and the distinction
matters:

- Every number checks out. `T∞ = LB = T_C = total` is *correct* for a
  build this serialized, not a degenerate case.
- The critical path is named in full, with per-element durations and
  shares — `UX-33` already fixed that, and it is where the real answer is.
- Confidence 1.00, zero violations, the incremental scenario correctly
  identified (`UX-55`).
- `UX-63` independently flags `cmake-stage1` as the peak-memory element
  at 1902 MB, which is the *same* element the critical path is telling
  you about. Two signals agree and neither reaches the headline.

The tool knows. It does not say. That is exactly the class of problem
`UX-33`/`UX-34`/`UX-35` were filed for — this task applies it to the two
lines a user reads first.

## Required Fix

1. **Lead with where the time is.** When attribution is dominated by
   execution, the biggest opportunity is not a wait category — it is the
   heaviest elements on the critical path. Say so: *"4 elements are 94%
   of this build's critical path; `cmake-stage1.bst` alone is 43.5%."*
2. **Rank by what governs this build.** Blast radius when the graph is
   the constraint (low occupancy *and* short critical path relative to
   total work); critical-path share when the chain is. The run already
   computes both numbers needed to tell which.
3. **Never headline a category below a floor of significance.** A
   "biggest opportunity" of 0.1% should say "no significant non-execution
   time — this build is execution-bound", which is a real and useful
   finding, rather than naming a 3.47-second category.
4. **Join the agreeing signals.** Peak memory (`UX-63`), critical-path
   share and per-element parallelism (`UX-32`) all point at
   `cmake-stage1` here. One line that says so is worth more than three
   blocks a reader has to cross-reference.

## Out of Scope

- The attribution model itself. 99.9% execution-on-chain is the *correct*
  answer for this build; the defect is presenting "largest of the
  remaining 0.1%" as the headline.
- `efficiency_score`'s definition, which `UX-27` already established
  measures scheduling against the given graph and is correctly 1.00 here.
  The fix is not to change the score but to stop letting it be the last
  word when occupancy is 33.8%.

## Acceptance Test

1. On round 7's real capture, the Key Findings block names
   `components/_private/cmake-stage1.bst` and states its share of the
   critical path.
2. A build with genuine wait time still leads with the wait category —
   this must not become "always show the critical path" .
3. An execution-bound build says so explicitly rather than reporting a
   sub-1% category as its biggest opportunity.
4. `examples/06`'s deliberately mis-optimized variant, where blast radius
   *is* the right ranking, still ranks by blast radius.

## Verification Log

Filed 2026-08-17 (round 8 preparation). Every quoted line is verbatim
from `analyze.txt` in the capture published to `captures/fdsdk-latest` as
`df20544` (run `32044281643`); the 94.0% figure is the sum of the four
named elements' durations against `t_infinity_observed` from the same
run's `analyze.json`. The `max(non_execution)` selection was read
directly from `bga/report/text.py`.
