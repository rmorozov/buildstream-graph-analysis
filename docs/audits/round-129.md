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
