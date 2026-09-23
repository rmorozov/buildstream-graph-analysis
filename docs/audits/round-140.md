# Round 140 — the workflow batch, run in parallel

Run on 2026-09-23 off main at `398b4db9` (`#285`, round 139), from
Ruslan's 19:07 ask for a batch of workflow rows run in parallel. The
architect shaped every row before its track ran; bookkeeping was 3 of
7 rows, one over the 40% cap, which Ruslan kept at 19:17.

```text
closed   UX-992 UX-990 UX-998 UX-999 UX-979 UX-977 UX-945 UX-997 UX-1000
shaped   UX-950 UX-955 (wait for round 141 under the cap)
filed    seven lines in the new UX-998 ledger, one of them review 27's
index    dev_close_task.py --counts: 961 scenarios, 15 open, 946 closed
```

## Every hold was a real defect

Nine verifications held seven times, and each hold was a real defect:

```text
UX-998   a hand-typed size row: 219/34 recorded, 233/35 measured
UX-992   growth never adopted (its verifier said MERGE; the session's size check caught it)
UX-997   git diff reads an untracked path clean, so publish would no-op forever
UX-997   three regressions only the full suite saw; a hand-picked subset passed
UX-997   MD032 in the Outcome
UX-1000  the register footer counted as a guard (350/567)
UX-1000  8 of 12 sampled "uncovered" rows named a guard, in four shapes
UX-1000  2 of 20 sampled "covered" rows cited a file as a limitation
```

`UX-1000`'s three holds share one cause: a row's guard lives in free
prose, and every pass over the prose finds a new citation shape. The
page now states which evidence it holds, `covered 366 / 567 (declared
121, inferred 245)`. Declared means the Decision's `Guard:` or the
Acceptance Test; inferred means the Outcome. Declaring a guard in one
field is filed as a bookkeeping line.

## CI caught two more

```text
#286 pip-audit   wcwidth 0.9.1 released upstream; lock refreshed (590fb00f)
#286 bst-tests   a module-level dev_records.load stopped collection in a job with no fetch
```

The second is `UX-997`'s own shape: a test resting on an untracked
record. Its guard reads citations, not import-time reads; collection
with the records moved aside now reads 9718 items, 0 errors.

## The push gate caught three

The new ledger's header had no blank line under `## Findings`, so its
first `--add` redded `make lint`. `fixing-guide.md` §6 still marked
the rows this round closed `(open)`; §7a names no step for it. And
31 rows had closed since review 26 against a bound of 25, so review
27 ran: one finding, the `retro` skill citing §2 for a `rules.md` row.

## Agents

| agent | model | task | tokens | calls | wall | friction |
|---|---|---|---|---|---|---|
| architect | opus | architect: UX-992 push gate cwd | 27k | 6 | 1.1 m | none reported |
| architect | opus | architect: UX-999 weekly retro | 36k | 11 | 2 m | none reported |
| architect | opus | architect: UX-998 bookkeeping ledger | 66k | 19 | 4 m | none reported |
| architect | opus | architect: bookkeeping batch UX-979, UX-977, UX-945, UX-990 | 43k | 24 | 3.8 m | none reported |
| architect | opus | architect: UX-950 and UX-955 gates | 70k | 34 | 6.1 m | none reported |
| implementer | sonnet | UX-992 the push gate reads the payload's cwd (mechanical) | 92k | 63 | 18.7 m | the size row for the hook's growth never adopted; caught at the session's size check |
| implementer | sonnet | UX-990 tools' BuildStream-version lines are claims (mechanical) | 268k | 120 | 35.5 m | none reported |
| verifier | sonnet | UX-990 verifier | 61k | 72 | 14.9 m | none reported |
| implementer | sonnet | UX-998 bookkeeping ledger (mechanical) | 207k | 173 | 40.3 m | a hand-typed size row (219/34 against 233/35 measured) |
| verifier | sonnet | UX-992 verifier | 132k | 54 | 31 m | did not run dev_sizes.py --check, so the unadopted growth passed |
| architect | opus | architect: UX-1000 area pages coverage | 50k | 20 | 4.5 m | none reported |
| implementer | sonnet | UX-979, UX-977, UX-945 bookkeeping batch (mechanical) | 719k | 176 | 48.3 m | its worktree began at origin/main, not the Decisions' commit |
| verifier | sonnet | UX-998 verifier | 55k | 46 | 11 m | dev_touching.py has no worker-count flag |
| implementer | sonnet | UX-999 weekly retro (mechanical) | 556k | 261 | 54.8 m | a new forced baseline entry refused; git routed through dev_records._git |
| verifier | sonnet | UX-979 UX-977 UX-945 verifier | 40k | 39 | 8.2 m | make lint past the 120 s foreground timeout |
| verifier | sonnet | UX-999 verifier | 52k | 46 | 8.5 m | which skill guard the Decision meant |
| verifier | sonnet | UX-1000 T1 verifier | 82k | 59 | 12.7 m | guard_files read the register footer as a guard |
| verifier | sonnet | UX-997 T2 verifier | 109k | 81 | 23 m | only the full suite caught three regressions a hand-picked set missed |
| verifier | sonnet | UX-1000 T1 verifier (second) | 71k | 52 | 11.2 m | 8 of 12 uncovered rows named a guard; only a hand-judged sample finds it |
| verifier | sonnet | UX-1000 T1 verifier (third) | 83k | 45 | 10.2 m | no regex tells a proving citation from a limiting one |
| implementer | sonnet | UX-997 T2 records off main (mechanical) | 1367k | 485 | 136 m | git diff reads an untracked path clean; the fixture had no .gitignore |
| implementer | sonnet | UX-1000 T1 area pages (mechanical) | 1066k | 472 | 132.4 m | every pass over free prose found a new citation shape |
| verifier | sonnet | UX-997 T2 verifier (second) | 226k | 65 | 31.6 m | a 16-minute full suite on two workers |
| implementer | sonnet | UX-1000 T2 CI publishes the area pages (mechanical) | 154k | 111 | 27.9 m | a fourth publishing job broke two generic guards the Decision did not name |
| verifier | sonnet | UX-1000 T2 verifier | 78k | 59 | 14 m | the push hook blocked pushes to throwaway bare remotes |
| general-purpose | sonnet | architecture review 27 (the cadence guard came due) | 194k | 120 | 10.3 m | claimed directions.md lacks rows 138-139; both exist |

26 rows, 5,904k fresh tokens, each derived by
`dev_track_cost.py --ledger`. The closing session's own row is not
here.
