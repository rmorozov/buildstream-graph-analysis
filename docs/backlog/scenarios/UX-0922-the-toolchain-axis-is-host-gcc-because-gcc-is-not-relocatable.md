# UX-922: the examples' toolchain axis is this host's gcc because gcc's search paths are not relocatable, so a second `arch=` variant needs a second machine

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
  can carry verbatim — the same trick `tools/nix_store_fetch.py`
  already plays for `make`. That was not weighed in `UX-914`'s axis B
  paragraph, which predates the pin landing.

Whichever wins, `tools/sysroot_manifest.py`'s toolchain rows become
`origin: pinned` and the declaration stops being a host fact.

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
host compiler is staged over one of them — the same mutation
`UX-914` ran against the `make` pin, applied to gcc.

The examples build and capture on the pinned toolchain, and every
example figure the documents carry is re-derived with the deviation
recorded, because a different compiler is a different program.

`tools/sysroot_manifest.py`'s runtime rows are byte-identical before
and after, which is the claim that the two axes really are
independent.

## Outcome
