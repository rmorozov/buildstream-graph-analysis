# UX-565: Part 29 is wired to `None` while the store holds the series it needs

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-234 (the store as a distribution), UX-92 | **Serves:** R3, the CI owner asking how stable an element's duration is | **Topic:** analysis

## Motivation

```text
bga/analyzer.py:2039-2040          historical_durations = None    # unconditionally
bga/diagnostics/analyzer.py:1027   returns empty when None
specification.md:1396-1422         Part 29, duration variability from a history
```

When the spec was written no history existed. `bga/run_store.py`
and `cache_trend.py` now hold a series of runs of the same project,
`--aggregate` already reads it per host class, and Part 29's
precondition is met on every store with two or more runs — and the
wiring still passes `None`.

## Required Fix

`analyze` on a snapshot reads the store's prior runs of the same
host class (the `UX-234` join) into `historical_durations`; Part 29's
output reaches the analysis document (an addition) and the page's
element cards, which already draw a history sparkline from the same
runs (`HISTORY_POINTS_MAX`). A guard on a planted store of three
runs.

## Out of Scope

- Cross-host histories — refused by `UX-186`'s rule, as today.

## Acceptance Test

On a store of three same-host runs the variability block is
non-empty; mutation: restore `None` — red.

## Outcome

**The gap.** A planted store of three same-host runs of the golden
fixture, traces scaled 1.0 / 1.6 / 2.4, each with a real
`write_element_slice` beside it. `bga analyze` on the newest:

```text
diag.duration_variability: []
elements keys: ['blast_radius', 'blast_radius_ranked_by',
 'criticality_probability', 'downstream_count', 'element_durations',
 'slack', 'top_blast_radius', 'unweighted_depth', 'zero_slack_share']
duration_variability in document: False
```

The Motivation's three line references all hold as written
(`analyzer.py:2039-2040`, `diagnostics/analyzer.py:1027`,
`specification.md:1396-1422`).

**The close.** Same store, same command:

```text
"base.bst": {"coefficient_of_variation": 0.3265986323710904,
  "high_variability": true, "mean_us": 10000.0, "median_us": 10000,
  "p75_us": 14000, "p95_us": 14000, "samples": 3,
  "host_class": "Ryzen 9 7950X · 32 cores · unknown memory_bytes"}
```

Samples are prior snapshots of **this run's host class** plus this
run's own measured durations. Its own, not its slice: `bga snapshot`
analyses (`tools/bga_snapshot.py:543`) before it writes the slice
(`:548`), so a series read from the store alone gives the capture's
`analyze.json` one sample fewer than a later `bga analyze` of the same
directory. Measured with the newest slice deleted: identical output.
Window `HISTORY_RUNS_MAX = 12`, the sparkline's — on a planted 30-run
store every row reads `"samples": 12`.

Cost, on the same fixtures (`store_listing` is what the read adds, and
`bga view` already pays it once per page):

```text
3 snapshots    store_listing 0.009s cold / 0.000s warm   analyze 0.007s
30 snapshots   store_listing 0.019s cold / 0.004s warm   analyze 0.011s
```

`python3 tools/dev_refresh_analysis.py` → `0 of 2 committed analysis
document(s) disagree`: neither committed fixture is in a store, so the
golden did not move.

**Mutations** (`tests/unit/test_part_29_reads_the_store_it_has.py`,
11 tests, `PYTHONDONTWRITEBYTECODE=1 PYTEST_XDIST=`):

| mutation | reddened | count |
|---|---|---|
| `historical_durations = None` (the named one) | the block, the class label, the field census | 4 failed, 7 passed |
| drop the host-class filter | `..._other_machines_runs_are_not_samples` | 1 failed, 10 passed |
| `>= stamp` → `> stamp` (this run's slice counts too) | `..._does_not_depend_on_when_it_is_asked` +2 | 3 failed, 8 passed |
| `HISTORY_RUNS_MAX` 12 → 11 | `..._window_is_the_one_the_sparkline_draws` | 1 failed, 10 passed |
| floor `MIN_BASELINE_RUNS` → 2 | `..._two_runs_are_below_the_floor` | 1 failed, 10 passed |
| `host_class` → `None` on every row | `..._names_the_machine_its_samples_came_from` | 1 failed, 10 passed |
| publish `p50_us` (undeclared) | `..._published_fields_are_declared` | 1 failed, 10 passed |
| delete the two `ELEMENT_MAPS` rows | `..._card_draws_it` | 1 failed, 10 passed |
| `ELEMENT_KEYED_OPTIONAL = ()` | whole file, at import (`KeyError`) | 1 error |

Under the named mutation `..._does_not_depend_on_when_it_is_asked`
does **not** discriminate — both sides are `None`, so it passes
vacuously. It is discriminating for the third row and is kept for that.

**Deviation from the Required Fix:** none. Two surfaces beyond the four
the salvage patch named: `schemas.ANALYZE_RUN_DEPENDENT_KEYS` (a
conditional `_SIGNALS_TABLES` member not listed there fails
`test_no_level_carries_nothing.py`, 2 failed before it was added), and
no spec edit — 32.4 already declares `signals.duration_variability`,
and this makes that declaration true rather than aspirational.
