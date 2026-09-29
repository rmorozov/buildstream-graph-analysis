# Round 149 — a housekeeping round: retro proposals, filed guard rows, and the bookkeeping sweep

Run on 2026-09-28 off main, Ruslan's ask (13:53) - "batching all open
bookkeeping and guard entries and new filed bookkeeping entries and
guard tasks from retro and making housekeeping round" - which lifts
`UX-993`/`UX-994`'s 40% bookkeeping cap for this round by his word. Ships
on `#299` (reusing the pull request already open on the 2026-09-28
retro, `docs/audits/retro-2026-09-28.md`, at his word - "I propose
reusing PR 299"). 11 tracks ran in parallel: `UX-938`, `UX-950`,
`UX-955`, `UX-1041`, `UX-1090`, `UX-1091`, `UX-1092` (steps A and B),
`UX-1093`, and bookkeeping sweeps A, B, C.

```text
closed   UX-938 UX-950 UX-955 UX-1041 UX-1090 UX-1091 UX-1092 UX-1093
         UX-1102 (review 30, after #298 and #300 merged in)
open     UX-1040 (a paid paired-model reading; put to Ruslan as a
         decision rather than run unbudgeted)
filed    4 bookkeeping lines at integration (fail-open UX-1041 took the
         r140 line; UX-938's rules.md 80-cap conflict with UX-1092;
         coverage: dev_close_task.py owner:/unpayable: non-empty check;
         coverage: test_every_control_has_a_resting_appearance.py's
         inherited-weight gap)
swept    12 bookkeeping lines (sweeps A/B/C; UX-1041 took the r140
         fail-open line); UX-1092 promotes the r140 dev_area_pages
         coverage line (`promoted r149 UX-1092`)
index    dev_close_task.py --counts: 1023 scenarios, 17 open, 1006 closed
spread   dev_touching.py --spread: 33-172 of 654 test files
```

## What the round showed

11 parallel tracks on a 4-core box drove load average to 50-63 and
turned every gate into a 10-25 minute wait - the dominant friction in
15 of 20 runs (`runs.txt`). `merge=union` in `.gitattributes` on
`docs/backlog/bookkeeping.md` let two branches each carry a different
status for the same line, so a merge kept both copies and silently
reopened 12 already-swept lines across two of the integrator's eleven
merges; rebuilt by hand each time (integration.md, merges 7 and 9),
filed as its own `coverage` line rather than fixed in-round. The
`UX-1092` backfill's prose inference (Outcome text with no `Guard:`
field or Acceptance Test name) measured 7 of 8 right on the verifier's
sample - one file (`UX-0245`) named a guard its own Deviation disclaims,
hand-corrected at integration.

## The merge

11 tracks merged in sequence (`integration.md`); five needed a fix-up
after their own gates read red on the merged tree:

- **(a)** `UX-1090`'s new helpers grew `dev_retro.py` past its
  `dev_sizes.py` reference cell (24 -> 27 functions, 186 -> 207 lines);
  `--adopt` refused upward, `--adopt --force` wrote the two grown cells.
- **(b)** sweep C's fixed `BOOTS_A_BROWSER` pattern brought 5
  previously invisible browser test files into `test_the_tiers_are_a_partition.py`'s
  population with no `tests/tiers.py` row; 5 MEDIUM rows added
  (durations measured, one seam padding fix alongside).
- **(c)** `UX-1041`'s `refusal()` widened to let `dev_touching.py`'s
  print-only flags (`--spread`, `--list`, `--why`, `--size`) through
  from a linked worktree; `implementer.md`/`verifier.md` aligned to
  select with `--list` and run pytest at `-n 2`.
- **(d)** `UX-938`'s `UX-1014` Reading corrected to name both hosts
  (`owner:CodSpeed Graviton and an x86 16-core host`).
- **(e)** `UX-1092`'s backfill re-run on the merged tip (step B, after
  `UX-0245` was hand-written first): 1021 files, `{'named': 175,
  'inferred': 455, 'none-absent': 2, 'none-closed': 373, 'none-open':
  16}`; `dev_area_pages` covered rows: 419 / 629 (none 210, inferred
  r149 267, no line 0).

`rules.md`'s 80-line cap forced a choice between `UX-938`'s new
`**Reading:**` row and a duplicate sentence already in
`fixing-guide.md` §5 - the duplicate dropped (`UX-938`'s Deviation).

## Full suite (tip `daad6afb`, before this document's own commit)

```text
python3 -m pytest -n 2 -q
2 failed, 10088 passed, 199 skipped, 1 warning in 733.48s
```

The two failures are `test_a_run_is_priced.py`'s round-149 register
clauses, which this document and its ledger rows now satisfy.

## Agents

| agent | model | task | tokens | calls | wall | friction |
|---|---|---|---|---|---|---|
| architect | opus | UX-1090 UX-1091 | 33k | 8 | 1 m | none reported |
| architect | opus | UX-1092 | 27k | 9 | 1 m | none reported |
| architect | opus | UX-938 UX-1041 | 50k | 19 | 2 m | none reported |
| architect | opus | UX-1093 | 53k | 21 | 7 m | none reported |
| architect | opus | sweep r149 | 23k | 5 | 1 m | none reported |
| implementer | sonnet | sweep A | 172k | 347 | 44 m | load avg 50-63 from 11 parallel tracks |
| implementer | sonnet | UX-955 | 116k | 90 | 44 m | make lint past 120s under load |
| implementer | sonnet | UX-1090 | 132k | 165 | 43 m | dev_records fetch refused in worktree; 7 failures reported that did not reproduce |
| implementer | sonnet | sweep C | 159k | 141 | 44 m | load avg 55-62 |
| implementer | sonnet | UX-1091 | 243k | 541 | 47 m | make lint timed out at 120/500/900s under load |
| implementer | sonnet | UX-950 | 181k | 282 | 69 m | full suite unfinished in-session under load |
| implementer | opus | UX-1092 | 132k | 93 | 52 m | selector 27 min under load; worktree refused compound git |
| implementer | opus | UX-1041 | 102k | 92 | 52 m | classifier refused heredoc/pipe/make lint forms ~8 times |
| implementer | opus | UX-1093 | 80k | 69 | 52 m | pkill -f matched own shell |
| implementer | opus | sweep B | 85k | 52 | 60 m | worktree refused compound commands |
| implementer | sonnet | UX-938 | 194k | 179 | 67 m | rules.md at 80-line cap with zero slack |
| verifier | sonnet | UX-955 UX-1090 UX-1091 sweep A sweep C | 121k | 97 | 24 m | concurrent checkout raced a background run |
| verifier | sonnet | UX-950 UX-1041 UX-1092 UX-1093 sweep B | 111k | 88 | 21 m | make lint pyright past 180s |
| verifier | sonnet | UX-938 | 74k | 54 | 9 m | pyright shadow gave a false new finding |
| integrator | opus | round 149 | 161k | 116 | 57 m | merge=union reopened 12 swept bookkeeping lines |
| general-purpose | opus | architecture review 30 (UX-1102) | 160k | 55 | 18 m | none reported |

Full detail, including outcome cells, is `docs/audits/agent-runs.md`'s
own round-149 rows (21: 5 `architect`, 11 `implementer`, 3 `verifier`,
1 `integrator`, 1 `general-purpose` for review 30).

`make push-check` is this session's, run on the commit about to push
(fixing-guide.md §7a step 7).
