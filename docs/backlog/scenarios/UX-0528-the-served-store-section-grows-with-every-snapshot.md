# UX-528: the served store section and run picker grow with every snapshot

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-394 (the cross-run controls, filed at two runs), UX-316 (the store exhibit) | **Serves:** the CI owner whose store holds a hundred runs | **Topic:** viewer

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

## Outcome (round 80, 2026-09-02) — 🟢 Done

### The gap, measured

A store of N copies of the golden run, served and read at 1440x900
(`test_the_store_section_takes_a_window.py` is the instrument):

```text
                    N=2    N=12    N=100   N=100 after
picker options        2      12      100            12
twin rows             2      12      100            12
svg marks             5      27      203            27
store-trend nodes    29      92      620            94
store-trend text    250   1,296   10,451         1,522
store.json          745   4,121   34,056         4,206
```

`--aggregate --format json` is the CLI's own document over the whole
listing, so the page's window does not bound it: **3,884 B -> 1,948** at
100 against 1,931 at twelve, with `STAMPS_MAX = 12`.

### After

`store_listing(project, window)` trims the rows and keeps `count` and
`total_bytes` about the whole store with `shown` beside them, so the page
can say what it is a window of. `bga view` passes `STORE_WINDOW = 12`;
`--list` passes nothing — a listing is O(N), this item's Out of Scope.

The two nodes and 226 characters N=100 does not share with N=12 are the
window's sentence and the control that opens the rest — asserted as
*exactly two*, not a tolerance. "Show all" fetches `store-all.json`,
offered **only** when the page's copy is windowed and only once pressed;
past the window a typed stamp opens `?run=`. A clause holds
`STORE_WINDOW` equal to `element.js`'s `HISTORY_POINTS_MAX`: two windows
disagreeing about "recent" is worse than either.

### What the wider run found

`make test-touching` reached 1,981 tests and named a regression from an
**earlier commit in this track**: `distributionStrip` read its column
with `querySelectorAll("td[data-column=…]")`, which `UX-526` turned into
"the rows the bound shows" — *"across all 60 rows"* drawn from 25, now
`columnCells` over `everyRow`. And both size bounds tripped, page only —
this track is **+4,649 B** (294,848 -> 299,497), split 1,139 / 758 /
2,752 across its three items. **§3.6:** that is half the round. The
other track grew the same page from the same base, so the merged tree is
415,729 / 465,748 B and the bounds landed at **420,000 / 470,000**, not
this commit's 418,000 / 468,000; the per-item table lives beside them in
`test_the_report_you_can_attach.py`. `store/v1` gains `shown` and
`store-aggregate/v1` `stamps_total`; both **additions**, no bumps
(§3.7), both with a quantity.

### Mutations verified red and reverted (6)

| # | mutation | red |
|---|---|---|
| M1 | `STORE_WINDOW = None` | 9 |
| M2 | `stamps` uncapped | 1 |
| M3 | the window is the **oldest** rows (`rows[:window]`) | 1 |
| M4 | "show all" hands back the window it drew | 1 |
| M5 | no typed run id past the window | 1 |
| M6 | the heading does not say it is a window | 1 |

M3 is the one worth keeping: every count clause passes over the twelve
*oldest* runs, and the drift question is answered backwards.

### Acceptance Test

```text
$ pytest tests/unit/test_the_store_section_takes_a_window.py -q
11 passed in 17.96s      make lint clean
```

Reported at **18s**; tiered by the merge at **13.4s** alone on a quiet
machine — `MEDIUM`. The reference entry comes from CI's adopt
(`UX-447`).

### Deviation from the Required Fix

None.
