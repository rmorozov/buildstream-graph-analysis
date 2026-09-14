# UX-853: the memory gate sums the elements that run together

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-850 | **Found by:** round 118, UX-850's verifier | **Serves:** R5 (two elements each under the bound do not jointly exceed the host) | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

`UX-850`'s gate reads `MemAvailable` once per tick and compares it
against one element's planned peak times the tokens it would hold. Two
running elements each pass on their own; together they exceed the host.
An element on its implicit token alone never reaches the gate, so N such
elements co-reside unchecked. The verifier named it.

## Required Fix

`tools/bst_native_build_tracer.py`: `Broker._memory_gate` reserves,
per tick, the sum over every running element of `peak_rss * (1 + tokens
held)` before granting; a grant is withheld when `MemAvailable` minus
that sum, minus the candidate's own increment, goes under zero; a
running element with no planned peak counts as the plan's median peak.
The `memory_withheld` row gains `reserved` (the sum). Nothing else in
the broker moves.

## Decomposition

Input classes: one running element, two whose peaks each fit and whose
sum does not, an element on its implicit token only, an unplanned
element at the median; the journey it extends is R5's "does this
machine fit this build" under the mode.

## Out of Scope

Reading memory from the hook per process (a live RSS rather than the
plan's peak) - a later row, `UX-682`'s shape.

## Acceptance Test

`tests/unit/test_the_pool_withholds_for_memory.py` gains a case with
two running elements each under the bound whose sum is over it: the
second grant is withheld and its row carries the sum; mutation: reserve
only the candidate's own peak - red.

## Outcome

**Gap measured.** `git show b9f64a1e:tools/bst_native_build_tracer.py |
grep -c reserved` = 0 - `_memory_gate` compared only the one candidate's
own `peak * held_after` against `MemAvailable`; an unplanned running
element (`peak_rss.get(element)` returning `None`) bypassed the gate
entirely rather than counting at the median.

**Close measured.**
`python3 -m pytest tests/unit/test_the_pool_withholds_for_memory.py -v`:

```text
TestTheBrokerWithholdsByPlannedPeak::test_below_the_bound_withholds PASSED
TestTheBrokerWithholdsByPlannedPeak::test_above_the_bound_grants PASSED
TestTheBrokerWithholdsByPlannedPeak::test_a_plan_without_peak_rss_withholds_nothing PASSED
TestTheBrokerWithholdsByPlannedPeak::test_a_peak_that_alone_exceeds_the_machine_grants_nothing PASSED
TestTheBrokerWithholdsByPlannedPeak::test_memory_returning_grants_a_previously_withheld_element PASSED
TestTheBrokerWithholdsByPlannedPeak::test_two_running_elements_summed_exceed_the_bound PASSED
TestTheBrokerWithholdsByPlannedPeak::test_an_idle_elements_implicit_token_counts_in_the_sum PASSED
TestTheBrokerWithholdsByPlannedPeak::test_an_unplanned_running_element_counts_at_the_median PASSED
TestThePoolReadsMemoryPSI (3 cases) PASSED
test_count_memory_psi_withdraws_reads_the_ledger_it_writes_beside PASSED
12 passed in 0.56s
```

**Mutation table.**

| mutation | reddened | count |
|---|---|---|
| `reserved = sum(...)` replaced with `reserved = 0` (candidate-only, no summing) | `test_below_the_bound_withholds`, `test_memory_returning_grants_a_previously_withheld_element`, `test_two_running_elements_summed_exceed_the_bound`, `test_an_idle_elements_implicit_token_counts_in_the_sum`, `test_an_unplanned_running_element_counts_at_the_median` | 5 of 12 |

Reverted from the pre-mutation copy in the scratchpad; the same 12
cases pass again.
