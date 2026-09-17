# Round 126 — a compiler-LTO shim, and the slate around it

Run on 2026-09-17, after round 125 merged. In progress: this document
is the round's running record, opened with the pull request so CI
collects on the branch from the first commit, and closed with the round.

## The premise

Round 125 gave the operator a per-element `--jobserver-auth-override`:
force `fd` on a pinned ≤4.2.1 element so it fills the pool, `off` on a
known-LTO one. But it left a caveat standing: an element that *does* GCC
LTO under a forced `fd` still ICEs on the cross-gcc-13 — `make` passes
`--jobserver-auth=R,W` in `MAKEFLAGS`, the compiler driver is a grandchild
across bwrap, and at the LTO link `lto-wrapper` reads the raw fd it cannot
open (`opts-common.cc:2123`, measured). The operator's only move for such
an element was `off` — which caps it at recipe `-jN`, the crawl round 124
set out to fix.

The mechanism to fill an LTO element's box without the ICE cannot be the
token-acquiring wrapper the linkers use: a grandchild across bwrap cannot
open the raw fd to acquire from it. It can only **strip** the unusable
auth (so `lto-wrapper` never touches the fd) and pass a **static**
`-flto=N` cap that GCC honours directly — a PATH-shadow shim over the GCC
driver. (clang/LLVM ThinLTO is already covered: its link parallelism is
`ld.lld --thinlto-jobs`, and `ld.lld` is a wrapped tool.)

## Plan

| wave | rows | why |
|---|---|---|
| build | `UX-880` | the `flto` override style + a reference compiler-LTO shim (keep `fd` for make → compiles fill the pool; strip auth + static `-flto=N` for the GCC driver → LTO link fills without the ICE; don't scrub when shim-covered) |
| build | `UX-883` | a preflight warning naming the LTO-on-sub-4.4-make element and its clean remedy (move to make ≥4.4 for fifo pool-fill) |
| file | `UX-881` `UX-882` `UX-884` | the `--wrapper-dir` override for a custom-prefix toolchain; the `public: bga.jobserver-auth` version-controlled surface; the make/autotools LTO scrub gap (needs a measurement first) |
| file | `UX-885` `UX-886` | process: the push gate runs `make lint` too; the token-refill guard's 2s timing flake |

Two rows built as bounded `implementer` tracks (the shim contract is
fully specified in `UX-880`'s Required Fix, so no design judgement is
left open); five filed for later rounds. The custom-prefix delivery
(`UX-881`, `UX-882`) is what makes the shim reach the user's real
in-sandbox toolchains — filed, not built, this round.

## What closed

_(filled at close)_

## The verifiers found

_(filled at close)_

## Agents

_(filled at close)_

## The gate

| run | head | result |
|---|---|---|
| 0 | the filing | red only on the round-open bootstrap guards; docs-only |

## Standing

_(filled at close)_
