# UX-1005: bga recommends a builder count and a pool size from a capture, and the critical path gets the next token

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1004, UX-1003 | **Found by:** Ruslan on the jobserver batch thread (2026-09-24): whether to oversubscribe BuildStream's builders or native `max-jobs` depends on graph shape and the machine, and there is no rule for it | **Serves:** R5, R4 (a single-machine deployment sized from its own readings) | **Topic:** analysis | **Area:** unassigned | **Shape:** judgement

## Motivation

Builders are breadth across the graph, `max-jobs` depth inside a recipe,
and both draw on one machine. A static split fits one phase of the build
and wastes the other: `11-serial-giant`'s off arm idles two of four
cores behind `giant.bst` at `max-jobs: 2`. Under the pool the split
reduces to two numbers - builders, and tokens - with peak concurrency
about active builders plus tokens, since each running recipe keeps its
own implicit slot through configure and install. Nothing reads either
number off a capture, and tokens go first come, first served.

## Decomposition

surfaces: a `bga analyze` section beside the critical path; the pool's grant order in `tools/jobserver/pool.py`
guards: a fixture graph with a wide phase and a narrow one reads a builder count from its ready-set width and a pool size from the host's knee; a starved pool grants the critical-path element first
gap: whether ready-set width over time is recoverable from Plane 1 alone; and where admission lives - the shim taking a real token before exec'ing bwrap (builders set wide, BuildStream unmodified, the wait reported apart from the build) or a change proposed upstream to BuildStream's scheduler (Ruslan, 2026-09-24: not without modifying BuildStream)
track: shaped by the `architect` (Decision below); three bounded tracks
gate: after `UX-1004`'s knee is on record

## Required Fix

Recommend builders from the capture's ready-set width and tokens from
the knee, memory per job and the pool's PSI readings; put the margin in
tokens, which can be withheld, not builders, which cannot.

## Decision

Route: admission in the shim. It acquires a token before starting bwrap and releases it after `waitpid`. `Broker` ranks the waiting shims by slack, and bga subtracts the wait from the element's span. The fork-and-wait path already exists for proxy sandboxes (`bwrap_shim.py:1335-1354`); `Broker` already grants tokens to running elements least-slack first (`pool.py:658-698`, guarded by `test_the_broker_grants_by_slack.py`).

Rejected:

- An upstream scheduler change: it is not ours to land and does not reach a stock BuildStream.
- A raw read on the global FIFO for priority: the kernel wakes waiting readers in no priority order.

Deadlock: none. An admitted sandbox needs no second token, because the admission token is its implicit slot. A pool withdrawn to zero stalls admissions until `_handle_underload` refills it (`pool.py:347-352`).

Gate for track B, read 2026-09-24:

- BuildStream puts no deadline on the sandbox. `_sandboxbuildboxrun.py:233-250` polls `wait(timeout=1)` only to check for shutdown; buildbox-run's own Rust source is unread.
- An element's commands reach bwrap as one batch, since `_SandboxREAPIBatch` joins them into one script (`_sandboxreapi.py:242-301`). The fdsdk auto arm reads 25 bwrap invocations against 23 `Running commands` starts.

Tracks:

- A, bounded, product (`bga/correlate.py`, `bga/cli.py`): builders from the replay's ready width, the pool from UX-1004's recorded knee. Mutations: builders from `max_jobs`; pool from `host_cpu_count`.
- B, bounded, product (`bwrap_shim.py`, `jobserver/ledger.py`, `normalize/timestamps.py`): with a pool of 1, the second shim waits for the first; the wait row leaves the BUILD span. Mutations: drop the release; keep the wait in the span.
- C, bounded, product, after B (`pool.py`): the waiting least-slack shim is admitted before an earlier arrival; element `None` waits on the global FIFO. Mutation: sort by arrival.

## Out of Scope

Remote execution with separate executor hosts.

## Acceptance Test

`bga analyze` on `11-serial-giant` and on the fdsdk pair prints a
builder count and a pool size, each with the reading it came from.

## Outcome (track A only - B and C remain)

Gap measured: `bga analyze` printed no builder count or pool size at
all - `grep -c "Builders (ready-set"` against any prior report is 0.
`compute_capacity_recommendation` (`UX-116`) answers a different
question (the CPU/memory-bound `--builders`, from the sweep's own
scheduling knee), not the ready-set width or `UX-1004`'s host knee.

Close, on a synthetic `13-mixed-graph`-shaped fixture (giant.bst 8-wide,
24 single-core siblings, `tests/fixtures/wide_and_narrow/run`,
host_cpu_count 16):

```text
$ bga analyze tests/fixtures/wide_and_narrow/run
Critical Path Length: 1 elements
  Path: giant.bst

Builders (ready-set width): 25, from the replay's ready-set width - right only with admission in place (UX-1005 tracks B/C)
  Safe cap without admission: 8 builder(s) - the host's cores leave free once the critical path's own max-jobs=8 is subtracted
Pool size: 16, from host_cpu_count (16) - no calibrated knee supplied via $BGA_CALIBRATED_CORES, so this is uncalibrated

$ BGA_CALIBRATED_CORES=2 bga analyze tests/fixtures/wide_and_narrow/run
Pool size: 2, from UX-1004's calibrated knee (2 effective core(s))
```

Builders: `compute_ready_set_width` replays with `PROCESS` capacity set
to the task count (nothing queues), then counts peak concurrency - a
delta-per-instant sum, `finish_us` exclusive. Pool: `UX-1004`'s knee has
no per-capture field (a schema decision this bounded track does not
take - see Deviation), so it travels as `$BGA_CALIBRATED_CORES`,
falling back to `host_cpu_count` labelled uncalibrated.

Predictor check, `examples/11-serial-giant`: no fixture capture exists
for it (`grep -rl giant tests/fixtures` returns none; `graviton_arms.sh`
runs real hardware, per `test_the_real_core_reading_cites_a_reproducible_run.py`'s
own docstring), so the given reading (max-jobs 3 on 16 cores, 261s vs
auto 112s, -57%) could not be re-run here. Structurally it is orthogonal
to this track: `11-serial-giant`'s critical path is one element deep
(`giant.bst` alone, three small leaves waiting on it), so this
predictor's ready-set width there is small and the reading is about
native `max-jobs` (a UX-677 question), not builders/pool sizing.

| mutation | reddened | count |
|---|---|---|
| builders from `max_jobs` | `TestReadySetWidth` (3 of 3 cases) | 3 |
| pool from `host_cpu_count` | `TestPoolFromTheCalibratedKnee` (3 of 3 cases) | 3 |
