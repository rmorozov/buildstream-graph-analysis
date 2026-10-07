# UX-1284: a link step that peaks above every compile before it is reserved at the compile's size

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-1134 | **Found by:** Ruslan's promotion question on round 166 (2026-10-02): what stands between `auto` and arbitrary configurations | **Serves:** R4, R5 | **Topic:** capture | **Area:** tools | **Shape:** mechanical | **Reading:** owner:CodSpeed Graviton

**Guard:** test_a_late_peak_is_held_once_live.py, test_the_new_jobserver_shapes_hold_their_property.py

## Motivation

UX-1134's gate learns an element's per-job size from its finished
jobs and holds while a live job is bigger than every finished one.
A link or LTO step at the end of an element can peak at several
times its compiles (lto1, a large static link), and it starts after
the gate has already settled on the compile's size with the pool
widened to fit it. No example has that shape: `16-memory-bound-giant`
is cc1-bound all the way, 2.8 GB per job. Inferred, not measured.

## Decomposition

Input classes: an element whose final link peaks at k x its compile
(k = 2, 4); an `-flto` element under `lto1` with jobserver width.
Journey: a new `examples/17-*` shape, a `graviton_arms.sh` leg, the
UX-1014 table.

## Decision

```text
Route:     build the example, the leg and a scripted guard this round; leave the gate alone until Graviton reads it - the Required Fix asks for a gate change only "if auto loses there", and the gate has no signal that predicts an unseen peak.
Rejected:  gate reserve now - raising MEMORY_RESERVE_JOBS taxes every build including memgiant's measured shape; the link's arrival is too late (tokens out, revoking is UX-1283's Out of Scope); a --plan peak misses no-plan; and it writes files 1282/1283 own.
Rejected:  example only, no guard - the `rss unsettled` hold (memory.py:126-128) is the one thing that stops more tokens once the link starts, and nothing claims it for a late peak.
Files:     examples/17-late-peak-giant/{project.conf,elements/{toolchain,giant,all}.bst} (last step a link peaking at k x a compile, k a project option 2|4); examples/stage_cpp_toolchain.sh (17 in the lists ~:286/:305); examples/check_shape_property.py (`late-peak PLANE2 E K`: last step maxrss >= K x largest cc1 maxrss, from hook END lines); examples/11-serial-giant/graviton_arms.sh (`latepeak` leg, off vs autocap, k=4); .github/workflows/codspeed-probe.yml (leg in matrix); tests/unit/test_the_new_jobserver_shapes_hold_their_property.py (SHAPES entry for 17 + pass/fail cases); tests/unit/test_a_late_peak_is_held_once_live.py (new).
Guard:     test_a_late_peak_is_held_once_live.py - finished compile END lines at c, one live link descendant at 4c (scripted /proc root + meminfo, real FIFO, as test_the_pool_withholds_for_measured_rss_with_no_plan.py): PoolController.tick withholds its next `+` with an `rss unsettled` ledger row. Shapes file: a link at 1x fails late-peak; every surface names 17/latepeak.
Mutation:  delete the unsettled loop memory.py:126-128 → late-peak guard red; late_peak returns ok for any K → failing case red; drop latepeak from the matrix → surfaces test red.
Class:     product
Split:     one track, parallel with 1282/1283; merged after them.
Question:  none - the Graviton run is a permission; Outcome records "gate unchanged, pending reading".
```

## Required Fix

An example whose last step peaks above its compiles, its Graviton
reading under `off` and `auto`, and, if `auto` loses there, a gate
that keeps the reserve for the step it has not seen yet.

## Out of Scope

Choosing the linker; `-flto` partitioning policy.

## Acceptance Test

The new leg's `off` and `auto` walls and peak memory, run id pasted,
with `auto` completing.

## Outcome

Gate unchanged, pending the Graviton `latepeak` reading (a permission,
not run here). No `bst`, `buildbox-casd`/`-run`, `bwrap` or staged
toolchain in this container, so 17 was not built under `bst`; its
`giant.bst` configure commands ran on the host gcc 13.3 under the real
`hook.c` (`make -j4`, `BST_TRACE_ELEMENT=giant.bst`).

**Gap measured.** No shape out-peaked its compiles late: 16 units of
20000 lines, plain link (16's shape) - `cc1 151 MB`, `ld 19 MB` (0.13x).
Nothing claimed the `rss unsettled` hold for a late step; the shapes
test had no 17 (base file: `23 passed`, no `late-peak` check).

**Close measured.** 17 off-`bst`, hook END lines:

```text
$ check_shape_property.py late-peak r2/trace.log giant.bst 2    # unit_lines 20000, late_k 2
OK late-peak: giant.bst:cc1_peak=152MB late_peak=451MB(lto1) ratio=2.97 k=2
$ check_shape_property.py late-peak r4/trace.log giant.bst 4    # unit_lines 20000, late_k 4
OK late-peak: giant.bst:cc1_peak=154MB late_peak=682MB(lto1) ratio=4.43 k=4
```

LTO calibration (standalone, partition=one, 20000-line plain cc1 150 MB):
lto1 over 4/10/20 units of 20000 lines 235/393/416 MB, of 40000 lines
4/8/12 units 451/503/496 MB - lto1 saturates with units, grows with
lines, so `late_k` scales lines. `-flto` cc1 is 48/82/150 MB at
20000/40000/80000 lines. Every ratio was measured at `unit_lines 20000`
on host gcc 13.3 only; nix gcc 14 on aarch64 is unmeasured. The
`latepeak` leg pins that point (`--option unit_lines 20000 --option
late_k 4`).

```text
$ pytest tests/unit/test_the_new_jobserver_shapes_hold_their_property.py tests/unit/test_a_late_peak_is_held_once_live.py
33 passed in 1.47s
```

| mutation | reddened | run printed |
|---|---|---|
| memory.py:126-128 (the unsettled loop) deleted | `test_a_link_at_four_compiles_is_held_unsettled` | 1 failed, 1 passed |
| check `ok = True` | `test_a_link_no_bigger_than_a_compile_fails_it` | 1 failed, 29 passed |
| check `late = rows` (a peak before the last cc1 counts) | both late-peak cases | 2 failed, 28 passed |
| `latepeak` dropped from the probe matrix | `test_the_probe_runs_every_leg_and_keeps_the_captures` | 1 failed, 29 passed |
| leg OPTS without `--option unit_lines 20000` | `test_the_latepeak_leg_runs_the_measured_point` | 1 failed, 30 passed |
| each reverted from its copy | - | 33 passed |
