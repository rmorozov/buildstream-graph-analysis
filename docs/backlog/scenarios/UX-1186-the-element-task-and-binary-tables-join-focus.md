# UX-1186: the element, task and binary tables join Focus, Inspect and the jump box

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1182 | **Found by:** the round-157 data-exploration review (`/mnt/project-files/view-ui-review/data-exploration/review.md`) of the 1,202-element two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 20 --width 60`, Plane 2 rewritten by heavy.py to 5,849 processes and at most 81 binaries per element) at `cbc739b0`, Chromium 1440x900 and 390x844 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Finding: 4 of the review.

The elements table (1,202 rows), the task table, `binary_cost` and `by_binary` carry 0 `a.inspect` and 0 `tr[data-element]`; the page's 96 keyed rows are all in 6 small sections (headline 3, critical path 22, horizon 5, bottleneck 51, sensitivity 5, batch 10). Focus on `layer12/mod030` leaves 4 sections undimmed and collapses the elements table. The jump box answers "Nothing matches" for `gperf`, `python3` and `cc`. A card's "Also in" names 3 sections and never the element, task or binary tables. Breaks `UX-208`'s rule that a declared element column earns every row a generic Inspect. No `dl` on the page exceeds 19 pairs (`confidence`), and every population map already renders as a two-column table; what they lack is a declared key.

## Decomposition

Input classes: the 1,202-element two-plane page, the heavy-binary page (`UX-1182`'s, heavy.py's until it lands), `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Rule, "a population's key column is declared": a table keyed by element, task or binary declares that column (`bga:keyed_by`), so every row carries `data-element` or `data-binary`, an Inspect link, Focus membership and a jump-box entry. Declare the key in `bga/viewer/pairs.js` and `elementSignalTable`; map a task to its element for `KEYED_BY_TASK_UID`; add a `binary` kind to `jumpTargets`; Focus dims such a table's other rows rather than collapsing it. Per D2, a `dl` stays for at most 40 (`TABLE_OPENS_BOUNDED_ABOVE`) scalar pairs about one subject; a map keyed by a population is a table with a declared, linked key column whatever its length, and never unrolls into a `dl`. The rule lands in `docs/design/styleguide.md` §1 and §3k.

## Decision

Owner (Ruslan, 2026-09-30 19:04 ("your defaults looks good to try")), D2: a `dl` stays for up to 40 scalar pairs about one subject. Any population map becomes a table with a declared, linked key column, whatever its length. There is no unrolling into a `dl`. Class: product.

## Out of Scope

The pager (`UX-1185`); the binary membership itself (`UX-1183`).

## Acceptance Test

`tests/unit/test_a_population_key_is_declared.py`: for every table whose schema declares `bga:keyed_by`, mounted rows with the data attribute equal mounted rows, Focus never collapses such a table, and on `UX-1182`'s page the jump box finds a binary. Mutation: drop the declaration on `elements`; the guard reds.

## Outcome

Open.
