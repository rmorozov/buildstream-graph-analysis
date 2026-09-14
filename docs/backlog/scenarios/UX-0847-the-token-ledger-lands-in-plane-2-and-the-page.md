# UX-847: the token ledger lands in Plane 2 and the page

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-845, UX-846 | **Found by:** round 117, Direction 20 | **Serves:** R4 and R5 (was the pool or the graph the bound) | **Topic:** analysis | **Area:** bga | **Shape:** judgement

## Motivation

Every acquire and release under the mode is a timed event no plane
records: the server's pool moves (`UX-845`'s ledger), the wrappers'
holds (`UX-846`) and the sub-makes' reads are invisible to the
envelope, which sees busy cores but not why they were idle - tokens
nobody took, or tokens everybody waited for. `max_jobs_advice` has no
pinned-element rule and cannot say an element is joined.

## Required Fix

`bga/analyzer.py` and `bga/schemas.py`: a `jobserver` block under
`analyze/v6`, additive - `mode`, `pool_ceiling`, `tokens_idle_share`
(pool tokens unclaimed while an element waited on none), `tokens_starved_share`
(a client blocked on the FIFO while busy cores were below capacity),
per-element `tokens_held_p50`/`max` and `joined` (yes, pinned, held,
unknown kind); `bga/correlate.py`'s `max_jobs_advice` marks a pinned
element `refusal: pinned by the project` instead of a number; the
Perfetto trace gains a `jobserver` track from the ledger; the page
draws the block as one table with the two shares in the lead.

## Decomposition

Input classes: a run without the mode (the block absent, byte for
byte today's output), a run with every element joined, a run with a
pinned element and a held tool; the journey it extends is R4's "were
the cores busy" question in the answer key.

## Out of Scope

The scheduler's decisions (`UX-849`); the finding text's wording is
`UX-824`'s register.

## Acceptance Test

`tests/unit/test_the_token_ledger_has_two_shares.py` builds a
synthetic ledger and asserts the two shares and the per-element table;
mutation: count a held token as idle - red. The committed fixtures
refresh with no diff.

## Outcome

**The gap measured.** Before: `bga.schemas.schema('analyze/v6')` had
61 top-level properties and no `jobserver` key; `compute_max_jobs_advice`
took no `pinned_elements` argument and could only ever set
`row["refusal"]` to a thin-evidence or memory sentence; `grep -rn
"jobserver_ledger" tools/bst_native_build_tracer.py` found the
`PoolController`'s own writer and `summarize_jobserver_ledger`'s
reader, and no third site embedding the raw rows into `report`.
`tools/bga_timeline.py` drew `HOST_COUNTERS` only - no jobserver
counter track. Ledger size for a 30 s capture at the 250 ms tick
(`JOBSERVER_POOL_INTERVAL_S`): 120 controller rows, measured 14,040 B;
one wrapper acquire/release row measured 78 B - both well under any
downsampling threshold, confirming the "no downsampling" decision.

**The producer.** `held`/`tokens_held_p50`/`max` were wired but null in
every real capture - no site joined UX-846's wrapper `acquire` rows
(pid, tokens) to an element. `tools/bst_native_build_tracer.py` gains
`read_pid_to_element` (a second streaming pass over the raw log, the
same move `bga_timeline.element_spans` already makes, reusing
`stream_records`' own `pid`/`element` fields rather than threading a
second output through `Plane2Fold`'s call graph), `tokens_by_element`
(the pure join: `{element: [tokens, ...]}` plus an `unmapped` count)
and `summarize_jobserver_tokens_by_element` (reduces to p50/max).
Wired into `report["jobserver_tokens_by_element"]` and the new
`report["jobserver_tokens_unmapped"]`, read unchanged by
`bga/report/json.py`. `TestReadPidToElement` writes a real raw log in
`parse_trace_log`'s own `START/END ... element=.. cmd=..` format (two
elements/three pids, an empty log, a malformed line beside two
well-formed ones) and asserts the exact map.

**The close measured.**

```text
$ python3 -m pytest tests/unit/test_the_token_ledger_has_two_shares.py -q
...................
19 passed in 0.62s

$ python3 tools/dev_refresh_analysis.py
  ok    tests/fixtures/golden/mixed_task_kinds
  ok    tests/fixtures/with_timeline
0 of 2 committed analysis document(s) disagree with the analyzer

$ python3 tools/dev_baseline.py --check
clean: 561 finding(s) match tests/quality_baseline.json; ... (no `new:` lines)
```

**Mutation table.**

| guard | mutation | result |
|---|---|---|
| `test_a_wrapper_row_is_not_a_tick` | `compute_jobserver_shares`'s tick filter widened from `"action" in row` to every dict row | red: `idle == 0.5` not `1.0` |
| `test_a_pinned_element_gets_no_number` | `compute_max_jobs_advice`'s pinned-refusal block removed | red: `refusal is None` not `"pinned by the project"` |
| `test_a_pid_no_element_owns_is_unmapped` | join replaced `pid_to_element.get(pid)` with the first mapped element | red: `({'held.bst': [3]}, 0)` not `({}, 1)` |
| `test_two_elements_three_pids` + malformed-line case | `read_pid_to_element`'s body replaced with `return {}` | red: `{} == {100: 'a.bst', ...}` (both cases) |

Each reverted from a scratch copy, re-confirmed 19 passed before commit.

**Deviation.** The verifier held twice: first on
`jobserver_tokens_by_element` having no producer (always null, an
undisclosed proxy), then on the producer itself having no guard
(`return {}` stayed green) - both closed by code, not by disclosure.
