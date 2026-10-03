# Round 170 - the junction-heavy onboarding walk's rows, UX-1320..1331

Run on 2026-10-03 from the onboarding walk of a three-project stand-in
with local junctions two levels deep and of carbonOS (report in
`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`).
Twelve rows filed in `44afd957`, seven tracks merged, then one
integration fix.

```text
closed   UX-1320 UX-1321 UX-1322 UX-1323 UX-1324 UX-1325 UX-1326 UX-1327
         UX-1328 UX-1329 UX-1330 UX-1331
filed    UX-1320..UX-1331
index    dev_close_task.py --counts: 1274 scenarios, 10 open, 1264 closed
spread   dev_touching.py --spread: 35-209 of 837 test files
```

## What closed

- `UX-1320`: Plane 2 keys a junctioned element by its full Plane 1 name
  (join 12 of 12 traced, 16 in Plane 1).
- `UX-1321`, `UX-1326`: `blast` reads a junction and a path inside its
  checkout; `--no-cost` reads the project when no snapshot exists.
- `UX-1322`: a build run through a wrapper script is captured.
- `UX-1323`, `UX-1324`: a comparison of different work is no verdict; a
  builders recommendation needs more built elements than builders.
- `UX-1325`: `cache-logs` reads every project a local junction brings in.
- `UX-1327`: `analyze` rolls a run up by junction (`variant-cost`,
  alias `junction-cost`).
- `UX-1328`..`UX-1331`: `doctor` counts what a junction stages as
  unseen and points above the error; a short element name is offered its
  junction-qualified match; `--help` opens with the first three commands.

## Lessons

- The walk's figures were not all right: 13 became 12 (`UX-1320`), the
  junction reads 16 of 16 and the base path 13, not 11 (`UX-1321`).
- Five verifier holds: `UX-1321`/`1326` (two surviving mutations),
  `UX-1322` (unguarded swap), `UX-1323` (signed-delta mutation),
  `UX-1327` (3 doc/schema reds, 5 more in the fixup), `UX-1330` and
  `UX-1331` (a required key; a container false positive).
- Environmental reds (missing records) buried 5 real ones among 119 in
  `UX-1327`'s track.
- The merged tree reddened the schema-prose guard on `withheld`, and the
  blast emit guard needed an integration fix (`8b5a9327`, surface 628).
- `test_the_verification_log_is_true` fails at base `44afd957` too.

## Agents

| round | agent | model | task | tokens | tool calls | wall | outcome | friction |
|---|---|---|---|---|---|---|---|---|
| 170 | implementer | sonnet | UX-1320 (judgement) | 197k | 159 | 39.2 m | merged | project names needed `bst show %{vars}` |
| 170 | implementer | sonnet | UX-1321, UX-1326 | 192k | 146 | 50.7 m | merged | worktree sandbox refused compound shell; probes via scratch scripts |
| 170 | implementer | sonnet | UX-1321, UX-1326 fix loop | 199k | 6 | 7.8 m | merged | see round-170 |
| 170 | implementer | sonnet | UX-1322 | 164k | 112 | 29.4 m | merged | see round-170 |
| 170 | implementer | sonnet | UX-1322 fix loop | 185k | 30 | 5.1 m | merged | see round-170 |
| 170 | implementer | sonnet | UX-1323, UX-1324 | 191k | 139 | 30.2 m | merged | page budget 33 B headroom |
| 170 | implementer | sonnet | UX-1323, UX-1324 fix loop | 197k | 10 | 3.4 m | merged | see round-170 |
| 170 | implementer | sonnet | UX-1325 | 76k | 63 | 19.7 m | merged | see round-170 |
| 170 | implementer | sonnet | UX-1327 | 221k | 140 | 30.6 m | merged | environmental reds (missing records) buried 5 real ones among 119 |
| 170 | implementer | sonnet | UX-1327 fix loop | 243k | 40 | 32.3 m | merged | see round-170 |
| 170 | implementer | sonnet | UX-1328, UX-1329, UX-1330, UX-1331 | 109k | 103 | 24.3 m | merged | see round-170 |
| 170 | implementer | sonnet | UX-1328, UX-1329, UX-1330, UX-1331 fix loop | 127k | 22 | 2.3 m | merged | see round-170 |
| 170 | verifier | sonnet | UX-1320 verifier | 44k | 20 | 14.2 m | complete | PASS |
| 170 | verifier | sonnet | UX-1321, UX-1326 verifier | 65k | 46 | 29.6 m | complete | held: 2 surviving mutations, key count, selector ceiling |
| 170 | verifier | sonnet | UX-1322 verifier | 49k | 19 | 4.1 m | complete | held: unguarded swap, wrong hint |
| 170 | verifier | sonnet | UX-1323, UX-1324 verifier | 37k | 12 | 3.4 m | complete | held 1323: signed-delta mutation survived |
| 170 | verifier | sonnet | UX-1325 verifier | 28k | 14 | 1.4 m | complete | PASS |
| 170 | verifier | sonnet | UX-1327 verifier | 45k | 24 | 11.6 m | complete | held: 3 doc/schema reds |
| 170 | verifier | sonnet | UX-1328, UX-1329, UX-1330, UX-1331 verifier | 36k | 20 | 1.8 m | complete | held 1330 (required key), 1331 (container false positive) |
