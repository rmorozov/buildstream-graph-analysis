# UX-74: one capture yields one finding, so a user on a dense graph pays an hour of CI per step — and the report never says which steps are independent

**Priority:** High | **Status:** 🟢 Done | **Depends on:** `UX-70` (done — which built the per-element simulation this generalizes), `UX-20` (done — whose grouping rule is measured wrong here) | **Topic:** analysis

## Motivation

Round 9's real capture takes ~60 minutes of CI to produce. From it, a
user learns which element to fix first. To learn the *second* one they
must fix the first and capture again — and `UX-70` measured why that is
not a theoretical concern on this graph: **77% of elements have zero
slack**, so the chain re-forms the moment anything shrinks.

The tool can already answer "and then what" from the capture it has. The
whole simulation below is 5 longest-path recomputes at **0.40 ms each**
on this 126-element graph, against the ~60 minutes each real re-capture
costs:

| step | makespan | cumulative saving | what becomes binding next |
|---|---|---|---|
| baseline | 3610.5s | — | cmake-stage1, openssl, python3, doxygen, bison |
| zero `cmake-stage1.bst` | 2040.8s | 1569.8s (43%) | openssl, python3, doxygen, bison |
| zero `openssl.bst` | 1518.2s | 2092.3s (58%) | python3, doxygen, bison, **ninja (149.6s)** |
| zero `python3.bst` | 1423.1s | 2187.4s (61%) | **git-minimal (547.7s)**, doxygen, bison |
| zero `git-minimal.bst` | 878.5s | 2732.1s (76%) | doxygen, bison |
| zero `doxygen.bst` | 480.9s | 3129.6s (87%) | **icu (430.8s)** |

Two of the elements in that right-hand column are among the heaviest in
the entire build and **appear in no report the tool produces today**:

```text
  1569.8s  ON-PATH   components/_private/cmake-stage1.bst
   672.1s  ON-PATH   components/openssl.bst
   639.8s  ON-PATH   components/python3.bst
   547.7s  off-path  components/_private/git-minimal.bst     <- 4th heaviest, invisible
   513.5s  ON-PATH   components/doxygen.bst
   430.8s  off-path  components/icu.bst                      <- 6th heaviest, invisible
```

Their realizable saving today is genuinely 0 — the report is not wrong to
rank them last. But "worth nothing right now" and "worth 547.7s two steps
from now" are different statements, and the user who is planning a
quarter's work needs the second one. Today they discover `git-minimal`
only by spending two fix-and-recapture cycles to find it.

## The parallel-workstreams question, measured

The same simulation answers "can two people work on this at once", and
the answer here is yes, with a number:

```text
individual:  cmake-stage1 1569.8s | openssl 522.5s | doxygen 513.5s
sum:         2605.8s
joint (all three zeroed together):  2605.8s  = 72% of the build
```

On this graph the three top savings are **exactly additive** — measured,
not assumed. That is the single most useful sentence the report could
carry for planning ("these three are worth 72% of the build together, and
they do not overlap"), and it is nowhere: the report states 43.4%, 14.5%
and 14.2% separately and leaves the reader to guess whether they compose.
On a different graph they would not, which is precisely why it must be
computed rather than left to the reader's arithmetic.

## `UX-20`'s independence rule is backwards for a chain-bound build

`bga/structural/batching.py` already exists to answer this, and produced
**0 groups and 10 serialized pairs** on the real capture. Its rule:

> Elements that ARE on the same dependency chain are reported as
> `serialized_pairs` instead - fixing one doesn't help until the other is
> also fixed, so they were deliberately not grouped together.

Measured on real data, that premise is false in both directions:

- `cmake-stage1`, `openssl` and `doxygen` are all on the **same chain**,
  and their savings **add exactly** (2605.8s = sum). Being in series is
  what makes savings compose: shortening two links of one chain shortens
  the chain by both.
- `cmake-stage1` and `git-minimal` are on **different chains**, and their
  joint saving is **1569.8s — the same as `cmake-stage1` alone**. Being
  parallel is what makes savings *not* compose: the other chain was never
  binding.

So `UX-20` groups the elements whose savings take a maximum and refuses
to group the ones whose savings take a sum. It is also fed from
`top_opportunities`, which `UX-71` shows saturates to a single tied value
on this build — a candidate list of five elements that are all on one
chain, which is why it returned zero groups.

The two questions were conflated. They are separate and both worth
answering:

- **Do the savings add?** A property of the *schedule* — answered by
  simulating the set together, which `batching.py` already does.
- **Can two people work on them at once?** A property of the *work* —
  two different elements are two different pieces of work regardless of
  their graph relationship. `cmake-stage1` (a C++ template compile
  problem, per `UX-69`) and `openssl` (a configure-heavy autotools build)
  are two engineers' worth of independent work whose results add.

## Required Fix

1. **Publish the horizon.** After the ranked candidates, name what
   becomes binding after each is fixed, with the cumulative saving —
   the table above, capped at a small number of steps. Every figure is a
   longest-path recompute the tool already performs.
2. **Publish the joint saving of the recommended set**, computed by
   zeroing the set together, and say explicitly whether it equals the sum
   or falls short of it.
3. **Name the latent heavies.** Elements with substantial measured
   duration and zero realizable saving today, which enter the frontier
   within the horizon, listed as "not worth touching yet, worth N s after
   step K".
4. **Fix `UX-20`'s framing.** Group by "do the savings add", which is
   simulated; report graph independence as a separate, secondary fact
   about whether the work can proceed concurrently. Feed it from
   `realizable_saving_us`, not from the saturated score.
5. **Stay honest about the model.** This is a structural simulation over
   *this run's* measured durations: it assumes fixing an element makes it
   instant and that nothing else changes. That is the same "fixing =
   eliminate duration" convention `UX-70` and `best_case_speedup` already
   use, and the report must say so rather than let a 76% number read as a
   forecast.

## Out of Scope

- Predicting *how* to make an element faster. The horizon says where to
  look; `UX-69`'s binary breakdown says what is inside.
- Any claim that the horizon survives a real re-capture unchanged. It is
  a projection from one run's durations; a re-capture is still the
  ground truth, and the point is that a user should not need five of
  them to see five findings.

## Acceptance Test

1. On round 9's capture, `bga analyze` names `components/_private/
   git-minimal.bst` and `components/icu.bst` as latent heavies with the
   step at which each becomes binding.
2. It states the joint saving of its top-3 recommendation (2605.8s, 72%)
   and that it equals the sum on this graph.
3. On a graph where two candidates are on parallel chains, the report
   says their savings do *not* add, with the simulated joint figure.
4. The added cost of the horizon is a bounded number of longest-path
   recomputes, and `bga analyze` on the real capture stays comfortably
   inside its current ~1.1s.

## Fix Implemented

Three new signals, all published in `--format json` and rendered in
`Key Findings`, computed in 17 ms on the real 126-element graph:

```text
  Together, the top 3 are worth 2605.8s (72% of the build) - exactly the sum of
  their individual savings, so they are three separate pieces of work that do not overlap
  Work them in this order (by what a fix is worth, not by size), with what the build
  drops to: cmake-stage1.bst (2041s) -> openssl.bst (1518s) -> doxygen.bst (1005s)
    - the last of those leaves 72% of the build removed, projected from this run
      without building again
  Waiting off the critical path, worth nothing to fix today:
  components/_private/git-minimal.bst (548s), components/icu.bst (431s) (+2 more)
    - they bound how far shortening the chain can go
    (structural projections over this run's measured durations, where "fixed" means
    the element becomes instant - a re-capture is still the ground truth)
```

`git-minimal.bst` is the **4th heaviest element in the whole build** and
`icu.bst` the 6th; before this they appeared nowhere in any output the
tool produced.

### Correction 1: the horizon is greedy by saving, and that changes who appears

This task's table was produced by zeroing the *heaviest* element on each
step's path, which routed through `python3.bst` and surfaced
`git-minimal.bst` as a horizon step. The shipped horizon is greedy by
**realizable saving** — the order a user would actually work in — and it
never fixes `python3.bst`, because it is worth 114.1s. So
`git-minimal.bst` never becomes binding *along that route*, and the
horizon alone would not have named it.

That is the correct answer to "what becomes binding next" and the wrong
answer to "what heavy work is invisible". They are separate questions, so
`latent_heavies` is a separate signal: off-path elements above `UX-65`'s
existing 1%-of-wall-clock floor, sorted by their own duration. It names
`git-minimal.bst` and `icu.bst` regardless of which route the horizon
takes, which is what the acceptance test was really asking for.

### Correction 2: feeding `UX-20` the horizon reintroduced a `UX-44` bug

The obvious reading of Required Fix 4 — feed `compute_batch_opportunities`
from the horizon — is wrong, and the existing test suite caught it. A
later horizon step is worth something *only once the steps above it are
done*; handing those to a batcher that simulates against the baseline
durations ranks an element that cannot move the finish, which is exactly
what `UX-44` removed.

Batching is fed instead from the elements whose saving is realizable
against **this** run — `critical_path_detail` entries with a non-null
`realizable_saving_us` — which is still the `UX-70` ranking rather than
the saturated score, and still un-starves it: **0 groups → 1** on the
real capture (`openssl.bst` + `ninja.bst`, genuinely independent chains),
with 9 serialized pairs.

### The two questions `UX-20` conflated are now answered separately

- **Do the savings add?** `joint_saving`, simulated by zeroing the set
  together in the same longest-path model as `realizable_saving_us`.
  Measured both ways and tested both ways: two links of one chain give
  150 of 150 (they compose); two parallel branches give 100 where the
  individual savings are 40 and 0 (neither the sum nor a maximum, which
  is precisely why it must be simulated).
- **Can the work proceed concurrently?** `batch_opportunities`, whose
  text heading now says so and states that its replay-model figures are
  not the longest-path joint saving in `Key Findings`.

`UX-20`'s grouping model itself is left intact. Rewriting it to the
longest-path model would produce a second, differently-derived answer to
a question `joint_saving` already answers; separating the questions was
the actual defect.

### Concision

The horizon names the same three elements in the same order as `UX-76`'s
fix-order line, with more information, so that line is suppressed when
the horizon renders — no fourth listing of the same names. Pinned by a
test.

Tests: 7 new in `tests/unit/test_optimization_horizon.py`, 6 new in
`tests/unit/test_headline_points_at_the_time.py`. Golden snapshot
regenerated (additive keys only). Suite: 1087 → 1100.

## Verification Log

Filed 2026-08-18 (round 10 preparation). Every figure is from the capture
published as `5eda28a` (run `32064333551`), replayed locally at
`74c94e3`: the successive-zeroing table, the per-element duration list,
and the joint/individual savings are from `compute_critical_path` over
`compute_element_durations(analyzer.normalized_tasks)`; the 0.40 ms
recompute cost is 100 iterations of `compute_critical_path` on the same
graph; the `0 groups / 10 serialized_pairs` result is
`structural.batch_opportunities` in that capture's own `analyze.json`.
