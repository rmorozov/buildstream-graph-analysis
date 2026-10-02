# UX-1268: a capacity-bound run reads "capacity matched demand", and the check does not see it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 walk of the merged page (2026-10-02) | **Serves:** R1, R5 | **Topic:** analysis | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

On the 2,402-element two-snapshot synthetic page (`tests.pages.two_plane_run(runs=2)`, `--layers 40 --width 60 --workload binaries`) at 1440, the decision reads capacity-bound and the first finding "92.6% of wall-clock time is resource wait (43.7 min)", while `#capacity_verdict` reads "Capacity matched demand: neither over- nor undersubscribed" and `#violations` reads "Nothing to report": `bga/consistency.py`'s PAIRS has no row for the diagnosis against the capacity verdict. `#ready_queue` reads "Nonzero fraction 1.0%" (its gloss: high means capacity bound) with 4 slots 99.7% occupied and a peak depth of 60.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Required Fix

Either the capacity verdict and the ready-queue fraction read builder-bound where the diagnosis does, or the consistency check reports the pair as a disagreement naming both sides.

## Out of Scope

UX-861's host-core cap (UX-1259).

## Acceptance Test

On this page the verdict, the ready-queue reading and the diagnosis agree, or `#violations` names the pair; golden and macro_micro unchanged. Mutation: drop the new pair or wording, and the guard reds.
