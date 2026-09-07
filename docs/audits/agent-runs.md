# Agent runs — what a subagent cost, and what went wrong

One row per subagent run the audit sessions launched, from the figures
the Agent tool returns (tokens, tool calls, wall clock) and the
agent's own closing *friction* line. `tools/dev_process_bands.py`
reads the Outcomes for what the *process* did; this table is where
the *runs* are counted, so the next round can choose a model and a
shape from numbers rather than from memory. Rows are appended by the
orchestrating session at the end of the round; a run cut off by a
limit is a row too.

| round | agent | model | task | tokens (fresh: input + cache creation, `UX-710`; reads low by the last response's output) | tool calls | wall | outcome | what cost the most / what went wrong |
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
| 95 | implementer | sonnet | track C: UX-700 the symbol index (bounded), incl. the verifier's two fixes | 216k | 101 | 25 m | merged | the task's Acceptance Test named five dead exports that the file never lists; the proxy classifier misread cp/pytest chains as git |
| 95 | implementer | sonnet | track A: UX-709 batch --move (bounded), incl. the verifier's two fixes | 271k | 97 | 31 m | merged | a batch grammar argparse cannot express; proving the single-id call byte-identical cost most |
| 95 | implementer | sonnet | track B: UX-707 --session and UX-710 --ledger (bounded), incl. the verifier's two fixes | 281k | 129 | 31.1 m | merged | ran twice against the main checkout instead of the worktree; a heredoc containing the word complete was refused as a shell builtin |
| 95 | verifier | sonnet | verifier of track C | 46k | 29 | 5.6 m | one guard could not fail; `__all__` listed dead; attribute calls and shadowing unresolved | `make test-touching` is a no-op once the track's commit is HEAD; `--base` needed |
| 95 | verifier | sonnet | verifier of track A | 45k | 48 | 9.8 m | leaked module globals; a repeated id closed twice; a false lint claim | the leak is invisible under `-n auto`; found by running the two files serially |
| 95 | verifier | sonnet | verifier of track B | 63k | 44 | 8.4 m | the first response never a rebuild; `--list` guard untested; 139k vs 145k explained | the harness's billed total had to be dug out of a task-notification string |
| 95 | implementer | sonnet | track D: UX-694 the finding baseline (bounded), incl. the verifier's five fixes | 296k | 117 | 45.7 m | merged | the git-diff guard makes the adding commit's own pre-commit lint red until it is HEAD; the brief's scope (`tests/` in the paths) contradicted the task's Out of Scope |
| 95 | verifier | sonnet | verifier of track D | 64k | 38 | 8.4 m | `tests/` scanned against Out of Scope (92 % `S101`); the git-diff guard absent; shrink with stale+new untested; a reformat re-identifies; `--shrink` wipes on a parse failure | the Required Fix names four analyzers and the Outcome said nothing of the three dropped |
| 100 | implementer | sonnet | `UX-732` the log's landed-after range (judgement, taken in the brief) | 189k | 115 | 35.1 m | reworked, then merged | the chosen route was wrong: a blob comparison calls a clean 3-way a landing, which is every merge here |
| 100 | implementer | sonnet | `UX-732` rework: the combined diff replaces the blob | 244k | 39 | 11.5 m | merged | the first pass's own reproduction used an unbounded `git log`, which answers a different question than `anchor..HEAD` |
| 100 | implementer | sonnet | `UX-734` three counted figures (judgement) | 100k | 76 | 15.7 m | merged | found the review's own replacement figure off by two, and corrected it |
| 100 | implementer | sonnet | `UX-735` the export size, derived (bounded) | 63k | 56 | 12.0 m | merged | — |
| 100 | implementer | sonnet | `UX-736` the architecture's status table (judgement, taken in the brief) | 66k | 59 | 12.7 m | merged | its first mutation flipped to 🔴, which `UX-561`'s worktree exemption absorbs — the guard passed for the wrong reason |
| 102 | implementer | sonnet | `UX-667` the rail is a source list (judgement, decided in the brief) | 319k | 243 | 59.6 m | merged | reverse-engineering which prose in a judgement Required Fix was load-bearing DOM and which was already true; reported a base failure as pre-existing that `origin/main` passes |
| 102 | implementer | sonnet | `UX-691` a flake ledger (bounded) | 146k | 105 | 21.1 m | merged | the derived cost row and the context map both red from adding two test files, and neither is in the task file or `rules.md` |
| 102 | implementer | sonnet | `UX-702` a performance ratchet at the gate (bounded) | 259k | 230 | 52.6 m | merged | issued early reads against the shared checkout instead of its worktree; left `dev_perf_ratchet.py` off the §6 context map |
| 102 | implementer | sonnet | `UX-712` the size ledger (bounded) | 416k | 227 | 59.2 m | merged | stalled twice waiting on a background notification that never arrives; found pylint attributes every duplicate-code hit to one arbitrary module |
| 102 | implementer | sonnet | `UX-703` a weekly mutation run (bounded) | 226k | 207 | 76.6 m | merged | stalled on a backgrounded mutmut run; mutmut copies the tree one directory deeper, so every `parents[N]` root in this repo resolves wrong inside a mutant |
| 103 | implementer | sonnet | `UX-705` burn-down batch 1: S607 under `tools/` (bounded) | 190k | 160 | 35.4 m | merged | resolving the executable turns a literal argv into one with a Name in it, which is what S603 reads - 16 of 23 cannot close without growing S603 |
| 103 | implementer | sonnet | `UX-705` burn-down batch 2: SIM115 under `tools/` (bounded) | 73k | 92 | 14.9 m | merged | wall clock: make test is ~7 min and the turn budget went into polling for it, not into the fix, which was mechanical as briefed |
| 103 | implementer | sonnet | `UX-742` a dead-export detector eslint cannot be (bounded) | 252k | 101 | 31.1 m | merged, two fixes | strip_comments blanks a string body wholesale, silently erasing the module paths a name-level import parse needs - 286 unread before the switch to raw text |
| 103 | implementer | sonnet | UX-749 | 84k | 69 | 19 m | merged; nine pseudo-path citations to bare ids, branch count dated | the task file's own citation list omitted UX-3; verifying the count beat trusting the list |
| 103 | implementer | sonnet | UX-746 | 159k | 71 | 21.5 m | merged after correction; the four workflows are on the map and the walk reaches them | copied the task file's false 'manual' premise forward without opening the .yml |
| 103 | implementer | sonnet | UX-748 | 413k | 121 | 48.6 m | merged after correction; three guards widened, log re-anchored, range regex widened again | measured its acceptance test in a tree where its own commit did not yet exist |
| 103 | verifier | sonnet | UX-746 verify | 251k | 81 | 27.4 m | both vacuity claims reproduced load-bearing; found the capture row misdescribes its workflow | the Outcome named each mutation but not the counter-mutation proving it load-bearing |
| 103 | verifier | sonnet | UX-749 verify | 104k | 77 | 30.2 m | count and guard confirmed; caught a 6-line comment against the Register's cap, and the #anchor gap | a loaded box turned one full suite into three background waits |
| 103 | verifier | sonnet | UX-748 verify | 91k | 66 | 15.5 m | found the acceptance test does not survive being committed, and the new guard vacuous on 'remain open' | the defect was invisible from the track's own uncommitted sandbox; only re-running against HEAD showed it |
| 103 | implementer | sonnet | UX-674 | 410k | 363 | 104.2 m | merged after correction; four font sizes, h3 below h2, prose at 72 of its own glyphs | a type-scale row that needed a layout-model change; scope grew four times, each reported |
| 103 | verifier | sonnet | UX-674 verify | 120k | 80 | 55.3 m | found a false budget-cost claim, an undisclosed non-rewrite, and the layout change no new guard reads | the task file alone could not resolve which sentences its Motivation named |

Round 101's four tracks are **not** here: this session could not
identify their transcripts with certainty after a context rebuild, and
a guessed row is worse than a missing one. Round 102's five are, all
derived with `dev_track_cost.py --ledger`.

Two of the five stalled waiting on a background notification that never
arrives, with a finished round of work uncommitted in a worktree; both
committed cleanly once told to run in the foreground. Three of the five
left a derived figure or a §6 context-map row behind - the same class
the round itself was about, arriving in the tracks' own work.

What the forty-seven rows already say: a researcher that reads a document
whole costs 100-180k; a walker that drives every control costs 336k;
the two cuts cost a re-run each. The `walk` and `design-review`
skills fix the report shape so the next rows are smaller, and the
model column is what `CLAUDE.md`'s advisory is measured against.
