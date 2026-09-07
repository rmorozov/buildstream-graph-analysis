# UX-751: the landed clause reads endpoints where the open clause reads the range

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-748 (the open clause), UX-231 (the directions guard) | **Serves:** the reader trusting a Direction's status line | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-748` gave `test_a_range_called_open_names_no_closed_filing` a
range-expanding helper, `_ids_in()`, so a status calling `A..B` open
reddens when any id inside it has closed. Its sibling,
`test_a_landed_status_names_only_closed_filings`, still reads the two
literal endpoints via `_ITEM` — the narrowness `UX-748` exists to
remove, left in place on the other half of the pair.

It is not hypothetical. Direction 18 read:

```text
**Status:** landed — `UX-685`..`UX-692` all closed.
```

while `UX-689` and `UX-690` were 🔴 Not Started, and the guard passed
because `685` and `692` are both closed. `UX-748`'s verifier confirmed
the mechanism by swapping `_ids_in()` into that clause:

```console
UX-689 is not closed
UX-690 is not closed
```

`UX-748` corrected the sentence — the status now names the six that
landed and the two that did not — but left the clause reading
endpoints, because widening it was outside that row's three named
guards. So the guard would pass on the same shape again tomorrow.

## Required Fix

1. Swap `_ITEM` for `_ids_in()` in
   `test_a_landed_status_names_only_closed_filings`, so a `landed`
   status is checked against every filed id its ranges span.
2. Sweep every `landed` and `partial` status in `directions.md` for the
   sentences the widening reddens, and correct each to what is true —
   the sentence is the defect, not the guard.
3. **The inverse check:** restore `` `UX-685`..`UX-692` all closed `` and
   confirm the widened clause reddens naming `689` and `690`. If it
   does not, the widening is vacuous and the fix is not made.

## Out of Scope

- `_RANGE_OPEN`'s phrasing set. `UX-748` widened it to
  `are|is|remain|remains` with an optional `still`; a further phrasing
  is a new finding and wants its own measurement rather than a guess
  bolted onto this row.
- The `landed as A..B` historical-record shape, which `UX-748`'s own
  comment says is a fixed record and correctly not range-expanded.

## Acceptance Test

`test_a_landed_status_names_only_closed_filings` reads `_ids_in()`,
`make test` is green with every corrected status pasted, and the
mutation above reddens it naming both open ids.

## Outcome

**Gap measured:** `test_a_landed_status_names_only_closed_filings` read
`{int(n) for n in _ITEM.findall(rest)}` — two endpoints of a range, not
its span. Population, via the guard's own `_statuses()`:

```console
$ python3 -c "import sys; sys.path.insert(0, 'tests/unit'); \
import test_every_direction_names_its_reader as m; \
print(len([1 for h, s in m._statuses() \
if s.split('**Status:**', 1)[1].strip().startswith('landed')]))"
15
```

15 `landed` statuses, range-expanded via `_ids_in()`, name 94 ids;
checked against the guard's own closed-set and independently against
`closed.md`'s index:

```console
$ python3 -c "...ids = union of _ids_in(rest) for the 15 landed rows...
print(len(ids)); print(sorted(ids - m._closed_filings())); \
print(sorted(ids - closed_md_ids))"
94
[]
[]
```

All 94 already closed both ways; only Direction 18's sentence
(corrected by `UX-748`) would have reddened. No sentence needed
correcting.

**Close measured:** swapped `_ITEM.findall(rest)` for `_ids_in(rest)`
in the landed clause. `pytest
tests/unit/test_every_direction_names_its_reader.py -q` → `23 passed`.
Inverse check — restored line 1558 to `landed — `UX-685`..`UX-692` all
closed.`, reran the single test:

```text
FAILED …test_a_landed_status_names_only_closed_filings
AssertionError: a `landed` status citing open work:
['## Direction 18…: UX-689 is not closed',
 '## Direction 18…: UX-690 is not closed']
```

Both open ids named; reverted `directions.md` to the checked-in text
(unchanged — no correction was live-needed).

**Mutation table:**

| clause | mutation | reddened | count |
|---|---|---|---|
| landed clause | restore `685..692 all closed` (endpoints-only phrasing `_ids_in` now expands) | yes, names 689 & 690 | 1 failed, 22 deselected |

`make test` for this row is the round's batch gate, run once after
`UX-755`'s fix lands — that row's own `make test` currently reads `12
failed, 7606 passed`, all 12 real-`bst` end-to-end tests failing on
`Cache too full` (BuildStream sizing its 5% reserve off nominal disk
rather than free space), none in this diff's touching set.

`_closed_filings()`/`_filing_numbers()` read each file's own
`**Status:**` header, not `README.md`/`closed.md`; if the two ever
drift the guard sides with the header — no live instance found here.
