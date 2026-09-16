# UX-877: the sandbox-make downgrade covers every kind that injects MAKEFLAGS

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-874 | **Found by:** round 123, the user (a cmake element whose sandbox-built cmake runs /usr/sysroot/bin/make, GNU Make 4.4 on the host) | **Serves:** R2 (an explicit --jobserver-auth fifo still narrows for a cmake element's own make) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** judgement

## Motivation

`UX-874`'s `sandbox_make_auth_style` narrows `fifo` to `fd` only
for `_MAKE_LIKE_KINDS` (`make`, `autotools`); every other kind is
returned `fifo` unnarrowed. But `kind_job_env` injects a `fifo`
`MAKEFLAGS` for more than those: a `cmake`/`meson` element on the
Makefiles path (no jobserver-client ninja) gets `MAKEFLAGS` through
`_ninja_aware_env`, and so does a `JOBS`-carrying table-less kind
(`jobs_env`). Their generated or invoked make reads that string - the
user's `cmake` element runs `/usr/sysroot/bin/make` under a fifo
`MAKEFLAGS` and dies, the exact defect `UX-874` was meant to stop,
skipped because `cmake` is not in the make-like set. The kinds the
downgrade covers must be the kinds that receive a `MAKEFLAGS`, not a
narrower hand-picked pair.

## Required Fix

`tools/native_trace/bwrap_shim.py`: `sandbox_make_auth_style` runs
the sandbox-make probe (and narrows `fifo` to `fd`) for every kind
whose `kind_job_env` injects `MAKEFLAGS` - `make`, `autotools`,
`cargo`, and the `cmake`/`meson`/`jobs_env` path when it is not the
ninja-client/ninja-static case - not only `_MAKE_LIKE_KINDS`. Derive
the set from the injection, not a second hand-kept list: a kind gets
the probe exactly when it would be handed a `fifo` `MAKEFLAGS`. A kind
that never injects `MAKEFLAGS` (`ninja_static`, `unknown_kind`) is
still returned unnarrowed.

## Decomposition

Input classes: make/autotools (already narrowed), cmake/meson on
the Makefiles path (newly narrowed), cmake/meson resolving to a ninja
client (no MAKEFLAGS, unnarrowed), jobs_env kind, unknown_kind (no
MAKEFLAGS). Surfaces: `tools/native_trace/bwrap_shim.py`
(`sandbox_make_auth_style`, its kind gate) ·
`tests/unit/test_bwrap_shim.py`. Parallel with UX-876 (disjoint file).

## Out of Scope

Identifying the exact make binary a cmake recipe invokes (an
absolute-path or sysroot-built make the probe cannot see) - the reason
`UX-876` makes `auto` pick `fd`; this row only widens the narrowing
that runs when `fifo` is the resolved style. The `auto` default
(`UX-876`).

## Acceptance Test

`tests/unit/test_bwrap_shim.py`: with the resolved style `fifo`
and a fake sandbox `make` reporting `GNU Make 4.3`, a `cmake`-kind
element on the Makefiles path narrows to `fd` (was left `fifo`), and a
`meson`/`jobs_env` kind likewise; a `cmake` element resolving to a
jobserver-client ninja (no `MAKEFLAGS`) is unnarrowed. Mutation:
restore `element_kind not in _MAKE_LIKE_KINDS: return "fifo"` - the
cmake case keeps `fifo` and reddens.
