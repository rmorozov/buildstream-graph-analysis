# UX-1005: bga recommends a builder count and a pool size from a capture, and the critical path gets the next token

**Priority:** High | **Status:** 🟡 In Progress | **Depends on:** UX-1004, UX-1003 | **Found by:** Ruslan on the jobserver batch thread (2026-09-24): whether to oversubscribe BuildStream's builders or native `max-jobs` depends on graph shape and the machine, and there is no rule for it | **Serves:** R5, R4 (a single-machine deployment sized from its own readings) | **Topic:** analysis | **Area:** unassigned | **Shape:** judgement

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

## Outcome

Tracks A, B and C landed.

Gap: `bga analyze` printed no builder count or pool size
(`grep -c "Builders (ready-set"` is 0), no token gated `bwrap`'s start
(`grep -n ADMISSION_POOL tools/native_trace/bwrap_shim.py` matched
nothing), nothing created the admission pool, and `subtract_admission_
wait` was not wired into `normalize_trace`. Graviton, `13-mixed-graph`,
16 cores: 4 -> 32 builders took the wall 143s -> 208s at equal host CPU
(1160s, 1180s), the giant's `Running commands` to 198s.

Close, track A: as before (`tests/fixtures/wide_and_narrow/run`).
Close, track B: as before (9 tests, `test_admission_*`).

Close, track C:

```text
$ python3 -m pytest tests/unit/test_the_admission_broker_ranks_by_slack.py \
    tests/unit/test_admission_falls_back_when_the_broker_is_gone.py \
    tests/unit/test_the_tracer_creates_the_admission_pool.py \
    tests/unit/test_admission_wait_feeds_normalize.py \
    tests/unit/test_cli_resolves_admission_wait_for_normalize.py \
    tests/unit/test_analyze_leaves_admission_wait_out_of_the_build_span.py -q
18 passed in 0.78s
```

`open_admission_pool` creates the pool under `--jobserver`, sized
`min(host cores, this recipe pool's ceiling)`, reported as
`jobserver_admission_pool: {pool_size, wait_total_us, ranked_grants}`.
`AdmissionBroker` (`--plan` only) ranks waiting shims by slack, least
first, ties/`None` by arrival - the shim (`_admitted_via_broker`) asks
its own grant FIFO first, falling back to the raw pool FIFO after a
5s timeout, so an absent broker cannot deadlock a build. `_resolve_
admission_wait`/`analyzed()` (`bga/cli.py`) read the Plane 2 report's
`jobserver_ledger` before `normalize()`, so `subtract_admission_wait`
now runs inside `normalize_trace` on every real `bga analyze`.

| mutation | reddened | count |
|---|---|---|
| A: builders from `max_jobs` | `TestReadySetWidth` | 3 |
| A: pool from `host_cpu_count` | `TestPoolFromTheCalibratedKnee` | 3 |
| B: drop the release | `test_a_pool_of_one_serializes_the_second_shim_behind_the_first` | 1 |
| B: keep the wait in the span | `test_the_wait_leaves_the_build_span`, `..._clamps_rather_than_inverting` | 2 |
| C: rank by arrival, not slack | `test_a_later_arrival_with_less_slack_is_admitted_first` | 1 |
| C: broker-open failure admits | `test_no_fifo_for_the_element_falls_back_immediately` | 1 |
| C: `min(cores, ceiling)` -> `ceiling` | `test_the_admission_status_file_reports_pool_size_and_wait` | 1 |
| C: drop the `normalize()` pre-call | `test_a_recorded_admission_wait_shortens_the_reported_build_span` | 1 |

Not re-measured: `11-serial-giant` (see track A/B); the Graviton reading
above is the session's own, after this track.

### Deviation

- A: UX-1004's knee travels as `$BGA_CALIBRATED_CORES`; a
  `--calibrated-cores` flag grew `bga analyze --help` past its 45-line
  guard. The recommendation prints in `--format text` only; the JSON
  schema and the page are `bga/report/json.py`'s.
- B: one token per sandbox, not `n-1` (unchanged).
- C: the admission pool is seeded to its *full* size, not `n-1` like the
  recipe jobserver - no implicit slot to reserve one of for. `bga/cli.py`
  reads the Plane 2 report twice (once for the admission wait, once in
  `_attach_plane2_capacity`) rather than hoisting the whole attach
  earlier - out of this track's own surface (`pool.py`). The broker-dir
  fallback timeout is a fixed 5s, not configurable.
