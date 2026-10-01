# Round 161 - round 160's walk residue, UX-1219..UX-1234

Run on 2026-10-01, from round 160's close (base `cd2466b2`, #306 merged): the
walk residue `UX-1219`-`UX-1232` in four tracks (G, C, H, T), plus the owner's
cards `UX-1233` and `UX-1234`. Review 34 arrived cherry-picked from #307 as
`bb4defa44`. Push-check is run after the close commit.

```text
closed   UX-1219 UX-1220 UX-1221 UX-1222 UX-1223 UX-1224 UX-1225 UX-1226 UX-1227
         UX-1228 UX-1229 UX-1230 UX-1231 UX-1232 UX-1233 UX-1234
filed    UX-1235 UX-1236
open     UX-1235 UX-1236
index    dev_close_task.py --counts: 1189 scenarios, 6 open, 1183 closed
spread   dev_touching.py --spread: 34-184 of 782 test files
```

## What closed

| row | close |
|---|---|
| `UX-1219` `UX-1220` `UX-1221` `UX-1222` | Back and Forward: collapse all, the narrow rail jump box, a card link and Focus each keep the place Back restores |
| `UX-1223` `UX-1224` `UX-1225` `UX-1227` | tables and palette: All rows restores chain order, a printed table states its filter, a binary jump lands on by_binary filtered, the palette starts at its ends |
| `UX-1226` `UX-1228` `UX-1229` | cards and filters: a card label reads as its column title, `downstream:` follows the closure, coarse pointers focus the heading after "+N more" |
| `UX-1230` `UX-1231` `UX-1232` | guards and styleguide: the badge arms and the shared-word rule have tests, section 3d states two rules, the hang guard's sleeper outlasts the harness only as a backstop |
| `UX-1233` | page budget 160,000 -> 165,000 B (owner's card) |
| `UX-1234` | shared titles: "Element duration" column, "Duration" card (owner's card) |

## The figures

- Page half (golden): 159,146 B at `cd2466b2`; tracks H +148, C +272, T +263, W +36 (sum +719, about 159,865 B) under `PAGE_BUDGET_B` 165,000.
- Full suite on the merged tree before fixes: 3 failed, 11,707 passed, 211 skipped in 660.46 s (tier listing of 12 browser guards, selector max 184 > 180, a title clash); fixed in `5a687a53d`.

## Residue

`UX-1235` (a binary jump lands below the stuck tools; `UX-1177`'s assertion
was swapped, a mild weakening) and `UX-1236` (a bare `downstream` comparison
says what it read) are filed open.

## Lessons

- The page budget was raised by owner card at 854 B headroom.
- A derived label surfaced two unreadable column titles (owner card -> `UX-1234`); the fix clashed with the one-title-per-field guard on the merged tree only.
- Implementers hit sandbox refusals on compound shell commands (cost: literal-path scripts).
- #307 collided on `UX-1220` and renumbered.

## Agents

| round | agent | model | task | tokens | tool calls | wall | outcome | friction |
|---|---|---|---|---|---|---|---|---|
| 161 | architect | opus | shape UX-1219..1222 | 46k | 27 | 2.7 m | complete | architect shaped four rows |
| 161 | architect | opus | shape UX-1223,1224,1226,1230,1231 | 70k | 33 | 3.5 m | complete | architect shaped five rows |
| 161 | architect | opus | shape UX-1225,1227,1228,1229,1232 | 52k | 25 | 3.0 m | complete | architect shaped five rows |
| 161 | implementer | sonnet | track G: UX-1232,1230,1231 | 61k | 52 | 12.2 m | complete | track G |
| 161 | verifier | sonnet | track G + UX-1233 | 35k | 32 | 4.5 m | see round-161 | 4 PASS |
| 161 | implementer | opus | track C: UX-1226,1229,1228 (+272 B) | 137k | 94 | 23.6 m | complete | track C |
| 161 | verifier | sonnet | track C | 41k | 29 | 2.8 m | see round-161 | 3 PASS, two labels judged worse (owner card -> UX-1234) |
| 161 | implementer | opus | track H: UX-1221,1219,1222,1220 (+148 B) | 137k | 128 | 36.9 m | complete | track H |
| 161 | verifier | sonnet | track H | 48k | 29 | 6.0 m | see round-161 | 4 PASS |
| 161 | implementer | sonnet | track W: UX-1234 (+36 B) | 79k | 74 | 17.8 m | complete | track W |
| 161 | implementer | opus | track T: UX-1224,1223,1227,1225 (+263 B) | 148k | 132 | 52.3 m | complete | track T |
| 161 | verifier | sonnet | track T | 44k | 29 | 3.6 m | see round-161 | 4 PASS, UX-1177 assertion swap mild weakening (UX-1235) |
