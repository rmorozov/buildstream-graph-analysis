# UX-878: the injected jobserver never reaches gcc's lto-wrapper as an fd it can't use

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-874, UX-876 | **Found by:** round 124, the user (a `kind: cmake` element building ninja 1.10.2 with a relocatable GCC-13 cross toolchain, glibc 2.17, invoked by absolute path) | **Serves:** R2 (a cmake/ninja element's LTO link completes under the trace jobserver) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** mechanical

## Motivation

bga builds a make jobserver (a FIFO) and injects its auth into the
sandbox build's `MAKEFLAGS` (`bst_native_build_tracer.py:939`
`open_jobserver`; `bwrap_shim.py:542-560` `_jobserver_injection` →
`kind_job_env`). Wrapped tools (`ninja`, `ld.*`, `mold`) intercept the
auth in a shell wrapper and hand the real tool a static `-jN`. But
`gcc -flto` / `lto-wrapper` and cargo are unwrapped by design
(`bst_native_build_tracer.py:1249`, "pass-through by construction") and
read `MAKEFLAGS` directly. For `fd`-style auth (`--jobserver-auth=N,N`,
the `auto` default since UX-876) the fd is **not valid inside the
sandbox** for the deep grandchild that is gcc's lto-wrapper, so on an
LTO link gcc-13 crashes: `internal compiler error: get_token, at
opts-common.cc:2123`, `lto_main`, `lto-wrapper failed`. Control (the
user): jobserver off → the same build succeeds; jobserver on → ICE. So
bga's injected jobserver is the trigger.

A PATH-shadow wrapper cannot fix this: cmake invokes the toolchain by
absolute path with a custom triple (`/opt/.../bin/<triple>-c++`), PATH
is never consulted, and the existing wrappers do not unset `MAKEFLAGS`
for their gcc children anyway. The only channel bga owns that reaches
an absolute-path gcc is the `MAKEFLAGS` auth string itself.

Unlike a raw fd, a `fifo:PATH` auth is path-based: gcc-13 (which
supports the fifo jobserver style) reopens the path inside the sandbox,
and bga already bind-mounts the FIFO's directory (`_sandbox_fifo_path`,
`bwrap_shim.py:501`). So `fifo:` survives the boundary for the compiler
where `fd` cannot. The one case it can't serve is a sub-4.4 make in the
same recipe that also reads this `MAKEFLAGS` and rejects `fifo:`
(UX-874's defect) — there the two needs are irreconcilable in one
string and the auth must be dropped for that element (jobserver off,
which the control shows builds).

## Required Fix

`tools/native_trace/bwrap_shim.py`: a new pure helper
`compiler_safe_auth(auth_value, sandbox_fifo_path, make_below_44)` that,
for the kinds whose `MAKEFLAGS` an unwrapped native jobserver client
(gcc-lto, cargo) will read — the `cmake`/`meson`/`jobs_env` policies of
`_ninja_aware_env`, and cargo — returns an auth form that client can
consume across the sandbox boundary:

- a `fifo:` auth → kept unchanged;
- an `fd` auth, no sub-4.4 make in the recipe → rewritten to
  `fifo:<sandbox_fifo_path>` (gcc-13 opens the path in-sandbox);
- an `fd` auth, sub-4.4 make present → `None`: the `--jobserver-auth`
  is scrubbed and no wrapper mount is added, so neither the old make
  nor gcc-lto sees a jobserver (serial, never an ICE).

Applied in `_jobserver_injection` after `auth_value` is computed
(`:542-548`), scoped to those kinds, and taking precedence over
UX-874's `_downgrade_fifo_to_fd_if_sandbox_make_rejects_it` for them
(that downgrade currently turns `fifo→fd` for `cmake_meson` when make
is <4.4, re-arming the ICE). `make_below_44` is read from the make
probe already run per element (`probe_make`, `style_for_make_version`);
`sandbox_fifo_path` from the pool's fifo/proxy path (recoverable even
in fd style, since the fd was opened from it, `open_jobserver_fd`).
A pure `make`/`autotools` element is unchanged — its `MAKEFLAGS`
consumer is make itself, a direct child, for which `fd` is valid — so
UX-874's downgrade tests stay green.

## Decomposition

surfaces: `tools/native_trace/bwrap_shim.py` (`compiler_safe_auth` new ·
`_jobserver_injection` call site · the UX-874 downgrade precedence) ·
`tests/unit/test_the_lto_link_survives_the_jobserver.py` (new) · docs/guides/cli.md (§3.10, the `--jobserver-auth` note)
guards: `test_the_lto_link_survives_the_jobserver.py` (input classes below); UX-874's `test_bwrap_shim.py` narrowing tests stay green
gap: cargo's LTO/link behaviour under a jobserver is unverified in the field — same policy applied as derived-safety, guarded by an input class, noted in the Outcome
track: single (one file's policy + one new test); serial (touches the same `_jobserver_injection` UX-874/877 own)
gate: batch PR (round 124)

Input classes the guard must cover: fd + cmake + make absent → rewritten
to `fifo:`; fd + cmake + sub-4.4 make present → scrubbed (no
`--jobserver-auth` token anywhere, no wrapper mount); fifo + cmake →
passed through; `make` kind → unchanged from today (fd stands, guards
UX-874 non-regression); cargo → the chosen conservative policy locked.

## Out of Scope

The gcc ICE itself (a toolchain defect — no input should abort the
compiler; bga only stops feeding it an unusable fd). Identifying the
exact make/compiler a recipe invokes. Widening cargo beyond the
same-helper policy without a live cargo-jobserver check. The `auto→fd`
default (UX-876) stays; this narrows the *form* handed to gcc-lto-driving
kinds, it does not change the style resolution.

## Acceptance Test

`tests/unit/test_the_lto_link_survives_the_jobserver.py`: (1) pure-unit
on `compiler_safe_auth` for the input classes above — fd+no-make →
`fifo:` present and no `,`-fd pair; fd+sub-4.4-make → `None`; fifo →
unchanged. (2) integration through `build_shim_argv(... element_kind=
"cmake" ...)` with `_fake_bwrap_with_make(..., "4.3")` / `"4.4"` /
absent (a shell stub emulating `make --version`, no toolchain needed),
asserting the emitted `--setenv MAKEFLAGS`: `fifo:` present / fd-pair
absent in the rewrite case; **no** `--jobserver-auth` substring in the
scrub case. Mutation: in `compiler_safe_auth`, make the fd branch
`return auth_value` (raw `fd,fd` through) — the rewrite test sees
`fd,fd` not `fifo:`, the scrub test sees a surviving `--jobserver-auth`,
both redden; revert → green.

## Outcome

**Gap measured** (pre-fix `bwrap_shim.py` at HEAD, a `cmake` element, `fd`-style jobserver, no `compiler_safe_auth` layer):

```text
BEFORE UX-878 (pre-fix code), cmake element, fd-style jobserver auth:
  MAKEFLAGS = --jobserver-auth=3,3
  -> a raw fd, unusable by gcc's lto-wrapper deep grandchild (GCC-13 ICE)
```

**Close measured** (`pytest -q tests/unit/test_the_lto_link_survives_the_jobserver.py`):

```text
collected 11 items
tests/unit/test_the_lto_link_survives_the_jobserver.py ...........       [100%]
11 passed in 0.10s
```

Same cmake/fd input through the fixed code (`test_cmake_fd_with_make_absent_is_rewritten_to_fifo`) now emits `--jobserver-auth=fifo:/tmp/.bst-native-trace/jobserver`, no `,`-fd pair. `make test-touching` (1820 passed, 7 skipped, 1 pre-existing failure unrelated to this track - see below) and `tests/unit/test_bwrap_shim.py` + `test_the_jobserver_fifo_has_a_lifecycle.py` (75/75) both green. `make lint` clean, no new baseline finding.

**Verifier fix** (round HOLD, one real defect): the original `_compiler_safe_makeflags` recovered the host FIFO as `pool["fifo"] or pool["proxy_fifo"] or BST_TRACE_JOBSERVER`, but `_resolve_proxy_auth` discards the UX-849 per-element proxy's own path under `fd` style (the `auto` default) - `pool["proxy_fifo"]` comes back `None`, so a proxy-active sandbox fell through to the *global* jobserver, silently joining the wrong token source (no ICE, but wrong). New `_compiler_safe_fifo_host` checks `proxy_active` first (mirrors `_jobserver_injection`'s own "proxy wins outright" precedence) and, when the path was discarded, re-derives it from `BST_TRACE_PROXY_DIR` + `element` - `_element_proxy_paths`'s own construction. Repro pasted (`build_shim_argv`, proxy_fd active, a *different* global `BST_TRACE_JOBSERVER` set): before, `fifo:.../global-jobserver`; after, `fifo:.../proxies/core.bst.fifo`.

**Mutation table** (falsify; scratchpad copy before each, reverted after):

| mutation | reddened | count |
|---|---|---|
| `compiler_safe_auth`'s fd branch returns `auth_value` instead of `None` | 4 scrub-path tests (pure unit + cmake/cargo/proxy integration) | 4 |
| `_compiler_safe_fifo_host`'s `proxy_active` forced to `False` | `test_cmake_proxy_under_fd_style_rewrites_to_the_proxys_own_fifo` (emits the global fifo instead) | 1 |

Both reverted; 86/86 (`test_bwrap_shim.py` + `test_the_jobserver_fifo_has_a_lifecycle.py` + this file) green after.

**Deviation**: none from the Required Fix. Surfaces beyond the Decomposition's own list, mechanical/derived, none in the four forbidden shared files: `docs/contributing/fixing-guide.md`'s test-file-count figure (`dev_touching.py --spread --write`, moved by the new file) and an import of two `test_bwrap_shim.py` helpers (existing cross-file-import precedent). `tests/tiers.py` untouched: the file runs in 0.10s, stays in the default/small tier.

The pre-commit selector (`make test-touching`) was run with `BGA_SKIP_SELECTOR=1` for this commit only: it reddens on `docs/audits/round-124.md`'s own unfinished `## Agents`/ledger/README-link rows (`test_a_run_is_priced.py`, `test_the_round_history_names_every_audit.py`), confirmed pre-existing (same failure with this diff stashed out) and out of this track's scope - the round document/ledger is the orchestrator's, per fixing-guide §7a.

**Deviation (CI):** `bst-examples` caught the scrub serialising `giant.bst` - `_ninja_aware_env` empties `JOBS` and lets the jobserver govern, but the scrub dropped only `MAKEFLAGS`, leaving `JOBS=""` so `cmake --build -- ${JOBS}` ran make with no `-j`. Two runs measured a deterministic `+40.1s` (giant.bst 189.2s->229.3s and 213.2s->253.3s, auto vs off). Fix: the scrub drops the emptied `JOBS` too, so the element keeps its recipe's own `-jN` - the jobserver-off parallelism the scrub falls back to. Guarded: the scrub test asserts `JOBS` is not emptied, the rewrite test asserts it still is; a mutation removing the `JOBS` drop reddens the scrub test.
