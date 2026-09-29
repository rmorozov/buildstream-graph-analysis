# Round 151 — the quality gates, audited and batched

Run on 2026-09-29 off the quality-gates audit
(`docs/audits/quality-gates-2026-09-29.md`), which filed `UX-1108`-`UX-1123`.
Ruslan lifted the process cap for the round (2026-09-29 06:19, "let's batch
tasks you filed and implement them in parallel"). Seventeen close: `UX-1118`
(the formatter) landed after the first close as its own track, and
`UX-1123` and `UX-1126` were filed and closed at the merge and on CI;
`UX-1124` and `UX-1125` are filed open.

```text
closed   UX-1108 UX-1109 UX-1110 UX-1111 UX-1112 UX-1113 UX-1114 UX-1115
         UX-1116 UX-1117 UX-1118 UX-1119 UX-1120 UX-1121 UX-1122 UX-1123
         UX-1126
filed    UX-1123 UX-1124 UX-1125 UX-1126
open     UX-1124 UX-1125
index    dev_close_task.py --counts: 1079 scenarios, 23 open, 1056 closed
spread   dev_touching.py --spread: 34-175 of 700 test files
census   34 files, 1887 tests, 68.9 s
```

## What closed

- `UX-1108` — CI cancels a superseded PR run; a push gets its own run-id group and is never cancelled.
- `UX-1109` — bst-smoke, bst-tests and bst-examples no longer wait for test (bst-smoke needed test too, so the row's own route shortened nothing against bst-examples' 620-964s spread).
- `UX-1110` — the `UX-1004` width calibration runs on push and on a PR labelled jobserver only.
- `UX-1111` — pytest-timeout (300 s, signal) replaces the small-tier backstop; the single-process small tier runs on push only.
- `UX-1112` — push-check lints only the markdown changed against the merge-base (0.57 s against 3 m); make lint keeps the full scan.
- `UX-1113` — the gate runs the interpreter's locked ruff and pyright and refuses to judge off the lock.
- `UX-1114` — a SessionStart hook unshallows and installs the lock, never in a linked worktree, always exit 0.
- `UX-1115` — area-pages-publish needs both adopt jobs to succeed.
- `UX-1116` — the hook builds with -Wall -Wextra; -Werror and an ASan/UBSan process-tree run guard it.
- `UX-1117` — hypothesis property tests over the Plane 1 reader, near-miss lines included.
- `UX-1119` — Google docstring convention through the baseline (D2-D4 less three layout rules, 22 findings held).
- `UX-1120` — closed.md split into 128-row chunks under closed/; lint-docs 173 s -> 82 s.
- `UX-1121` — the tier-drift and analyzer-clock verdicts report on a PR; timing.yml judges them daily on main.
- `UX-1122` — dev_guard_prices.py joins CI seconds to the Guard map; the retro prices its guards (215 need an owner, 328 inferred owners to confirm).
- `UX-1123` — the Verification Log gains the round-151 entry (63 properties, 26 emitted ids).
- `UX-1118` — the tree is `ruff format`-ed, quote-style preserve (859 files), held by lint and the edit hook.
- `UX-1126` — the size ledger hands pylint its files sorted; CI's walk order had moved an R0801 cell.

## Filed

- `UX-1124` — `parse_timestamp` reads the wrapper's UTC stamp as local time (found by `UX-1117`'s architect).
- `UX-1125` — a red ledger gives `dev_guard_prices` a last-catch source (`UX-1122` T2).

## Agents

| round | agent | model | task | tokens | tool calls | wall | outcome | friction |
|---|---|---|---|---|---|---|---|---|
| 151 | researcher | sonnet | researcher: quality-gates audit, CI  | 86k | 19 | 3.3 m | report | jobs API history needed 200 calls |
| 151 | researcher | sonnet | researcher: quality-gates audit, lint  | 31k | 10 | 1.1 m | report | ruff --select overrides ignore; pylint absent |
| 151 | researcher | sonnet | researcher: quality-gates audit, tests  | 40k | 20 | 3.4 m | report | addopts -v changes collect output |
| 151 | architect | opus | architect: UX-1108 1109 1110 1111 1115 1121  | 86k | 24 | 4.3 m | shaped | found bst-smoke also needs test |
| 151 | architect | opus | architect: UX-1112 1113 1118 1119 1120  | 93k | 32 | 16.5 m | shaped | measured the format on a scratch copy |
| 151 | architect | opus | architect: UX-1114 1116 1117 1122  | 57k | 25 | 4.3 m | shaped | found parse_timestamp reads UTC as local |
| 151 | implementer | opus | implementer: UX-1108 1109 1110 1115 1111 1121  | 197k | 193 | 30.2 m | merged | sandbox refused compound git; three weak guards sent back |
| 151 | implementer | sonnet | implementer: UX-1113 1112 1119  | 115k | 112 | 37.3 m | merged | size ledger and forced S603 undeclared |
| 151 | implementer | sonnet | implementer: UX-1116 1117  | 68k | 51 | 9.4 m | merged | property 2 random-only, sent back |
| 151 | implementer | sonnet | implementer: UX-1114 1122  | 87k | 94 | 33.7 m | merged | unrecorded read as quiet, sent back |
| 151 | implementer | sonnet | implementer: UX-1120  | 111k | 80 | 29.5 m | merged | two guard gaps sent back; census row the session's |
| 151 | verifier | sonnet | verifier: UX-1116 1117  | 32k | 19 | 2.5 m | PASS | property 2 weak |
| 151 | verifier | sonnet | verifier: UX-1108..1121  | 47k | 26 | 3.7 m | PASS | three surviving mutations |
| 151 | verifier | sonnet | verifier: UX-1114 1122  | 29k | 21 | 2.5 m | PASS | skill wording over-promised |
| 151 | verifier | sonnet | verifier: UX-1120  | 51k | 26 | 4.1 m | PASS | two surviving mutations |
| 151 | verifier | sonnet | verifier: UX-1113 1112 1119  | 41k | 31 | 11.3 m | PASS | push-check pipe had no pipefail |

Every verifier returned PASS. Five tracks took send-backs first: property 2
random-only (`UX-1117`), three weak guards with surviving mutations
(`UX-1108`-`UX-1121`), unrecorded read as quiet (`UX-1122`), two guard gaps
(`UX-1120`), and a push-check pipe with no pipefail (`UX-1113`).

## Friction worth the round

- The merge's baseline union kept `UX-1114`'s forced batch beside track B's.
- The census row for `UX-1120` was the session's, not the track's.
- Verifiers found surviving mutations in three A guards and two E guards.
- The sandbox refused compound git in the A track.

Step 7 (`make push-check` on the commit about to push) is the
session's, not this close's.
