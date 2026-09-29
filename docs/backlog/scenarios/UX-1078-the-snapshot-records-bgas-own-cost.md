# UX-1078: a snapshot does not record what bga itself cost the build

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1077 | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R5, R8 | **Topic:** capture | **Area:** tools | **Shape:** mechanical

**Guard:** test_the_snapshot_records_its_tail.py

## Motivation

The capture budget is 15-25% of time and resources (2026-09-20),
and `UX-895` measured the capture's overhead during the build
(+9.3% wall, all arms on). Nothing measures the tail after it, which
every one of several hundred review builds a day pays, and which grows
with the graph rather than with the work: an incremental build of a
5,002-element project that rebuilds nothing still pays one analysis
and a compare over the whole graph (about 104 s here, [the audit](../../audits/perf-snapshot-view-2026-09-28.md); inferred
for the cached case, not captured).

## Decomposition

Input classes: a complete tail, an interrupted one, a `--no-compare` snapshot. Journeys: `bga snapshot --list` and the store aggregate.

## Required Fix

In `tools/bga_snapshot.py`: The snapshot writes `tail.json`: wall and peak RSS per post-build
phase and the build's own wall. `bga snapshot --list` and the page
show bga's share beside the build; the store aggregate carries it, so
an agent pool's owner can read it across builds. `tail.json` is a
capture-directory document, so its schema lands in `bga/schemas.py`.

## Out of Scope

A budget that fails a build.

## Acceptance Test

`tests/unit/test_the_snapshot_records_its_tail.py`: A snapshot of the golden store writes `tail.json` with one row per
phase that `UX-1077` announces, and `--list --format json` carries the
total. Mutation: drop a phase from the file, and the guard reds.

## Decision

Shaped by the architect, 2026-09-28; adopted by the session.

- **Route:** one recorder in `bga/progress.py`: `with progress.timed(name):` announces the phase (UX-1077), prints its elapsed time and appends a row to an in-process ledger. Per-phase peak RSS is VmHWM from `/proc/self/status`, reset by writing `5` to `/proc/self/clear_refs` at phase start; null off Linux; never `ru_maxrss` (a whole-process high-water mark). `bga_snapshot` rewrites `tail.json` after each phase, so an interrupted tail keeps its rows with `complete: false`; a skipped phase (`--no-compare`) is absent, not zero; the build's own wall is timed around its subprocess. UX-1080's calls land in the same ledger as `calls` under their phase, through `progress.timed_call(argv)` around the subprocess calls in `bst_native_build_tracer.py` and `bst_show_to_graph.py`.
- **Schema:** `tail/v1` = `{schema, producer, build_wall_s, phases: [{name, wall_s, peak_rss_kb|null, calls: [{verb, wall_s, exit}]}], complete}`. No stored total; `store_listing` and the aggregate sum it (UX-996).
- **Rejected:** separate timers for printing and the file (two lists that drift); per-phase `ru_maxrss` (a proxy); a committed `total_s` (derivable).
- **Files:** `bga/progress.py`, `tools/bga_snapshot.py`, `tools/bga_view.py` (UX-1077's steps), `bga/schemas.py`, `bga/run_store.py` (TAIL_NAME, layout row ~701), `bga/store_aggregate.py`, the store exhibit's module under `bga/viewer/`, `tests/unit/test_the_snapshot_records_its_tail.py`.
- **Guard:** with `BGA_FORCE_PROGRESS=1` on the golden store, the phase names in `tail.json` equal the phases announced on stderr; `--list --format json` carries their sum; `--no-compare` has no compare row; the file validates against `tail/v1`.
- **Mutation:** remove one phase's `timed` wrapper, or make the writer drop its last row.
- **Class:** product. **Split:** UX-1077+UX-1078 one track (opus), after UX-1072/1075/1081 merge; UX-1080 after it.

## Outcome

**Gap measured:** the guard against the base tree (`46f21ac`, `git
archive HEAD`): no snapshot writes `tail.json` (`run_store` has no
reader - `AttributeError: ... 'read_tail'`, 4 tests); a `store/v1` row
has no tail key (`KeyError: 'bga_tail_us'`); the page's store twin is
`Snapshot · Duration · Verdict` only. `6 failed in 1.02s`.

**Close measured:** `tail/v1` rewritten after every `progress.timed`
row (`on_row`, atomic `os.replace`), `complete: true` only when the
tail ends; the second golden snapshot writes:

```text
{"schema": "tail/v1", "build_wall_us": null, "phases": [
 {"name": "Plane 2 report", "wall_us": 1372, "peak_rss_bytes": 52957184, "calls": []},
 {"name": "run directory", ...}, {"name": "raw log gzip", ...},
 {"name": "analyze", "wall_us": 39466, ...}, {"name": "element slice", ...},
 {"name": "compare", "wall_us": 57603, ...}, {"name": "store size", ...}],
 "complete": true}
```

`build_wall_us` is null there because the harness replaces
`run_traced_build`; `timed_build()` sits on the `with` around
`run_wrapped` (UX-1077's AST guard). `store/v1` rows gain
`bga_tail_us` and `build_wall_us` (absent before `tail.json`),
`--list` prints `build N.Ns + bga N.Ns`, `store-aggregate/v1` a
`bga_tail_us` distribution per class and blended, the store twin a
`bga after the build` column (`1.0 s beside a 9.0 s build`) once a row
carries it. `tail/v1` is recorded in CHANGELOG's Unreleased row, whose
kind derives `extending` against 0.4.1; no version moved, no tag.
`pytest tests/unit/test_the_snapshot_records_its_tail.py` -> `6 passed`;
the release guard `47 passed`; `test_the_report_you_can_attach.py` ->
`32 passed`. `make test-touching ARGS="--base 7c0ebe0d"` -> `280 file(s)
selected ... 5627 passed, 95 skipped in 251.36s`.

Writer cost (`writer.py`, 7 rows): `_write_tail` 293 us per rewrite,
1,476 B; `producer.stamp()` 36.1 ms cold, once, before the build. Seven
rewrites are 2 ms against the 1,202-element tail's 3.6 s (UX-1077's
`cost.py`).

**Mutation table:**

| mutation | reddened | count |
|---|---|---|
| the writer drops its last row | `..._phases_the_tail_announced`, `test_no_compare_has_no_compare_row`, `..._interrupted_tail_keeps_its_rows` | 3 failed, 3 passed |
| `element slice`'s `timed` removed | `..._phases_the_tail_announced`, `..._interrupted_tail_keeps_its_rows` | 2 failed, 4 passed |
| the listing sums all but one row | `test_the_listing_carries_the_sum` | 1 failed, 5 passed |
| `complete` never true | `..._phases_the_tail_announced` | 1 failed, 5 passed |
| no rewrite after each phase (`on_row` dropped) | `..._interrupted_tail_keeps_its_rows` | 1 failed, 5 passed |
| compare runs under `--no-compare` | `test_no_compare_has_no_compare_row` | 1 failed, 5 passed |
| `tail/v1` types `complete` as a string | `..._phases_the_tail_announced` | 1 failed, 5 passed |
| a phase's wall written in seconds again | `..._phases_the_tail_announced` | 1 failed, 5 passed |
| the aggregate's class drops the tail | `test_the_aggregate_carries_the_tail` | 1 failed, 5 passed |
| the page never adds the column | `test_the_page_shows_the_tail_beside_the_build` | 1 failed, 5 passed |
| the page drops the build beside the tail | `test_the_page_shows_the_tail_beside_the_build` | 1 failed, 5 passed |
| `--list` text prints no tail | `test_the_listing_carries_the_sum` | 1 failed, 5 passed |
| release guard: the tree checked against 0.4.1 though Unreleased exists | `..._real_one_for_the_newest_release`, `..._unreleased_row_is_what_the_tree_answers_for` | 2 failed, 45 passed |
| release guard: Unreleased drops `tail/v1` | `..._real_one_for_the_newest_release`, `..._next_cut_would_be` | 2 failed, 45 passed |
| release guard: Unreleased's kind left at `patch` | `test_its_kind_is_what_the_next_cut_would_be` | 1 failed, 46 passed |

Reverted from the copy: `6 passed`, `47 passed`.

**Deviation:** the Decision's `wall_s` and `peak_rss_kb` are
`wall_us`/`build_wall_us` and `peak_rss_bytes`: `UX-341` retired
`seconds` and `kilobytes` from `schema_hints.QUANTITIES`, and the
number census (`test_every_number_says_what_it_is.py`) resolves every
numeric leaf of every printable contract against it.
