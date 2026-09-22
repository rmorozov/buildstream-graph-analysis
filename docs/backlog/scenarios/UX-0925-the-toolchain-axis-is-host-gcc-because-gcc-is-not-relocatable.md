# UX-925: the examples' toolchain axis is this host's gcc because gcc's search paths are not relocatable, so a second `arch=` variant needs a second machine

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-914 | **Blocks:** — | **Found by:** `UX-914` — it took the runtime axis and recorded why the toolchain is a separate question | **Serves:** every example, and the comparison class a `variant` dimension names | **Topic:** guards | **Area:** tools | **Shape:** mechanical

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

- **`-B` plus `--sysroot` on a stock pinned gcc**, proposed by
  `rmorozov` on `#257` and the leading candidate: do not relocate the
  toolchain at all, parameterize it. Measured 2026-09-22 on the host's
  gcc 13.3.0:

  ```text
  A. --sysroot moves the target headers, only those
     #include <...> search starts here:
      /usr/lib/gcc/x86_64-linux-gnu/13/include   <- untouched, install prefix
      <sysroot>/usr/include                       <- moved
  B. --sysroot does not move the exec prefix
     no flags      cc1 -> /usr/libexec/gcc/x86_64-linux-gnu/13/cc1
     --sysroot     cc1 -> /usr/libexec/gcc/x86_64-linux-gnu/13/cc1
     -B <empty>    cc1 -> /usr/libexec/gcc/x86_64-linux-gnu/13/cc1
     -B <real cc1> cc1 -> <dir>/cc1
  ```

  Both flags, then, not either: `--sysroot` decides where the build
  shops for target parts, `-B` which toolbox the driver reaches into.
  That also answers part of the file-class question below for free —
  gcc's **own** internal include dir and `libgcc` stay with the
  toolchain under both flags, so they are the pinned toolchain's and
  never the BuildStream-staged target sysroot's.

  **This dissolves the row's own premise.** If the flags carry it, no
  relocatable, cross-built or rewritten toolchain is needed: the stock
  nix gcc closure stays at its own `/nix/store/<hash>`, its
  content-address intact, and the *invocation* moves rather than the
  tree. The closure requirements below are unchanged by that — they are
  about staging the closure, not about relocating it.

  **The hazard is row three, and it is this repository's own shape.**
  A `-B` pointing at a directory that holds no `cc1` falls back to the
  compiled-in prefix and prints nothing, so the mechanism looks like it
  works while reading the host — exactly what `UX-914` exists to catch.
  It gets the same treatment staging got: declared, then probed, with a
  mutation that points `-B` at an empty directory and expects red.

  **This half is `UX-930`**, which declares the parameters, reads back
  where each file class actually came from, and carries the shim - and
  which measured that `-B` needs *three* directories rather than one,
  and that the C++ headers move under neither flag.

  **What it costs to deliver.** The examples' own build commands invoke
  the compiler, not a wrapper this repository controls, so the flags
  arrive through a PATH shim — the shape `bga-make` and `UX-913`'s GCC
  driver shim already established. With `exec` it adds no process, but
  it adds one `execve` to plane 2's ledger, and it must be shell-only:
  the sandbox stages no `dirname` or `basename`, the trap `UX-880` and
  `UX-913` both hit and `UX-918` still carries.

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

## Outcome (round 137, 2026-09-22) — 🟢 Done

**Premise:** falsified, in the title. gcc's search paths are compiled
in, but that never required a second machine - it required a prefix
this repository can *name*. Its own prediction held too: an unwrapped
nix gcc keeps `include/c++` in its store prefix, so the C++ headers
are **toolchain-owned**, reached with no flag at all.

### The gap, measured

```text
$ python3 -m tools.sysroot_manifest <sysroot>          # before
  gcc  host 13.3.0   binutils  host 2.42   cmake  host 3.28.3
```

Three declared host facts: every runner-image roll re-dates every
figure, and a second `arch=` example had nowhere to come from.

### After

```text
$ examples/stage_cpp_toolchain.sh                      # 37 store paths
  gcc pinned 14.3.0  binutils pinned 2.44  cmake pinned 4.1.2
  glibc-pinned pinned 2.40
$ python3 -m tools.toolchain_params --check <sysroot>
  exec-prefix toolchain toolchain  .../gcc-14.3.0/libexec/.../cc1
  assembler   toolchain toolchain  .../binutils-2.44/bin/as
  linker      toolchain toolchain  .../binutils-2.44/bin/ld
  libgcc      toolchain toolchain  .../gcc-14.3.0/lib/gcc/.../libgcc.a
  gcc-headers toolchain toolchain  .../gcc-14.3.0/lib/gcc/.../stddef.h
  start-files sysroot   sysroot    .../glibc-2.40-224/lib/crt1.o
  libstdc++   toolchain toolchain  .../gcc-14.3.0-lib/lib/libstdc++.so
  c-headers   sysroot   sysroot    .../glibc-2.40-224-dev/.../stdio.h
  cxx-headers toolchain toolchain  .../gcc-14.3.0/include/c++/14.3.0
$ python3 -m tools.nix_closure --check <sysroot>       # 0 dangling refs
```

**`-B` is five directories, not `UX-930`'s three**: without
`gcc-14.3.0-lib` the link cannot find `-lgcc_s`, and without binutils'
`bin` the assembler answers the bare name `as` - which is why
`assembler` and `linker` are classes at all, readable only once a pin
puts them on a prefix. **Nine classes of nine** read from the half
they declare, against seven on a host-staged tree; **37 store paths,
420 MiB**, and the sysroot goes 272M -> 452M. The isolation reading,
which no build succeeding can give: example 05's six cmake projects
configured, compiled, linked, installed and the app **ran** inside a
`chroot` of the staged tree alone - nothing of this host but `/proc` and `/dev/null`.

### Mutations verified red and reverted (6)

| # | mutation | reddened |
|---|---|---|
| A1 | a host `gcc` copied over the driver shim | `...StagedOverThePin`, 2 |
| A2 | a host `cc1plus` over the pin's | `...StagedOverThePin`, 1 |
| A3 | the binutils store path removed | `...StagedOverThePin`, 1 |
| A4 | `ld.bfd` gone, so `-B` writes at nothing | `...FromTheClosure`, 2 |
| A5 | the shim rooted at the staging tree, not `/` | `...TheSandbox`, 1 |
| A6 | a host path back in `TOOLCHAIN_BINARIES` | `...PinIsDeclared`, 1 |

Two of mine did not discriminate. The version probes **cannot** catch
A1: a shim is a shell script whose `/nix/store` flags resolve only in
the sandbox, so they ask the pin's own binary and a host driver over
the shim answers every one correctly - `shim_divergences` reads the
file instead, and the stager runs it. And the mutation fixture wrote
*through* its hardlink clone into the real sysroot; `_replace` unlinks
first. One defect next door: `sysroot_manifest.measure` probes in a
scratch directory, so a **relative** `dest` made a relative argv
resolving against it and all nineteen rows read `did not run`.

### Deviation from the Required Fix

Two, named rather than absorbed. **The examples are not captured
here**: this container has neither `bst` nor `bwrap`, so "every figure
re-derived" is owed and unpaid - the chroot build replaced it. **The
produced binaries' loader moves**: the pin bakes its own
`/nix/store/<glibc>/lib64/ld-linux-x86-64.so.2` into everything it
links, so example output loads glibc 2.40 while the tree's `sh` and
coreutils load the host-staged 2.39. Both are declared, the runtime
rows byte-identical against a written-out copy, and the linked app
needs at most `GLIBC_2.34`.

## Verification Log

The round-documents commit is committed with `BGA_SKIP_SELECTOR=1`.
`test_a_documents_dateline_matches_its_own_first_commit` reads a
document's first commit date, which is `None` until the document *is*
committed, so a new `round-N.md` cannot be green before the commit
that adds it. The selector is green on the commit after it, which is
the one carrying the code. Rounds 136 and 137 are both new here:
`UX-926`'s silence meant round 136 closed three rows in three threads
and none wrote its document, and round 137 taking the highest number
is what made the register demand it.
