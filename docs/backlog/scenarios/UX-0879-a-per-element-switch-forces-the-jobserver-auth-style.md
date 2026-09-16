# UX-879: a per-element switch forces the jobserver auth style, overriding auto

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-876, UX-878 | **Found by:** round 125, the user (a mixed-make project — some elements pinned to GNU Make ≤4.2.1, others migrating to 4.4 — needs to force `fd` on a ≤4.2.1 element so it fills the pool while it is being fixed, rather than let UX-878 scrub it to its recipe `-jN`) | **Serves:** R2 (an operator migrates make version by version and keeps the jobserver's effect per element) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** bounded

## Motivation

`--jobserver auto` resolves one style for the whole capture, and UX-878
scrubs the compiler-driving kinds (`cmake`/`meson`/`jobs_env`, cargo)
when the sandbox make is <4.4 — correct against the GCC-13 LTO ICE, but
it caps those elements at their recipe `-jN` (`max-jobs`, e.g. 8) instead
of the pool ceiling (the agent's cores, e.g. 40), so a lone LLVM element
crawls at 8 with 32 cores idle (round 124 Standing; ceiling sizing
confirmed `os.cpu_count()`, `bga/cli.py:2499` `resolve_jobserver_ceiling`).

A project cannot move every element to make 4.4 at once — some are
incompatible with make >4.2.1. The operator needs to **force `fd` on a
named ≤4.2.1 element** (so it fills the pool via the fd jobserver its
make accepts) or **`off` on a known-LTO one**, per element, while the
rest stay `auto`. No such override exists: the style is decided only by
the global default and the per-element make probe.

## Required Fix

A per-element auth override that takes precedence over the auto/
scrub/fifo resolution, resolved in the shim against the element name.

- Capture flag (MVP): `bga capture run --jobserver-auth-override
  'fd:<glob>[,<glob>] fifo:<glob> off:<glob>'` (repeatable or
  space-separated `style:glob` groups; element-name globs). Threaded to
  the shim via a new env `BST_TRACE_JOBSERVER_AUTH_MAP`.
- In `tools/native_trace/bwrap_shim.py`, before the auto decision
  (`_jobserver_injection` / the UX-878 `compiler_safe` path), match
  `kind_context.element` against the map. On a match, force the style:
  `fd` → the raw `--jobserver-auth=<fd,fd>` (no scrub, no fifo rewrite),
  `fifo` → the `fifo:` path, `off` → scrub (no auth, no wrapper mount).
  On no match → today's behavior unchanged.
- Precedence: an explicit override > the auto/probe decision. (A
  `public: { bga: { jobserver-auth: … } }` element annotation is the
  version-controlled second surface — filed separately, out of scope
  here.)

## Out of Scope

The compiler shim that lets an `fd`-forced element which *does* LTO
avoid the ICE and still fill the box (round 126). The make/autotools
LTO scrub gap. Changing the `auto` default (UX-876 stays). The
`public:` annotation surface (a follow-up filing).

## Acceptance Test

`tests/unit/` new file: through `build_shim_argv(... element_kind=
"cmake" ...)` with a fake sandbox make reporting 4.3 and
`BST_TRACE_JOBSERVER_AUTH_MAP` set — an element matched to `fd` emits
`--jobserver-auth=<fd,fd>` (no scrub, no `fifo:`) *even though* the make
is 4.3; matched to `off` emits no `--jobserver-auth` and no wrapper
mount; matched to `fifo` emits the `fifo:` path; an unmatched element
falls to auto (scrubbed on 4.3, per UX-878). Plus a pure-unit on the
glob resolver. Mutation: make the override resolve to `auto` always —
the `fd`/`off`/`fifo` match tests redden.

## Outcome

(filled at close)
