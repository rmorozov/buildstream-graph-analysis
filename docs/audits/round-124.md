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
| `UX-878` | (filled at close) |

## The verifiers found

(filled at close)

## Agents

(filled at close)

## The gate

(filled at close)

## Standing

(filled at close)
