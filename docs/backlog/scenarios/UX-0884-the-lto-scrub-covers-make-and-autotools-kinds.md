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

## Outcome

_(filed round 126, not built — needs a make-kind LTO measurement first)_
