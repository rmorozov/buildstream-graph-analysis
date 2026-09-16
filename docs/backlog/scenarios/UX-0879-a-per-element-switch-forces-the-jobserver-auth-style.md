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

## Decomposition

surfaces: `bga/cli.py` (the `--jobserver-auth-override` capture flag →
`BST_TRACE_JOBSERVER_AUTH_MAP`) · `tools/bst_native_build_tracer.py` (env
passthrough) · `tools/native_trace/bwrap_shim.py` (`resolve_auth_override`
new · the `_jobserver_injection` override branch before the UX-878
compiler-safe path) · `tests/unit/test_a_per_element_switch_forces_the_auth_style.py` (new) · docs/guides/cli.md (§3.10, the env inventory + flag)
guards: the new test file (input classes below); UX-874/878's `test_bwrap_shim.py` + `test_the_lto_link_survives_the_jobserver.py` stay green
gap: the earlier `main()` sandbox-make probe still runs for an overridden element (harmless — `_forced_auth` ignores the resolved pool style) — a future round if "never probe when overridden" is wanted end-to-end
track: single (one override path + one guard); serial (touches the same `_jobserver_injection` UX-878 owns)
gate: batch PR (round 125)

Input classes: element matched to `fd` on sub-4.4 make → raw fd (no
scrub); matched to `off` → scrubbed, recipe `-jN` kept; matched to
`fifo` → fifo path; first-match-wins across groups/globs; unmatched →
auto (scrub on 4.3, per UX-878 — the non-regression anchor).

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

**Gap measured** (`test_an_unmatched_element_on_make_4_3_is_scrubbed` in
the new file, same fixture as UX-878's own
`test_cmake_fd_with_make_4_3_is_scrubbed_with_no_wrapper_mount`): with no
override, a cmake element on a fd-style pool with a sandbox `make` 4.3
gets `MAKEFLAGS` scrubbed entirely (no `--jobserver-auth` anywhere) -
exactly the "lone LLVM element crawls at 8 with 32 cores idle" gap the
Motivation names, with no way to keep that one element filling the pool
while its make stays pinned.

**Close measured** (`pytest -q tests/unit/test_a_per_element_switch_forces_the_auth_style.py`):

```text
collected 11 items
tests/unit/test_a_per_element_switch_forces_the_auth_style.py .......... [ 90%]
.                                                                        [100%]
11 passed in 0.08s
```

Also green, unchanged: `tests/unit/test_bwrap_shim.py` (67),
`tests/unit/test_the_lto_link_survives_the_jobserver.py` (11) - no
UX-874/UX-878 regression.

**Mutation table** (`resolve_auth_override` forced to always return
`None`, the "auto" outcome - scratch copy of `bwrap_shim.py` saved
before, restored after):

| mutation | reddened | count printed |
|---|---|---|
| `resolve_auth_override` -> always `None` | the 3 pure-unit match tests, `first_match_wins`, `multiple_globs`, and all 3 integration tests (fd/off/fifo forced) | `8 failed, 3 passed` |
| revert | none | `11 passed` |

The `off`-forced integration test was first written against a make-4.3
fixture, where UX-878's own auto/scrub path already produces the same
observable argv as a forced `off` - the mutation left it green (a guard
that read a proxy the gate under test already excludes). Rewritten
against make 4.4, where auto rewrites to `fifo:` instead of scrubbing,
so a forced `off` is now a real assertion about the override, not
something auto would have done anyway; the mutation now reddens it too
(8 of 11, not 7).

**Deviation**: `docs/guides/cli.md`'s environment inventory
(`## The environment \`bga\` reads`) and its "Flags reachable only from
`--help`" section both needed a new row/bullet for
`BST_TRACE_JOBSERVER_AUTH_MAP`/`--jobserver-auth-override` -
`tests/unit/test_the_environment_surface_is_an_inventory.py` catches an
undocumented name in `bga/`, `tools/` on sight, so this was required to
keep `make test-touching` green rather than a choice. `tools/dev_touching.py`'s
own cost-row in `docs/contributing/fixing-guide.md` (554 -> 555 test
files) and the round-125-opening's own gaps (`## Decomposition`,
`docs/README.md`'s link to `round-125.md`) are pre-existing/shared
derived state, confirmed unchanged on the base commit and left for the
orchestrator's batch-level re-derive, same as `tests/tiers.py`.
