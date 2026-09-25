# UX-1010: a second fixture for the jobserver's breadth win - one giant, many single-core elements

**Priority:** Medium | **Status:** 🟡 In Progress | **Depends on:** UX-1009 | **Found by:** Ruslan on the jobserver batch thread (2026-09-24): "a single giant element and several elements that consume only one make job ... with 2x buildstream builders we potentially can spawn enough non-parallel elements and have a win" | **Serves:** R4, R5 (the fixture UX-1005 needs and does not have) | **Topic:** capture | **Area:** tools | **Shape:** bounded

## Motivation

`examples/11-serial-giant` shows one win shape: a single long element,
alone on the critical path, whose native recipe (`max-jobs`) can be
widened by `--jobserver auto`. Ruslan's second shape is different -
breadth, not width: a giant plus several elements that each use only
one core, all ready to build *alongside* it rather than after it, so
raising BuildStream's own `--builders` (not any element's own recipe
width) is what lets more of them run at once instead of queuing. `11`'s
three leaves cannot show this - they are a build dependency on the
giant, so they are never ready to compete with it for a builder slot.
`UX-1005` (bga recommends a builder count and a pool size from ready-set
width) names exactly this "narrow elements queued while cores idle"
case as one its recommender has to get right, and has no fixture for
it.

## Required Fix

A new example project, `examples/13-mixed-graph`: `giant.bst` (the same
element as `11-serial-giant`'s own - 256 generated C files, the
`giant_lines` option carried in unchanged) plus 24 `narrow-*.bst`
elements, each real ~20-30s single-core work
(`variables: notparallel: True`, the mechanism `06-macro-micro-
optimization`'s `core.bst` already uses to force `make -j1` - a real
`-j1` on the command line takes GNU make out of jobserver mode
entirely, so neither `--builders` nor `--jobserver auto` can widen it).
All 25 depend only on `toolchain.bst` - none depends on the giant - so
they are all ready at once and `all.bst`'s own dependency list is the
only place that "depends on everything". Same staged sysroot as `05`-
`12` (`stage_cpp_toolchain.sh`'s clone list), same generator as `10`/`11`
(`stage_cpp_toolchain.sh`'s generator clone list). Wired into
`examples/README.md`.

`examples/11-serial-giant/graviton_arms.sh` gains a `mixed` leg: three
interleaved repeats, cold caches, on `13-mixed-graph`, three arms -
`off4` (`bst`'s own default builders), `off32` and `auto32` (both
`--builders 32`) - reusing the script's existing `build`/`peak`/`busy`/
`shares`/`binaries` helpers and notice/summary conventions unchanged.

## Out of Scope

Running the Graviton arms (the session does that - this row stays
🟡 until it has that reading). `UX-1005`'s own recommender - this is
its fixture, not its implementation. Any `.github/workflows/ci.yml`
`bst-examples` change (no guard in this repository enumerates example
projects by name against that job; adding one was not required to
satisfy a guard, so it was not done - see Decomposition). Any
`.github/workflows/codspeed-probe.yml` matrix change (the session
does that once the Graviton reading is in hand).

## Decomposition

surfaces: `examples/13-mixed-graph/` (new: `project.conf`, `elements/*.bst`,
`README.md`), `examples/stage_cpp_toolchain.sh`'s two clone lists,
`examples/README.md`, `examples/11-serial-giant/graviton_arms.sh`
guards: `make lint` (PyMarkdown on both new/changed READMEs), `sh -n`
on the arms script's own syntax, `make push-check`'s `dev_sizes.py
--check` and `dev_close_task.py --check`
gap: whether any existing test enumerates example projects by name
(searched `tests/`, `.github/workflows/ci.yml`'s `bst-examples` job -
neither does; `bst-examples` runs a fixed, explicit list of steps, one
per project, and this project is not one of them by design - no `bst`
build of it runs in CI's own gated job)
track: implementer
gate: `make test-touching`, `make push-check`

## Acceptance Test

`examples/11-serial-giant/graviton_arms.sh mixed`, on CodSpeed's
Graviton (16 real Cortex-A72 cores), staged the same way UX-1009's own
steps stage the toolchain and buildbox - three interleaved repeats of
`off4`/`off32`/`auto32`, cold caches every build, `builds.txt`'s three
distinct arm names each read a wall, `giant-peak`, and the pool/share
line `bga capture run` produces. The session runs this and pastes the
reading below.

## Outcome

Not yet run (🟡) - the session runs the Acceptance Test above on the
Graviton and pastes the three measured parts (gap, close, mutation
table) once it has that reading.

**`BGA_SKIP_SELECTOR=1` on this commit**: `make test-touching` reddens
on `test_every_task_file_has_a_row_in_the_table` - this task file's own
index row is the orchestrator's row-move, not this track's (this track
may not edit `docs/backlog/scenarios/README.md`, per `UX-0548`/`UX-0671`'s
own documented case).
