# UX-913: the jobserver scrubs itself off every cmake element under a make-4.3 sandbox, so auto and off are the same build

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-874, UX-878, UX-879, UX-882 | **Blocks:** UX-910 | **Found by:** round 132 — `11-serial-giant` reads `peak 2` under `auto` on six consecutive CI pairs, and the capture's own warning says why | **Serves:** every example and every real project whose sandbox ships GNU Make 4.3 | **Topic:** guards | **Area:** tools | **Shape:** judgement

## Motivation

`UX-910` asks why `11-serial-giant` reads `peak 2` against a ceiling of
4 under `--jobserver auto`. The capture answers it in its own output,
four times per run, and no round had read it:

```text
Warning: giant.bst scrubbed to recipe -jN (sandbox make <4.4); move it to
  make >=4.4 for fifo pool-fill, or force fd/flto (UX-879/880)
Warning: leaf-a.bst scrubbed to recipe -jN (sandbox make <4.4); ...
Warning: leaf-b.bst scrubbed to recipe -jN (sandbox make <4.4); ...
Warning: leaf-c.bst scrubbed to recipe -jN (sandbox make <4.4); ...
```

`12-junctioned`'s `core.bst` carries the same line in the same run
(`35545829617`, `artifacts/11-serial-giant/run-auto`).

The chain, run against `giant.bst`'s real parameters rather than
described:

```text
jobserver_decision(2, 2)                        -> joined
style_for_make_version("GNU Make 4.3")          -> fd
kind_job_env("cmake", auth, ninja unavailable)  -> [("JOBS",""),("MAKEFLAGS",auth)], "cmake_meson"
"cmake_meson" in _COMPILER_SAFE_POLICIES        -> True
compiler_safe_auth(fd-style, make_below_44=True)-> None
```

A `None` from `compiler_safe_auth` drops `MAKEFLAGS` **and** `JOBS`, so
BuildStream's own `-j2` stands: jobserver-off behaviour, reached from
`--jobserver auto`. No ninja is staged in that sysroot (`BINARIES` in
`examples/stage_cpp_toolchain.sh` names gcc, g++, cmake, make,
binutils, and no ninja), so the cmake row takes its make path, and the
sandbox's `make` is the host's — Ubuntu 24.04 ships GNU Make 4.3.

**The consequence is that `auto` and `off` are the same build.** That
is one fact explaining every reading `UX-910` collected: `peak 2` on
all six pairs, and walls that differ only by run-to-run noise. They
were never two configurations. The `11-serial-giant` step asserts a
strict inequality between a thing and itself, which is why which side
of zero it lands on is a coin flip.

**Why the scrub exists**, and why it over-reaches here. `UX-878` stops
a raw fd auth reaching an *unwrapped* native jobserver client — gcc's
`lto-wrapper`, cargo — which is a deep grandchild across `bwrap` and
cannot open the fd (measured: a GCC-13 ICE). `UX-874` had already
downgraded `fifo:` to `fd` for a sub-4.4 make, which rejects a `fifo:`
auth outright. Together, on a make-4.3 sandbox, every `cmake_meson`
element loses its jobserver. But the consumer under `cmake_meson` with
a Unix Makefiles generator is `make` itself, a direct child that can
use an inherited fd, and this example requests no LTO at all.

## Required Fix

Two questions, and the first is cheap enough to answer before the
second is designed.

**Does forcing `fd` restore the width?** `UX-879`/`UX-882` already
provide the lever: `_forced_auth("fd", …)` keeps `auth_value` raw,
"exactly as `_jobserver_injection` computed it pre-UX-878 (no fifo
rewrite, no scrub)". A `public: bga: jobserver-auth: fd` annotation on
the four elements of `11-serial-giant` turns the mode back on for them
without touching any shared code. One CI run then says whether `peak`
rises above 2.

It may not. If the fd does not survive `bwrap` into the sandbox, make
4.3 will report the jobserver unavailable and fall back to `-j1`, and
the element gets *slower*, at `peak 1`. That outcome is as informative
as the other and must be recorded either way, not retried until it
reads well.

**Should `cmake_meson` be in `_COMPILER_SAFE_POLICIES` at all?** The
policy's own consumer is `make`. Narrowing the scrub to the policies
whose consumer really is an unwrapped grandchild (`cargo`, and
`cmake_meson` only when LTO is actually requested) would restore the
mode for every make-4.3 cmake project rather than for one annotated
example. That is the real fix and it needs its own measurement: what
`UX-878`'s own guard reddens on, and whether a non-LTO cmake build
with a raw fd reproduces the GCC-13 ICE that motivated it.

## Out of Scope

Changing `UX-874`'s downgrade, or the `fifo:`/`fd` resolution itself.
Staging a `make >= 4.4` into the examples' sysroot — a second remedy
the warning names, and a bigger change than this row (Ubuntu 24.04 has
no 4.4 package, so it means building one). `12-junctioned`'s
`core.bst`, which carries the same warning and is its own fixture.
`UX-910`'s gate, which stays wrong whatever this row finds: a strict
unbanded inequality is the wrong instrument even once the two arms
genuinely differ.

## Acceptance Test

One `bst-examples` run on a branch carrying the annotation, with the
`Per-element native parallelism` table read for `giant.bst`:

- `peak > 2` means the mode is restored and `UX-910`'s close condition
  is met.
- `peak 1` means the fd does not cross the sandbox boundary, and the
  row closes on that reading with the `fifo`/`make >= 4.4` route named
  as the remaining one.
- `peak 2` with the warning still printed means the annotation did not
  match the element, which is a defect in
  `read_element_auth_map_for_jobserver`'s own lookup and its own row.

The warning's absence for the four annotated elements is the guard
that the annotation took effect at all, and it is read from the run's
log, not assumed.

## Outcome
