# UX-1231: the styleguide states two rules: a filtering link moves focus to its filter, an entry naming no View is at the opening View

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-160 residue pass, track W3 (2026-10-01) | **Serves:** R1 | **Topic:** docs | **Area:** unassigned | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_the_styleguide_names_its_guards.py` (holds the §3d row naming `test_a_card_s_more_reaches_every_dependency_both_ways.py`)

## Motivation

Track W3 (`UX-1214` follow-up 2) found two candidate rules: "a link that filters a table moves focus to its filter" and "an entry naming no View is at the opening View" (popstate sets the View as it clears a filter; the real defect was Forward).

## Decomposition

Input classes: the 1,202-element two-plane page and its `--workload binaries` variant, at 1440 and 390.

## Required Fix

The styleguide states both rules, each naming the guard that holds it.

## Out of Scope

The behaviour (`UX-1214`, closed).

## Acceptance Test

`test_the_styleguide_names_its_guards.py` passes with both rules stated and each guard named; deleting a rule's guard reds it. Mutation: restore the defect, and the guard reds.

## Decision

Architect, round 161 (2026-10-01):

```text
Route:     Add both rules to styleguide §3d (prose and index row ~:52) and name test_a_card_s_more_reaches_every_dependency_both_ways.py (N4: focus to the box; N3: Back to the reader's View, Forward to the link's) in §7's §3d row (~:2448); that guard's docstring cites "(styleguide §3d)".
Rejected:  a new §3m section for history (own §7 and index row for one sentence); prose only (the ledger guard cannot see an uncited guard).
Files:     docs/design/styleguide.md, tests/unit/test_a_card_s_more_reaches_every_dependency_both_ways.py (docstring line 1 only)
Guard:     tests/unit/test_the_styleguide_names_its_guards.py: every named guard cites its section, and no guard cites a section the table leaves out.
Mutation:  Remove the guard's name from §7's §3d row: test_no_guard_cites_a_section_the_table_omits reddens.
Class:     bookkeeping (1 of 14, under the 40% cap)
Split:     parallel unless UX-1219..1222 edit styleguide §3d/§7 or that guard file.
Question:  none. Default: one guard holds both rules; if a history track adds a Forward/opening-View guard, name that file for rule 2.
```

## Outcome

**Gap measured.** Before: `grep -n "UX-1231\|moves focus to its box" docs/design/styleguide.md` found neither rule; §7's §3d row did not name `test_a_card_s_more_reaches_every_dependency_both_ways.py`, which held N4 (focus in the box) and N3 (Back/Forward) uncited.

**Close measured.** Styleguide §3d states both rules (index row, new bullet) and §7's §3d row names the guard; that guard's docstring line 1 cites `(styleguide §3d)`. Rule 2 names this guard: the history track's Back/Forward guard is not on this base. `test_the_styleguide_names_its_guards.py` + `test_the_register_is_terse.py`: 1427 passed; `make lint` clean.

**Mutation table.**

| Mutation | Red | Count |
|---|---|---|
| remove the guard's name from §7's §3d row | `test_no_guard_cites_a_section_the_table_omits` ("§3d is cited by [...], and its row does not name them") | 1 failed, 13 passed |
| remove `(styleguide §3d)` from the guard's docstring | `test_every_named_guard_exists_and_cites_its_section` and `test_no_guard_cites_a_section_the_table_omits` | 2 failed, 12 passed |

Both reverted from copies; rerun green.

**Deviation.** None. The Acceptance Test's guard file is unchanged: its two existing tests already hold the new row.

