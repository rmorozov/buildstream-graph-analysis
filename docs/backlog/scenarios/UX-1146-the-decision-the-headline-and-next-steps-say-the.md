# UX-1146: the decision, the headline and next steps say the same thing three times

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings M1 | **Serves:** R1, R8 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_decision_is_said_once.py`

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §M1).

`#headline` repeats the decision sentence word for word; `#next_steps` is a whole section whose body is "6 steps, in the decision panel"; Why #1 and Why #3 repeat the same two paragraphs.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

The headline keeps its evidence only; next steps is the rail's link into the decision; a paragraph shared by several Why blocks is shown once under the list.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: no sentence of 8+ words appears twice in visible text, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Decision

Viewer only; the payload is unchanged and the JSON door still carries every field. `bga/viewer/sections.js`: `FIELDS_DRAWN_ELSEWHERE` (the field-level twin of `DRAWN_ELSEWHERE`) drops `headline.sentence` from `#headline`, and `next_steps` joins `DRAWN_ELSEWHERE`; the runbook branch that drew its one-link section goes. `bga/viewer/decision.js`: the panel's "Next" becomes "What should I run next?" (`#decision-next`, `data-rail-sub`), which `nav.js`'s `subsections` lists as the decision's rail sub-entry; a finding two or more Why folds name leaves those folds and is said once, under the actions, in a "What they share · N findings" fold (folded, so the landed path to the first command does not grow - `test_pointer_travel_is_a_budget.py`'s J1 at 390 reddened with it open). A finding card also stops printing an evidence string its detail already printed (`macro_micro`'s remote-execution "Not additive" sentence). Guard: sentences of 8+ words in the landed page's text, rail excluded, Why folds open - none twice; `golden`, `macro_micro` and the two-plane page. Mutation: give `#headline` its sentence back.

## Outcome

**Gap measured.** Two-plane page (`gen-synthetic --seed 1 --store --layers 8 --width 14`), the guard's measure, before this row (identical at 1440 and 390):

```text
sentences >= 8 words 63, said twice 4, next_steps section: yes
  3 x Elements most worth optimizing first, by blast radius
  2 x Shared source: one repository decides most of this build: any commit to https://
  2 x This build is scheduler-bound, not chain-bound: the critical path is 42% of the
  2 x Wide reach, not declared foundation - declare or dismiss: layer00/mod002.bst (81
```

**Close measured.** Same page after, 1440 and 390:

```text
sentences >= 8 words 58, said twice 0, next_steps section: no
```

**Mutation table** (`PYTEST_XDIST= python3 -m pytest tests/unit/test_the_decision_is_said_once.py`, 10 tests):

| mutation | reddened | run |
|---|---|---|
| `FIELDS_DRAWN_ELSEWHERE` loses `headline.sentence` | `test_no_long_sentence_appears_twice` x3 | 3 failed, 7 passed |
| `DRAWN_ELSEWHERE` loses `next_steps` | sentence x3, rail sub-entry x3 | 6 failed, 4 passed |
| Why folds keep shared findings, no shared block | sentence x3, `test_the_two_plane_page_shares_a_finding_between_why_folds` | 4 failed, 6 passed |
| card evidence repeats its detail | sentence (`macro_micro`) | 1 failed, 9 passed |

Reverted: 10 passed.

**Deviation.** Re-based for the removed `next_steps` section: `test_a_runbook_is_not_a_table.py` (the section-is-a-link class becomes drawn-once and rail-links-the-list), `test_the_order_the_page_has.py`, `test_the_rail_takes_a_step.py`, `test_back_after_a_reveal_re_folds.py` (5 landed sections, not 6), `test_the_page_has_geometry.py` (the narrative is `headline` alone), `test_every_population_at_zero_one_and_many.py` (not swept - drawn elsewhere), `test_a_new_control_class_lands_declared.py` (`a.runbook-link` retired). `docs/design/rendered-strings.json` regenerated; styleguide §1e and §5a rows and their ledger rows amended. `chapters.js` still names `next_steps` as a member of the decision chapter; it renders nothing there now.

Round-154 fixer: the why-shared fold now counts (1 level, N rows, data-levels/data-rows, §3a.1) so the depth walk passes; next_steps dropped from the decision chapter members in chapters.js; rendered-strings inventory re-written.
