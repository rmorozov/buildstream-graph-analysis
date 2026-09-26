# UX-1023: the page has a compact size class, and compact draws no empty chrome

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the styleguide audit (2026-09-26, PR #294), styleguide §6e.10 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical

## Motivation

Measured on `main` at `98ab850`: `python3 -m tools.bga_view <run> --export` on `macro_micro` and `golden`, booted in Chromium at 1440x900 and 390x844.

- every budget (§3c, §3e) is measured at 1440x900 only;
- at 390px the rail collapses to "Sections ▸" and an empty grey band renders beneath it (no horizontal overflow, 390/390);
- `style.css` has five `max-width`/`min-width` blocks the guide never names.

## Decomposition

Input classes: 1440x900 and 390x844; rail folded and open; both fixtures. The journey extends reading the page on a desk into reading it on a phone.

## Required Fix

Two size classes, regular (≥ 60rem) and compact, named in `bga/viewer/style.css`; the five media blocks collapse onto them; the empty band goes.

## Out of Scope

A phone-specific layout beyond the compact class.

## Acceptance Test

`tests/unit/test_the_page_has_a_volume_budget.py` gains a compact column at 390x844, and a booted check on the rail at 390x844: every rendered child of `nav.toc` shows text or a control. The band is `nav.toc > div.actions-group` (top 150px, 11px high, `macro_micro`), whose children are all hidden at compact. Mutation: restore the band, and the check reds.

## Outcome

**Gap measured.** `#actions-group` in `nav.toc` renders its
border-top and padding-top (`.toc .actions-group`) whenever its only
child, `#actions`, stays `hidden` - measured on `golden` and
`macro_micro` exports at
390x844: `getBoundingClientRect()` top 149.7px, height 9px, no text or
control inside. Confirmed with a probe against both fixtures
(`bad: [{'tag': 'DIV', 'id': 'actions-group', ...}]` before the fix).
The five layout `@media` blocks used two breakpoints, 40rem
(`.wf-row`) and 60rem (four others), for what the styleguide names one
pair of size classes.

**Close measured.** `bga/viewer/style.css`:
`.actions-group:has(> #actions[hidden]) { display: none; }` - the group
now renders nothing when its only content is hidden; `.wf-row`'s
`@media (max-width: 40rem)` moved to `60rem`, so every layout query in
the file keys off the one pair, regular >= 60rem / compact below,
named in a comment beside `:root`. Re-measured at 390x844: rail-child
probe returns `bad: []` on both fixtures; `#actions-group` rect height
0. `test_the_page_has_a_volume_budget.py` gains
`COMPACT_LANDED_HEIGHT_PX` (golden 8,500, macro_micro 11,400 - measured
8,308 / 11,193) and `TestTheCompactSizeClassIsBoundToo`, whose second
clause is the rail-emptiness check (`offsetParent` for a real control,
`innerText` for real text - `textContent`/`querySelector` alone both
returned false negatives on a `hidden` descendant during development).
`docs/design/styleguide.md` §7's `§6e` row gained
`test_the_page_has_a_volume_budget.py` (it now cites §6e.10).

**Mutation table.**

| guard | mutation | reddened | count |
|---|---|---|---|
| `.actions-group:has(...)` CSS rule | `display: none` -> `display: block` | `test_no_rail_child_is_empty_chrome[golden]`, `[macro_micro]` | 2 failed / 32 collected |

Reverted from a copy (`style.css.good`), `__pycache__` cleared, both
tests green again.

**Deviation:** none from the Required Fix. `make test-touching` on the
full diff shows 6 failures; 5 reproduce identically on the merge base
alone (`bga/plane2.py` module-width, §6c/§6e citation and small-tier
browser-guard listing, and §3e's stale 7,300/7,600 landed-height
figures - all pre-existing, none of this row's files) and the sixth
(`test_a_button_input_select_and_summary_all_ring`) passed 3/3 solo and
7/7 under `-n 4` in isolation - a shared-core timing flake in the
full-suite run, not reproduced against this diff alone.
