# Round 163 - the round-162 review's rows, UX-1235, UX-1236, UX-1244..UX-1257

Run on 2026-10-02, from round 162's filing (base `08baf490`, #309 merged): the
two open residue rows `UX-1235`, `UX-1236` and the review's fourteen rows
`UX-1244`-`UX-1257`, batched at Ruslan's request of 2026-10-01 21:51. Round 162
(#309) filed rows only and has no document. Push-check is run after the close
commits.

```text
closed   UX-1235 UX-1236 UX-1244 UX-1245 UX-1246 UX-1247 UX-1248 UX-1249
         UX-1250 UX-1251 UX-1252 UX-1253 UX-1254 UX-1255 UX-1256 UX-1257
filed    UX-1258 UX-1259 UX-1260 UX-1261 UX-1262 UX-1263 UX-1264 UX-1265 UX-1266 UX-1267
open     UX-902 UX-1014 UX-1134 UX-1040 UX-1258 UX-1259 UX-1260 UX-1261 UX-1262
         UX-1263 UX-1264 UX-1265 UX-1266 UX-1267
index    dev_close_task.py --counts: 1216 scenarios, 14 open, 1202 closed
spread   dev_touching.py --spread: 34-189 of 796 test files
```

## What closed

| row | close |
|---|---|
| `UX-1235` `UX-1236` | a binary jump lands below the stuck tools at every width; a bare `downstream` comparison reads the quantity column or is said back unread |
| `UX-1244` `UX-1245` `UX-1246` | a capacity-bound run reads `capacity_bound` and gets the builders step; slot occupancy is no CPU evidence; a host-core cap is `host_cores`, not `CPU` |
| `UX-1247` `UX-1255` | `by_binary` is per-binary totals (`analyze/v7`); Plane 2 reaches the findings (`costliest-binary`, `jobs-waiting`) |
| `UX-1248` `UX-1249` `UX-1256` | finding titles lead with their number (max 217 -> 144 characters); findings say each thing once and info without a step folds; every finding publishes its step |
| `UX-1250` `UX-1251` `UX-1252` | next steps name the run by `@stamp`; floors labels carry a segment border; all-clear counters are one sentence |
| `UX-1253` `UX-1254` `UX-1257` | four published verdict-disagreement pairs; the agent sizing card; the compare chapter leads with the delta |

## Owner calls pending

Recorded, not decided; each carries its default.

- `UX-1254`: the `macro_micro` controls bound 868 -> 872 (decision card posted; default "Raise to 872").
- `UX-1249`: the 50-class words bound 13,200 -> 13,500 (the 107 step words alone exceed 13,200; default carried).
- `UX-1244`: the diagnosis names UX-861's host-core cap and says to measure above it with `bga sweep`; whether the cap should hold a builder-bound run whose cores idle at 21% is Ruslan's (filed as `UX-1259`).

## The figures

- Page half: 159,873 B at the start of `UX-1246`, 160,605 B after `UX-1254` (+684), 160,409 B with `UX-1257`; `PAGE_BUDGET_B` 165,000.
- `macro_micro` opened height 39,522 -> 37,828 px under `UX-1249`; the card merge of `UX-1267` measured 40,222 against 39,188.
- `dev_sizes.py --adopt --force`: 16 cells grew; `duplicate_blocks` unchanged in every cell.
- A review is due: `test_the_review_has_a_cadence.py` reads 33 scenarios closed since review 34, against a bound of 25. Not run here.

## Residue

`UX-1258`-`UX-1267` filed open (`Found by:` the round-163 verification): a disclosure for the builders step, the host-core cap against a measured CPU reading (waits on Ruslan), the 1440 rail-open landing, the `#binary_cost` sentence, store pages for the said-once guard, a relative run path, a `resource_wait` fixture, the graph-width title, the `joint-saving` pair, and ranked cards without the map rows.

## Lessons

- The verification log's anchor is the oldest commit naming the credited id, so the re-grounding commit is credited to a residue id no earlier commit names (`UX-1267`).
- `dev_sizes.py --adopt` also rewrote the cell file's `paths` key to the full tree.

## Agents

| round | agent | model | task | tokens | tool calls | wall | outcome | friction |
|---|---|---|---|---|---|---|---|---|
| 163 | architect | opus | shape, wave 1 of 3 (ids not in the brief) | 58k | — | 2.8 m | see round-163 | architect Decisions on the 16 rows |
| 163 | architect | opus | shape, wave 2 of 3 (ids not in the brief) | 68k | — | 2.7 m | see round-163 | architect Decisions on the 16 rows |
| 163 | architect | opus | shape, wave 3 of 3 (ids not in the brief) | 92k | — | 4.4 m | see round-163 | architect Decisions on the 16 rows |
| 163 | implementer | opus | track A: UX-1253, UX-1244 | 158k | — | — | see round-163 | tool calls and wall not in the brief |
| 163 | implementer | opus | track A fix round: UX-1253, UX-1244 | 195k | — | — | see round-163 | verifier fix; tool calls and wall not in the brief |
| 163 | implementer | opus | track B: UX-1245, UX-1246 | 152k | — | 28 m | see round-163 | tool calls not in the brief |
| 163 | implementer | opus | track C: UX-1254 | 183k | — | — | see round-163 | tool calls and wall not in the brief |
| 163 | implementer | opus | track C fix round: UX-1254 | 203k | — | — | see round-163 | verifier fix; tool calls and wall not in the brief |
| 163 | implementer | opus | track F: UX-1250, UX-1256, UX-1248 | 316k | — | 95 m | see round-163 | tool calls not in the brief |
| 163 | implementer | opus | track G: UX-1247 | 195k | — | 44 m | see round-163 | tool calls not in the brief |
| 163 | implementer | opus | track K: UX-1257 | 105k | — | — | see round-163 | tool calls and wall not in the brief |
| 163 | implementer | opus | track K fix round: UX-1257 | 124k | — | — | see round-163 | verifier fix; tool calls and wall not in the brief |
| 163 | implementer | opus | track D: UX-1249 | 163k | — | 121 m | see round-163 | tool calls not in the brief |
| 163 | implementer | opus | track H: UX-1255 | 176k | — | — | see round-163 | tool calls and wall not in the brief |
| 163 | implementer | opus | track H fix round: UX-1255 | 206k | — | — | see round-163 | verifier fix; tool calls and wall not in the brief |
| 163 | implementer | opus | track J: UX-1252 | 159k | — | — | see round-163 | tool calls and wall not in the brief |
| 163 | implementer | opus | track J fix round: UX-1252 | 181k | — | — | see round-163 | verifier fix; tool calls and wall not in the brief |
| 163 | implementer | sonnet | track V: UX-1251 | 45k | — | — | see round-163 | tool calls and wall not in the brief |
| 163 | implementer | sonnet | track V fix round: UX-1251 | 62k | — | — | see round-163 | verifier fix; tool calls and wall not in the brief |
| 163 | implementer | sonnet | track W: UX-1235, UX-1236 | 58k | — | — | see round-163 | tool calls and wall not in the brief |
| 163 | implementer | sonnet | track W fix round: UX-1235, UX-1236 | 65k | — | — | see round-163 | verifier fix; tool calls and wall not in the brief |
| 163 | verifier | sonnet | UX-1245, UX-1246 verifier (track B) | 40k | — | — | see round-163 | tool calls and wall not in the brief |
| 163 | verifier | sonnet | UX-1253, UX-1244 verifier (track A) | 56k | — | — | see round-163 | tool calls and wall not in the brief |
| 163 | verifier | sonnet | UX-1247 verifier (track G) | 64k | — | — | see round-163 | tool calls and wall not in the brief |
| 163 | verifier | sonnet | UX-1251, UX-1235, UX-1236 verifier (track V+W) | 42k | — | — | see round-163 | tool calls and wall not in the brief |
| 163 | verifier | sonnet | UX-1257 verifier (track K) | 34k | — | — | see round-163 | tool calls and wall not in the brief |
| 163 | verifier | sonnet | UX-1254 verifier (track C) | 63k | — | — | see round-163 | tool calls and wall not in the brief |
| 163 | verifier | sonnet | UX-1250, UX-1256, UX-1248 verifier (track F) | 52k | — | — | see round-163 | tool calls and wall not in the brief |
| 163 | verifier | sonnet | UX-1249 verifier (track D) | 47k | — | — | see round-163 | tool calls and wall not in the brief |
| 163 | verifier | sonnet | UX-1255 verifier (track H) | 34k | — | — | see round-163 | tool calls and wall not in the brief |
| 163 | verifier | sonnet | UX-1252 verifier (track J) | 48k | — | — | see round-163 | tool calls and wall not in the brief |
| 163 | integrator | sonnet | integrator: six parts, 16 rows | 321k | — | — | see round-163 | figure is approximate (~) over six parts; tool calls and wall not in the brief |
