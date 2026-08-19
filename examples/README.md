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
`../stage_cpp_toolchain.sh`, which stages one from *this host's own*
installed packages (no docker/debootstrap/network pull needed - see that
script's own header for the real trial-and-error this took to get
working: symlink chains through `/etc/alternatives`, this host's usrmerge
layout, GNU ld linker scripts with embedded `AS_NEEDED` paths, and
liblto_plugin.so's two real install locations all had to be handled).

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
`docs/guides/optimization-walkthrough-06.md` and the `UX-27`..`UX-40` backlog
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
