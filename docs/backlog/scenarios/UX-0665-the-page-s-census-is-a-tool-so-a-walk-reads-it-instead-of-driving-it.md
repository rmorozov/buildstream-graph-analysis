# UX-665: the page's census is a tool, so a walk reads it instead of driving it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-359 (the page fixture every browser guard measures), UX-532 (the nested-row class a census would have caught) | **Serves:** the orchestrating session paying for a walk | **Topic:** guards | **Shape:** bounded

## Motivation

Every walk since round 63 has re-derived the same census by driving
the page: sections, rail entries, controls grouped into classes with
counts, tables with folded cells, planes present. Round 77's control
walk cost 336k tokens and most of it was that census; round 82's
five researchers rebuilt the trace and contract inventories the same
way. The `walk` skill fixes the report's shape; nothing yet makes the
census a two-kilobyte artifact a walker reads.

## Required Fix

`tools/dev_page_census.py <export.html>`: boots the export through
`tests/browser.py` once and prints JSON — sections (id, chapter,
depth), rail entries, controls by class (selector, label, count, one
example section), tables with nested tables, drawings with twins,
planes present, and the page's counters the volume guard already
takes. Two consumers:

- the `walk` and `design-review` skills read it first and drive one
  instance per class the census names — a class the census does not
  know is the finding;
- a guard holds the class registry: every control class on the
  golden and macro_micro pages is declared (selector, label pattern,
  the § that owns it) — a new control lands with its row, and a table
  whose cells fold is enumerated so `UX-532`'s shape cannot hide
  behind a fixture that has none.

## Out of Scope

- Driving controls in the tool — a census counts; the walker drives.
- Screenshots — the `design-review` skill's step, not the census.

## Acceptance Test

The census of the round-90 export lists the classes round 77
counted (193) within ±5 and names every table with a nested table;
mutation: add an undeclared button to a fixture page — the registry
guard reds naming its selector.

## Outcome

**Gap measured.** No `tools/dev_page_census.py` existed; a walk
re-derived sections/rail/controls/tables by hand each time (round 77,
336k tokens). `python3 tools/dev_page_census.py <export.html>` now
prints the JSON census in one boot. `golden` and `macro_micro` (no
round-90 export in this environment — no real `bst`/hook capture) give
20 and 21 control classes, 26 in union, document-wide; a first,
`main`-scoped draft measured only 20/21 and silently missed the
stepper (Top/Prev/Next), the jump box and the run selector, which live
in the rail beside `main` — found by the falsify mutation, not read
off the code. `macro_micro` already names two folded tables
(`restructuring`, `serialization_point_risks`); `golden` names none,
confirming the motivation's own claim that neither fixture carries
`UX-532`'s shape at 60 rows, so the guard also boots
`pages.shared_resource_run`, which enumerates `resource_blast`'s 25
nested tables. Every `svg`/`div[data-grade]` drawing's twin is found
correctly on both fixtures (`exhibit` ⇔ `has_twin`, 23 and 12
drawings, zero mismatches) once the twin search is narrowed to 2
ancestor hops — at 5 hops an annotation-grade sparkline sharing a
section with an exhibit read as having a twin it does not own.

**Close measured.** `tests/unit/test_a_new_control_class_lands_declared.py`
(4 clauses, medium tier, 1.77-1.82s single-process) holds a 26-row
`REGISTRY` (selector, label pattern, owning § or UX-id) against
`golden` + `macro_micro`, in both directions, plus the nested-table
enumeration on `shared_resource_run`. `make lint` clean (ruff, PyMarkdown,
`dev_baseline.py --check` at 299, unchanged). The round-90 export named
in the Acceptance Test does not exist in this worktree (`examples/06`'s
real two-plane capture is gitignored and needs a live `bst`+hook); the
class-count and mutation clauses are verified on the committed
fixtures instead — see the deviation.

**Mutation table.**

| mutation | reddens | count |
|---|---|---|
| add `button.probe-mutation` to `nav.js`'s stepper | `test_every_measured_class_is_in_the_registry`, naming `['button.probe-mutation']` | 1/4 |
| narrow `button.describe`'s pattern to `^ZZZ$` | `test_a_declared_label_still_matches_what_is_measured`, naming `('golden'/'macro_micro', 'button.describe', '?')` | 1/4 |
| add a `REGISTRY` row for `button.stale-mutation-probe` | `test_the_registry_is_not_wider_than_what_is_measured`, naming `['button.stale-mutation-probe']` | 1/4 |
| break the nested-table selector to `td tableXXX` | `test_a_table_whose_cells_fold_is_enumerated`, `macro_micro`'s enumeration reads empty | 1/4 |

All four reverted from the pre-edit copy and confirmed green again.
