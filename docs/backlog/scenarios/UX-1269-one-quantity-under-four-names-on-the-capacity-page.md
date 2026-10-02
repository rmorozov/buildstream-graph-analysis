# UX-1269: one wait quantity carries four names, and two glosses contradict their source

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 walk of the merged page (2026-10-02) | **Serves:** R1 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

On the 2,402-element two-snapshot synthetic page at 1440: the decision says "Scheduling gap 42.5 min", the time chapter "Waiting on resources 43.7 min", `#floors` "Certified headroom 9.9 s", and "Execution on the chain 3.0 min" sits beside "Chain floor T∞ 4.6 min", with nothing saying which to quote. `#utilisation` glosses "Effective CPUs 4" as "Builder slots as recorded, not host cores" while its source line reads "Detected host cores". `costliest-binary` says "Start with make" at 36.0 s of CPU, 0.3% of the 3.1 h capacity, and `by_binary`'s Wall 2.9 h for make sums its children.

## Decomposition

Input classes: the 2,402-element two-plane page, `golden` and `macro_micro`.

## Decision

Route:     give each wait key one reader name in format.js TERMS; the decision's opportunity split (decision.js:723) states how scheduling gap relates to resource wait; the effective_cpus gloss defers to its source line; costliest-binary measures its share against capacity_cpu_us, and below OPPORTUNITY_FLOOR_PCT it takes `why_none` instead of "Start with".
Rejected:  one shared name for scheduling_gap_us and resource_wait_us (42.5 vs 43.7 min: they are different quantities, so the fix states their relation and does not merge them); new figures (out of scope); a floor read against measured CPU (make is 100%-relative there, which is the bug)
Files:     bga/viewer/format.js, bga/viewer/views.js (737-751 labels), bga/viewer/decision.js (opportunity split only), bga/schemas.py (utilisation.effective_cpus description, ~5259), bga/findings.py (costliest-binary, ~2290), tests/unit/test_a_wait_quantity_has_one_name.py
Guard:     tests/unit/test_a_wait_quantity_has_one_name.py: on the 2,402-element two-plane page, no two drawn labels name the same key differently, the Effective CPUs gloss matches its source line, and costliest-binary carries step.why_none
Mutation:  restore the "Scheduling gap" label beside the capacity-bound sentence; separately, read the share against `measured` again: each reds
Class:     product
Split:     one track. The costliest-binary clause writes the findings.py function the binaries group (UX-1275, UX-1261) reads, so merge it after that group or move the clause there
Question:  none

## Required Fix

Each of these quantities is named once in reader words with its relation to the others stated where two appear together; a gloss agrees with its source; a Plane 2 finding whose share of capacity is below Plane 1's opportunity floor carries no step to act on.

## Out of Scope

The figures themselves.

## Acceptance Test

On this page no two headings name the same wait quantity differently, the Effective CPUs gloss matches its source, and costliest-binary below the floor reads as context. Mutation: restore one name, and the guard reds.
