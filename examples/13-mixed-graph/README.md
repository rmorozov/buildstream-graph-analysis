# 13-mixed-graph

The jobserver's second win shape (Ruslan, 2026-09-24, the jobserver batch
thread): a single giant element plus several elements that each consume
only one real core. With 2x BuildStream `--builders` there can be enough
of the narrow elements ready to spawn into the cores the giant does not
use - a win from *breadth* (more elements running at once), not from
`--jobserver auto` widening any one element's own recipe.

`examples/11-serial-giant` cannot show this: its three leaves are a
*build dependency* on the giant, so they are never ready to build
alongside it and never compete with it for a builder slot. Here
`giant.bst` and all 24 `narrow-*.bst` elements depend only on
`toolchain.bst` - all 25 are ready at once, and `bst`'s `--builders` is
what decides how many of them actually run together.

## The giant

`giant.bst` is the same element as `11-serial-giant`'s own `giant.bst` -
256 C files generated inside the sandbox
(`../10-jobserver`'s `files/gen/cmake/generate.sh`, hardlink-cloned in,
not a second copy), `giant_lines` lines each (default `9800`, same
enum option as `11`). Unlike `11`, this project sets no `max-jobs` cap -
the win here is about builder count, not native recipe width, so the
giant runs at BuildStream's own default `max-jobs`.

## The 24 narrow elements

Each `narrow-NN.bst` compiles 24 generated C files at 1800 lines each.
`11-serial-giant`'s own README measured this host's single-core `cc1`
rate at roughly 1s per 1800-line unit (a diagnostic run at
`giant_lines=1800`, 256 units in ~160s at `-j1`) - 24 units is a design
target of roughly 20-30s of real, single-core compile per narrow
element, not a pasted Graviton reading (that reading is the Acceptance
Test the session runs).

**How narrowness is enforced.** Each `narrow-NN.bst` sets
`variables: notparallel: True` - BuildStream's real per-element
parallelism control, already used by
`examples/06-macro-micro-optimization`'s `core.bst` to force one
element's own `make` to `-j1`. An explicit `-j1` on the command line
takes GNU make out of jobserver mode entirely for that invocation, so
neither `--builders` nor `--jobserver auto` can widen it - the same
reason a real autotools `./configure`, a `python setup.py build` step,
or a hand-written serial `make` recipe stays on one core no matter how
much idle capacity the host has. This is a real mechanism, not a
`sleep N` proxy: the compiler genuinely runs one `cc1` at a time.

## Why the shape needs both pieces

24 independent single-core elements alone would just be `10-jobserver`
at a different width - real cores idle only when the *ready set* is
narrower than the builder count, and the giant provides a phase where
that is not true (one element's build dependency has nothing else
ready behind it, same as `11`). The giant alone, with three build-order
leaves, is `11`'s own shape - it cannot show a *width* win because
nothing else is ever ready to run beside it. Together: while the giant
holds one builder slot and up to its own `max-jobs` cores, the 24 narrow
elements are all ready at once, and only the builder count decides how
many of them get a slot rather than a queue position.

Related, open: `UX-1005` (bga recommends a builder count and a pool
size from a capture, from the ready-set width and the host's knee) -
this project is the fixture that shape needs and does not have
("narrow elements queued while cores idle"). Not implemented here.

## Running it

Same staged sysroot as `05`-`12` - `../stage_cpp_toolchain.sh`
hardlink-clones it here too, and hardlink-clones `10-jobserver`'s own
`files/gen/cmake/generate.sh` in as well (reused, not a second copy).

```bash
../stage_cpp_toolchain.sh
bst build all.bst                 # BuildStream's own default builders
bst --builders 32 build all.bst   # 2x this host's core count
```

## Graviton three-arm run

`../11-serial-giant/graviton_arms.sh mixed`, run from
`examples/11-serial-giant/` (the arms script's `mixed` mode points itself
at this project): three interleaved repeats, cold caches every build, of
`off` at `bst`'s default builders, `off` with `--builders 32`, and `auto`
with `--builders 32` (arms `off4`, `off32`, `auto32` in `builds.txt` -
distinct names per arm; `off32`/`auto32` name the 2x-builders figure
the win shape is about, `off4` the unmodified-builders baseline).
The session runs this on CodSpeed's Graviton and pastes the reading into
`UX-1010`'s task file Outcome (`docs/backlog/scenarios/`) - not run here.
