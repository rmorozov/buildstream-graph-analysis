# UX-1293: `design/directions.md` holds the directions in order, and its round history moves to `audits/`

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** none | **Found by:** the docs audit (2026-10-02, findings 8, 11) | **Serves:** contributors | **Topic:** docs | **Area:** unassigned | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_the_directions_are_in_order.py`; `tests/unit/test_docs_links_and_commands.py::test_the_architecture_chapter_links_the_backlog_instead_of_copying_it`

## Motivation

`directions.md` is 2,781 lines: 20 Directions interleaved with
"Round 24/25/26" chapters (1061-1246), an "Implementation status
(updated 2026-08-16)" (372), a "Round history" (1985) and a
"Verification Log" (2120), with Directions 10-14 after those.
`architecture.md` (~287-300) embeds a table of Done UX rows. A design
page that is also a log cannot be read as the argument it is.

## Required Fix

Directions in numeric order, each its own `##`; round, status and
verification chapters move to `docs/audits/directions-history.md`;
`architecture.md`'s row table becomes a link to the backlog.

## Out of Scope

Rewriting any Direction's argument.

## Acceptance Test

`##` headings of `directions.md` are Directions 1-20 in order and
nothing else; the moved chapters' line count is preserved; link and
anchor guards green.

## Outcome (2026-10-02) — 🟢 Done

**Premise:** held.

### The gap, measured

```text
$ wc -l docs/design/directions.md          2781
$ grep -c '^## ' docs/design/directions.md   27: 20 Directions, "The one finding", and six
  non-Directions - Implementation status (372), Round 24/25/26 (1061-1246),
  Round history (1985), Verification Log (2120); Directions 10-14 after them (2132-2781)
docs/design/architecture.md  "Real extensions beyond the original spec": 75 `| UX-N |` status rows
```

### After

```text
$ grep '^## ' docs/design/directions.md | sed 's/:.*//' | tr '\n' ' '
Direction 1 ... Direction 20 - 20 `##` headings, 1-20 in order, nothing else
$ wc -l docs/design/directions.md docs/audits/directions-history.md
  2416 directions.md   370 directions-history.md (6-line header + the six chapters)
moved chapters: 365 lines in the original (with their trailing blanks), 364 + header after (EOF blank)
non-blank line multiset, original vs both files (moved links rebased back): 2351 = 2351;
  the one difference is "## The one finding ..." -> "**The one finding ...**" (the preamble's lead)
architecture.md: 84 lines of table -> a 3-line paragraph linking backlog/scenarios/README.md
$ pytest the 15 files naming directions.md or the history + the new guard
2 failed, the rest passed - both `guides/pilot.md` (UX-1289's row for the parallel track)
```

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| A1 | the pre-`UX-1293` `directions.md` restored | `test_every_heading_is_a_direction_in_order`, 1 failed |
| A2 | Directions 10 and 11 swapped | the same, 1 failed |
| A3 | a `## Round history` chapter appended | the same, 1 failed |
| A4 | `## Verification Log` dropped from the history | `test_the_history_holds_the_chapters_that_left`, 1 failed |
| A5 | a `\| UX-01 \| … \| 🟢 Done \|` row typed back into architecture.md | `test_the_architecture_chapter_links_the_backlog_instead_of_copying_it`, 1 failed |
| A6 | round 166's row dropped from the history (retargeted guard) | `test_every_round_document_has_a_history_row`, 1 failed |

### Deviation from the Required Fix

"The one finding everything else follows from" stays as the preamble
with a bold lead rather than a `##`. Retiring the status table replaced
`test_the_architecture_table_is_read_at_all` with its inverse (A5), and
the two keys only it and Round 24 named (`omitted_structural_opportunities`,
`cumulative_saving_us`) went into architecture.md's `analyze/v7` row.
Round-history rows now land in `docs/audits/directions-history.md`
(closer agent, fixing guide step 6 retargeted).
