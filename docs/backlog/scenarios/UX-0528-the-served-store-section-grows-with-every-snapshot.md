# UX-528: the served store section and run picker grow with every snapshot

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-394 (the cross-run controls, filed at two runs), UX-316 (the store exhibit) | **Serves:** the CI owner whose store holds a hundred runs | **Topic:** viewer

## Motivation

A store of N copies of the ex06 snapshot, served by `bga view`:

```text
                              N=2        N=20       N=100
select#bga-run options          2          20         100    nav.js:451-466
#store-trend rows / svg        3 / 5    21 / 43    101 / 203  views.js:293-323, 369-375
#store-trend text             279 B    2,447 B   12,050 B
store.json                    3.2 KB   31.9 KB   159 KB     bga_snapshot.py:887
--aggregate --format json     2.4 KB    3.7 KB    6.0 KB    stamps, store_aggregate.py:193
history sparklines            2 pts     12         12       HISTORY_POINTS_MAX = 12, element.js:1132
```

The sparklines beside these got a window; the store exhibit, its
table and the picker did not. `UX-394` was filed with two runs in
the store and never saw the axis.

## Required Fix

- The store exhibit and its table twin take the same window the
  sparklines have (the last 12, with the count and a "show all" on
  the §3a focus path); the run picker lists the windowed runs plus
  `@last`/`@prev`, and a typed run id for the rest.
- `store.json` is written windowed for the page (the CLI `--list`
  keeps every row; it is a listing), and `--aggregate --format
  json` drops `stamps` or caps it — the text output already does.

## Out of Scope

- The listing commands' text output — a listing is O(N) by
  definition.
- Pruning the store — `run_store.py`'s `prune` exists.

## Acceptance Test

At N=100 the served page's store nodes and picker options are the
same as at N=12; mutation: remove the window — red at N=100.
