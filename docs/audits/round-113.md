# Round 113 — the two rows left, and the shelf's pull requests unblocked

Run on 2026-09-12.

Round 112 left two open rows — `UX-689`'s next chapter and `UX-809` —
and two Dependabot pull requests (#216, #217) red since 2026-09-08.
This round took the rows as tracks behind verifiers, and the pull
requests as what they were: one gate reading a body the register
never governed.

## What closed

- `UX-810` — filed and closed: the Plane 3 chapter (46 lines) into `docs/design/areas/tools.md`, the tools area's own page with the chapter as its first section. No guard reads inside the chapter — the track blanked it and re-ran the 21 guard files to prove it, 437 both ways — so the whole chapter moved; the verifier reproduced the blank-and-rerun.
- `UX-809` — the price's two assumption sentences, rendered under the joint line byte-for-byte from the payload, only when a row is priced. The verifier's own mutation found one of the three guard classes inert: the no-advice case is absorbed by the helper's older short-circuit; the refusals-only test is the one that discriminates. Recorded in the Outcome.
- `UX-811` — filed and closed on PR #217's red: Dependabot's 75-line generated body reddened `UX-696`'s commit-body gate on every shelf pull request, so the shelf could never merge. The tool skips a GitHub App's commit (`[bot]@users.noreply.github.com`) and counts it in its sentence; a person with the same body still reds. Session-side.

- `UX-812` — filed and closed after the gate reddened on it a second time: the impact guard asked the backlog for an open analysis row; it now reads the tool on a synthetic index and agrees with an independent parse of the real one, empty included.
- `UX-813` and `UX-814` — review 22's two filings, closed in-round: the history guard's bullet walk counted `UX-695` twice and never saw `UX-806`, an over-count and an omission cancelling to round 111's sixteen; §6's `dev_commit_bodies.py` row was behind `UX-811`.

Filed: `UX-810`, `UX-811`, `UX-812`, `UX-813`, `UX-814`.

## Review 22

The cadence guard came due at 27 closes since review 21. One reader
over the five groups rounds 111 to 113 touched: every guarded count
reproduces (the contract inventory, 22 modules, 263 keys, the advisory,
the capture flags); the two findings are the same shape review 20
named, one turn further — a record a guard *does* read, with the
guard's population narrower or self-cancelling than the sentence. The
entry is in `docs/audits/architecture-review.md`.

## The shelf's pull requests

PR #217 (six action bumps) and PR #216 (ruff 0.15.8 → 0.16.6, pyright
1.1.408 → 1.1.411) were red on `test (3.x)`: #217 on the commit body,
#216 on `make lint` at a base 158 commits old. Each branch got main
merged in, `UX-811`'s tool and tests ported (three files — the filing's
index hunks conflict), and #216 its lock recompiled with the bumped
pins and the baseline's `ruff_version` refreshed. The new ruff and
pyright read today's tree differently: two new findings (`S103` on the
shim's world-executable chmod, `reportOptionalOperand` on a delta
format) and one stale row — fixed and shrunk on the branch, not
baselined (`UX-693`'s rule). Each
was gated in its own worktree (8,287 passed, 13 min under the round's
load) and pushed. PR #217's `sizes` job then reddened on the ported
tool's growth — that job is not in `make test` — so both branches
adopted the ledger and were gated again.

## In progress

`UX-689`: four areas landed (viewer, Plane 2, projection, Plane 3). The
next chapter is "Joining the planes" (`architecture.md:209`), the `bga`
area, its own item when filed.

## What the verifiers found

Two verifier runs, two PASS, one with a finding the track's table could
not see (`UX-809`'s inert class). `UX-811` had no verifier: PR #217's
own `test (3.x)` is the check that names it; `UX-812` to `UX-814` were
session-side, each a guard mutated red before the close.

## Standing

The suite's shape, derived by `dev_shape_budget.py` and printed by
`dev_close_task.py --check` (`UX-690`):

```text
shape         files   CI seconds    share
unit            452       821.1s    48.1%
sweep             1         2.1s     0.1%
journey           2         0.1s     0.0%
browser          53       845.2s    49.5%
enormous         20        39.3s     2.3%
total           528      1708.0s
```

## Process, measured

- The push hook reads the main checkout's HEAD, not the branch being pushed: a branch gated in a worktree pushes only after the gated commit is checked out in the main checkout with the worktree's gate record beside it. Two pushes each took that detour; the hook's model is one checkout.
- No pre-commit hook fires in a worktree; both tracks ran the touching sweep by hand after committing, as the brief told them to. A brief line that assumes the hook would have skipped it.
- Gates ran 13 minutes with two of them and two tracks on four cores, against 6 quiet.
- The `sizes` job is CI-only: a gate can be green on a commit the job reds. Adopt before the push, not after the red.
- A verifier's second mutation (render unconditionally) is what found the inert class; the track's own table stopped at the mutation the task named.
- The round's gate reddened twice on the same guard as round 112's (an emptied topic) and once on the review cadence; the first is fixed at the guard (`UX-812`), the second ran review 22.

## Agents

Five runs — 2 `implementer`, 2 `verifier`, 1 `researcher` (review 22),
all on `sonnet`. Both tracks were mechanical or bounded; `UX-811` to
`UX-814` were the session's.

| | |
|---|---|
| implementer | 2 tracks, both merged behind a verifier; 85k and 111k tokens; 14 and 21 m |
| verifier | 2 runs, two PASS; 59k and 59k tokens; 10 and 12 m |
| researcher | review 22; 175k tokens, 13 m; two filings |
