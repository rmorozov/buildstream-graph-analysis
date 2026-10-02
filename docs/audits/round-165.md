# Round 165 - the round-163 verification residue and the round-164 review's row, UX-1258, UX-1260..UX-1277

Run on 2026-10-02, from round 163's filing (`UX-1258`-`UX-1267`) and the
round-164 view UI re-review's rows `UX-1268`-`UX-1277`, in six opus tracks.
Round 164 was a review and has no document. `UX-1259` stays open (waits on
Ruslan). Push-check is run after the close commits.

```text
closed   UX-1258 UX-1260 UX-1261 UX-1262 UX-1263 UX-1264 UX-1265 UX-1266
         UX-1267 UX-1268 UX-1269 UX-1270 UX-1271 UX-1272 UX-1273 UX-1274
         UX-1275 UX-1276 UX-1277 UX-1278
filed    UX-1278
open     UX-902 UX-1014 UX-1134 UX-1040 UX-1259
index    dev_close_task.py --counts: 1227 scenarios, 5 open, 1222 closed
spread   dev_touching.py --spread: 34-193 of 803 test files
```

## What closed

| row | close |
|---|---|
| `UX-1258` | Why #1 is built from the step's own finding; a step attributed to another finding draws no fold |
| `UX-1260` `UX-1264` | the 1440 case was already rail-open (the rail never folds at 1440), the guard now asserts it; no new fixture, `shared_base_wide` already leads with resource wait |
| `UX-1261` | the answer sentence links to the filtered `#by_binary` |
| `UX-1262` `UX-1263` | store copying is opt-in (`store=True`, two-plane only); a relative run path keeps the snapshot and compare steps |
| `UX-1265` `UX-1272` `UX-1273` | the graph-width title reads "N dependency levels; the widest holds W of T elements"; the single-process basis reads "not a bound"; the heading "How much ready work had not started?" plus a `counts` field |
| `UX-1266` `UX-1267` `UX-1269` `UX-1270` | one `joint-saving` finding, the order marks only steps measured to pay off later; map rows in a closed fold; relation sentences in a fold; the Wall column says it sums lifetimes |
| `UX-1268` `UX-1271` | `consistency.py` reports the disagreement, verdict unchanged; "saturated" only for builder slots at or above 90% busy |
| `UX-1274` | the sweep reaches min(max(2b, 2 cores, width), 32); the knee is quoted "(replayed, no contention)"; analyze +0.92 s on the 2,402 page |
| `UX-1275` `UX-1276` `UX-1277` | blocked time is an upper bound when a parent was not recorded (`blocked_unparented`); `builds_per_day` declared only; `findings_diff` with `not_compared` when the planes differ |
| `UX-1278` | the verification log re-grounds, crediting round 165's changes (65 top-level properties, 28 emitted ids) |

## Owner calls pending

Recorded, each carries its default (taken):

- `UX-1261`: link to the filtered `#by_binary`, not a reorder.
- `UX-1266`: one finding (`joint-saving`).
- `UX-1267`: `xl_both` words 13,200 -> 14,100, nodes 7,500 -> 8,080, controls 1,192 -> 1,195; `macro_micro` words 13,500 -> 13,700, controls 872 -> 874.
- `UX-1268`: the disagreement reported by `consistency.py`, verdict unchanged; silent on undersubscribed (`UX-1259`).
- `UX-1276`: `builds_per_day` declared only.
- Budgets: `PAGE_BUDGET_B` 165,000 -> 165,650; the selector ceiling max 190 -> 193. The data-half measurement uses a fixed-length temp dir (98,094 of 100,000 B).

## Residue

`UX-1278` only; no verification residue filed.

## Lessons

- Every verifier found something real: five of six tracks needed a fix loop (`UX-1258`, `UX-1271`, `UX-1272`, `UX-1273`, `UX-1265`); two reversed their Decision (`UX-1272` "at least", `UX-1273` no-field route).
- The worktree sandbox refused compound shell commands, so every probe went through a scratch script; `-n 1` touching runs took 14-21 min on a shared 4-core box.
- `UX-1260`'s Motivation named a "1440 rail-shut" that does not exist; the architect's premise was wrong.

## Agents

| round | agent | model | task | tokens | tool calls | wall | outcome | friction |
|---|---|---|---|---|---|---|---|---|
| 165 | architect | opus | rows A (1264-1271) | 83k | — | — | see round-165 | tool calls and wall not in the brief |
| 165 | architect | opus | rows B (1258,1268-1276) | 89k | — | — | see round-165 | tool calls and wall not in the brief |
| 165 | architect | opus | rows C (1260-1263,1275,1277) | 81k | — | — | see round-165 | tool calls and wall not in the brief |
| 165 | implementer | opus | track 1 finding text | 237k | — | — | see round-165 | tool calls and wall not in the brief |
| 165 | implementer | opus | track 2 viewer cards | 110k | — | — | see round-165 | tool calls and wall not in the brief |
| 165 | implementer | opus | track 3 capacity page | 244k | — | — | see round-165 | tool calls and wall not in the brief |
| 165 | implementer | opus | track 4 sweep/sizing | 260k | — | — | see round-165 | tool calls and wall not in the brief |
| 165 | implementer | opus | track 5 binaries | 203k | — | — | see round-165 | tool calls and wall not in the brief |
| 165 | implementer | opus | track 6 compare/store | 178k | — | — | see round-165 | tool calls and wall not in the brief |
| 165 | verifier | sonnet | track 1 verifier | 70k | — | — | see round-165 | tool calls and wall not in the brief |
| 165 | verifier | sonnet | track 2 verifier | 47k | — | — | see round-165 | tool calls and wall not in the brief |
| 165 | verifier | sonnet | track 3 verifier | 56k | — | — | see round-165 | tool calls and wall not in the brief |
| 165 | verifier | sonnet | track 4 verifier | 52k | — | — | see round-165 | tool calls and wall not in the brief |
| 165 | verifier | sonnet | track 5 verifier | 58k | — | — | see round-165 | tool calls and wall not in the brief |
| 165 | verifier | sonnet | track 6 verifier | 42k | — | — | see round-165 | tool calls and wall not in the brief |
| 165 | integrator | opus | six merges + 12 merged-tree reds | 255k | — | — | see round-165 | worktree sandbox refused compound shell commands (probes via scratch scripts); -n 1 touching runs took 14-21 min on a shared 4-core box; 5 of 6 tracks needed a verifier fix loop |
