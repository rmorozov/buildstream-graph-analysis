# Round 124 — the LTO link survives the jobserver

Run on 2026-09-16, after round 123 merged. In progress: this document
is the round's running record, opened with the pull request so CI
collects on the branch from the first commit, and closed with the round.

## The premise

With round 123's `--jobserver auto → fd` in hand, the user ran a
`kind: cmake` element building ninja 1.10.2 with a relocatable GCC-13
cross toolchain (glibc 2.17, invoked by absolute path with a custom
triple; they build a stack of such toolchains in-sandbox, gcc-13 →
modern LLVM → everything else). The `ninja_test` LTO link crashed:
`internal compiler error: get_token, at opts-common.cc:2123`,
`lto_main`, `lto-wrapper failed`. Control: with the jobserver off the
same build succeeds; with it on it ICEs. bga injects a make jobserver
into the sandbox `MAKEFLAGS`; wrapped tools (ninja, ld.*, mold) convert
it to a static `-jN`, but `gcc -flto`/`lto-wrapper` and cargo are
unwrapped and read `MAKEFLAGS` directly. For `fd`-style auth the fd is
not valid inside the sandbox for the deep grandchild that is gcc's
lto-wrapper, so it reads garbage and aborts.

A PATH-shadow wrapper cannot fix this — the compiler is invoked by
absolute path with a custom triple, and `MAKEFLAGS` is inherited
whatever the compiler's name or path. The one channel bga owns that
reaches every consumer is the injected `MAKEFLAGS` auth string itself,
so the fix is toolchain-agnostic by construction.

## Plan

| wave | rows | why |
|---|---|---|
| 1 | `UX-878` | one file's injection policy (`bwrap_shim.py`) plus one new guard |

One row filed.

## What closed

| row | what landed |
|---|---|
| `UX-878` | the injected jobserver auth is normalized at the one channel that reaches an absolute-path, custom-prefix compiler — the sandbox `MAKEFLAGS`. For the kinds whose auth an unwrapped native client reads (`cmake`/`meson`/`jobs_env`, cargo), `compiler_safe_auth` rewrites an `fd` auth to `fifo:<path>` (gcc-13 and modern LLVM reopen the bind-mounted path in-sandbox; a raw fd does not survive the boundary) or, when a sub-4.4 make shares the string, scrubs it (serial, never an ICE). Takes precedence over UX-874's `fifo→fd` downgrade for those kinds. `_compiler_safe_fifo_host` targets the element's own per-element proxy FIFO, not the global one. Pure `make`/`autotools` keep raw `fd` (their consumer is make itself, a direct child) |

## The verifiers found

- `UX-878`: HOLD, then PASS. The HOLD was real and would have hit the
  field: for a UX-849 per-element proxy under the default `fd` style,
  `pool["proxy_fifo"]` is `None` (the path is discarded when the fd is
  opened), so the rewrite fell back to the *global* jobserver path and
  silently named the wrong FIFO — no ICE, but the wrong token source.
  The fix re-derives the element's own proxy FIFO
  (`BST_TRACE_PROXY_DIR` + element) and a new proxy input class guards
  it. On PASS: 11 tests, both mutations (the scrub branch and the
  proxy-host resolution) reddened their tests, no UX-874 regression
  (75/75), scope and derived count clean.

## Agents

2 runs priced, one `implementer` track and one `verifier` read, both
on `sonnet`; the track was resumed once for the proxy fix and the
verifier once to re-check it. A `researcher` (the jobserver plumbing)
and a `Plan` read (the interception mechanism) ran before the filing;
their reads are the session's own context, not priced tracks.

| role | runs | tokens | calls | minutes |
|---|---|---|---|---|
| implementer | 1 | 464k | 172 | 44 m |
| verifier | 1 | 214k | 78 | 23 m |

## The gate

| run | head | result |
|---|---|---|
| 0 | `4bc02b33` (the filing) | red only on the round-open bootstrap guards (Agents/ledger/register empty, README link) and an upstream `platformdirs` lock drift; docs-only |
| 1 | the close | the run this commit is pushed under; the pull request carries the figure |

## Standing

The box has no cross toolchain and cannot build a real cmake+LTO
element, so the guard drives the auth-form decision through
`build_shim_argv` and a fake sandbox make — the same instrument
rounds 122–123 used. On the user's host, `bga snapshot` now hands a
gcc-lto-driving element a path-based `fifo:` auth its GCC-13 (or modern
LLVM) reopens inside the sandbox, or nothing when a sub-4.4 make shares
the recipe — never a raw fd the compiler's lto-wrapper aborts on. The
`requirements.lock` was refreshed (`platformdirs` 4.11.9) to clear the
pip-audit freshness check. Left standing: the fix assumes a gcc-lto
consumer supports the `fifo:` style (GCC-13 and LLVM ≥19 do); a
toolchain that reads `MAKEFLAGS` but supports neither `fifo` nor a
sandbox-valid fd would get a clean rejection, not an ICE, and would be
the next field signal.
