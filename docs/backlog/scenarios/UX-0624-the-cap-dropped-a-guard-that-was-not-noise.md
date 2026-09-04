# UX-624: the cap dropped a guard that was not noise

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-605 (the cap), UX-522 (the census set), UX-336 (the selector) | **Found by:** round 85, by the contracts track paying for it | **Serves:** a track adding a declared key | **Topic:** guards

## Motivation

`UX-605` capped a coverage-map entry at 25 files, because CI's adopted
`tests/touch_map.json` made a one-module diff select 180 of 449. The
cap is right about the noise and wrong about one file it took with it:

```text
$ python3 -c "…dt.select(['bga/schemas.py', 'bga/compare.py'])…"
cap=        25  selected=  53  test_every_number_says_what_it_is.py: False
cap=1000000000  selected= 216  test_every_number_says_what_it_is.py: True
                                why: ['map', 'map']
```

Both entries are over the cap — `bga/schemas.py` maps 189 files,
`bga/compare.py` 30 — so both are discarded whole, and the guard that
reads every declared quantity goes with them. It is reachable **only**
through the map: no grep from either module names it.

The cost is not hypothetical. `UX-610` added `verdict_provenance` to
`compare/v2`, passed `make test-touching`, and failed that census;
the track amended its commit. The next declared key does the same.

The cap is not the defect. Discarding an over-wide entry *whole* is:
it treats a map entry as one claim when it is 189 of them.

## Required Fix

A guard reachable only through an over-wide map entry still reaches the
selection — by joining the census set (`UX-522`), by the map being
pruned rather than capped, or by the cap dropping the entry's noise and
keeping what a narrower rule would have kept. Argued from the
measurement, not chosen for tidiness.

Whatever is chosen must keep `UX-605`'s property: a one-module diff
does not select a third of the suite.

## Out of Scope

- The map's contents and how CI adopts it — `UX-605` measured that and
  the cap stands.
- `UX-610`, which paid the cost and is closed.

## Acceptance Test

A `bga/schemas.py`-only diff whose selection contains
`test_every_number_says_what_it_is.py` and stays under `UX-605`'s
ceiling of 25 median / 130 max files.
