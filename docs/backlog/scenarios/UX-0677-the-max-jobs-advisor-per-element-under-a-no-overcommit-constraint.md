# UX-677: the max-jobs advisor — per element, under a no-overcommit constraint

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-676 (the intervals), UX-230 (what-if pricing), UX-31 (pinned elements) | **Serves:** R4 and R2 — the operator who sets the numbers and the owner whose recipe carries them | **Topic:** analysis | **Shape:** bounded

## Motivation

BuildStream has no cross-element job server, so `builders ×
native max-jobs` is a static product: too small and cores idle, too
large and the elements that happen to overlap overcommit the machine.
The tool names the pinned elements (`UX-31`) and nothing else — an
element whose `max-jobs` is *high* and overlaps four others is the
same defect with the other sign, and the tool is silent.

## Required Fix

Per element: measured cores busy while it built (`UX-675` series
joined to its span) against its resolved `max-jobs` (`UX-377`) and
the builders it overlapped with — then a recommended `max-jobs` per
element that keeps the sum of overlapping jobs under the cores and
the summed peak RSS under host memory. Stated as the fallback it is:
the `UX-679` jobserver removes the need for static numbers where it
can run.

**Three decisions, taken here.** Round 102's track stopped rather
than invent them, correctly — this row was dispatched as a track
before its judgement was taken, which was the orchestrator's error
and not the track's.

**1. The evidence is the series against the span, not `UX-676`'s
interval rows.** `underutilized_intervals` and `overcommitted_intervals`
are capped at 40 rows and ranked; they are a *sample* of the windows,
so joining them per element would be an instrument reading a proxy
for the thing it names (fixing guide §5). Join `UX-675`'s host counter
samples to each element's BUILD span directly.

**2. An element with thin evidence gets a refusal, not a default.**
Where an element's BUILD span carries too few host samples to support
a number, the row for it says so and says why. The threshold is the
track's to measure and state — pick it from the fixture's real sample
spacing rather than a round number, and paste the distribution that
chose it. A recommendation that silently falls back to the run-level
figure is the shape this repository has been burned by.

**3. The constraint is checkable, and it extends an existing
document.** The inequality: at every instant, the sum over elements
building then of their recommended `max-jobs` is at most the host's
cores, and the sum of their measured peak RSS is at most host memory.
A guard verifies the *published recommendation* satisfies it on a real
fixture — not that the formula has the right shape. Publish it as
per-element keys on the document that already carries the capacity
recommendation rather than minting a new contract id.

**Out of this row, and filed as `UX-739`: pricing it by replay.**
The Required Fix said "priced by replay (the `whatif` scheduler with
per-element job counts)". `bga/whatif.py` has no such mode — it
projects elements becoming *instant* over this run's measured
durations, which is different arithmetic. A per-element-job-count
replay is a scheduling simulation that does not exist, and building
one inside this row is the unbounded surface the track flagged.

## Out of Scope

- Writing the numbers into the project — the advice is a table and
  the `bst` variable lines to paste; `bga` does not edit recipes.

## Acceptance Test

On example 06 the advisor recommends raising core.bst above `-j1` and
prices the drop; on a synthetic run with two `-j8` elements
overlapping on four cores it recommends the split that fits.
Mutation: drop the memory constraint — the advisor guard reds on a
run whose peaks exceed RAM.

## Outcome

**Gap measured.** `capacity_recommendation` named `pinned_elements`
(one core) and nothing for the other sign. No fixture publishes both a
host CPU series and per-process peak RSS, so the memory half of
decision 3 had no committed evidence to check against either.

**Threshold measured.** On `tests/fixtures/host_cpu` (2s sampling, 12
raw intervals over the run), overlapping-interval counts per element:
`toolchain.bst` 0, `all.bst` 0, `app.bst` 1 (1.95s span), six `-j4`
elements 2, `lib-c.bst` 3, `core.bst` 5 (10s span). One interval is a
single delta that can extend well past an element's own duration; two
is the floor at which a reading is actually inside the span more than
once. `MIN_HOST_SAMPLES_IN_SPAN = 2` in `bga/correlate.py`.

**Close measured.** `compute_max_jobs_advice` joins the raw series
(`wall_samples`/`intervals`, not `UX-676`'s capped tables) to each
element's span; `recommended = max(1, host_cores // local_max_concurrency)`
provably keeps any instant's sum at or under `host_cores` (proof in the
function's docstring). Run for real on `host_cpu`: `core.bst` (max-jobs
1, notparallel) is recommended to 2; the six `-j4` elements that never
overlap more than one other are recommended down to 2; `app.bst`,
`toolchain.bst`, `all.bst` refuse (thin evidence). Checked directly
against every window: `sum(recommended for building) <= 4` holds
everywhere (max observed sum was exactly 4). The synthetic two-`-j8`
case (Acceptance Test, `TestTheSplitThatFits`) splits to 2+2 on 4
cores. The memory refusal is demonstrated on `host_cpu`'s own real
overlap (`core.bst`/`lib-a.bst`) with peak RSS figures stated directly,
since no committed fixture carries both series.

**Mutation table.**

| mutation | reddened | count |
|---|---|---|
| `local_max = 1` (ignore overlap) | `test_an_overlapping_dash_j4_element_is_recommended_down`, `test_the_published_recommendation_never_overcommits_cores`, `test_two_dash_j8_elements_are_split_to_fit`, `test_room_in_memory_leaves_the_cpu_number_alone` | 4 of 9 |
| memory check disabled (`False and ...`) | `test_an_overcommitting_overlap_is_a_refusal` | 1 of 9 |

Both reverted from the pristine copy; suite green after each revert.

**Deviation.** "Prices the drop" (Acceptance Test) is `UX-739`'s
replay pricing, out of scope per the Required Fix's own carve-out; not
implemented. No committed fixture carries both a host CPU series and
per-process peak RSS, so the memory constraint's real-fixture
demonstration uses `host_cpu`'s real overlap with directly-stated RSS
rather than a fully end-to-end capture.
