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

A project whose store holds N copies of the golden run, served by
`bga view` and read at 1440x900 (`tests/unit/test_the_store_section_takes_a_window.py`
carries the instrument):

```text
                      N=2      N=12     N=100     N=100 after
picker options          2        12       100              12
twin rows               2        12       100              12
svg marks               5        27       203              27
store-trend nodes      29        92       620              94
store-trend text      250     1,296    10,451           1,522
store.json            745     4,121    34,056           4,206
```

`--aggregate --format json` is the CLI's own document, over the whole
listing, so the page's window does not bound it: **3,884 B -> 1,948** at
100 snapshots, against 1,931 at twelve, with `STAMPS_MAX = 12`.

### After

`store_listing(project, window)` trims the rows and keeps `count` and
`total_bytes` facts about the whole store, with `shown` beside them —
so the page can say what it is a window of. `bga view` passes
`STORE_WINDOW = 12`; `--list` passes nothing, because a listing is O(N)
by definition and that is this item's Out of Scope.

The two nodes and 226 characters N=100 does not share with N=12 are the
window's own sentence and the control that opens the rest — §3a's rule,
and the clause asserts the difference is exactly two rather than
allowing a tolerance something else could grow into. "Show all 100
snapshots" fetches `store-all.json`, which the server offers **only**
when the page's copy is windowed and nothing fetches until it is
pressed, and redraws the twin with every row. The run picker lists the
window; past it, a typed stamp opens `?run=` directly.

`STORE_WINDOW` and `element.js`'s `HISTORY_POINTS_MAX` are held equal by
a clause: they answer the same question — the last dozen runs of this
project — and two windows disagreeing about "recent" is worse than
either.

### What the wider run found, and what it cost

`make test-touching` over this diff reached 1,981 tests and named two
regressions from **earlier commits in this track**, both fixed here:

- `distributionStrip` read its column with
  `querySelectorAll("td[data-column=…]")`, which `UX-526` turned into
  "the rows the bound shows". A strip labelled *"across all 60 rows"*
  was drawn from 25. `tables.js` now exports `columnCells`, which reads
  over `everyRow`, and the two other call sites use it.
- The export grew and both size bounds tripped. Page bytes only — the
  embedded data is byte-identical at every step:

```text
                  page      golden   macro_micro
before         294,848     408,787       458,782
UX-526         295,987     409,926       459,921   (+1,139)
UX-527         296,745     410,684       460,679   (+  758)
UX-528         299,497     413,436       463,431   (+2,752)
```

  411,000 -> 418,000 and 463,000 -> 468,000, restated in
  `test_the_report_you_can_attach.py` with that table.

`store/v1` gains `shown` and `store-aggregate/v1`'s class entries gain
`stamps_total`; both are **additions**, so no contract bumps
(fixing guide §3.7), and both are declared with a quantity because
`test_every_number_says_what_it_is.py` asks.

### Mutations verified red and reverted (6)

| # | mutation | reddened | count |
|---|---|---|---|
| M1 | `STORE_WINDOW = None` | the whole acceptance — `the run picker offers 100 runs`, `rows: 100 against 12` | 9 failed |
| M2 | `stamps` uncapped | `the aggregate caps its stamps` — `unknown host names 100 runs` | 1 failed |
| M3 | the window is the **oldest** rows (`rows[:window]`) | `the window keeps the latest runs` | 1 failed |
| M4 | "show all" hands back the window it drew | `show all loads every snapshot` — `all: 12` | 1 failed |
| M5 | no typed run id past the window | `a stamp past the window can be typed` | 1 failed |
| M6 | the heading does not say it is a window | `it says which runs it is drawing` | 1 failed |

M3 is the one worth keeping: every count clause passes over the twelve
oldest runs, and the drift question is answered backwards.

### Acceptance Test

```text
$ python3 -m pytest tests/unit/test_the_store_section_takes_a_window.py -q
11 passed in 17.96s
```

`make lint` clean. The new file is **18s** and needs a `LARGE` row in
`tests/tiers.py` and a `tests/ci_reference.json` entry — both this
track's orchestrator's, not written here.
