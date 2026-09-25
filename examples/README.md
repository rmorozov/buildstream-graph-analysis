# Real BuildStream example projects

Six real BuildStream projects, each targeting a different corner case
this tool cares about, built for real (not just `bst show`) in CI
(`.github/workflows/ci.yml`'s `bst-examples` job) to generate real traces,
`bga` run directories, and reports for later analysis. See
`docs/backlog/tasks/` for the specific backlog items 01-03 map to, and
`docs/backlog/scenarios/` for 04-06's.

All sources are `kind: local` or a throwaway `kind: git` remote generated
at build time - no network access needed, nothing sensitive committed.

## 01-resource-contention

Eight independent elements (`work-a.bst`..`work-h.bst`), each doing 3
real seconds of work, all simultaneously ready to build. Built with a
builder count smaller than the fan-out width to force genuine
`RESOURCE_WAIT`/`SCHEDULER_WAIT` gaps (P1-31, P1-32).

```
bst --builders 2 build all.bst
```
(run from inside `01-resource-contention/`)

## 02-deep-chain-mixed-kinds

A depth-4 chain across mixed element kinds (`import` -> `manual` ->
`compose` -> `manual`), plus a junction reached through a runtime-only
dependency - real build, not just `bst show` (P4-12).

```
bst build all.bst
```
(run from inside `02-deep-chain-mixed-kinds/`)

## 03-project-refs-identity

A git-sourced element under `ref-storage: project.refs`, exercising
`tools/bst_extract_run.py --strict`'s real consistency check (P4-13) and
generating real "touch and rebuild" retry/rebuild data (P1-37). The git
source's upstream is a throwaway repo generated deterministically by
`../stage_project3_remote.sh` (fixed committer identity/dates, so the
resulting commit SHA is reproducible from committed seed content alone).
The same script also renders `elements/libbar.bst` from
`elements/libbar.bst.in`, substituting the real (per-checkout) absolute
path to that remote - BuildStream project options have no free-form
string type to hold an arbitrary path (only
`bool`/`enum`/`flags`/`element-mask`/`arch`/`os`), confirmed via a real
CI failure, so this is templated rather than passed as a `--option`.

```
../stage_project3_remote.sh
bst source track libbar.bst
bst build all.bst
```
(run from inside `03-project-refs-identity/`)

## 04-critical-path-optimization

Ten elements with two deliberate, independently discoverable optimization
opportunities: a scheduling bottleneck (a 4-way fan-out constrained by
`--builders`) and a structural one (an unnecessary serial split plus one
oversized step on the critical path). `optimized/` is a second, complete
BuildStream project - the same shape with both fixes applied - so the pair
can be run through `bga compare` as a real before/after. See
`docs/guides/optimization-walkthrough.md` for the full worked walkthrough (every
command and its real output) and `docs/backlog/scenarios/UX-0005-optimization-walkthrough-tutorial.md`
for the task this was built for.

```
bst --builders 2 build all.bst   # baseline, from inside 04-critical-path-optimization/
bst --builders 4 build all.bst   # scheduling fix - no project change needed
(cd optimized && bst --builders 4 build all.bst)   # structural fix
```

**Capture note**: unlike 01-03 above, this project's CI step captures each
build with `tools/bst_run_wrapped.py` and extracts with `--format wrapped`,
not `--format raw` - `--format raw` was found, while building this example,
to corrupt cross-task ordering on a real saved multi-task log (BuildStream's
own `[HH:MM:SS]` elapsed prefix resets per-task, not per-invocation; see
`docs/backlog/scenarios/UX-0006-raw-log-timestamp-corruption.md`). If you're capturing
this project's build yourself rather than reading CI's artifacts, do the
same:

```
python3 -m tools.bst_run_wrapped 04-critical-path-optimization build.log -- bst --builders 4 build all.bst
python3 -m tools.bst_extract_run --format wrapped 04-critical-path-optimization build.log run/
```
(run from `examples/`)

## 05-cmake-cpp-toolchain

Real C/C++ code (5 modules: `core.bst` + a 4-way `lib-a..d.bst` fan-out +
`app.bst`), compiled through CMake generating real Makefiles and built
with real GNU Make - not a `sleep N` proxy like 01/04. Built specifically
to test whether BuildStream's `--builders` and each element's own native
`max-jobs` (real intra-element parallelism, e.g. `make -jN`) compete for
the same CPU cores - they do; see
`docs/backlog/scenarios/UX-0009-builders-max-jobs-joint-optimization.md` for the
real evidence (both source-code citations and a real 6-configuration
timing table) and `docs/backlog/scenarios/UX-0010-total-duration-excludes-pre-task-overhead.md`/
`UX-0011-native-build-system-profiler-tool.md` for what it surfaced beyond
that.

**Needs a real toolchain staged into the sandbox** (BuildStream's sandbox
binds in nothing from the host, and a real C/C++ build needs a real
gcc/g++/cmake/make/binutils sysroot, not just a shell) - see
`../stage_cpp_toolchain.sh`.

The sysroot is two independent axes (`UX-914`) - a **runtime** (glibc,
the shell, coreutils, `make`) and a **toolchain** (gcc, binutils, cmake
and the headers that travel with them) - and `tools/sysroot_manifest.py`
declares, per package, which axis it is on, whether it is pinned or
host-staged, and what version this repository says it is.

The **toolchain axis is entirely pinned** (`UX-925`): gcc, binutils and
cmake are fetched from `cache.nixos.org` as one 37-path closure and
staged at their own `/nix/store/<hash>` prefixes, content-addresses
intact. Nothing is relocated, because a nix gcc is no more relocatable
than Ubuntu's - the *invocation* moves instead, through five `-B`
prefixes and a `--sysroot` baked into a PATH shim at `/usr/bin/gcc`
(`UX-930` wrote the shim, `tools/nix_toolchain.py` carries the pins).

On the **runtime axis** `make` is pinned too (`UX-915`): its version
decides every example's jobserver auth style. glibc, the shell and
coreutils are still this host's, copied in at their own absolute paths -
see the stager's header for the trial-and-error that took (symlink
chains through `/etc/alternatives`, this host's usrmerge layout, GNU ld
linker scripts with embedded `AS_NEEDED` paths).

Staging prints that table and checks it against the staged copies:

```text
runtime:
  glibc      host    2.39  (1 probed of 1 declared)
  coreutils  host    9.4  (4 probed of 4 declared)
  dash       host    dash answers no --version, so the sysroot cannot state it  (0 probed of 1 declared)
  make-4.2   pinned  4.2.1  (1 probed of 1 declared)
  make-4.4   pinned  4.4.1  (2 probed of 2 declared)
toolchain:
  binutils   pinned  2.44  (7 probed of 7 declared)
  cmake      pinned  4.1.2  (1 probed of 1 declared)
  gcc        pinned  14.3.0  (7 probed of 7 declared)
  glibc-pinned pinned  2.40  (1 probed of 1 declared)
```

Two glibcs, and both are declared. The host-staged 2.39 loads the
tree's own `sh` and coreutils; the closure's 2.40 loads the pinned
compiler **and everything the pinned compiler links**, because an
unwrapped nix gcc bakes its own `ld-linux-x86-64.so.2` into every
binary it produces. That is why the pin brings the C headers and the
start files with it, and why staging the host's `/usr/include` beside
them was removed rather than left: a build that found both would link
and mean nothing.

`tools/toolchain_params.py --check` then reads back, per file class,
which half really answered - the parameters are silent when they are
wrong, and `-B` at a directory with no `cc1` falls back to the
compiled-in prefix at exit 0:

```text
toolchain	pinned
  exec-prefix  toolchain toolchain  .../gcc-14.3.0/libexec/gcc/<triple>/14.3.0/cc1
  assembler    toolchain toolchain  .../binutils-2.44/bin/as
  linker       toolchain toolchain  .../binutils-2.44/bin/ld
  libgcc       toolchain toolchain  .../gcc-14.3.0/lib/gcc/<triple>/14.3.0/libgcc.a
  gcc-headers  toolchain toolchain  .../gcc-14.3.0/lib/gcc/<triple>/14.3.0/include/stddef.h
  start-files  sysroot   sysroot    .../glibc-2.40-224/lib/crt1.o
  libstdc++    toolchain toolchain  .../gcc-14.3.0-lib/lib/libstdc++.so
  c-headers    sysroot   sysroot    .../glibc-2.40-224-dev/include/stdio.h
  cxx-headers  toolchain toolchain  .../gcc-14.3.0/include/c++/14.3.0/vector
```

A **pinned** row that disagrees fails the staging - the pin did not
take. A **host** row that disagrees only warns, because a different
working host is not a broken sysroot; it is a different program under
measurement, and `tests/unit/test_the_sysroot_declares_both_axes.py` is
what reddens. If you stage on a host outside Ubuntu 24.04, expect that
warning: the figures the documents carry were measured against the
versions above, and re-declaring them means re-deriving the figures.

Adopting a whole pinned base instead (Debian, Alpine, freedesktop-sdk)
was weighed and declined in `UX-914`: every mirror those need is refused
at CONNECT from the development container, and two of them would change
the libc, so a component becomes a pin when its version is shown to
decide a reading rather than all at once - which is what `UX-925` then
did for the whole toolchain axis at once, since a compiler's closure
arrives as one unit.

```
sudo apt-get install -y build-essential cmake
../examples/stage_cpp_toolchain.sh   # (or ./stage_cpp_toolchain.sh from examples/)
bst --builders 4 --max-jobs 4 build all.bst   # BuildStream's own defaults - real fastest config found
```

To regenerate the real (committed) generated C++ source itself (only
needed if you're changing the workload, not for a normal build):
`python3 generate_sources.py` (run from inside
`05-cmake-cpp-toolchain/`).

Same wrapped-log capture note as `04-critical-path-optimization` applies
here (`--format wrapped`, not `--format raw` - see `UX-06`).

## 06-macro-micro-optimization

Eleven real elements (a `toolchain` import, nine real CMake/C++ modules,
an `all` stack) built to be walked through a **full macro-then-micro
optimization cycle** with `bga` - the project behind
`docs/audits/case-study-06-macro-micro.md` and the `UX-27`..`UX-40` backlog
round.

Where `05-cmake-cpp-toolchain` exists to answer one measurement question,
this one is *deliberately mis-optimized in three independent,
one-line-fixable ways*, one per level of the cycle:

1. **Macro / graph shape** - `lib-a..lib-f` are declared as a six-deep
   dependency chain, not a six-wide fan-out off `core.bst`.
2. **Macro / over-declared dependency** - every `lib-*.bst` build-depends
   on `codegen.bst`; only `lib-f.bst` consumes it.
3. **Micro / inside one element** - `core.bst` carries
   `variables: notparallel: True`, BuildStream's real per-element
   parallelism control, so its eight ~1s translation units compile
   strictly one at a time (confirmed by a real Plane 2 trace:
   `core.bst -> make -j1`, every other element `-j4`). Invisible in
   BuildStream's own element-level log, and therefore invisible to
   `bga`'s Plane 1 - it takes `tools/bst_native_build_tracer.py` to see.

`optimized/` fixes exactly those three and nothing else. Every source
file is generated into *both* variants by the same `generate_sources.py`,
so a `bga compare` across the pair isolates the three changes. Measured
on a real 4-core host: **39.57s -> 27.50s (-30.5%)**.

Every translation unit is calibrated to cost about a second of real
`g++` time (see `generate_sources.py`'s `WEIGHT`), deliberately - with
sub-100ms compiles the whole signal drowns in BuildStream's own
per-element sandbox staging.

Same toolchain requirement as `05-cmake-cpp-toolchain`, and the same
script stages it (it hardlink-clones the one staged sysroot into this
project and its `optimized/` variant, so this costs no extra disk):

```
sudo apt-get install -y build-essential cmake
../examples/stage_cpp_toolchain.sh   # (or ./stage_cpp_toolchain.sh from examples/)
bst --builders 4 --max-jobs 4 build all.bst              # the mis-optimized baseline
(cd optimized && bst --builders 4 --max-jobs 4 build all.bst)
```

Same wrapped-log capture note as `04`/`05` (`--format wrapped`, see
`UX-06`), and the same full-rebuild caveat: clear
`~/.cache/buildstream ~/.local/share/buildstream` between the two builds
or the second one is a near-total cache hit with nothing to time.

## 07-declared-vs-used-dependencies

A deliberately minimal project that exercises `UX-46`'s declared-vs-used
dependency detection in **both directions** — the one thing
`06-macro-micro-optimization` cannot do, because `UX-46` measured that
project and found *every* cross-element build dependency in it to be
decorative.

`user.bst` and `unrelated.bst` declare identical dependencies
(`base.bst` + `toolchain.bst`) and differ only in whether their source
actually includes `base.hpp`:

```
Declared build dependencies never read: 1 candidate(s) across 1 element(s); 4 edge(s) confirmed used
  unrelated.bst              never read: base.bst  (5 staged file(s))

  user.bst      -> base.bst   1/5 staged files opened   <- correctly NOT flagged
  unrelated.bst -> base.bst   0 of 5 files opened       <- correctly flagged
```

An over-eager detector flags both; an inert one flags neither. Full
detail in that project's own
[`README.md`](07-declared-vs-used-dependencies/README.md).

## 08-process-storm

Two thousand short-lived `cat /dev/null` processes in one sandbox — 575
processes per second against `06-macro-micro-optimization`'s 18/s. It
exists because `UX-106`'s overhead budget names a configure-heavy
fixture and no project in this repository was one: `06`'s wall clock is
`cc1plus`, so any per-process tracing cost hides inside it.

```
Processes traced: 2003 (2000 matched, 3 no observed exit)
Wall span: 3.484s
```

Used by `UX-108` to decide whether the ptrace spine defaults on. Full
detail in that project's own [`README.md`](08-process-storm/README.md).

## 09-fine-grained-siblings

Eight elements with the identical build-dependency set, each doing
sub-second work in a sandbox that stages a shared sysroot. It exists
because `UX-100`'s merge criterion — *"siblings paying more sandbox toll
than they spend building"* — had fired only on synthetic unit-test input,
and both real captures correctly said no, which cannot tell a working
detector from an inert one.

The obstacle was not the shape but the instrument. BuildStream stages
dependencies by hardlink and times its own phases to the second, so the
project's real 8k-file C++ sysroot stages in `00:00:00` and the toll
rounds to **zero**. `bulk.bst` is 60,000 one-byte files — the file count
at which "Staging dependencies" reaches one second and the toll becomes
visible at all:

```text
8k-file toolchain only:   toll 0.0s of 1.0s total, share 0.00  -> no candidate
plus 60k-file bulk.bst:   toll 1.0s of 2.0s total, share 0.50  -> candidate fires
```

`merged/` is the same eight translation units in one element — the fix
the candidate recommends — so the projection can be checked against a
real rebuild rather than against arithmetic. `UX-120`'s verification log
carries that table, and the measurement is why the projection now ships
as a floor rather than an estimate.

Generate the bulk tree once (it is gitignored, like the toolchain):

```
examples/09-fine-grained-siblings/generate_bulk.py
```

## 10-jobserver

Four independent elements (two `autotools`, two `cmake`), each linking
one binary from 64 C files generated inside the sandbox at build time -
the compile-bound evaluation Direction 20's `--jobserver auto` needs
(`UX-848`): `06-macro-micro-optimization`'s critical path is a declared
chain, so its wall never moved under the mode (round 112). Same staged
sysroot as `05`/`06`/`09`. Full detail, real captures and the honest
result in that project's own [`README.md`](10-jobserver/README.md).

## 11-serial-giant

One `cmake` element (`giant.bst`, 256 C files generated inside the
sandbox - four times `10`'s per-element 64) alone on the critical path
under three small leaves that wait on it, `max-jobs: 2` (`10`'s host
default is 4) - the server's shape (`UX-857`): a 40-core server caps one
element at 8 by default, and `10`'s four saturated cores cannot show
what happens when one long element is capped below the core count with
half the graph idle behind it. Same staged sysroot as `05`-`10`; the
generator is `10`'s own script, hardlink-cloned in, not a second copy.
Full detail, real captures and the ratio in that project's own
[`README.md`](11-serial-giant/README.md).

## 12-junctioned

A local junction (`elements/junction.bst`) into `sub/`, a real second
BuildStream project holding one `cmake` element and the stack that
groups it - the shape `UX-869` (the FIFO under `bind_dst`) and `UX-871`
(a junctioned element's kind) were both real first-day defects on, with
no example project to catch either in CI (`UX-872`). Same staged
sysroot as `05`-`11`, cloned into `sub/files/toolchain/` (a junctioned
subproject is a real, separate project). Full detail, the real
`bga snapshot --jobserver auto` reading and `kinds_read.json`'s own
diagnostic in that project's own [`README.md`](12-junctioned/README.md).

## 13-mixed-graph

The jobserver's second win shape (Ruslan, 2026-09-24): one `giant.bst`
(the same element as `11-serial-giant`'s own) plus 24 `narrow-*.bst`
elements, each a real single-core compile (`variables: notparallel:
True`, forcing `make -j1` - the same mechanism `06-macro-micro-
optimization`'s `core.bst` uses). All 25 are ready at once (none
depends on the giant), so `bst --builders` decides how many of the
narrow elements run alongside the giant instead of queuing behind it -
the shape `11`'s build-order leaves cannot show. Related, open: `UX-1005`
(bga recommends builders from ready-set width) names this as the case
it lacks a fixture for; not implemented here. Same staged sysroot as
`05`-`12`; the generator is `10`'s own script, hardlink-cloned in. Full
detail in that project's own [`README.md`](13-mixed-graph/README.md).

## Shared setup

`01-resource-contention`, `02-deep-chain-mixed-kinds`, and
`04-critical-path-optimization` (including its `optimized/` variant)'s
`manual.bst`/`compose` elements need a real shell in the sandbox, which
BuildStream doesn't provide on its own (the sandbox is assembled purely
from staged dependencies). Run once before building any project:

```
sudo apt-get install -y busybox-static
../examples/stage_runtimes.sh   # (or ./stage_runtimes.sh from examples/)
```

On Ubuntu 24.04+ runners, bubblewrap also needs one more thing to build a
network-namespaced sandbox at all - see `.github/workflows/ci.yml`'s
`bst-smoke`/`bst-examples` jobs for the exact `sysctl` workaround
(confirmed via a real CI run, not a guess).
