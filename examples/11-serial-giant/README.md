# 11-serial-giant

BuildStream caps one element's `max-jobs` at 8 by default; a 40-core
server building an llvm-sized element alone on the critical path builds
it at `-j8` with 32 cores idle. `giant.bst` (256 generated C files - four
times `10-jobserver`'s per-element 64) models that element, alone on the
critical path under three small leaves that wait on it, `max-jobs: 2`
(the server's 8-of-40, scaled to this box's four cores) - `10` cannot
show it, since its four independent elements already saturate four
cores at `off`.

Same staged sysroot as `05`-`10` - `../stage_cpp_toolchain.sh`
hardlink-clones it here too, and hardlink-clones `10-jobserver`'s own
`files/gen/cmake/generate.sh` in as well (reused, not a second copy).

```bash
../stage_cpp_toolchain.sh
bst build all.bst
```

(run from inside `11-serial-giant/`, `XDG_CONFIG_HOME` pointed at
`xdg_config_home/` for `max-jobs: 2` - project.conf's own comment has
the why)

## Real captures, this box, 2026-09-14

4-core host, cold artifact cache both times (fresh `XDG_CACHE_HOME`/
`XDG_DATA_HOME` per run), `bga 0.4.1`. `giant.bst` generates 256 C files
at 9800 lines each (up from an earlier 1800 - see below for why);
standalone `gcc -c` on one such file is 0.47-0.55s on this host:

```bash
XDG_CONFIG_HOME=$PWD/xdg_config_home bga capture run --run-dir run-off  --jobserver off  . plane2-off.json  -- bst build all.bst
XDG_CONFIG_HOME=$PWD/xdg_config_home bga capture run --run-dir run-auto --jobserver auto . plane2-auto.json -- bst build all.bst
bga compare run-off run-auto
```

```text
Verdict: REGRESSED  (total duration +15.98s, +10.9%, 147.16s -> 163.14s)
Which Elements Changed:
  giant.bst: +16.00s (140.25s -> 156.25s)
  leaf-b.bst: -0.60s (3.60s -> 3.00s)   leaf-a.bst: -0.10s (3.60s -> 3.50s)
  leaf-c.bst: -0.10s (3.60s -> 3.50s)
```

**Width measured.** `off`: `peak_work_concurrency 2, requested_jobs 2,
achieved_vs_requested 1.0` - the `-j2` cap held exactly. `auto`:
`peak_work_concurrency 3` (above 2 - the giant did take the pool's
tokens; `requested_jobs`/`achieved_vs_requested` are both `null` under
`auto`, since a joined process never asks for an explicit `-jN`).
`jobserver_pool`: `ceiling 3, capacity 4, moves 0, pool_min 2, pool_max
2` - **the giant's ceiling under `auto` on this 4-core box is 3 jobs,
not 4** (`capacity`, minus one token of headroom `resolve_jobserver_
ceiling` reserves when the wrapped command names no `--builders`). The
ledger's first row is `pool 2, hold, "no sample yet"`, its last `pool 2,
hold, "busy 4.0 within band"` - `moves` stayed 0 because the box read
essentially 4.0 busy cores for the whole build, never idle enough to
grant more than the seeded 2 tokens. `jobserver_decisions`: `giant.bst`
reads `joined`, policy `cmake_meson` - the mechanism is working; the
pool structurally cannot widen this element past 3 on 4 cores (8 of 40
on the server it models).

**Where the wall goes.** `giant.bst`'s own measured CPU (off): `cc1`
121.44s (87% of it), `as` 9.27s, `cmake`'s own helper calls 3.34s, `cc`
0.66s, `ld` 0.27s, configure 0.40s - 135.19s total. The element's own
measured-process span is 89.01s (compile phase; `cpu_per_wall_second
1.5`, i.e. both of `off`'s two slots busy most of that span), but the
element's authoritative wall (Plane 1) is 140.25s - a ~50s gap outside
any measured compiler/assembler/linker process, which `generate.sh`
(8.78s standalone on this host) and `cmake`'s own configure (0.40s CPU)
do not explain by themselves; the remainder is BuildStream's own per-
element staging/sandbox/install/cache steps plus this shared box's own
contention (`/proc/loadavg` read 7-10 on 4 cores through these
captures - not idle). Compile-phase share of the giant's wall: 63.5%
(`off`, 89.01s / 140.25s) and 65.5% (`auto`, 102.40s / 156.26s) - a
5.4x jump in per-file compile CPU (1800 -> 9800 lines) barely moved
this share (was 64.8% at 1800 lines): the ~50s gap grew alongside the
compile phase rather than staying fixed, so it is not simply diluted by
raising `LINES` further on this box. Not tuned past this point.

**Auto regressed, reproducibly.** Two independent back-to-back pairs at
9800 lines both read `REGRESSED +10.9%` on `giant.bst` - `auto` genuinely
ran wider (mean concurrency 2.79 of peak 3, near-saturated) and moved
more real compiler work (102.40s vs 89.01s of work span), but the
element's own wall still grew, 140.25s -> 156.25s. Three compiler
processes plus `PoolController`'s own 250ms polling thread on a 4-core
box already reading ~8 load average leaves less scheduling slack than
`off`'s two, not more - the same shape of finding `10-jobserver`'s own
README already made for a different reason (an already-saturated box,
the mode's own overhead has nothing idle to redistribute into).

**The leaves add contention, not shape.** `leaf-a`/`b`/`c.bst` build
only after `giant.bst` finishes (a build dependency), so they add
nothing to `giant.bst`'s own span - they exist so the mode has a real
second wave of elements requesting tokens once the giant releases them,
rather than the pool sitting idle after one element.

**Expected vs. measured, numbers only.** Width: expected 2 (`off`) -> 3
(`auto`) - pool ceiling 3 = 1 implicit job + 2 FIFO-seeded tokens
(`ceiling - 1`); measured 2 -> 3 (`per_element_parallelism.peak_work_
concurrency`, `plane2-off.json`/`plane2-auto.json`, the two `bga
capture run` commands above). From UX-858, 2026-09-15, the pool's
ceiling is the host's own capacity rather than `cores - builders` - 4
here, not 3 - seeded at `ceiling - 1` = 3, so the giant's expected
width is now 4 against 2; the dated readings above were taken at
ceiling 3, before this change. Measured 2026-09-15 with `--builders 4`
(builders equal to the cores, which opened at ceiling 1 before
UX-858), quiet box, fresh caches: `off` 296.26s, `auto` 256.47s
(IMPROVED -13.4%), the giant 291.30s -> 250.30s, its width 2 -> 4,
its compile span 76.66s -> 39.08s, the pool 0 -> 3 over three adds. Wall: compile share 64% (`off`,
`work_span_s 89.01s` / `giant.bst|BUILD dur_us 140.246s` in
`run-off/trace.json`) gives an Amdahl-style expected `auto` wall of
147.16s x (0.36 + 0.64 x 2/3) = 115.8s if only the compile phase moved
2 -> 3-wide; measured `auto` wall 163.14s (`bga compare run-off
run-auto`, above) - slower than both `off`'s 147.16s and the 115.8s
expectation, not faster.

**Risk in the CI step's own assertion.** This box read `auto` over
`off` twice at `/proc/loadavg` 7-13 (above); the step's hard `auto <
off` check stands on the CI runner's own quiet reading, not this one -
if it reds there too, that is the finding, and the assertion should
drop in favour of the two printed walls, not be tuned to pass.

**Quiet-box pair, measured at the round's close** (same box, `/proc/
loadavg` 1.58 at the start of `off`, 2.83 at the end of `auto`, no
other agents or suite running; fresh `XDG_CACHE_HOME`/`XDG_DATA_HOME`
per run, the two `bga capture run` commands above, then `bga compare
run-off run-auto`):

```text
Verdict: IMPROVED  (total duration -30.47s, -10.6%, 286.53s -> 256.06s)
  giant.bst: -31.05s (281.30s -> 250.25s)
```

`giant.bst`'s `peak_work_concurrency` 2 -> 3, its measured-process span
71.19s -> 47.54s (x 0.668 against the 2/3 the width predicts), `cc1`
CPU 122.6s -> 121.3s - the same work, one job wider. The walls are
twice the loaded pairs' because the sandbox is: plain `bst build
all.bst` with no `bga` in the same environment took 276.3s (`giant.bst`
"Running commands" 4:31), the recipe standalone on this host 76.1s
(`sh generate.sh giant 256 9800` 8.75s, `cmake` 0.28s, `make -j2`
67.06s), and the capture itself 281.30s - the hook's share is ~10s,
BuildStream's own staging under `buildbox-run` the rest. The CI step's
`auto < off` assertion stands on this reading.
