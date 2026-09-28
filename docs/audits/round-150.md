# Round 150 — bga's own cost, from the snapshot tail through the view

Run on 2026-09-28 off main at `aa0198f6` (the snapshot and view
performance audit, `docs/audits/perf-snapshot-view-2026-09-28.md`),
which filed `UX-1072`-`UX-1083`. All twelve close this round, plus two
bookkeeping rows the integrator seams left behind (`UX-1101`, `UX-1103`). `UX-1100`
(cut 0.5.0) and `UX-1102` (the architecture review) stay open.

```text
closed   UX-1072 UX-1073 UX-1074 UX-1075 UX-1076 UX-1077 UX-1078
         UX-1079 UX-1080 UX-1081 UX-1082 UX-1083 UX-1101 UX-1103
filed    UX-1100 UX-1101 UX-1102 UX-1103
open     UX-1100 (cut 0.5.0) UX-1102 (architecture review)
index    dev_close_task.py --counts: 1054 scenarios, 24 open, 1030 closed
spread   dev_touching.py --spread: 33-174 of 677 test files
```

## What closed

- `UX-1072` — the snapshot tail reuses `_analyze`'s own result for the
  slice instead of re-analyzing it: slice at 5,002 el 12.5 s -> 0.00 s.
- `UX-1073` — compare reads each side's published analysis under a full
  fingerprint match (Ruslan's Unify call: each side keeps its own
  Plane 2), sibling Plane 2 digested rather than stat'd (verifier
  finding): compare 5,002 el 49.45 s/2,010 MB -> 1.27 s/125 MB.
- `UX-1074` — graph reachability is one bitset closure per graph: `bga
  analyze` 5,002 el 1,967 MB -> 437 MB, 29.7 s -> 13.2 s, output
  byte-identical.
- `UX-1075` — the raw Plane 2 log gzips at level 6 instead of 9: 16.0 s
  -> 3.1 s on 417 MB.
- `UX-1076` — each element's opened paths are interned: 560 MB -> 261 MB;
  the guard reads VmHWM, never `ru_maxrss` (it carries across `exec`
  and red the push gate).
- `UX-1077` — the snapshot tail and `bga view` announce and time every
  phase; a pipe gets no ticker.
- `UX-1078` — `tail.json` (`tail/v1`) records bga's own cost, filed
  under a CHANGELOG Unreleased row (Ruslan's call): real examples/06
  bga 2.9 s beside a 32.4 s build, 0.4 s beside 1.2 s warm.
- `UX-1079` — `bga capture report` reads opens from a gzipped raw log
  instead of dropping them silently.
- `UX-1080` — BuildStream calls around the build are timed in
  `tail.json`'s own "before the build" phase, `bst show` timeout 300 s.
- `UX-1081` — `bga view --export` counts a step's tracks before
  rendering: 2 renders -> 1 at 5,002 el (~2 s of 48 s).
- `UX-1082` — the cache key set reads from the build's own Plane 1 log;
  the pre-build `bst show` is dropped (-1.2 s per snapshot).
- `UX-1083` — an equal fingerprint reuses the graph
  (`BGA_BASELINE_RUN_DIR`): warm examples/06 5.1 s -> 3.57 s, no
  `bst show`.
- `UX-1101` — the Verification Log re-grounds at round 150's merge,
  covering `UX-1073` and `UX-1078` together (63 properties, 26 emitted
  ids); neither track's own entry could see the other's contract
  change.
- `UX-1103` — at the #298 merge, the Verification Log re-grounds past
  `UX-1064`'s `--resolve` row (63 properties, 26 emitted ids), and the
  selector ceiling takes the merged reading: p90 61, max 174 over 677.

## In progress

`UX-1100` (cut 0.5.0) stays open — `tail/v1` is a new contract, filed
under an Unreleased row rather than cutting this round.

## Agents

| round | agent | model | task | tokens | tool calls | wall | outcome | friction |
|---|---|---|---|---|---|---|---|---|
| 150 | architect | opus | architect: UX-1073, UX-1078 | 52k | 13 | 2.5 m | shaped both; Unify route (Ruslan) for UX-1073 | — |
| 150 | implementer | sonnet | implementer: UX-1074 | 686k | 256 | 95.4 m | merged, VERIFIED | verifier found 184 s guard, fixed to 1 s plus memory guard |
| 150 | implementer | sonnet | implementer: UX-1079, UX-1076 | 130k | 114 | 33.4 m | merged, VERIFIED | ru_maxrss carried across exec red the push gate |
| 150 | implementer | sonnet | implementer: UX-1082, UX-1083 | 949k | 399 | 91 m | merged, VERIFIED | verifier found live wiring gap (help cap) |
| 150 | implementer | sonnet | implementer: UX-1075, UX-1072, UX-1081 | 810k | 302 | 90.1 m | merged, VERIFIED | — |
| 150 | implementer | opus | implementer: UX-1073 | 2079k | 214 | 280.3 m | merged, VERIFIED | verifier found a Plane 2 stat proxy, fixed to digested |
| 150 | implementer | opus | implementer: UX-1077, UX-1078 | 1479k | 283 | 147.4 m | merged, VERIFIED | stopped once on the release-row question; Ruslan chose the Unreleased row |
| 150 | implementer | sonnet | implementer: UX-1080 | 408k | 218 | 59 m | merged, VERIFIED | verifier found pre-build call attribution gap |
| 150 | verifier | sonnet | verifier: UX-1074 | 75k | 75 | 34 m | PASS | worktree lacks gitignored ci_reference.json/flake_ledger.json/touch_map.json |
| 150 | verifier | sonnet | verifier: UX-1079, UX-1076 | 62k | 51 | 16.3 m | PASS | worktree lacks gitignored ci_reference.json/flake_ledger.json/touch_map.json |
| 150 | verifier | sonnet | verifier: UX-1082, UX-1083 | 90k | 78 | 14.4 m | PASS | worktree lacks gitignored ci_reference.json/flake_ledger.json/touch_map.json |
| 150 | verifier | sonnet | verifier: UX-1075, UX-1072, UX-1081 | 161k | 120 | 40.9 m | PASS | worktree lacks gitignored ci_reference.json/flake_ledger.json/touch_map.json |
| 150 | verifier | sonnet | verifier: UX-1073 | 99k | 92 | 16.6 m | PASS | found the Plane 2 stat proxy, sent back |
| 150 | verifier | sonnet | verifier: UX-1077 | 99k | 89 | 13.3 m | PASS | dev_env_check suggests pip install -e <worktree>, forbidden by the brief |
| 150 | verifier | sonnet | verifier: UX-1078 | 156k | 137 | 23.9 m | PASS | new tail/v1 contract forces a release row, surfaced at the touching sweep |
| 150 | verifier | sonnet | verifier: UX-1080 | 87k | 61 | 13.4 m | PASS | found pre-build call attribution gap, sent back |
| 150 | integrator | opus | integrator: merge t4 t1 t2 t3 | 47k | 28 | 12.6 m | merged | pushed-gate reds only the merged tree showed: ru_maxrss across exec, bst-gated population count, spread fixture count |
| 150 | integrator | opus | integrator: merge UX-1080, UX-1073 | 60k | 45 | 16 m | merged | pushed-gate reds only the merged tree showed |

Every verifier returned PASS; three tracks (`UX-1074`, `UX-1073`,
`UX-1080`) took a real sendback first and merged clean after. `t6`
(`UX-1077`, `UX-1078`) stopped once on whether the new `tail/v1`
contract forces a release; Ruslan chose the CHANGELOG Unreleased row
over cutting.

## Friction worth the round

- Worktrees lack the gitignored `tests/ci_reference.json`,
  `flake_ledger.json`, `touch_map.json`; every verifier lost time
  re-deriving what the main checkout already had.
- `dev_env_check` suggests `pip install -e <worktree>`, which the
  implementer brief forbids.
- A new contract (`tail/v1`) forces a release-row question that
  surfaced only at the touching sweep (`UX-1078`); resolved by the
  Unreleased row.
- Pushed-gate reds appeared only on the merged tree, not on any single
  track: `ru_maxrss` carried across `exec`, a bst-gated population
  count, and a spread fixture count.

Step 7 (`make push-check` on the commit about to push) is the
session's, not this close's.
