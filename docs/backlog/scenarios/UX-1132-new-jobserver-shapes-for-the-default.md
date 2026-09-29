# UX-1132: three new example shapes and their arm legs test the "safe cap plus auto" default

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1010 | **Found by:** round 152's architect, splitting UX-1014 into what a session can build and what needs the owner's hosts | **Serves:** R4, R5 | **Topic:** capture | **Area:** tools | **Shape:** mechanical | **Reading:** runner:bst-examples

**Guard:** `tests/unit/test_the_new_jobserver_shapes_hold_their_property.py`

## Motivation

UX-1014 asks for readings on shapes the default has not met. The
shapes themselves, their `graviton_arms.sh` legs and a probe that keeps
its captures are buildable here; the Graviton spend, the x86 16-core
host and a real project stay with UX-1014.

## Decomposition

Input classes: two independent giants; a chain of wide elements; a memory-bound giant under PSI withdraw.
Journey: `bga capture run --jobserver off|auto` then `bga analyze`, on `bst-examples` and the Graviton arms.

## Required Fix

`examples/14-two-giants` (two independent giants, two critical chains),
`examples/15-wide-chain` (a chain of wide elements), and
`examples/16-memory-bound-giant` (a giant whose units are memory-heavy,
so the pool's PSI withdraw fires), built on the same staged toolchain as
`05`-`13`; a `graviton_arms.sh` leg per shape; `codspeed-probe.yml`
gains those legs and an `upload-artifact` of the arms' captures. Each
shape builds once on `bst-examples` and its designed property is
checked there.

## Decision

Route: three projects on 11/13's sysroot and `10`'s generator (clone lists in `stage_cpp_toolchain.sh`), one committed checker `examples/check_shape_property.py` (`two-giants`/`wide-chain`/`memory-giant`, `UX-354`: no JSON keys in a `run:`), one `bst-examples` step per shape at a small line count plus an `if: always()` notice step, and `graviton_arms.sh` legs `twogiants`/`widechain`/`memgiant` running `off` against `autocap` (`--jobserver auto --builders` cores less `min(cpus, 8)`); `memgiant` picks its `mem_lines` rung from `MemTotal`/`nproc` so a core-wide pool oversubscribes RAM 1.5x. Rejected: a second generator for memory-heavy units (cc1's RSS already scales with `LINES`: 9800 -> 83 MB, 40000 -> 284 MB, 80000 -> 549 MB at -O0 on the dev host); asserting PSI withdraws on the 4-core runner (16 GB never pressures - printed, not asserted); `case $MODE in` for the new PROJ selection (the `UX-905` guard reads the first such block as the dispatch). Files: `examples/14-two-giants/`, `examples/15-wide-chain/`, `examples/16-memory-bound-giant/`, `examples/check_shape_property.py`, `examples/stage_cpp_toolchain.sh`, `examples/README.md`, `examples/11-serial-giant/graviton_arms.sh`, `.github/workflows/ci.yml`, `.github/workflows/codspeed-probe.yml`, `.gitignore` (13-16's staged `files/`). Guard: `tests/unit/test_the_new_jobserver_shapes_hold_their_property.py`. Mutation: `notparallel: True` on `giant-b.bst`; a capture reading giant-b at width 1. Class: capture.

## Out of Scope

Running the Graviton arms (UX-1014, at the round's end, by the owner's
word of 2026-09-29), the x86 host, a real project.

## Acceptance Test

`bst-examples` builds each new shape and prints its property check
(two giants building concurrently, each chain element wider than 1,
the memory giant's peak RSS per job). Mutation: make the second giant
`notparallel`; the two-giants width check fails.

## Outcome

**Gap measured.** Before: `examples/` stopped at `13-mixed-graph`; `graviton_arms.sh`'s dispatch handled `pairs|cap3|noharm|mixed|mixed8|overhead|diag`; `codspeed-probe.yml` ran `leg: [mixed8]` and uploaded nothing; `bst-examples` built no shape with two giants, a wide chain or a memory-bound giant.

**Close measured.** Three projects, three `bst-examples` steps and one `if: always()` notice step, three legs in the probe's matrix plus `actions/upload-artifact` of `$RUNNER_TEMP/arms/` per leg. `sh -n graviton_arms.sh` clean (dash). The checker on a synthetic capture (no `bst` in this sandbox - the real builds are CI's):

```text
$ check_shape_property.py two-giants ... (giant-b width 3) -> rc=0: OK two-giants: giant-a.bst:width=4 giant-b.bst:width=3 overlap=8.5s
$ check_shape_property.py two-giants ... (giant-b width 1) -> rc=1: FAIL two-giants: giant-a.bst:width=4 giant-b.bst:width=1 overlap=8.5s
```

cc1 peak RSS vs `LINES` (`generate.sh` unit, `gcc -c`, `getrusage` children, dev host): 9800 -O0 83 MB; 40000 -O0 284 MB (1.47 s); 80000 -O0 549 MB (3.63 s), -O2 289 MB. Hence CI's `mem_lines 80000` and floor 200 MB.

| Mutation | Reddened | Count |
|---|---|---|
| `notparallel: True` on `giant-b.bst` (Acceptance) | both giants parallel | 1 failed, 22 passed |
| two-giants ignores width | notparallel capture fails | 1 failed, 22 passed |
| two-giants ignores overlap | serial giants fail | 1 failed, 22 passed |
| wide-chain accepts width 1 | narrow link | 1 failed, 22 passed |
| memory floor dropped | memory floor | 1 failed, 22 passed |
| 14 dropped from the toolchain clone list | staging | 1 failed, 22 passed |
| `twogiants` off the probe matrix | probe | 1 failed, 22 passed |
| probe upload without `if: always()` | probe | 1 failed, 22 passed |
| notice step without `if: always()` | bst-examples x3 | 3 failed, 20 passed |
| `twogiants` dispatch arm removed | arms leg | 1 failed, 22 passed |
| `memgiant` points at 11's project | arms leg | 1 failed, 22 passed |
| `## 15-wide-chain` heading renamed | index | 1 failed, 22 passed |
| revert | - | 23 passed |

