# UX-679: a jobserver every sandbox joins — the prototype bga can run

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-105 (the bwrap shim), UX-675 and UX-676 (the instruments that judge it) | **Serves:** R4 and R5 — dynamic sharing instead of static tuning | **Topic:** capture | **Shape:** judgement

## Motivation

Every native build system BuildStream drives speaks the GNU jobserver
protocol (`make`, `ninja`, `cmake`'s generators, `cargo -j`), and
BuildStream runs no jobserver — so five sandboxes each believing they
own eight cores is the whole utilization problem. The tool already
injects into every sandbox (the `bwrap` shim mounts the hook; the
hook is `LD_PRELOAD`ed in every process) and already measures what
happens inside (Plane 2). A jobserver FIFO passed through the same
shim, with `MAKEFLAGS=--jobserver-auth` and the ninja/cmake
equivalents set in the sandbox environment, is a prototype no other
tool is placed to build — and its evaluation is `UX-676`'s envelope
before and after.

## Required Fix

A design spike, not a feature: `bga capture --jobserver N` runs a
jobserver outside the sandboxes, binds the FIFO in through the shim,
sets the environment; the snapshot records it as a capture option;
`UX-676`'s envelope on the same project with and without it is the
result, pasted in the Outcome. Whether it becomes a supported mode is
decided on that number.

## Out of Scope

- BuildStream's own remote execution — a different mechanism
  (`UX-680`).
- Build systems without jobserver support — they keep their static
  `max-jobs` (`UX-677`).

## Acceptance Test

Example 06 captured both ways: the envelope's under-utilized share
and the wall clock, side by side, on one machine; the shim guard
holds that the FIFO is bound only when the flag is given.

## Outcome

**Mechanism landed.** `tools/bst_native_build_tracer.py run --jobserver N`
(default off): opens a FIFO in the capture's scratch dir, writes `N-1`
`+` tokens, exports `BST_TRACE_JOBSERVER`, records `jobserver: N`|`null`
in the report, closes/removes the FIFO after the build.
`tools/native_trace/bwrap_shim.py`'s `open_jobserver_fd` opens it
read-write, `os.set_inheritable`s it; `build_shim_argv` injects
`--setenv MAKEFLAGS --jobserver-auth=<fd>,<fd>` only when given a
jobserver_fd. Three facts confirmed on this machine before relying on
them: `bwrap` passes an inherited fd through with no bind; GNU Make 4.3
rejects `--jobserver-auth=fifo:...` (fd style only); four `sleep 1`
targets under a 4-token jobserver ran in 1.01s joined, vs. the
`-j2 forced in submake: resetting jobserver mode` warning when `-j` is
on the command line.

**The two captures**, examples/06, cold `bst` cache each
(`cachedir` + `quota: 3G`/`reserved-disk-space: 500M`):

```text
python3 -m tools.bst_native_build_tracer run --host-samples host-a.jsonl --run-dir run-a --trace-spine on proj-a native-a.json -- bst --config bst-a.conf build all.bst
python3 -m tools.bst_native_build_tracer run --host-samples host-b.jsonl --run-dir run-b --trace-spine on --jobserver 4 proj-b native-b.json -- bst --config bst-b.conf build all.bst
```

`bga analyze RUN --plane2 NATIVE.json --format json`, `utilization_envelope`:

| | a (no jobserver) | b (`--jobserver 4`) |
|---|---|---|
| underutilized_share | 0.857 | **0.214** |
| overcommitted_share | 0.0 | 0.0 |
| busy_cores_p50 | 1.985 | 3.97 |
| Plane 1 wall (`total_duration_us`) | 30.249s | 30.462s |
| Plane 2 max observed concurrency | 24 | 24 |
| Plane 2 wall span | 28.625s | 27.205s |
| core.bst native span (peak concurrency) | 10.29s (peak 2) | 4.98s (peak 4) |

**Join check.** No `resetting jobserver mode` in run-b or native-b.json
(`grep -rl`, exit 1 = no match). `bst show --format '%{env}' core.bst`
under proj-b: `JOBS:` empty (proj-a: `-j4`/`-j1`); per-element native
parallelism peaked at 3–4 for every `lib-*.bst` with no `-j` on the
command line — joined, not serial.

**Finding on `-j` on the command line.** A bare `environment: JOBS: ''`
at project.conf's top level composed *under* buildstream_plugins'
cmake.yaml per-kind default and did not take (`JOBS: -j%{max-jobs}`
still won); `elements: cmake: environment: JOBS: ''` composes over it
and did. A supported mode needs this per-kind override, not a
top-level one — a real finding about how BuildStream's own composition
order works, not a defect in the mechanism.

**Result.** Cores went from 85.7% underutilized to 21.4% — core.bst
(pinned `notparallel`, previously the only-serial element) roughly
doubled its achieved concurrency. Total wall barely moved (30.2s vs.
30.5s): this project's dominant cost is the *macro* six-deep dependency
chain (`UX-679`'s Motivation cites it), which a jobserver cannot
shorten — it only raises utilization inside each element's own window.

**Mutation table** (`tests/unit/test_bwrap_shim.py`):

| mutation | reddened | revert |
|---|---|---|
| inject `MAKEFLAGS` unconditionally | `test_..._omits_makeflags_when_no_jobserver_fd` (2 failed) | green, 16/16 |
| never inject `MAKEFLAGS` | `test_..._injects_one_makeflags_setenv...` (1 failed) | green, 16/16 |

**Deviation.** `tests/unit/test_help_is_short.py`'s `CAP` raised 45→47
(a 15th flag on `capture run`: one option line plus a usage-line wrap
`[--jobserver N]` forces, at zero headroom already) — not a declared
surface, done because the flag cannot land otherwise. `docs/guides/cli.md`
gained the `BST_TRACE_JOBSERVER` inventory row and a capture-flags
bullet, both required by existing guards. This is a spike: the decision
of whether it becomes a supported mode is the orchestrator's, on the
numbers above.
