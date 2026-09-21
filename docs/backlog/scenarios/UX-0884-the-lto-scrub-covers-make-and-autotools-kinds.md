# UX-884: the LTO scrub covers make/autotools kinds, not only cmake/meson/cargo

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-878 | **Found by:** round 126 (UX-878's `_COMPILER_SAFE_POLICIES` names `cmake_meson`, `jobs_env`, `cargo` — a `make`/autotools element that itself drives GCC LTO is excluded on purpose, but the exclusion's safety is unproven for the LTO case) | **Serves:** R2 (a make/autotools element that does GCC LTO does not ICE under the injected jobserver) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement

## Motivation

`_COMPILER_SAFE_POLICIES = {cmake_meson, jobs_env, cargo}`
(`bwrap_shim.py:445`) deliberately **excludes** `make`: its reasoning
(`_MAKE_CONSUMER_POLICIES`, `bwrap_shim.py:436-439`) is that a `make`
element's MAKEFLAGS consumer is `make` itself — a direct child, for which
a raw fd is valid. That is true for make's own `-j` scheduling. But if a
`make`/autotools element's recipe **also** does GCC LTO (a link step that
spawns `lto-wrapper`), the same grandchild-fd ICE applies: `lto-wrapper`
is not `make`, it is a grandchild reading MAKEFLAGS. UX-878's downgrade
never runs for this kind, so a `make`-kind LTO element on a forced/native
fd would ICE exactly as the cmake case did — untested, unproven either
way.

## Required Fix

Establish, with a real (or faithfully faked) `make`-kind LTO fixture,
whether the grandchild-fd ICE reproduces for a `make` element. If it does:
extend the compiler-safe path to a `make` element **only for its LTO
link** (not its own `-j`, which must keep the fd), which likely means the
UX-880 shim rather than a blanket scrub (a scrub would serialize make's
own jobs). If it does not (e.g. make ≥4.4 fifo is universal in the field
for make-kind), record the measurement and close as won't-fix with the
evidence. This is judgement because the fix depends on a measurement not
yet taken.

Surfaces (if a fix is needed): `bwrap_shim.py` (`_COMPILER_SAFE_POLICIES`
or a new LTO-aware branch for `make`), and probably UX-880's shim over the
GCC driver applied to `make` kinds too.

## Decomposition

surfaces: TBD by measurement — `bwrap_shim.py` policy set, possibly UX-880's shim
guards: a `make`-kind LTO integration case in `test_the_lto_link_survives_the_jobserver.py` (extends UX-878's harness)
gap: no `make`-kind LTO fixture exists today; step 0 is to build/fake one and reproduce or refute the ICE
track: session's own (judgement — the fix is unknown until measured)
gate: a later round (filed this round, not built)

## Out of Scope

UX-880's cmake/GCC shim (this asks whether it must also cover `make`).
Everything the `make` element's own `-j` relies on (must not regress).

## Acceptance Test

A `make`-kind element with an LTO link step under a forced/native fd,
through `build_shim_argv` + the shim harness: either it ICEs (and the fix
prevents it) or it does not (and the measurement is recorded). Mutation
depends on the branch the measurement selects.

## Measurement (round 129)

Pure-function measurement through `bwrap_shim`, pasted:

```text
kind_job_env("make", "--jobserver-auth=7,7")  -> policy=make,
    pairs=[('MAKEFLAGS', '--jobserver-auth=7,7')]
_compiler_safe_makeflags("--jobserver-auth=7,7", "make", [], ctx=...)
    -> --jobserver-auth=7,7   (unchanged: make ∉ _COMPILER_SAFE_POLICIES)
compiler_safe_auth(fd, fifo_path, make_below_44=True)  -> None   (scrub)
compiler_safe_auth(fd, fifo_path, make_below_44=False) -> fifo:…  (rewrite)
```

Findings:

- A `make`-policy element's `MAKEFLAGS` carries the auth **unchanged**;
  `_compiler_safe_makeflags` only rewrites `_COMPILER_SAFE_POLICIES`
  (`{cmake_meson, jobs_env, cargo}`), which excludes `make`
  (`bwrap_shim.py:445`).
- The UX-880 GCC-driver flto shim is mounted only when the per-element
  override is exactly `flto` (`_jobserver_injection`, `"flto_active":
  override == "flto"`), never on the default `--jobserver auto` path.
  So a `make`-kind element under auto gets no shim.
- Therefore a grandchild `gcc -flto`/lto-wrapper reads the raw auth. It
  ICEs **only when that auth is fd-style**, i.e. the resolved make is
  **< 4.4** (make gained `fifo:` in 4.4). For make ≥ 4.4 the auth is
  already `fifo:PATH` (path-based), which lto-wrapper (gcc ≥ 13.1) opens
  across the sandbox — no ICE.

So the gap is real but confined to **make < 4.4 + gcc ≥ 13 `-flto`** — an
old-make/new-toolchain combination, with no field report. The fix (mount
the UX-880 flto shim for `make` kinds, a no-op unless `-flto` is in argv)
would re-risk round 126's incident: the `cc/gcc/g++/c++` shims in a
shared wrapper dir broke minimal `make`-kind sandboxes lacking coreutils
(`dirname: not found`), which is why they were moved behind
`flto_active`. A `make`-kind mount needs that minimal-sandbox regression
guard first.

## Outcome

_Held open (round 129): the gap is characterized above — narrow (fd-style
make < 4.4 + gcc ≥ 13 LTO), no field report, and the fix re-risks round
126's minimal-sandbox breakage. Awaiting a field report before code;
the shim-for-make with its regression guard is the fix when it bites._
