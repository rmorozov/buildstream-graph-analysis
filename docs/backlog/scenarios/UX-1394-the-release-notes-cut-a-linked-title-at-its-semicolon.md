# UX-1394: `bga release-notes` cuts a linked title at the semicolon inside it

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-252 | **Found by:** Ruslan's review of PR #353 (2026-11-27) | **Serves:** R8 | **Topic:** cli | **Area:** unassigned | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_a_release_bullet_keeps_its_whole_title.py`

## Motivation

`tools/bga_release_notes.py` `_first_sentence` splits a closed row's summary on
`(?<=[.;])\s`. The summary is a Markdown link, so UX-1392's
title "`viewer.md` says staleness is not a version comparison; `UX-1367` made
it one" ended at "version comparison;" with the link unclosed in the
`CHANGELOG.md` body.

## Required Fix

A linked title is one unit: only the 200-character limit may shorten it, and
inside the brackets. A plain summary still ends at its first clause.

## Out of Scope

Regenerating a committed `CHANGELOG.md` block; that is the release owner's.

## Acceptance Test

A unit test on that title: kept whole and closed; a plain summary still cut; a
long linked title shortened inside its brackets. `bga release-notes --from 1313
--to 1330` prints the UX-1392 bullet whole.

## Outcome

**Gap measured** (`python3 -c "import bga.cli as c, sys; sys.argv=['bga','release-notes','--from','1313','--to','1330']; c.main()" | grep UX-1392`, base `0066be7b`): bullet ended `...version comparison;` with the link unclosed.

**Close measured** (same command): the bullet ends `made it one](docs/backlog/scenarios/UX-1392-...md)`; `grep -c "made it one"` = 1.
`pytest tests/unit/test_a_release_bullet_keeps_its_whole_title.py` = 3 passed.

| Mutation | Result |
|---|---|
| `linked = _LINKED.fullmatch(text.strip())` -> `linked = None` | 2 failed, 1 passed |

Known: `tests/unit/test_the_release_body_is_generated.py` now reddens on the committed `CHANGELOG.md` 1313->1330 block (line 144 holds the old cut bullet); regenerating it was withheld here and belongs to the release owner.
