# 10-jobserver

The compile-bound example Direction 20's `--jobserver auto` needs
(`UX-848`). Round 112 declined the mode on `06-macro-micro-optimization`
because that project's wall never moved (30.25s -> 30.46s): its
critical path is a six-deep declared chain, and no jobserver shortens a
chain. This project is four **independent** elements - two `autotools`,
two `cmake` - each generating 64 arithmetic-heavy C files at build time
(`files/gen/*/generate.sh`, run inside the sandbox - nothing generated
is committed) and linking one binary, behind one `all.bst`. `project.conf`
leaves `max-jobs` at the default, same as `06`.

Same staged sysroot as `05`/`06` - `../stage_cpp_toolchain.sh`
hardlink-clones it here too, nothing staged twice.

```
../stage_cpp_toolchain.sh
bst build all.bst
```
(run from inside `10-jobserver/`)

## Real captures, this box, 2026-09-14

4-core host, cold artifact cache both times (`rm -rf ~/.cache/buildstream
~/.local/share/buildstream` before each), `bga 0.4.1`:

```
bga capture run --run-dir run-off  --jobserver off  examples/10-jobserver plane2-off.json  -- bst build all.bst
bga capture run --run-dir run-auto --jobserver auto examples/10-jobserver plane2-auto.json -- bst build all.bst
bga compare run-off run-auto
```

```text
Verdict: REGRESSED  (total duration +1.22s, +5.6%, 21.62s -> 22.83s)
Certified Floors:
  Total Duration           21.62s ->     22.83s   (+1.22s)
  Dispatch Occupancy        90.8% ->      89.8%   (-1.0pp)
Which Elements Changed:
  mod-c.bst: +2.90s (16.00s -> 18.90s)   mod-d.bst: +2.90s (16.00s -> 18.90s)
  mod-a.bst: +2.00s (13.05s -> 15.05s)   mod-b.bst: +2.00s (13.05s -> 15.05s)
```

**All four elements got slower, not faster.** Both runs build `all.bst`
with BuildStream's own default `--builders`/`--max-jobs` (4, this
host's core count) - so at `--jobserver off` all four elements are
already running concurrently, each internally at `-j4`: the box is
already 16-way-oversubscribed on 4 cores before the mode adds anything,
not idle. `--jobserver auto`'s own pool controller (`UX-845`) is a real
extra process ticking `cpu_busy_cores` every 250ms on top of that
oversubscription, which this capture's own regression is consistent
with costing more than it redistributes.

**Stage-1 numbers.** `UX-843` (the per-kind environment table so
`cmake` elements join via `MAKEFLAGS` rather than their own `-j%{max-
jobs}`) and `UX-846` (token-holding wrappers) are not in this branch's
base - confirmed live above: `mod-c.bst`/`mod-d.bst` (`cmake`) grew by
as much as `mod-a.bst`/`mod-b.bst` (`autotools`, the pair that does join
the jobserver today), which is what "cmake does not join yet" predicts.
The session re-runs this capture after those two land, and Direction
20's `Status` for the mode is decided on that later row, not this one.

**Stage-3 numbers, this box, 2026-09-14 (`UX-849`, `UX-846`/`UX-843`
both in this branch's base now).** This box's `make --version` is
4.3 - `--jobserver-auth` reads `fd` here (UX-841), and `UX-849`'s
proxies now follow that same style rather than always `fifo:`:

```
bga capture run --run-dir run-C --jobserver auto examples/10-jobserver plane2-C.json -- bst build all.bst
bga analyze run-C --plane2 plane2-C.json -f json -o plan-C.json
bga capture run --run-dir run-D --jobserver auto --plan plan-C.json examples/10-jobserver plane2-D.json -- bst build all.bst
```

`--jobserver auto` (no `--plan`): **32.23s**. `--jobserver auto --plan
plan-C.json`: **41.41s** - slower, not faster: the broker (`grants: 3,
drains: 3, elements_in_plan: 6`) redistributes an already 16-way-
oversubscribed 4-core box (Motivation above), and a 100ms broker
thread on top of `PoolController`'s own 250ms one is a second real
cost with nothing idle for either to hand out.
