# Agent runs — what a subagent cost, and what went wrong

One row per subagent run the audit sessions launched, from the figures
the Agent tool returns (tokens, tool calls, wall clock) and the
agent's own closing *friction* line. `tools/dev_process_bands.py`
reads the Outcomes for what the *process* did; this table is where
the *runs* are counted, so the next round can choose a model and a
shape from numbers rather than from memory. Rows are appended by the
orchestrating session at the end of the round; a run cut off by a
limit is a row too.

| round | agent | model | task | tokens | tool calls | wall | outcome | what cost the most / what went wrong |
|---|---|---|---|---|---|---|---|---|
| 64 | general-purpose | main | verification, 12 landings | 116k | 103 | 10 m | complete | mutation loop per guard; suite runs |
| 64 | general-purpose | main | outside walk, answer key | 175k | 95 | 18 m | complete | real bst build; trace_processor download (4 m) |
| 77 | researcher | main | process delta since round 74 | 51k | 12 | 1.6 m | complete | — |
| 77 | general-purpose | main | control walk, 782 controls | 336k | 105 | 24 m | complete | driving every class; nested-table sweep |
| 77 | general-purpose | main | growth audit, three axes | 226k | 76 | 19 m | complete | four seeded runs (48 s export at 4,002); a 100-run store |
| 82 | researcher | main | spec vs code | — | — | — | **cut by session limit**, re-run | limit reset 10:10 UTC; nothing returned |
| 82 | researcher | main | spec vs code (re-run) | 107k | 70 | 5.6 m | complete | 12 spec ranges; 17 guard files run |
| 82 | researcher | main | architecture + pipeline docs | 129k | 42 | 7 m | complete | 10 guard files; the yml read whole |
| 82 | researcher | main | guides + README + CHANGELOG | 105k | 47 | 6.9 m | complete | every subcommand `--help`; 6 README commands run |
| 82 | researcher | main | design docs | — | — | — | **cut by session limit**, re-run | — |
| 82 | researcher | main | design docs (re-run) | 178k | 36 | 6.2 m | complete | 31 styleguide guards run (126 s); directions.md read whole (2,065 lines) |
| 82 | researcher | main | process layer | 146k | 46 | 7.4 m | complete | ci.yml read whole (1,253 lines) |
| 90 | researcher | main | process + design delta since round 82 | 81k | 34 | 3 m | complete | — |
| 90 | general-purpose | main | design review, all-planes page, 7 screenshots | 229k | 62 | 24 m | complete | two real captures; three census re-runs after navigations killed the driver; `pkill -f` matched its own shell |
| 91 | researcher | sonnet | what the tool answers for the three utilization roles | 121k | 86 | 7 m | complete | computed-vs-published needed a grep of the consuming layer for each producer's names |
| 92 | researcher | sonnet | the test plan's landing, the suite's shape, the release gate, the backlog | 96k | 34 | 3.8 m | complete | the brief grouped rounds 64, 78 and 80 as one plan; each file's dateline read |
| 93 | researcher | sonnet | the lint gate, ruff by family, radon, pyright, bandit, eslint, CodeQL feasibility | 62k | 51 | 5.8 m | complete | `ruff --statistics` exits 1 on any finding — one invocation per family |
| 94 | researcher | sonnet | the stages as documented, the ledger by model, 60 closed tasks shaped, tasks per PR, the hooks timed | 145k | 76 | 11.4 m | complete | `git show --stat` on a merge hides the `closed.md` diff and truncates test paths; a batch commit closes 2-19 ids |

What the sixteen rows already say: a researcher that reads a document
whole costs 100-180k; a walker that drives every control costs 336k;
the two cuts cost a re-run each. The `walk` and `design-review`
skills fix the report shape so the next rows are smaller, and the
model column is what `CLAUDE.md`'s advisory is measured against.
