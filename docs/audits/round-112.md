# Round 112 — the last three open tasks, and what pricing them turned up

Run on 2026-09-12.

Round 111 left three open rows: the max-jobs advice unpriced (`UX-739`),
the jobserver spike (`UX-679`), and `UX-689`'s remaining chapters. This
round took all three the same way as the last — every track an
`implementer` on `sonnet` in a worktree, every merge behind a
`verifier` — after one probe the session ran itself: a cold two-plane
snapshot of `examples/06` on this machine, 52 s wall, which is the
capture every number below is pasted from.

## What closed

- `UX-807` — filed and closed: the projection chapter (57 lines) into `docs/design/areas/bga-replay.md`, the third area. One paragraph stayed behind, because `test_the_whatif_convention_is_one_claim.py` reads "never a sum" and the freedesktop-sdk table from the chapter itself; the verifier's own line-by-line diff found 0 sentences missing.
- `UX-808` — filed and closed: the advice listed one row per task, not per element. The probe's cold build had a FETCH task beside every BUILD task, so 22 rows for 11 elements, and a fetching element counted as building. BUILD tasks only now: 11 rows.
- `UX-739` — the max-jobs advice priced by replay. The judgement was taken in the brief: two replays of the run under Part 18's LPT rule, each lowered element's build floored at `max(observed, cpu / recommended)` from Plane 2's own CPU, published as a **floor** that errs optimistic, a raise refused, the joint figure a recompute and never a sum. On the probe: `codegen.bst` 4 → 1 costs 0 (slack absorbs it), the six lowered elements together +0.9 s on 29.6 s.
- `UX-679` — the jobserver every sandbox joins, as a spike: `bga capture run --jobserver N` opens a FIFO, writes N−1 tokens, and the shim hands the fd into the sandbox through `--setenv MAKEFLAGS --jobserver-auth=fd,fd` — bwrap passes inherited fds, and the sandbox's make 4.3 speaks only that style. On `examples/06`, the under-utilised share fell 0.857 → 0.214 at an unchanged wall (30.25 → 30.46 s). **Decision:** not a mode yet; the wall is what R4 and R5 buy on, and this project's critical path is its declared chain. The flag stays, off by default.

Filed: `UX-807`, `UX-808`.

## In progress

`UX-689`: three areas landed (viewer, Plane 2, projection). The next
chapter is Plane 3 (`architecture.md:163`), its own item when filed.

## What the verifiers found

Three verifier runs, three PASS — each with a finding the track's table
could not see:

- `UX-807`: an independent sentence diff; the verifier's own script double-rebased a link before it matched, the track's diff was right.
- `UX-679`: all four headline figures reproduced from the kept runs; the tracer's FIFO lifecycle (created and removed only under the flag) has no guard — the verifier's mutation passed the tracer's suite unchanged. Recorded in the Outcome as the guard that comes with the mode, if it becomes one. The size ledger had grown without a row move; adopted at the close.
- `UX-808`/`UX-739`: every figure reproduced from the probe capture, the live mutation (lib-f.bst 1 → 2) moving the projected makespan; two findings: the assumption sentences are on the payload and in the guide, not in the text (the Outcome's wording corrected), and dropping the `task is None` clause raised `AttributeError` — a refusal by name and a guard, added by the session before the close.

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

- The session's own probe found `UX-808` before any track ran; the price track then priced the corrected rows. A probe capture before decomposition is cheaper than a track discovering the fixture is wrong.
- The selector reddened the session's first close on a filing gap (`UX-808` had no `## Decomposition` block, required past `UX-690` for analysis filings); the price track hit the same red mid-work and had to be told. The block belongs in the filing step, before tracks are dispatched.
- Every track ran the CLI from its worktree by `PYTHONPATH`, because `bga` on PATH is the main checkout's editable install — a brief line that saved three tracks from measuring the wrong tree.
- `UX-679`'s capture help had zero headroom in `test_help_is_short.py`'s cap (45 of 45 lines); a fifteenth flag moved it to 47, stated in the Deviation.
- The size ledger adopted once, after the last merge, before the gate.

## Agents

Six runs — 3 `implementer`, 3 `verifier`, all on `sonnet`. Two tracks
were judgement-shaped; the session took the judgement in the brief and
the track the work.

| | |
|---|---|
| implementer | 3 tracks, every one merged behind a verifier; 98k, 254k, 287k tokens; 16, 36, 40 m |
| verifier | 3 runs, three PASS, each with a finding the track's table could not see; 63k, 90k, 108k tokens; 9, 11, 16 m |
