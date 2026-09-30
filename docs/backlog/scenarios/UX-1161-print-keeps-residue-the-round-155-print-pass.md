# UX-1161: print keeps residue the round-155 print pass left

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the round-155 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_print_fits_the_sheet_and_prints_no_dead_apparatus.py`

## Motivation

Page: the round-155 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements; `bga_view --export`, Chromium 1440x900 and 390x844) at `8b7e3d3b`.

Print at 794 px, `emulateMedia({media: 'print'})`: one SQL code line in `#perfetto-questions` runs to x=846; the "I am" label prints with no control; closed-fold markers "▸ Why #1" print above open content; 187 `.description` nodes, 16 visible in print (unopened descriptions never reach paper); rows held back by a table or card limit print only their count; at 390 in print 18 plain code elements overflow the right edge (pre-existing).

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Decision

- **Choice.** CSS only, in `UX-1154`'s `@media print` block (`bga/viewer/style.css`): `summary::before { content: none !important }` (no ▸/▾ on paper); `label` joins the control rule (a label prints only with its control, and no control prints); `pre, code { white-space: pre-wrap !important }` replaces `code.next-command`'s wrap (the SQL `pre` was `white-space: pre`); `body, td, th { overflow-wrap: anywhere }` (a cell or an element chip at 390); `.description { display: block !important }` - paper has no `?`, so every description prints, below its value. This reverses `UX-346`'s "paper gets the screen's answer", written while the `?` still printed.
- **Held-back rows** are counted, not printed: the `.fold-more` count and the `N of M` badges already print; the guard now holds them.
- **Rule.** Styleguide §2b.3 amended: print shows every description.
- **Guard.** Booted under print media, `golden`, `macro_micro` and the two-plane 8x14 page at 794 and 390: nothing past the sheet or clipped by a scroll box, no shown label without a shown control, no summary marker, every description whose parent prints is shown, every held-back count the screen shows prints. **Mutation:** drop each rule; its clause reds.

## Required Fix

Each named print defect is gone: code wraps inside the sheet, a label prints only with its control, no fold marker prints over open content, unopened descriptions and held-back rows print or say what is held.

## Out of Scope

The screen layout; the fold-more control (intended by `UX-1154`).

## Acceptance Test

In print at 794 px and 390 px no element's right edge passes the sheet, no control-less label prints, and every description and held-back row is on paper or counted. Mutation: restore one defect, and the guard reds.

## Outcome

### Gap measured

Two-plane page (`gen-synthetic --seed 1 --layers 8 --width 14`, `bga_view --export`), Playwright Chromium, `emulateMedia({media: 'print'})`, then a real `page.pdf({format: 'A4'})` read back by a zlib + ToUnicode pass:

```text
        past sheet  scroll-clipped  control-less labels  ▸ summaries  descriptions shown  held-back counts shown
794     1 (x=846)   0               39                   65           16 of 187           4 of 4 (+81 More, 3x 25 of 114)
390     154         5 tables        39                   65           16 of 187           4 of 4
A4 pdf: 71 pages, layout 845 px wide (shrunk to 94% to fit the SQL line), '▸' 65, 'I am' 1, 'as Markdown' 33, 'View:' 1, 'Ask about element' 1
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_print_fits_the_sheet_and_prints_no_dead_apparatus.py -q   # HEAD style.css
21 failed, 9 passed, 1 xfailed
```

### Close measured

```text
        past sheet  scroll-clipped  control-less labels  ▸ summaries  descriptions shown  held-back counts shown
794     0           0               0                    0            187 of 187          4 of 4
390     0           0               0                    0            187 of 187          4 of 4
A4 pdf: 80 pages, layout 795 px wide (no shrink), '▸' 0, 'I am' 0, 'as Markdown' 0, 'View:' 0, 'Ask about element' 0
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_print_fits_the_sheet_and_prints_no_dead_apparatus.py -q
30 passed, 1 xfailed
page bytes (test_the_page_itself_stays_within_its_budget's own number) 149,988 -> 150,130 (+142 B)
```

### Mutations verified red and reverted (7)

| # | mutation | reddened |
|---|---|---|
| M1 | drop `summary::before` | marker clause, 6 failed |
| M2 | drop `label` from the control rule | label clause, 6 failed |
| M3 | drop the `pre, code` wrap | sheet clause, 5 failed |
| M4 | drop the `body, td, th` wrap | sheet clause, 2 failed |
| M5 | drop the `.description` rule | description clause, 6 failed |
| M6 | hide `.fold-more` with the controls | count clause, 2 failed |
| M7 | the whole of HEAD's `style.css` | 21 failed |

Deviation: `macro_micro`-390's sheet case is a strict `xfail` naming `UX-1164`: its distribution ticks run to x=386/573 on screen as in print, that row's defect. `+142 B` takes the page past the old 150,000 B budget (`UX-1167` raises it). The `.path-more` count ("+N More" on a focused path strip) was left hidden: no fixture draws it on load, so no guard could hold it.
