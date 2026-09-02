# UX-120: the merge candidate has never fired on real data

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-100 (reopened by this filing) | **Topic:** guards

## Motivation

UX-100's acceptance named a positive case: *"a purpose-built
fine-grained example (N trivial elements sharing one heavy dependency)
… the merge candidate names the group, and the projected saving is
within the documented band of a real merged rebuild."* That fixture was
never built and the clause never ran — and unlike the task's two other
deviations, both recorded in the file, this omission is recorded
nowhere. The merge-candidate branch and its replayed projection have
fired only on synthetic unit-test input; every real capture it has seen
(`examples/06`, fdsdk incremental) correctly produced the *negative*
answer, which cannot distinguish a working detector from an inert one —
the exact evidence gap `examples/07` was built to close for UX-46.

Round 12 reproduced the negative results live (no candidates on either
capture) and downgraded UX-100 to 🟡 accordingly.

## Required Fix

Build the fine-grained fixture the acceptance describes (an
`examples/06` variant with sub-second libs sharing the staged
toolchain), capture it, and run the full loop: the merge candidate
names the group with its projected saving; then actually merge the
group and rebuild, and record measured-vs-projected. If the projection
misses its own documented band, that is the finding — fix or re-hedge
the projection before returning UX-100 to 🟢.

## Out of Scope

- The split-candidate half (its fdsdk evidence path ran).

## Acceptance Test

UX-100's original clause 1, run and pasted: fixture, capture, the
fired candidate, the real merged rebuild's number, and the band
comparison. `examples/06/optimized` still yields no candidate.

## Fix Implemented

`examples/09-fine-grained-siblings` — eight elements with the identical
build-dependency set, each doing sub-second work in a sandbox that stages
a shared sysroot — plus `merged/`, the same eight translation units in
one element. The merge candidate has now fired on real data, and the
projection has been checked against a real merged rebuild.

### The obstacle was the instrument, not the shape

The first attempt built exactly what the acceptance describes — eight
trivial libs sharing the staged C++ toolchain — and the candidate did
not fire. Measured:

```text
tiny-1.bst toll=0.00s total=1.00s share=0.00
tiny-2.bst toll=0.00s total=1.00s share=0.00
...
```

BuildStream stages dependencies by hardlink and times its own phases to
the second, so the project's real 7,969-file toolchain stages in
`00:00:00` and the toll rounds to zero:

```text
[--:--:--] START   [58239117] tiny-3.bst: Staging dependencies at: /
[00:00:00] SUCCESS [58239117] tiny-3.bst: Staging dependencies at: /
```

That is the same quantization `UX-100`'s own code comment already
recorded against the freedesktop-sdk tree (23 elements, median toll share
0.0, MAD 0.0) — and it is why the criterion had never fired on a real
capture. Not because no project is too fine-grained, but because a
sub-second staging is invisible to the measurement.

`bulk.bst` is the answer: 60,000 one-byte files, staged by the same
hardlink path, which takes BuildStream a whole second to report.

```text
[--:--:--] START   [df47e0c4] tiny-1.bst: Staging dependencies at: /
[00:00:01] SUCCESS [df47e0c4] tiny-1.bst: Staging dependencies at: /
[--:--:--] START   tiny-1.bst: Running commands
[00:00:00] SUCCESS tiny-1.bst: Running commands
```

```text
tiny-1.bst toll=1.0s total=2.0s share=0.50
... (all eight identical)
```

Both halves of the criterion clear: `toll_share >= 0.50` and
`toll_us >= 1.0s`.

## Verification Log

Done 2026-08-19. `UX-100`'s acceptance clause 1, run.

### The candidate fires, and names the group

```text
[medium] merge-candidate: 8 sibling element(s) spend at least half their time on
sandbox toll rather than on building: tiny-1.bst, tiny-2.bst, tiny-3.bst,
tiny-4.bst. Merging them would delete 7 staging(s), 7.0s of toll and at least a
replayed 1.0s of build - a floor, because the replay shortens the tasks without
collapsing them into one (UX-120). It also merges their cache granularity: one
source change then rebuilds the group
```

```json
{"deleted_toll_us": 7000000,
 "projection": {"replayed_baseline_us": 4050000,
                "projected_us": 3050000, "saving_us": 1000000}}
```

The first time this branch has produced a positive answer outside a unit
test.

### The real merged rebuild

Five repetitions each, `--builders 4 --max-jobs 4`, shared dependencies
pre-warmed once per variant and every element artifact deleted between
repetitions — so what is timed is eight sandboxes against one, not the
CAS import of `bulk.bst`.

| rep | eight siblings | merged |
| ---: | ---: | ---: |
| 1 | 8.58s | 6.39s |
| 2 | 8.35s | 5.17s |
| 3 | 8.90s | 4.90s |
| 4 | 8.52s | 5.82s |
| 5 | 8.18s | 6.52s |
| **median** | **8.52s** | **5.82s** |

Real saving, median to median: **2.70s**. Most conservative pairing
(fastest eight-sibling run against slowest merged run): **1.66s**.
Projected: **1.00s**.

### The finding: the projection is a floor, not an estimate

The projection is below even the most conservative real saving, so it is
sound as a *lower bound* and wrong as an estimate — it under-predicts the
median by 2.7×. The cause is structural rather than a tuning error: the
replay shortens N tasks by their toll and leaves them as N tasks, so the
group's wave structure survives the projection (eight one-second tasks on
four builders still take two waves) while a real merge collapses them
into one sandbox.

The degenerate case makes it plainest, and is now a test: two siblings on
two builders already overlap, so shortening one changes no makespan at
all and the projection is exactly **0** for a merge that really deletes a
staging.

`UX-120` offered "fix or re-hedge". **Re-hedged**, and the reason is
recorded rather than assumed: modelling the collapse means synthesising a
merged task and rewriting the group's edges in the replay, which is a
different change from this one and one that could be quietly wrong. A
projection that under-predicts is safe to act on; a projection that
*quietly* under-predicts is not. So the number now ships as "at least …
a floor, because the replay shortens the tasks without collapsing them
into one", carries `projection_is_a_floor` in the JSON, and the reason
lives in `_project_with_reduced_durations`'s own docstring.

### Deviation from the Required Fix, recorded

The acceptance says the projected saving must be *"within the documented
band of a real merged rebuild"*. **No band was ever documented** — the
phrase appears in `UX-100`'s acceptance and in this task, and no number
backs it anywhere in the repository. Rather than invent one after seeing
the data, the measurement above is published as the first real data point
and the projection is re-hedged into a claim that data supports (a floor)
instead of one it does not (an estimate within ±X%).

`examples/06/optimized` still yields no candidate — checked, and the
negative half of the acceptance holds.

Tests: 9 in `tests/unit/test_fine_grained_fixture.py` (fixture shape),
2 added in `tests/unit/test_granularity.py` (8 → 10).
