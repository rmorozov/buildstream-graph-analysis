# UX-990: the BuildStream behaviour claims in `tools/` are outside the register `UX-940` built for `bga/`

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-940 | **Blocks:** — | **Found by:** round 138 — enumerating `bga/`'s versioned claims for `UX-940` | **Serves:** whoever reads a BuildStream behaviour claim in the capture tools and has to decide whether it still holds on the pinned binary | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

`UX-940` put every BuildStream behaviour claim in `bga/` into
`tests/bst_claims.json`, each with the version it was last read on, and
its guard warns when that version is older than `ci.yml`'s
`BST_VERSION`. Its completeness clause reads `bga/` only, because
`bga/` is what the row named. The capture tools carry the same class of
claim, and none of them is in the register:

```text
$ grep -rnE "\bBuildStream 2\.[0-9]+\.[0-9]+\b" tools/ --include=*.py | wc -l
14
$ grep -rlE "\bBuildStream 2\.[0-9]+\.[0-9]+\b" tools/ --include=*.py | wc -l
8
```

Thirteen of the fourteen name 2.7.0 and one names 2.8.0; CI pins 2.8.1.
Some are behaviour claims (`bst_show_to_graph.py:127`, the only
per-element parallelism control; `bst_checkout_cost.py:18`, what
`_stream.py::checkout()` does), some are provenance of a fixture or a
log header (`bst_cache_logs.py:38`), and which is which is the reading
this row owes.

## Required Fix

Read each of the fourteen lines, register each that is a behaviour claim
with a 2.8.1 reading from that wheel, and widen the completeness clause
of `tests/unit/test_a_behaviour_claim_names_the_bst_it_was_read_on.py`
to `tools/`, with a way to say a line is provenance rather than a claim.

## Out of Scope

`tests/`'s fixture provenance (`bst 2.7.0` logs, a `toolchain` block),
which records what a fixture was captured with and does not age.

## Acceptance Test

The completeness clause reddens on a new versioned line in `tools/` that
is neither registered nor declared provenance, and every registered
`tools/` claim carries a reading pasted with its command.

## Decision

The `architect`, round 140, at `398b4db9`.

```text
Route:     read each of the 14 tools/ lines in the downloaded 2.8.1 wheel; register the claims in
           tests/bst_claims.json with provenance lines (path, anchor, reason) in the same
           register, not source markers; widen completeness to bga/ and tools/, per line
Rejected:  keep it in the bookkeeping batch - each line needs its own wheel reading, and a
           wrong claim is a wrong capture: product work
           a `# provenance` source marker - changes tools/ files under the sizes ratchet
Files:     tests/bst_claims.json, tests/unit/test_a_behaviour_claim_names_the_bst_it_was_read_on.py
Guard:     test_every_versioned_line_in_bga_and_tools_is_registered_or_provenance
Mutation:  add a "BuildStream 2.8.1" line to the registered tools/bst_show_to_graph.py -> red,
           which today's per-file check would not (measure bga/ per line first: 7 vs 16 anchors)
Class:     product
```

## Outcome

**Round 140, 2026-09-23**

**The gap.** `tools/` names a BuildStream version on 14 lines in 8
files; none was in `tests/bst_claims.json`, and its completeness clause
read `bga/` per *file*: `grep -rlE … bga/ | wc -l` names 6 files but
`grep -rnE … bga/ | wc -l` names 7 lines, and the register held 16
anchors across those 6 files - so a fresh `BuildStream 2.8.1` line
dropped into an already-registered file would pass unnoticed.

**The close.** 9 new claims (9 tools/ sites) plus 3 more tools/ sites
added to the existing `notparallel-clamps-to-one-job` claim, and 1
`bga/` site added to `max-jobs-is-protected` for
`serialization_points.py:10`'s own intro line - which the per-file
clause had also let through uncaught. 2 lines are `provenance` (an
external project.conf convention; a real log's own captured header),
listed with a `reason`, in the same register. The guard is now
`test_every_versioned_line_in_bga_and_tools_is_registered_or_provenance`,
per line over `bga/` + `tools/`, checked against claim sites and
provenance entries alike via the existing `where()`.

**The reading**, in 2.8.1's own wheel (`pip download buildstream==2.8.1
--no-deps`, sha256 `aa3412eb…9701`; read with `zipfile`, no install):

| tools/ line | text read | 2.8.1 source | verdict |
|---|---|---|---|
| `bst_run_wrapped.py:10` | elapsed prefix is per-`timed_activity` | `_messenger.py:312,317` `elapsed = datetime.datetime.now() - timedata.start_time` | holds |
| `bst_native_build_tracer.py:16` | no `buildbox-run-bubblewrap` to shadow | wheel has `buildbox-{casd,fuse,run}`, no `-bubblewrap` (`namelist()`) | holds |
| `bst_native_build_tracer.py:2531` | `-o`/`--option` the only two-value global | `cli.py:305-371`, `click.Tuple([str,str])` only at 351-358 | holds |
| `bst_extract_run.py:205` | real projects set `ref-storage` as a scalar | not a source behaviour - **provenance** | n/a |
| `bst_extract_run.py:393` | `project.refs` keyed by element+source | `_projectrefs.py:104` `lookup_ref(project, element, source_index)` | holds |
| `bst_show_to_graph.py:127,155,195` | `notparallel` the one control, clamps to 1 | `_variables.pyx:288-289` (UX-940's own reading; extra sites) | holds |
| `bst_show_to_graph.py:328` | `%{kind}` is the plugin kind | `widget.py:358` `fmt_subst(line, "kind", element.get_kind())` | holds |
| `bst_checkout_cost.py:18` | `checkout()` pays overhead once/invocation | `_stream.py:685-738`, one `_load()`/`query_cache()` per target | holds |
| `chrome_trace_to_bga_trace.py:15` | START/SUCCESS text is a path or a phrase | `job.py:341` `logfile=filename`; `element.py:1501` `"Staging sources"` | holds |
| `bst_log_to_chrome_trace.py:97` | elapsed format `HH:MM:SS[.ffffff]`/`--:--:--` | `widget.py:131-146` `render_time` | holds |
| `bst_log_to_chrome_trace.py:104` | scheduler defaults 10/4/4 | `userconfig.yaml:61,64,67` `fetchers: 10; builders: 4; pushers: 4` | holds |
| `bst_cache_logs.py:38` | a real log's own header text | a fixture's captured text - **provenance** | n/a |

All 12 behaviour claims hold on 2.8.1, so `confirmed_on` is `2.8.1` on
every new claim.

| # | mutation | result |
|---|---|---|
| M1 | inserted `# … BuildStream 2.8.1 …` as line 2 of the registered `tools/bst_show_to_graph.py` | red: `register or mark provenance in bst_claims.json: ['tools/bst_show_to_graph.py:2']` (1 failed, 5 passed, `-n 2`) |

Reverted from a saved copy (`diff` empty), `__pycache__` cleared, green
again (6 passed, `-n 2`).

`make lint`: clean. `tests/unit/test_the_register_is_terse.py`: passed.
Guard file alone, `-n 2` (machine shared with four other tracks; no
`make test`/`make test-touching` run).
