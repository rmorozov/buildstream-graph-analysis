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

Not started.
