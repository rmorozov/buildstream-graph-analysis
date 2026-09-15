# Round 120 — a 16-core field capture: the pool that never grew, the recipes that never joined, and six things the page got wrong

Run on 2026-09-15, after round 119 merged. In progress: this document
is the round's running record, opened with the pull request so CI
collects on the branch from the first commit, and closed with the round.

## The premise

The user ran the merged tool on a 16-core, 32 GB host with `--builders
16 --jobserver auto` on a project where llvm sits on the critical path,
and read eight things off the page. Four `researcher` reads on `sonnet`
ground-truthed each against the code before anything was filed: the
pool opened with a ceiling of 1 and could never grow (`resolve_jobserver_
ceiling` conflates the seed with the ceiling; `_handle_underload` never
passes `pool < ceiling - 1` at 0); manual-kind recipes spending `JOBS`
fall through `kind_job_env` as `unknown_kind`; swap is sampled and
folded into a verdict but never published or found; the capacity
recommendation's CPU constraint is unclamped (the fixture recommends 16
on 8 cores); `main table { display: block }` beats `[hidden]`; the
density strip ticks p50 and p95 only; the section renderer never
classifies an object value; the hook drops relative opens.

## Plan

| wave | rows | why |
|---|---|---|
| 1 | `UX-858` `UX-859` `UX-862` `UX-863` `UX-864` `UX-865` | mechanical, disjoint surfaces: the ceiling and seed, the `JOBS` env join, the twin's CSS, the strip's ticks, the map table, the hook's cwd |
| 2 | `UX-860` `UX-861` | judgement: a schema column and a finding each - the session's own |

## What closed

(in progress)

## Agents

no agents launched at this commit: the tracks start after the pull
request opens, and their rows land in the ledger as they finish.
