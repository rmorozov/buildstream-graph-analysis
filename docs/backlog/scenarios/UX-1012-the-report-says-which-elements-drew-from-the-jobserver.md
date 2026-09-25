# UX-1012: the report says which elements drew from the jobserver, not only which were offered it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1005 | **Found by:** Ruslan on the Graviton thread (2026-09-25): "does bga show in report which elements actually used jobserver and which are not?" | **Serves:** R4, R5 | **Topic:** analysis | **Area:** bga | **Shape:** judgement

## Motivation

`jobserver.per_element[uid].joined` (`bga/correlate.py:1404-1451`)
reads `yes | pinned | held | unknown_kind`, and `yes` is the offer, not
the draw. The draw is read from the element's peak width against its
own `max-jobs`, which lives in a separate table
(`per_element_parallelism`); the Graviton readings proved use that way
(`giant.bst` peak 8 -> 16, run 36116507787). The report never sets the
two side by side, and `bga analyze`'s terminal prints no per-element
jobserver line at all (`bga/report/text.py` never reads
`report["jobserver"]`; the only jobserver text is `bga compare`'s mode
header, `text.py:101-112`).

## Decomposition

surfaces: `bga/correlate.py` (the verdict), `bga/report/text.py` (the terminal table), the page's jobserver section
guards: an element whose peak exceeds its `max-jobs` under the pool reads `drew`; one joined at peak <= `max-jobs` reads `offered, not drawn`; `pinned` never reads `drew`
gap: what a `drew` verdict means once UX-1005 track B admits sandboxes on a token
track: after UX-1005

## Required Fix

One per-element table, terminal and page alike: joined, peak against
`max-jobs`, a `drew` verdict derived from the two, tokens held.

## Out of Scope

UX-1007 (`MAXJOBS`/`MAX_JOBS` spellings) and UX-1008 (a consumer with no
width promise); both still read `unknown_kind` here.

## Acceptance Test

`bga analyze --plane2` on the Graviton `11-serial-giant` auto capture
prints `giant.bst` as `drew` with peak 16 against `max-jobs` 8.

## Outcome

Not started.
