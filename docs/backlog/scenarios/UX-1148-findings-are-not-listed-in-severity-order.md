# UX-1148: findings are not listed in severity order

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the view UI review on a two-plane page (2026-09-29), findings M4 | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_findings_are_listed_by_severity.py`

## Motivation

Page: `bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14` (114 elements), `bga capture report --json plane2.log` in the newest snapshot, then `python3 -m tools.bga_view <snapshot>/run --export page.html`, booted in Chromium 1440x900 and 390x844 (view UI review, 2026-09-29, `view-ui-review.md` §M4).

`#findings` reads High, Medium, nine Info, Medium (certified-headroom), Info, Medium (shared-source-blast).

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390. The journey extends a first-time reader's pass over the page.

## Required Fix

Findings sort by severity, then by their published rank.

## Out of Scope

The analysis behind the values; other findings of the same review.

## Acceptance Test

Booted in the container: the `data-severity` sequence of `article.finding` is non-increasing, booted on the two-plane page. Mutation: restore the finding's shape, and the guard reds.

## Decision

The sort is the producer's: `compute_findings` ends with a stable sort by severity (`_LEAD_ORDER`), so the JSON, the text report and the page publish one order, and `reader_index`'s "severity, then published order" becomes the list's own. An indented finding (`chain-graph`, the note under the concentration table) travels with the finding above it; the page marks it `data-note-of` and indents it, so it is read as a note, not as an Info ranked among Highs. Committed analyses regenerated with `dev_refresh_analysis.py --write`. Guard: the `#findings` card severities, notes excluded, are non-increasing on the two-plane page, `golden` and `macro_micro`, and every note sits under its card. Mutation: drop the sort.

## Outcome

**Gap measured.** Two-plane page (`gen-synthetic --seed 1 --store --layers 8 --width 14`), `#findings` `data-severity` in order:

```text
high medium info info info info info info info info info medium info medium
```

**Close measured.** Same page after the change:

```text
high medium medium medium info info info info info info info info info info
```

`golden` and `macro_micro`: `high high [note] high high medium ...` - the one Info between Highs is `chain-graph`, now `data-note-of="time-concentration"`.

**Mutation table** (`PYTEST_XDIST= python3 -m pytest tests/unit/test_findings_are_listed_by_severity.py`):

| mutation | reddened | run |
|---|---|---|
| `compute_findings` skips `_by_severity` | `test_no_card_outranks_the_one_above_it` x3 fixtures | 3 failed, 7 passed |
| `_by_severity` ignores `indent` (note sorted on its own) | `test_an_indented_note_stays_under_its_table` | 1 failed, 9 passed |
| viewer never sets `data-note-of` | severity order + note placement, `golden` and `macro_micro` | 4 failed, 6 passed |

Reverted: 10 passed.

**Deviation.** The published order changes for every consumer (JSON, text, page); `tests/fixtures/golden/mixed_task_kinds/expected_output.json` and `tests/fixtures/with_timeline/analyze.json` regenerated - order and `provenance` order only, plus a `joint-saving` title drift in `with_timeline` already present at the base (not this row's). `tests/unit/test_report_key_findings.py` re-based: two tests cut the key findings at the headroom title, which now sorts above the criticality list; they cut at `Certified Floors:`. `bga/viewer/sections.js` and `style.css` touched for the note marker; the Decomposition named `bga/viewer` only.
