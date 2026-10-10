# UX-1350: the 390px page depends on its font, so eight guards red where `system-ui` is Inter

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** `make push-check` in the remote container, never green there (2026-10-08..10) | **Serves:** R8 | **Topic:** guards | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_narrow_page_keeps_its_place.py::test_back_after_a_rail_link_or_expand_all_lands_where_the_reader_read`

## Motivation

The page's font is `system-ui`, which Chrome on Linux resolves through
fontconfig's `sans-serif`: Inter in the container, DejaVu Sans on the
runner. Eight 390px guards red only here, so push-check never passes.
Three files, 117 tests, the default font the only change:

```text
$ FONTCONFIG_FILE=<sans-serif -> X> python -m pytest -n 4 \
    tests/unit/test_pointer_travel_is_a_budget.py \
    tests/unit/test_the_narrow_page_keeps_its_place.py \
    tests/unit/test_a_heading_is_its_question_alone.py
Inter (container default)   8 failed, 109 passed
DejaVu Sans                 117 passed
Liberation Sans             3 failed, 114 passed
```

A reader's `system-ui` is rarely DejaVu, so each red is a reader's page.
The owner chose fixing the page over pinning the guards' font (2026-10-10).

## Required Fix

Make Back, the section heading and the table tools row keep their
geometry under any font, with no font pinned in the guards.

## Out of Scope

macOS, where Chrome does not read fontconfig; the J1-J4 baselines beyond
re-reading the one main already exceeds.

## Acceptance Test

The three files pass with `FONTCONFIG_FILE` mapping `sans-serif` to Inter,
DejaVu Sans and Liberation Sans.

## Outcome (2026-10-10) — 🟢 Done

Three causes, each a reader's page:

- **Back**: an unrendered section is 600px of `contain-intrinsic-size`
  until the climb reaches it, so scroll anchoring grew `scrollY` under the
  reader and the first notch up read as a stop below. `app.js` keeps the
  line read (`elementFromPoint` under the sticky header, as its id'd block
  and the child path down) and its top; a stop whose `scrollY` grew while
  that line moved down is still the climb; Back lands the line. State keys
  are `line`/`path`/`lineTop`: `mark` is a guard's own. The narrow-page and
  jump-box guards assert the line read's drift, not `scrollY`; the jump-box
  guard's re-land dwells past the page's 1 s, or it is the climb's first step.
- **Heading**: the fold had `margin-right` and the head's `gap`, 16px; the
  Perfetto heading is 286.9px in Inter against 286.5px of room. The head's
  gap alone spaces it; the guard probes the row less the fold.
- **J4**: the table filter took its font's 20-character width (220px
  Inter, 192px DejaVu) and wrapped off Copy's line by 1px; it is `12rem`.

`PAGE_BUDGET_B` 166,250 -> 166,750 B, owner-call default: main read
166,248 B, this 166,695 B.

J1 both_scale 390 read 844 on main under DejaVu against a 769 base (9.75%
of 10%), and 852 under Inter: re-based to 844.

```text
$ fonts.sh <the three files + six more place, size and pane guards>
Inter        197 passed      # FONTCONFIG_FILE maps sans-serif per font
DejaVu Sans  197 passed
Liberation   197 passed
```

| Mutation | Guard | Inter |
|---|---|---|
| `app.js` place by `scrollY` (main's) | narrow page Back | 18 failed |
| fold `margin-right` restored | heading no taller than its text | 3 failed |
| filter `width: 12rem` removed | J4 macro_micro 390 | 8.55 > 7.83 bits |
