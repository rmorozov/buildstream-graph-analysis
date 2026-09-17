# UX-880: a compiler-LTO shim fills the box without the gcc-13 ICE

**Priority:** High | **Status:** 🟡 In Progress | **Depends on:** UX-878, UX-879 | **Found by:** round 125's Standing + the user (a pinned ≤4.2.1 element that *does* LTO on the cross-gcc-13 still ICEs under a forced `fd` — round 125's documented caveat) | **Serves:** R2 (an element that does GCC LTO fills the pool under the jobserver without crashing lto-wrapper) | **Topic:** capture | **Area:** tools-native_trace | **Shape:** bounded

## Motivation

UX-879 lets the operator force `fd` on a pinned ≤4.2.1 element so it fills
the pool. But an element that does **GCC LTO** under a forced `fd` still
hits the round-124 ICE: `make` passes `--jobserver-auth=R,W` in
`MAKEFLAGS`, the compiler driver is a grandchild across bwrap, and at the
LTO link `collect2` → `lto-wrapper` reads `MAKEFLAGS`, sees the raw fd,
tries to open it (not open in this process) → `internal compiler error:
get_token, at opts-common.cc:2123` (measured, GCC 13). UX-878's auto path
*scrubs* to avoid this, but a forced `fd` bypasses the scrub by design —
that is the whole point of the force, and the caveat round 125 documents
("use `fd` for non-LTO ≤4.2.1 elements, `off` for LTO ones meanwhile").

The mechanism that would fill an LTO element's box without the ICE cannot
be the token-acquiring wrapper the linkers use (`bga_run_wrapped`): a
grandchild across bwrap cannot open the raw fd to acquire from it. It can
only **strip** the unusable auth (so lto-wrapper never touches the fd) and
pass a **static** parallelism cap — `-flto=N` — that GCC's lto-wrapper
honours directly. That is exactly a PATH-shadow shim over the GCC driver.

(clang/LLVM ThinLTO is *already* covered: its link parallelism is
`ld.lld --thinlto-jobs`, and `ld.lld` is a `threads`-style wrapped tool.
The gap is GCC's driver, which reads `MAKEFLAGS` and is unwrapped.)

## Required Fix

A new per-element auth-override style **`flto`** (extending UX-879's
`--jobserver-auth-override 'fd:… fifo:… off:… flto:…'`) that:

- keeps the **`fd`** jobserver auth for `make` itself (so the compile
  phase still fills the pool, unlike `off`), and
- mounts a **reference compiler-LTO shim** over the GCC driver names
  (`gcc`, `g++`, `cc`, `c++`) that: (a) removes `--jobserver-auth=…` from
  the `MAKEFLAGS` it hands the real compiler (no fd → no ICE), and (b)
  **only when `-flto` is already present** in the argv, rewrites it to
  `-flto=N` where `N = $BST_TRACE_LTO_CAP` (default = the pool ceiling,
  `os.cpu_count()`); a non-LTO invocation is passed through untouched so
  the shim never *introduces* LTO.
- A `flto`-matched element is **not** sent through the UX-878 sub-4.4
  scrub — the shim, not the scrub, is what keeps it safe ("don't scrub
  when shim-covered").

Surfaces: `tools/native_trace/wrappers/_common.sh` (new `flto` branch in
`bga_run_wrapped`'s `case`, and the auth-strip), a new reference shim
script under `tools/native_trace/wrappers/`, `_AUTH_OVERRIDE_STYLES` +
`_forced_auth` + `_jobserver_injection` in `bwrap_shim.py` (the `flto`
branch: raw fd + shim mount + no scrub), `bga/cli.py` (accept `flto:` in
`--jobserver-auth-override`), `tools/bst_native_build_tracer.py`
(`BST_TRACE_LTO_CAP` passthrough), `docs/guides/cli.md` (§3.10 env +
flag), the contract note the user's own shim must satisfy.

## Decomposition

surfaces: `tools/native_trace/wrappers/_common.sh` (flto branch + strip) · new `tools/native_trace/wrappers/<gcc-driver-shim>` · `bwrap_shim.py` (`_AUTH_OVERRIDE_STYLES`, `_forced_auth`, `_jobserver_injection` flto branch, don't-scrub) · `bga/cli.py` (`--jobserver-auth-override` flto style + `--lto-cap`) · `tools/bst_native_build_tracer.py` (`BST_TRACE_LTO_CAP`) · `docs/guides/cli.md` (§3.10)
guards: `test_a_compiler_lto_shim_fills_the_box.py` (new): the shim script run under `sh` strips auth + rewrites `-flto`→`-flto=N` only when present (reuses UX-846's real-script-under-sh harness); the `_jobserver_injection` flto branch emits the fd auth + the wrapper mount + no scrub (reuses UX-878/879 harness)
gap: custom-prefix compilers are not PATH-reachable — the reference shim covers the standard driver names only; the operator's own shim for a custom prefix needs `--wrapper-dir` (UX-881, filed)
track: bounded `implementer` on `sonnet` (surfaces + guard + mutation are named); the shim contract is fully specified in Required Fix, so no design judgement is left open; parallel with UX-883 (shares only `bga/cli.py`'s capture-run entry, merge-additive)
gate: batch PR (round 126)

Input classes: `flto`-matched element with `-flto` in argv → `-flto=N`
emitted, auth stripped, no ICE; `flto`-matched with no `-flto` → passed
through untouched (never introduces LTO); make still gets the raw fd (pool
fill on compiles); a `flto`-matched element on sub-4.4 make is **not**
scrubbed (shim-covered); unmatched element → auto (UX-878, the anchor).

## Out of Scope

The `--wrapper-dir` override for a user's own shim (UX-881). The `public:`
annotation surface (UX-882). The make/autotools LTO scrub gap (UX-884).
clang/LLVM ThinLTO (already covered by the `ld.lld` wrapper). Changing the
`auto` default (UX-876 stays). Dynamically acquiring tokens in the shim
(impossible across bwrap for a raw fd — the static cap is the design).

## Acceptance Test

`tests/unit/` new file: (1) the reference shim script run under `sh` with
`MAKEFLAGS='--jobserver-auth=3,4 -j8'` and argv containing `-flto` emits
the real compiler with `-flto=<cap>` and a `MAKEFLAGS` that has no
`--jobserver-auth`; the same shim with no `-flto` in argv passes argv
through unchanged and still strips the auth. (2) Through `build_shim_argv`
with `BST_TRACE_JOBSERVER_AUTH_MAP='flto:llvm*'` and a make-4.3 fixture, a
`llvm`-named element emits the raw `--jobserver-auth=<fd,fd>` (make fills
the pool), the wrapper directory bind-mount, and is **not** scrubbed —
where an unmatched element on the same 4.3 make *is* scrubbed (UX-878).
Mutation: make the `flto` branch fall through to `off` (scrub) — the
"make keeps fd" and "not scrubbed" assertions redden.

## Outcome

_(filled at close)_
