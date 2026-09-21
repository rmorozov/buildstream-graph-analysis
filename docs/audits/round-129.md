# Round 129 — the four deferred rows: LTO on make, the lint gate, the flake, the brief

Run on 2026-09-17, after round 128 merged. In progress: this document
is the round's running record, opened with the pull request so CI
collects on the branch from the first commit, and closed with the round.

## The premise

Four rows filed across rounds 125–127 and deferred, all Medium, no new
field report behind them — the round clears the backlog's standing work
rather than chasing an incident. Two are pipeline hardening the session's
own tooling wants (a lint gate, a flake), one is a brief footgun the last
round hit twice, and one is an unproven exclusion in the jobserver policy
that only a measurement can settle.

- **UX-886** — `test_sigkilled_holder_is_refilled_and_named` hinges on a
  fixed 2s window for a SIGKILL to reap and `audit_leaks` to settle; CI's
  3.11 shard reddened on it while the other three passed the same sha
  (round 125). A real timing flake in the guard, not a defect in
  `audit_leaks`. Make it poll for the reap, bounded, so the refill+naming
  claim gates and the wall-clock does not.
- **UX-885** — the push gate covers `make test` (writes `.gate-covered`)
  but not `make lint`; round 125 pushed a blob a local lint passed and
  CI's pinned PyMarkdown reddened, skipping the whole test matrix. Fold
  `make lint` into the gate, on the **same pinned** versions CI runs.
- **UX-887** — the `implementer` brief tells a track to
  `pip install -e '.[dev]'` when dev deps are missing, which from a
  worktree repoints the shared editable `bga` install (the round-109
  failure mode). Fix the brief guidance; add a cheap pre-gate check where
  one fits.
- **UX-884** — `_COMPILER_SAFE_POLICIES` excludes `make` on the theory
  its MAKEFLAGS consumer is `make` itself (a valid direct-child fd). But a
  `make`/autotools recipe that *also* drives GCC LTO spawns `lto-wrapper`,
  a grandchild — the same fd ICE UX-878 fixed for cmake. Unproven either
  way; step 0 is a `make`-kind LTO measurement, then a shim or a
  won't-fix with the evidence.

## Plan

| wave | rows | shape | who |
|---|---|---|---|
| track | `UX-886` | bounded | `implementer` on `sonnet`, in a worktree — the guard's timing rewrite + a flake-ledger row |
| session | `UX-885` | judgement (process surface) | the gate/hook wiring is the session's own tooling; a broken gate blocks every push |
| session | `UX-887` | judgement | the fix is partly to the brief the session writes |
| session | `UX-884` | judgement | measurement-first; the fix is unknown until the ICE reproduces or refutes |

The track's surface (`test_a_leaked_token_is_refilled.py` + the flake
ledger) is disjoint from the three session rows. The four shared
merge-hotspot files the decompose skill names are the session's to
resolve once at close.

## What closed

Three of the four rows; `UX-884` stays open (below).

- **UX-886** (implementer track): `test_sigkilled_holder_is_refilled_and_named`
  now polls a 10s bounded retry (returning as soon as `_readable(fd) ==
  4`) instead of a fixed 2s window, so its refill+naming claim gates and
  the audit thread's ~1s cycle no longer reddens a loaded runner. The
  stale class name `…WithinTwoSeconds` was dropped at merge.
- **UX-885**: `test: lint` in the `Makefile` — `.gate-covered` is written
  only when lint (ruff, PyMarkdown, baseline) and the suite both pass.
  Guard `test_the_push_gate_includes_lint.py` reads the gate's own recipe
  through `make -n test`.
- **UX-887**: `tools/dev_env_check.py` (guard
  `test_the_env_check_catches_a_repoint.py`) catches a worktree-repointed
  `bga` or a shadowed non-pinned `ruff` before a merge gate;
  `implementer.md`/`verifier.md` now name the pinned-`ruff` PATH trap.
  Live-confirmed: the tool caught this machine's stale `ruff 0.15.8`.

- **UX-884** (held open): the measurement is in the task file — a
  `make`-kind LTO element gets a raw fd unprotected, but the ICE is
  confined to make < 4.4 + gcc ≥ 13 `-flto` (make ≥ 4.4 resolves to
  `fifo:`, which lto-wrapper opens). No field report; the fix (the flto
  shim for `make`) re-risks round 126's minimal-sandbox breakage, so it
  waits for a field report.

## The verifiers found

UX-886 (the round's one track) was read by a `verifier` on `sonnet`
after merge — verdict in the ledger row below. The session verified it
independently too (guard green, the refill mutation in `audit_leaks`
reddens `test_sigkilled_holder_is_refilled_and_named` at `assert 2 ==
4`, reverted green). UX-885 and UX-887 are the session's own; each new
guard was falsified (drop the `lint` prerequisite → 4 red; drop the
worktree exclusion → the round-109 case reddens).

## Agents

| round | agent | model | task | tokens | tool calls | wall | outcome | what cost the most / what went wrong |
|---|---|---|---|---|---|---|---|---|
| 129 | implementer | sonnet | UX-886 (implementer) | 38k | 22 | ~5 m | merged: 2s deadline → 10s bounded retry, refill+naming unchanged | worktree two commits behind the base, one extra `checkout -B`; no harness wall-clock |
| 129 | verifier | sonnet | UX-886 (verifier) | 44k | 24 | 3.6 m | PASS: early return unloaded, refill-skip mutation reddens, revert green | a dirty close-window worktree makes "what does HEAD contain" ambiguous |

UX-885 and UX-887 were the session's own (judgement / process surface),
committed and self-verified in place — no track, so no row here.

## The gate

| run | head | result |
|---|---|---|
| 0 | the filing | red only on the round-open bootstrap guards; docs-only |

## Standing

Three deferred rows cleared, one held with its measurement. The pipeline
gained two guards it wanted: a lint-inclusive gate (a lint-red tree can
no longer cover a pushable sha) and an env check that names the two
footguns round 127's tracks hit. The token-refill guard is deterministic
now. `UX-884` is the round's one open remainder — characterized, not
built, awaiting a make < 4.4 + gcc ≥ 13 LTO field report.
