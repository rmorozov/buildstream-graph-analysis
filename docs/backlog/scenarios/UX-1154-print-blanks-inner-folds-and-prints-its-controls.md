# UX-1154: a print blanks inner folds and prints its controls

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-154 walk, item 1 (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_print_opens_every_fold_and_drops_its_controls.py`

## Motivation

Page: the round-154 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844; screenshots in `round-154/`).

Under `emulateMedia print` at 1440: 66 closed `details` stay 24 px tall (Why 1-3, "What they share", "The rule", 16 provenance, 17 map tables, 4 question groups, 19 join-evidence); the controls print (74 collapse, 46 View as JSON, 38 `?`, 6 Copy command); the next-command text is clipped at the right edge. `style.css` unhides only `[hidden=until-found]`. Shot `round-154/print-decision-1440-folds-blank.png`.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

- **Choice.** CSS only, in the fold's `@media print` block (`style.css`): `::details-content { content-visibility: visible }` opens every closed `details` without touching `[open]` (no `beforeprint` script, which `emulateMedia` never fires); `button:not(.fold-more), input, select { display: none !important }` drops every control (the `!important` beats `th .th-filter`); `code.next-command { white-space: pre-wrap }` wraps (`main code` already carries `overflow-wrap: anywhere`).
- **Kept.** `.fold-more` prints: its text is the count of the rows the page holds out ("+81 More blast elements (90 in all)"), the only mark on paper that rows are missing.
- **Offset.** The twin's print block merges into this one and its `button.twin-toggle` / `button.chapter-open` rules go (the one control rule covers both).
- **Rule.** Styleguide §2b.3 said the `?` marker survives print; it now prints no control and opens every `details`.
- **Guard.** Booted under print media, `golden`, `macro_micro` and the two-plane 8x14 page at 1440 and 390: no closed `details` under 40 px, no visible control but `.fold-more`, no `code.next-command` with `scrollWidth > clientWidth`. **Mutation:** drop each rule; its clause reds.

## Required Fix

Print opens every inner fold, hides the controls, and wraps a next command instead of clipping it.

## Out of Scope

The analysis behind the values; the other findings of the round-154 walk.

## Acceptance Test

No `emulateMedia print` page has a closed `details` under 40 px, a visible control, or a clipped command. Mutation: restore the defect, and the new guard reds.

## Outcome

### Gap measured

Two-plane page (`gen-synthetic --seed 1 --layers 8 --width 14`, `bga_view --export`), Playwright Chromium 141, `emulateMedia({media: 'print'})`, then `page.pdf({format: 'A4'})`:

```text
          closed details <40px   visible controls   clipped next-command   print height   A4 pdf
1440      62 of 66               382                6 (1463>970 ...)       42,733 px      49 pages, 5,075 text-show ops
390       62 of 66               382                6                      -              -
controls: 74 collapse, 46 View as JSON, 38 ?, 7 Copy command, 19 Focus, 57 Working/Done/Set aside, 141 more (copy, table tools, Perfetto)
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_print_opens_every_fold_and_drops_its_controls.py -q   # HEAD style.css
16 failed, 3 passed
```

### Close measured

```text
          closed details <40px   visible controls         clipped next-command   print height   A4 pdf
1440      0 of 66                1 (.fold-more, +81 ...)  0                      66,800 px      76 pages, 6,915 text-show ops
390       0 of 66                1 (.fold-more)           0                      -              -
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_print_opens_every_fold_and_drops_its_controls.py -q
19 passed
golden export page_bytes 149,151 -> 149,221 (+70 B)
```

The 14 files naming print, `next-command`, the twin toggle or the page budget, single process: 1531 passed.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| M1 | drop the `::details-content` rule | closed-fold clause, 6 failed |
| M2 | drop the control rule | control clause, 6 failed |
| M3 | drop the `code.next-command` wrap | command clause, 4 failed |
| M4 | the whole of HEAD's `style.css` | 16 failed |

Deviation: two existing guards re-based. `test_a_drawing_is_graded.py` read `button.twin-toggle { display: none }` in a print block; it now reads the one control rule. `test_apparatus_in_its_place.py` forbade print hiding `.describe` (the `?`); it now holds only `.description`, per the amended §2b.3. `overflow-wrap: anywhere` on the print command was tried and dropped: no mutation reddened without it (inherited from `main code`).
