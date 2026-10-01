# UX-1228: a transitive downstream: clause filters the elements an element blocks, through every level

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** `UX-1214`'s Decision, dropped for budget (2026-10-01) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

`UX-1214`'s follow-up published `fan_in.direct` uncapped and dropped the transitive `downstream:<uid>` clause (a closure over `blocks`): its matcher alone measured +236 B page half. Page half at close: 159,147 of 160,000 B (853 B headroom). The Elements table's Downstream count reads 1201 for toolchain.bst; `depends_on:toolchain.bst` reaches its 1,200 direct dependents.

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

`downstream:<uid>` matches the closure of what <uid> blocks, from the rows' `blocks` lists, within the page budget.

## Out of Scope

`depends_on:` and `blocks:` (`UX-1214`, closed).

## Acceptance Test

On the 1,202-element page `downstream:toolchain.bst` matches its Downstream count; a guard in a new `test_a_downstream_clause_follows_the_closure.py`; the page half stays under 160,000 B. Mutation: restore the defect, and the guard reds.

## Outcome

Open.
