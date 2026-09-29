# UX-1013: admission ranks from BuildStream's own cached build logs when bga never captured the project

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-1005 | **Found by:** Ruslan on the Graviton thread (2026-09-25), on ranking admission with no previous capture | **Serves:** R4, R5 | **Topic:** capture | **Area:** tools | **Shape:** judgement | **Reading:** runner:bst-examples

**Guard:** `tests/unit/test_admission_ranks_from_cached_logs.py`

## Motivation

UX-1005 track C ranks waiting sandboxes by slack from a `--plan`, or,
with none, from graph structure: level from the bottom, ties broken by
declared width. Structure cannot see duration: on `13-mixed-graph` the
giant and its 24 narrow siblings share one level. A machine that built
the project before keeps each element's build log in BuildStream's
local cache (`bst artifact log`), so per-element durations may exist
where bga never ran.

## Decomposition

surfaces: the tracer's ranking source (`plan` / `structural` today)
guards: an element whose cached log reads the longest build ranks first at equal level; a log with no timing falls back to structural and says so
gap: whether `bst artifact log` carries start and end times reliably, per BuildStream version, and for a key that changed since
track: after UX-1005

## Required Fix

A third ranking source, `cached-logs`, between `plan` and
`structural`, named in the report.

## Decision

The reading that answers the Decomposition's gap, CI `bst-examples` at `dbdc366a` (PR #303, check run 109479167757), after a build of `10-jobserver`-style project with bst 2.8.1:

```text
UX-1013 --deps none | rc=2 lines=4 | Usage: bst artifact log [OPTIONS] [ARTIFACTS]...
UX-1013 leaf-a.bst | rc=0 lines=149 elapsed-stamps=8 | ... last: [00:00:03] SUCCESS leaf-a.bst: Running commands
UX-1013 giant.bst | rc=0 lines=892 elapsed-stamps=8 | ... last: [00:03:09] SUCCESS giant.bst: Running commands
```

So `bst artifact log <element>` (one element per call; `--deps` is not an option on 2.8.1) prints the cached build log, whose `SUCCESS <element>: Running commands` line carries the elapsed build time as `[HH:MM:SS]`. giant.bst read 00:03:09 against its measured 189.2 s.

- A third ranking source `cached-logs`, tried after `plan` and before `structural` in `bst_native_build_tracer.py` (~line 2480): for each element, run `bst artifact log <element>` in the project (timeout, stdout captured, rc checked) and parse the last `[HH:MM:SS] SUCCESS <element>: Running commands` line to seconds. Parser is a pure function over text, unit-tested on the two pasted shapes plus a log with no such line.
- Ranking value: the element's cached duration, longest first; within that, ties fall to the structural order. An element with no parsable log takes its structural rank below every element that has one — so the source is `cached-logs` only when at least one element parsed; if none parsed (rc!=0, no cache, bst missing), fall back to `structural` and print one line saying why (count of elements tried, count parsed).
- `ranking_source` becomes `"plan" | "cached-logs" | "structural" | None`; the report names it wherever it names the source today (find every consumer of `ranking_source` and the schema enum, if any).
- Guard: `tests/unit/test_admission_ranks_from_cached_logs.py` — parser on the pasted shapes; ranking puts the longest cached element first at equal structural level; all-unparsable falls back to structural and says so. Mutations: parser ignores the element name (a SUCCESS line for a dependency counts); fallback taken when some parsed; order reversed.
- Out of scope: remote caches; calling bst in the unit tests (monkeypatch the runner).

## Out of Scope

Remote caches' logs.

## Acceptance Test

On a project built once without bga, the capture's report names
`cached-logs` as the ranking source and ranks the longest element first.

## Outcome

**Gap measured.** CI `bst-examples` at `dbdc366a` (PR #303), bst 2.8.1,
pasted in the Decision: `bst artifact log giant.bst` rc=0, last line
`[00:03:09] SUCCESS giant.bst: Running commands` against a measured
189.2 s; `--deps none` is rc=2 (not an option). `ranking_source` was
`plan` / `structural` / `None`, with no source for a machine that built
the project without bga.

**Close measured.** `tools/bst_native_build_tracer.py` tries
`cached-logs` after `plan` and before `structural` through
`rank_admission` in `tools/jobserver/cached_logs.py` (new, behind the
package's `__all__`): one `bst artifact log e1 .. e200` per chunk of
200 (120 s timeout, rc checked; a failed chunk stays unparsed), the
concatenated stdout parsed per element by `parse_cached_build_seconds`,
ranked by `cached_log_ranking`. `dev_sizes.py --adopt --force`: tracer
`file_lines` 8946 -> 8947 (`longest_function` 589 -> 584),
`tools/jobserver/__init__.py` 80 -> 85; `dev_baseline.py --write --force
--reason UX-1013` for the one `S603` on the `bst artifact log` call. The
capture prints `admission ranking: cached-logs (P of N parsed) | first:
<top 3>` or `admission ranking: structural (cached logs: 0 of N
parsed)`, and `jobserver_admission_pool.ranking_source` carries the
source. CI step `11's second capture ranks admission from the cached
logs (UX-1013)` prints that line as a notice on a warm-cache second
capture of `11-serial-giant` - the Acceptance Test's reading, taken on `bst-examples` at `13731ab9` (PR #303, check run 109521626077):

```text
UX-1013 ranking | admission ranking: cached-logs (6 of 8 parsed) | first: giant.bst, leaf-a.bst, leaf-b.bst
```

```text
$ python3 -m pytest -v tests/unit/test_admission_ranks_from_cached_logs.py
test_the_parser_reads_the_elapsed_stamp_of_the_elements_own_success_line PASSED
test_a_success_line_for_another_element_is_not_this_ones PASSED
test_the_longest_cached_build_ranks_first_at_equal_level PASSED
test_no_parsable_log_falls_back_to_structural PASSED
test_one_call_reads_a_chunk_of_elements PASSED
test_the_report_names_the_source_that_ran[...cached-logs (1 of 2 parsed) | first: giant.bst, leaf-a.bst] PASSED
test_the_report_names_the_source_that_ran[...structural (cached logs: 0 of 2 parsed)] PASSED
7 passed in 0.39s
```

**Mutation table** (`tests/unit/test_admission_ranks_from_cached_logs.py`):

| mutation | reddened | run |
|---|---|---|
| none | - | 7 passed |
| one call per element (`CHUNK = 1`) | `test_one_call_reads_a_chunk_of_elements` | 1 failed, 6 passed |
| parser ignores the element name (`if True:`) | `..._another_element_is_not_this_ones`, `..._ranks_first_at_equal_level`, `test_one_call_reads_a_chunk_of_elements`, `..._names_the_source_that_ran[cached-logs]` | 4 failed, 3 passed |
| fallback taken when some parsed (`len(durations) < len(structural)`) | `..._ranks_first_at_equal_level`, `test_one_call_reads_a_chunk_of_elements`, `..._names_the_source_that_ran[cached-logs]` | 3 failed, 4 passed |
| order reversed (`durations[e]` for `-durations[e]`) | `..._ranks_first_at_equal_level`, `test_one_call_reads_a_chunk_of_elements` | 2 failed, 5 passed |

**Deviation from the Decision:** batched - `bst artifact log` takes
several ARTIFACTS, so one call reads 200 elements instead of one; one
call per element cost ~1 bst start per element on fdsdk-size graphs.
