# UX-1269: one wait quantity carries four names, and two glosses contradict their source

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-163 walk of the merged page (2026-10-02) | **Serves:** R1 | **Topic:** viewer | **Area:** bga, bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_a_wait_quantity_has_one_name.py`

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

## Outcome

The gap measured, at `b35c30e31`, the 2,402-element two-plane page exported, Chromium 1440, labels by data key:
`resource_wait_us ['Resource wait', 'Waiting on resources']` plus the drawing's `resource` tick `capacity full`;
`execution_on_chain_us ['Execution on chain', 'Execution on the chain']` plus `work on the chain`;
`scheduler_wait_us ['Scheduler wait', 'Waiting on the scheduler']`; `untracked_tail_us ['After the last task',
'Untracked tail']`. Effective CPUs gloss `Builder slots as recorded, not host cores` beside source `Detected host
cores`. `costliest-binary` step `Start with make` at 36.0 s, 0.3% of `capacity_cpu_us` 3.1 h.

The close measured, same page: every attribution key and both headroom keys carry one label (`Waiting on resources`,
`Execution on the chain`, `Waiting on the scheduler`, `After the last task`, ...; ticks the same words). The time
chapter's floors, under the waterfall, end `Scheduling gap is the wall clock beyond Chain floor T∞; it overlaps
Waiting on resources above and does not add to it.` Placed there, not under the decision's split: there it cost
390 J1/J2 wheel 466 -> 696 and 1,487 -> 1,734 px (`test_pointer_travel_is_a_budget.py`, budget x1.1); here 56
passed. Gloss: `The capacity this accounting divides by, in CPUs; the source line says where it came from.`
`costliest-binary` step: `{'why_none': "make is 0.3% of the run's CPU capacity, under the 1% opportunity floor:
context, not a lever."}`. `test_one_bucket_one_row.py` matches a bucket's row by `data-key`, and
`test_the_label_is_for_the_reader.py`'s suffix cases use keys outside `TERMS`. Guard: 4 passed; with
`test_plane_two_reaches_the_findings.py` 12 passed (37.2 s).

| mutation | reddened | run printed |
|---|---|---|
| restore the `resource` decomposition label "capacity full" | `test_each_wait_key_is_drawn_under_one_name` | 1 failed |
| drop `section.append(para)` in `renderOverview` | `test_the_time_chapter_states_the_waits_against_the_gaps` | 1 failed |
| restore "Builder slots as recorded, not host cores." | `test_the_effective_cpus_gloss_agrees_with_its_source` | 1 failed |
| share read against `measured` again | `test_a_costliest_binary_under_the_floor_carries_no_step` | 1 failed |
| reverted | | 4 passed |

Verifier fix: the overview's relation is now a fold, `How these figures relate` (class `overview-relation`, a
declared `LAYOUT_FOLDS` entry), under the floors: `Execution on the chain is the path that set this finish; Chain floor
T∞ is the graph's longest.`, `Scheduling gap ... overlaps Waiting on resources.`, `Certified headroom is the wall clock
beyond Resource floor LB; it overlaps Scheduling gap.` 390 macro_micro J2 wheel 1,578 px (limit 1,635.7). Kept terse:
the first wording put `xl_both` at 13,235 words over its 13,200 budget. `by_binary`'s Wall column title says it is
process lifetimes summed over every call and can exceed the run's wall clock (make 2.9 h on a 47.2 min run). The
Effective CPUs gloss names the source kinds; the guard needs the source line's kind in it.
Guard: 6 passed (25.3 s).

| mutation | reddened | run printed |
|---|---|---|
| chain relation's `data-role` renamed | `test_the_chain_and_the_headroom_say_what_they_are_beside` | 1 failed |
| headroom relation's `data-role` renamed | the same | 1 failed |
| Wall gloss restored to "summed the same way" | `test_the_binary_wall_says_it_sums_process_lifetimes` | 1 failed |
| gloss names no kind ("the source line says where it came from") | `test_the_effective_cpus_gloss_agrees_with_its_source` | 1 failed |
| reverted | | 6 passed |
