# UX-1266: joint-saving and optimization-horizon name the same element set on macro_micro

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 verification of UX-1249 (2026-10-02) | **Serves:** R1 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

joint-saving and optimization-horizon (both High) name the same element set on macro_micro; making them one finding is a decision about which findings the analysis emits. Also correct the comment at `tests/unit/test_the_page_has_a_volume_budget.py` (~:385) that says +201 words where +176 was measured.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Required Fix

Decide whether the two are one finding; correct the comment to +176.

## Out of Scope

The dedup rule (UX-1249).

## Acceptance Test

Either one finding on macro_micro, or the decision recorded with the two kept; the comment reads +176.
