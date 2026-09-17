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

| row | what landed |
|---|---|
| `UX-880` | a `flto` per-element auth-override style + a reference GCC-driver shim (`gcc`/`g++`/`cc`/`c++`). A `flto`-matched element keeps the raw `fd` auth for `make` (the compile phase still fills the pool, unlike `off`) and gets `--setenv BST_TRACE_FLTO_ACTIVE 1`; the shim, gated on that flag, strips `--jobserver-auth` from the compiler's `MAKEFLAGS` and rewrites an already-present `-flto` to a static `-flto=$BST_TRACE_LTO_CAP` (default the pool ceiling) — never introducing LTO where the recipe had none. So a forced-`fd` LTO element fills the box without the GCC-13 lto-wrapper ICE, and it is not sent through the UX-878 sub-4.4 scrub. `--lto-cap N` sets the cap |
| `UX-883` | a `bga capture run` preflight warning, one de-duplicated line per element that is both on a sub-4.4 sandbox make and a compiler-driving kind (`_COMPILER_SAFE_POLICIES`), naming the element and the make-4.4/`fd`/`flto` remedy. Reads the per-element make probe UX-874/878 already cached, never re-probes; advisory, the scrub is unchanged |

## The verifiers found

- `UX-880`: **HOLD, then PASS.** The first cut mounted the four GCC-driver
  shims in the shared wrapper dir with no per-element gate, so an
  *unmatched* make≥4.4 element on the UX-878 fifo path had its auth
  stripped and `-flto` pinned too — a static-cap regression that would
  oversubscribe a multi-builder box, and the "unmatched" guard used a
  `cmake`/4.3 combo the pre-existing scrub already excludes (it would pass
  with the bug). Fixed with the per-element `BST_TRACE_FLTO_ACTIVE` flag
  and a guard on the real leak path (a `make`-kind element that mounts the
  dir but is not flto-matched). Re-verified: the leak is closed (unmatched
  = pure pass-through, reproduced), both mutations redden, lint clean.
- `UX-883`: **PASS.** The warning gates on exactly the scrub condition
  (`_COMPILER_SAFE_POLICIES` + sub-4.4 make), byte-for-byte mirroring
  `_compiler_safe_makeflags`; both mutations reproduced; probe read, not
  re-run. Deviation: the Required Fix's "suppressible with a quiet flag"
  clause has no flag to hook in the tracer's argparse, so it prints
  unconditionally to stderr — consistent with the file's own precedent.

## Agents

Two `implementer` tracks and two `verifier` reads, all on `sonnet`; each
row HELD once and resumed (UX-880 for the scoping leak, its verifier
re-checking the fix; UX-883's implementer clean, its verifier PASS
first pass). A `researcher` read (the shim/wrapper-mount map) ran before
the filing — the session's own context, not a priced track (round-125's
convention).

| role | runs | tokens | calls | minutes |
|---|---|---|---|---|
| implementer | 2 | 689k | 358 | 54 m |
| verifier | 2 | 213k | 82 | 22 m |

## The gate

| run | head | result |
|---|---|---|
| 0 | `986ffdfb` (the filing) | red only on the round-open bootstrap guards (`test_a_run_is_priced` — the Agents/ledger/register rows this close fills); docs-only |
| 1 | the close | the run this commit is pushed under; the pull request carries the figure |

## Standing

The graded response to the GCC-13 LTO ICE is now three levers: UX-878's
`auto` normalizes the injected auth at source (fd→fifo on make≥4.4, else
scrub); UX-879's `--jobserver-auth-override` forces `fd`/`fifo`/`off` per
element; and UX-880's `flto` fills a forced-`fd` LTO element's box via a
static `-flto=N` shim without the ICE — the caveat round 125 documented is
closed for a PATH-reachable GCC driver. UX-883 names the element the
make-4.4 migration would unblock, so the operator is not left to hit the
ICE to learn it. Left standing for a later round: `--wrapper-dir` so the
shim reaches a custom-prefix in-sandbox compiler (`UX-881`); the
`public: bga.jobserver-auth` version-controlled surface (`UX-882`); the
make/autotools LTO scrub gap, which needs a make-kind LTO measurement
first (`UX-884`); and two process rows — `make lint` in the push gate
(`UX-885`) and the token-refill guard's 2s timing flake (`UX-886`).
