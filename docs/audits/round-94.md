# Process round 94: the pipeline, and which model runs which shape

Run on 2026-09-05, after round 93. A process round. The user asked
to review the decomposition and implementation workflow once more and
find where a simpler model can take batches of tasks that need no
design or problem solving; to define the optimal pipeline and land it
in `CLAUDE.md`, the guides and the skills; and to find the balance
between context spent and tasks closed per session. One researcher
(on `sonnet`) priced the stages and shaped 60 closed tasks; the
session read its own transcript. What landed is the shape, the model
per stage and the budget rule; the filings are `UX-706`..`UX-711`.

## What exists today

| | |
|---|---|
| the ledger | 17 rows — researcher and general-purpose runs; **0** `implementer`, **0** `verifier` rows: the two stages the brief wants delegated are the two never priced |
| the implementer | no `model:` line — it ran on whatever launched it |
| the decomposition block | `grep -rl '^## Decomposition' docs/backlog/scenarios` → **0** of 705 files; the skill's output was never written |
| 60 closed tasks, rounds 84-90 | Required Fix names a file 23 (38 %) · Acceptance Test names a guard and a mutation 3 (5 %) · touches a contract/process surface 9 (15 %) · Outcome ≤ 80 lines 60 · mutation table 55 |
| single-task commits (12 of 29) | files 2 / 3 / 6 / 7 / 9 (min/p25/median/p75/max) · insertions 3 / 17 / 128 / 182 / 385 · 7 touch a test file |
| implementing PRs #193..#206 | 3-27 tasks each over 13-74 commits; round 80: 24 items, 6 suite runs, 1.83 commits per item |
| the orchestrator (this session, round 46 on) | 336 responses, 5.16M fresh tokens; **11 rebuilds** (a response over 30k with no tool before it — a wake after idle or a compaction) = 3.76M, **73 %**; Write 8 % · reads 4 % · pytest 3 % · agents 1 % |
| the hooks | 8-33 ms each; the edit lint 767 ms (ruff start-up); the commit selector 40 ms on an empty selection |
| a sonnet track (round 75, `UX-525`) | read 38-64 % of the track; edit 10-41 %; close 1-22 % |

The orchestrator's number decides the budget rule: what it reads is
not the cost; the live context at each rebuild is.

## The pipeline

| stage | who | model | reads | writes |
|---|---|---|---|---|
| orient, research | `researcher` | sonnet | wide | a report |
| decompose | the session | the session's | the filing; `--shape` | the shape word, the brief with the base sha |
| mechanical / bounded track | `implementer`, a worktree | sonnet | the task file and its cited ranges | code, the guard, its mutation table, the Outcome's three measured parts |
| judgement item | the session | the session's | what it must | the same |
| verify | `verifier` | sonnet | the diff, the task file | a report |
| merge, gate, close | the session | the session's | reports only | the merge, one `make test`, the deviation line, the row move |

Shape, derived from the filing's text (`tools/dev_close_task.py
--shape`): the Required Fix names a file; the Acceptance Test names a
guard and a mutation; either names a contract or process surface.
Mechanical = all three the right way; bounded = a file, no named
guard; judgement = no file, or a contract or process surface. On the
open backlog the day it landed: 8 bounded, 35 judgement, 0 mechanical
— and four of this round's own filings came out judgement until their
Required Fix wrote `tools/` in front of the tool's name, which is the
rule working.

## What landed

`tools/dev_close_task.py --shape [--write]` and an eighth `--check`
property; `tests/unit/test_a_task_declares_its_shape.py` (12 clauses,
two mutations red); `**Shape:**` in every open task's header;
`implementer.md` on `sonnet`, handed mechanical and bounded only, and
writing the Outcome's three measured parts; the `decompose` skill's
§0 (shape) and §5 (the batch and the orchestrator's budget);
`CLAUDE.md`'s pipeline paragraph; fixing guide §1.5 rewritten from
"one task per session" to "one task per track; the budget is the
orchestrator's live context at each rebuild".

## Filed

`UX-706` (the shape — closed this round), `UX-707` (the orchestrator's
rebuilds counted and priced — High), `UX-708` (the first batch under
the pipeline, priced per shape — High), `UX-709` (a batch of ids in
one `--move` — Medium), `UX-710` (a ledger row derived from the
transcript — Medium), `UX-711` (a tool result longer than a screen
goes to a file — Medium).

## Agents

| agent | model | task | tokens | tool calls | wall | friction |
|---|---|---|---|---|---|---|
| researcher | sonnet | the stages as documented, the ledger by model, 60 closed tasks shaped, tasks per PR, the hooks timed | 145k | 76 | 11.4 m | `git show --stat` on a merge shows an empty diff to `closed.md` and truncates `tests/unit/` paths; a batch commit closes 2-19 ids, so "the closing commit" is rarely one task |

## Standing

The advisory now says `sonnet` for mechanical and bounded tracks on
an argument, not a row: a track is reading with an edit attached, and
the suite, the mutation table and the verifier judge it. `UX-708` is
the measurement that confirms or reverses it, and it is one batch
away. The user's question — context against tasks per session — has
a measured answer for the orchestrator: eleven rebuilds cost more than
every read, write and test together, so the session's context is kept
small by reading reports, and the batch is bounded by the merge's
price (1.46-1.83 commits per item), not by the context.
