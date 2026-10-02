# UX-1268: a capacity-bound run reads "capacity matched demand", and the check does not see it

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 walk of the merged page (2026-10-02) | **Serves:** R1, R5 | **Topic:** analysis | **Area:** bga, bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

On the 2,402-element two-snapshot synthetic page (`tests.pages.two_plane_run(runs=2)`, `--layers 40 --width 60 --workload binaries`) at 1440, the decision reads capacity-bound and the first finding "92.6% of wall-clock time is resource wait (43.7 min)", while `#capacity_verdict` reads "Capacity matched demand: neither over- nor undersubscribed" and `#violations` reads "Nothing to report": `bga/consistency.py`'s PAIRS has no row for the diagnosis against the capacity verdict. `#ready_queue` reads "Nonzero fraction 1.0%" (its gloss: high means capacity bound) with 4 slots 99.7% occupied and a peak depth of 60.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Decision

Route:     add PAIRS row `capacity_bound_vs_capacity_verdict` to bga/consistency.py: fires when headline.diagnosis is capacity_bound, checks_ran, and neither oversubscribed nor undersubscribed; it reads both sides. The ready-queue half closes with UX-1273's heading and gloss.
Rejected:  rewording "Capacity matched demand" breaks the Acceptance Test's "golden and macro_micro unchanged" and makes the analyzer's verdict depend on the headline it is built before (analyzer.py:1777); firing on undersubscribed too would enter UX-1259's host-core cap; a ready-queue pair is unnecessary once UX-1273 stops calling the fraction "capacity bound".
Files:     bga/consistency.py (read_verdicts gains capacity_undersubscribed; one Pair), tests/unit/test_the_page_checks_its_verdicts_agree.py, tests/quality_reference.json (consistency.py's file_lines cell, 117 today)
Guard:     tests/unit/test_the_page_checks_its_verdicts_agree.py: on tests.pages.two_plane_run(runs=2) `#violations` names capacity_bound_vs_capacity_verdict with both sides; golden and macro_micro name no new pair
Mutation:  delete the new Pair from PAIRS (or drop the `not under` clause and run with an undersubscribed fixture): the page case reds
Class:     product
Split:     one track, with UX-1273 in the same track (it carries the ready-queue reading this row's acceptance reads)
Question:  Default taken; Ruslan may reverse: report the disagreement instead of changing the verdict. The consistency.py cell rises through `dev_sizes.py --adopt --force` by the pair's lines (about 12).

## Required Fix

Either the capacity verdict and the ready-queue fraction read builder-bound where the diagnosis does, or the consistency check reports the pair as a disagreement naming both sides.

## Out of Scope

UX-861's host-core cap (UX-1259).

## Acceptance Test

On this page the verdict, the ready-queue reading and the diagnosis agree, or `#violations` names the pair; golden and macro_micro unchanged. Mutation: drop the new pair or wording, and the guard reds.
