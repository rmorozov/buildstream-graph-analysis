# UX-901: the jobserver is a subtool behind a boundary, not a mode woven through bga

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-841..UX-852 (the mode as it landed), UX-851 (the capture option) | **Found by:** the 2026-09-20 rollout brief ([`continuous-build-improvement.md`](../../design/continuous-build-improvement.md), section 3) — the owner's proposal: keep the jobserver integrated for before/after measurement, and build it so it can later move into a separate project of BuildStream helpers | **Serves:** R5 and R4 (the mode's value, measured), R2 (an element whose pin must survive), and every reader who needs bga to answer without it | **Topic:** capture | **Area:** tools-native_trace | **Shape:** mechanical

## Motivation

Until Direction 20, `bga` measured and never acted. The jobserver acts:
it injects a token pool into sandboxes, and the cost of acting is
already on the record — round 126's minimal-sandbox breakage and
`UX-878`'s GCC LTO ICE. That is a different risk class from a reader,
and it belongs behind a boundary rather than distributed through the
capture path, for two reasons that are not the same:

- **Extractability.** The owner intends the jobserver to be able to
  leave for a helpers project. What decides whether it can is whether
  its surface is a boundary or a set of call sites.
- **Non-dependence.** A tool whose answers require its own intervention
  to be switched on has stopped being an instrument. A capture with the
  mode off must answer everything a capture with it on answers, minus
  the ledger the mode itself writes.

## Required Fix

Name and document the boundary, then hold it with a guard: which module
owns the pool, the wrappers and the policy table; what bga calls to
start and stop it; and what crosses back — the token ledger, and nothing
else. Publish the mode's own facts as contract data (`UX-847`'s ledger
in Plane 2) rather than as something only the subtool's logs hold, so
that a future move takes the code and leaves the answers.

State in the same document what the boundary is *not*: it is not a
plugin system, and bga does not gain a second one for anything else.

## Decomposition

surfaces: the tracer's jobserver modules under `tools/`, the capture option `UX-851` added, `docs/design/architecture.md`'s Plane 2 map, and the Plane 2 contract's `jobserver` block
guards: a capture with the mode off carries every key a capture with it on carries but the ledger; an import guard that names which modules may reach the pool
gap: whether the boundary is a process boundary (the subtool is spawned) or an import boundary (a package with a declared surface) — the first extracts more cleanly, the second keeps the measurement cheap
track: session's own — it is an architecture decision with a measured consequence
gate: after `UX-895`, whose overhead number tells the boundary what it may cost

## Out of Scope

Moving the code to another repository. Changing the mode's default,
which stays off until a compile-bound capture's wall clock says
otherwise (Direction 20's bar). Any new intervention.

## Acceptance Test

The architecture document names the boundary and what crosses it; a
guard fails when a module outside the named set imports the pool; a
capture with `--jobserver off` and one with `auto` produce key sets
differing only by the jobserver block. Mutations: import the pool from
an unlisted module (red), drop one key from the off-capture (the set
comparison names it).

## Decision

The `architect`, round 141, at `ad27b616`.

```text
Route:     import boundary: new package tools/jobserver/ takes the pool (open/close_jobserver,
           PoolController, Broker, create_jobserver_proxies, the plan/meminfo readers,
           tracer:1244-2505) and the ledger (read/summarize_jobserver_*, tokens_by_element,
           read_jobserver_decisions, jobserver_auth_style), plus a new report_block() that
           returns the tracer:9272-9374 `jobserver*` keys (cache_key_set and project_max_jobs stay), so one report.update() is all
           that crosses back; __init__.__all__ is the declared surface, and
           tools/bst_native_build_tracer.py is its only caller; the tracer imports the
           surface names by name, so `monkeypatch.setattr(tracer, ...)` targets keep working.
           The shim's policy half (kind_job_env, _*_POLICIES, tracer:99-106's imports) stays
           in tools/native_trace/bwrap_shim.py, a declared member: write_bwrap_shim copies
           that one file alone (tracer:198-218) and it imports stdlib only (shim:30-40), so
           it cannot import a package. tools/jobserver/ imports stdlib and the shim, never
           the tracer or bga. architecture.md names the set, the surface, what crosses (the
           `jobserver*` Plane 2 keys, UX-847's ledger among them), and "not a plugin system"
Rejected:  process boundary - the FIFO's host fd must live as long as the capture (UX-679)
           and the Broker ticks in-process; a spawn adds a lifecycle and IPC and no
           number argues for it. No measured reason against the import boundary was found
           gate "after UX-895" - deviation: UX-895 needs the owner's 16-core host; the move
           changes no call path, so its overhead number is a follow-up that may reopen
           the process fork, not a precondition
           moving kind_job_env into tools/jobserver/ - breaks the single-file shim copy
Files:     tools/jobserver/__init__.py; tools/jobserver/pool.py; tools/jobserver/ledger.py;
           tools/bst_native_build_tracer.py; tests/unit/test_only_the_tracer_reaches_the_jobserver.py;
           tests/unit/test_a_capture_without_the_jobserver_loses_only_its_ledger.py;
           existing tests/unit/test_*.py whose monkeypatch targets a moved helper's
           internal call (retarget to tools.jobserver.pool, nothing else);
           docs/design/architecture.md ("Real package structure" and Plane 2 map);
           docs/design/areas/tools-native_trace.md; tests/quality_reference.json (--adopt).
           Not docs/design/continuous-build-improvement.md (UX-906 owns section 7a)
Guard:     test_only_the_tracer_reaches_the_jobserver.py (ast over bga/** and tools/**): only
           the tracer imports tools.jobserver; nobody outside the package imports a
           submodule or a name not in __all__; bga/** imports nothing from it; the package
           imports neither the tracer nor bga; the shim names the tracer may import are a
           declared list. test_a_capture_without_the_jobserver_loses_only_its_ledger.py:
           report_block() on a fixture ledger returns only `jobserver*` keys, and
           `bga analyze --format json` over tests/fixtures/macro_micro/run with and without
           those keys in plane2.json differs only by `jobserver*` keys, compared recursively
Mutation:  `from tools.jobserver.pool import PoolController` in tools/bga_timeline.py (red,
           names the module); `import tools.jobserver` in bga/correlate.py (red);
           `from ..bst_native_build_tracer import TraceError` in tools/jobserver/pool.py
           (red); report_block() emits `pool_peak` (red, names it); gate a non-jobserver
           key in bga/report/json.py on `native_report.get("jobserver_ledger")` (the set
           comparison names the key)
Class:     product - non-dependence and extractability for R5/R4; no process surface
Split:     one track; parallel with UX-906 (disjoint files; neither edits bwrap_shim.py)
Question:  none - the owner took the fork (import boundary, off by default, never required)
```

## Outcome

Gap measured: 1,834 lines of the pool/ledger/Broker/PoolController
surface moved out of `tools/bst_native_build_tracer.py` (9,473 lines)
into `tools/jobserver/__init__.py` (75), `pool.py` (781) and `ledger.py`
(356) - the tracer fell to 8,465 lines. Two reach-backs the Decision's
text did not name were resolved by binding, not importing: `PoolController`'s
`/proc/stat` sampler and `Broker`'s live raw-log pid reader are tracer
functions with no jobserver-only use (shared with `HostSampler` and
report assembly respectively), so `tools/jobserver/__init__.py` exposes
`bind_cpu_sampler`/`bind_pid_to_element_reader` and the tracer calls
them once, right after each reader's own definition - the package still
imports nothing from the tracer. `report_block()` took one dict
argument, not fifteen kwargs (`ruff PLR0913`, caught by `make lint`
before commit, not after).

Close measured: `python3 -m pytest` on the 27 existing jobserver-named
test files - 421 passed, 7 skipped, zero changed except two monkeypatch
targets already covered by the guard's own scope. `make lint`: clean
(576 findings match the baseline, zero new). `python3 tools/dev_sizes.py
--check`: one deliberate growth (`tools/bst_native_build_tracer.py`
`duplicate_blocks` 1 -> 10, from splitting near-identical jsonl-reading
loops across two files), adopted with `--adopt --force` in its own
`sizes:` commit. `make test-touching`: 3,229 of 9,711 tests, 1 failure -
`test_every_module_is_on_the_map` naming `tools/jobserver_arms.py`
(`UX-905`, already broken on the merge base before this track started,
not a file this Decomposition touches).

Mutation table:

| mutation | reddened | count |
|---|---|---|
| `from tools.jobserver.pool import PoolController` in `tools/bga_timeline.py` | the import sweep | 1 failed |
| `import tools.jobserver` in `bga/correlate.py` | the import sweep | 2 failed |
| `from ..bst_native_build_tracer import TraceError` in `tools/jobserver/pool.py` | the package's reach-back check (a real circular import, caught statically) | 4 failed |
| `report_block()` emits `pool_peak` | the key-set check | 1 failed |
| gate `data['mutation_probe']` in `bga/report/json.py` on `jobserver_ledger` | the off/auto key comparison | 1 failed |
| drop `bind_cpu_sampler(read_cpu_sample)` from the tracer | `test_the_tracer_binds_both_readers` | 1 failed |

All five reverted from copies made before editing; each guard returned
green with `__pycache__` cleared between runs (`UX-508`/`UX-625`).
