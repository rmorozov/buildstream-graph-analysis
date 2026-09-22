# UX-925: the examples' toolchain axis is this host's gcc because gcc's search paths are not relocatable, so a second `arch=` variant needs a second machine

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-914 | **Blocks:** — | **Found by:** `UX-914` — it took the runtime axis and recorded why the toolchain is a separate question | **Serves:** every example, and the comparison class a `variant` dimension names | **Topic:** guards | **Area:** tools | **Shape:** mechanical

## Motivation

`UX-914` split the examples' sysroot into two axes and closed the
runtime one: `make` is pinned from `cache.nixos.org`, and
`tools/sysroot_manifest.py` now declares every other package with the
version its staged copy reports, so a divergent host is loud rather
than silent. The toolchain axis is still whatever the staging host
installed:

```text
toolchain:
  gcc        host    13.3.0  (4 probed, 4 staged)
  binutils   host    2.42  (7 probed, 7 staged)
  cmake      host    3.28.3  (1 probed, 1 staged)
```

`stage_cpp_toolchain.sh`'s own header states why, and the reason is
real: gcc's internal search paths are compiled in, not relocatable, so
a gcc unpacked anywhere but its build prefix cannot find `cc1plus`,
its startup objects or its headers. That is what forced staging from a
host at absolute paths in the first place.

**What it costs.** `bga` ships `variant` as named dimensions —
`arch=aarch64`, `sanitizer=address` — and the comparison class is
build type *and* variant. A second `arch=` example needs a second
architecture's toolchain, which today means a second machine. And
`UX-914`'s declaration makes the toolchain a *declared* host fact
rather than an unknown one, which is progress, but a declared host
fact still reddens every time the runner image rolls.

## Required Fix

Pick and land a relocatable toolchain for the toolchain axis alone,
leaving the runtime axis exactly as `UX-914` left it. `UX-914`'s
axis B paragraph already did the survey; its two candidates and their
costs, not re-derived here:

- **`clang-cross`** publishes one `<target>.tar.xz` per target, 44 of
  them including `x86_64-unknown-linux-gnu` and
  `aarch64-unknown-linux-gnu` at glibc 2.44 — a drop-in *if* the asset
  can be fetched. Measured 2026-09-21: the repository clones from the
  development container, its GitHub release assets 403.
- **`crosstool-ng`** builds a `--with-sysroot` toolchain, so it is a
  builder rather than a tarball and not a drop-in for a staging script
  at all.
- **The nix binary cache**, which `UX-915` proved and `UX-914` chose
  for the runtime axis, carries gcc 14.3.0 and 15.1.0 and cmake as
  content-addressed store paths, and *is* reachable. It answers the
  relocatability constraint differently: a nix gcc is not relocatable
  either, but its prefix is `/nix/store/<hash>-...`, which the sysroot
  can carry verbatim — the same *prefix* trick `tools/nix_store_fetch.py`
  already plays for `make`. That was not weighed in `UX-914`'s axis B
  paragraph, which predates the pin landing.

  **It is not the same fetch, though, and this row must not assume it
  is** (`rmorozov` on `#257`). The `make` pin gets away with one NAR
  and no closure because both pins stop at `GLIBC_2.38` and one
  relative symlink answers their interpreter and RUNPATH — measured in
  `UX-915`. A gcc store object is not that: the driver and its wrapper
  reference separate gcc, binutils, libc, header and wrapper-support
  store paths, so **preserving the `/nix/store/<hash>` prefix is
  necessary and fetching one NAR is not sufficient**.

- **`pkgsCross` plus `patchelf`**, proposed by `rmorozov` on `#257`:
  cross-build the toolchain with nixpkgs' own infrastructure, then
  strip the store paths out of the result so nothing carries a
  `/nix/store` prefix at all. Two measurements against it, both taken
  2026-09-22 from the development container:

  ```text
  nixos-25.11 store-paths.xz, 216,353 paths
    aarch64-unknown-linux-gnu-*  3 hits, all `nim-wrapper`
    cross binutils, stage-final gcc   0 hits
    patchelf                     0.15.2 and 0.18.0-unstable, present
  readelf -d $(command -v gcc)   NEEDED only - no RPATH, no RUNPATH
  strings -a $(command -v gcc)   /usr/lib/gcc/  /usr/libexec/gcc/
  gcc -print-search-dirs         programs: =/usr/libexec/gcc/...
  ```

  So the channel indexes **no** cross toolchain: `pkgsCross` is a
  build, not a fetch, and a build needs a real Nix where this
  repository has a 60-line NAR reader and no daemon or root. And
  `patchelf` edits `PT_INTERP` and `RPATH`/`RUNPATH`; the driver has
  neither, and the paths it actually resolves `cc1`, the start files
  and the headers through are **string constants** compiled in at its
  configure prefix, which `patchelf` does not see. A nixpkgs `gcc` adds
  a second layer patchelf cannot reach at all: `cc-wrapper` is a shell
  script that injects absolute store paths as flags.

  The trade underneath: rewriting a store path breaks the
  content-address, and a pinned artifact's checkability is the whole of
  what `UX-914` bought. Where freedom from the prefix is really needed,
  the mechanism that keeps the hash is a **bind mount** of the staged
  store at `/nix/store` inside the sandbox — which is what the
  isolation clause below asks for anyway — not a rewritten binary.

  Two things here are reasoning, not measurement, and this row owes
  both a reading before it rules the route out: whether libiberty's
  `make_relative_prefix` already relocates a whole-tree move through
  `argv[0]`, and what a `-B`/`--sysroot`-driven gcc costs in the
  staging script.

Whichever wins, `tools/sysroot_manifest.py`'s toolchain rows become
`origin: pinned` and the declaration stops being a host fact.

**What a nix toolchain has to do that the `make` pin did not.** These
are requirements of this row, not options:

- Walk the selected store path's `.narinfo` `References` **transitively**
  — or otherwise materialize the exact closure — and stage every
  referenced store path at its own absolute `/nix/store/<hash>` name.
  A partial closure is a sysroot that builds by reaching outside
  itself.
- Prove the build cannot see the **host's** `/nix/store`. A staged
  closure that happens to work because the staging machine has Nix
  installed is the same host-decides-the-measurement defect `UX-914`
  closed, one layer down.
- State **which target sysroot owns what**: the start files (`crt1.o`,
  `crti.o`, `Scrt1.o`), `libgcc`, `libstdc++` and the C/C++ headers
  are currently staged by `stage_cpp_toolchain.sh` from the host's
  `/usr/lib/x86_64-linux-gnu` and `/usr/include`. A pinned toolchain
  brings its own; the row has to say, per file class, whether the
  pinned toolchain or the BuildStream-staged target sysroot provides
  it, because a mixture of the two links but does not mean anything.
- Decide the same question for the **decompressor**. `UX-915` chose
  `xz` NARs deliberately, because `lzma` is in the standard library
  and neither the runner nor the dev container has `zstd`; glibc's own
  NAR is `zstd`. A gcc closure will contain `zstd` NARs, so this row
  either vendors a decompressor or establishes one is present.

**Two things change the moment the compiler does**, both recorded in
`UX-914` and neither a reason not to do this:

- `gcc`/`g++` sit in `ORCHESTRATION_BINARIES`
  (`bst_native_build_tracer.py`) because they exec `cc1plus`;
  `clang`/`clang++` sit in `WORK_BINARIES` because clang compiles
  in-process. No example exercises that split today, so picking clang
  would be the first to.
- `UX-878`'s `_COMPILER_SAFE_POLICIES` (`bwrap_shim.py`) exists for
  gcc's `lto-wrapper` grandchild, which a clang/`lld` build does not
  have.

## Out of Scope

The runtime axis, closed by `UX-914` — glibc, the shell, coreutils and
`make` stay as that row left them, and a toolchain pin must not move
them. `UX-914`'s own declaration mechanism, which this row fills in
rather than replaces. The real-project capture's target choice. A
second `arch=` example project, which is what this unblocks, not what
it delivers. Whether the development container's network policy should
carry the `clang-cross` release assets — that is a request to the
environment's owner, not a finding against a candidate.

## Acceptance Test

`tools/sysroot_manifest.py --check` reports the toolchain axis'
packages as `pinned`, with versions this repository names, and
`tests/unit/test_the_sysroot_declares_both_axes.py` reddens when a
host compiler *or one of its helpers* is staged over them — the
mutations `UX-914` ran against the `make` pin and against `cc1plus`,
applied to the pinned tree.

**The closure is asserted, not assumed.** Every store path the
selected `.narinfo`'s `References` reaches transitively is present in
the sysroot at its own `/nix/store/<hash>` name, checked by walking
the staged tree against the fetched narinfos rather than by the build
succeeding. And a build run with the host's `/nix/store` made
unreachable produces byte-identical output to one run with it present
— which is the reading that says the closure is complete, where a
green build alone says only that *something* answered.

The manifest states, per file class (start files, `libgcc`,
`libstdc++`, C and C++ headers), whether the pinned toolchain or the
BuildStream-staged target sysroot owns it, and a guard reads that
against where the file actually came from.

The examples build and capture on the pinned toolchain, and every
example figure the documents carry is re-derived with the deviation
recorded, because a different compiler is a different program.

`tools/sysroot_manifest.py`'s runtime rows are byte-identical before
and after, which is the claim that the two axes really are
independent.

## Outcome
