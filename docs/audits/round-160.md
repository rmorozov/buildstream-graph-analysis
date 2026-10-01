# Round 160 — round 159's walk residue, UX-1206..UX-1217

Run on 2026-10-01, from round 159's close (base `ec816233`, round 159's head
plus `UX-1205`'s bst-tests fix): the round-159 walk's residue
`UX-1206`-`UX-1217`, twelve rows in two architect waves, merged, verified,
walked, and a residue pass. Head `c14ba043` before the close commit;
push-check is run after it.

```text
closed   UX-1206 UX-1207 UX-1208 UX-1209 UX-1210 UX-1211 UX-1212 UX-1213 UX-1214
         UX-1215 UX-1216 UX-1217
filed    UX-1219 UX-1220 UX-1221 UX-1222 UX-1223 UX-1224 UX-1225 UX-1226 UX-1227
         UX-1228 UX-1229 UX-1230 UX-1231 UX-1232
open     UX-1219..UX-1232
         UX-1014 UX-1134 UX-1040 UX-902 (open before the round)
index    dev_close_task.py --counts: 1185 scenarios, 18 open, 1167 closed
spread   dev_touching.py --spread: 34-180 of 770 test files
```

## What closed

| row | commits | close |
|---|---|---|
| `UX-1206` | `a5233569`, `9d01daaf`, `ae9cb4b1` | a column's whole displayed name reads as that column; a clause not applied filters nothing; a share-only payload names the column a share |
| `UX-1207` | `8af42bc8`, `a366b669`, `ae9cb4b1` | every map table's key column has one name across header, cell label and Copy (Markdown and JSON) |
| `UX-1208` | `fcf81194`, `a69d1d88`, `486db8af` | at 390 a rail link, Expand all and a chapter press keep the place last read for Back; a pause on the way up is the reading place |
| `UX-1209` | `87fc34e3`, `49c4eb39` | the rail's Markdown checkbox and its label meet the 13 px tools and the target minimum |
| `UX-1210` | `d4b992df`, `2384167f` | the critical path's stub never sorts, counts or outlives a bound; no stale More; print draws every chain box |
| `UX-1211` | `802b3023` | Copy follows the order on screen, sort included |
| `UX-1212` | `dfc7a104` | Focus heads its investigation; a section present without the element says so |
| `UX-1213` | `727727f7`, `b3dca2ae`, `bf7cad62` | a value reads the same in a card, a table, a badge and a sentence; one count formatter; a matched badge says all N matched |
| `UX-1214` | `d46f0575`, `c20bdfb6`, `17b5edaa` | a card's +N more reaches every element it counts: the full direct list is published, `depends_on:` and `blocks:` are exact, the link keeps the View and focuses the filter |
| `UX-1215` | `5fba7b0c` | every browser drive starts on a fresh session history |
| `UX-1216` | `960afb8a`, `cb193189` | the store trend, comparison band and element history drawings are read on a served 4-run page |
| `UX-1217` | `8bd22137` | every browser drive starts on an empty localStorage |

## The owner's decisions

- Ruslan, 2026-10-01 11:35: "let's proceed to next batch UX-1206..1217".
- 12:31, on `UX-1214`'s card: "publish all" - "maybe we already all have all this data like in blast radius table and we can point user there to traverse full list of dependencies as well as full list of dependents". Taken as: `fan_in.direct` published uncapped, the page inverts it, `depends_on:` and `blocks:` exact, both "+N more" links; the transitive `downstream:` filter dropped (+236 B).

## The waves

- Architect A (`UX-1206` `UX-1207` `UX-1210` `UX-1211` `UX-1213` `UX-1214`): tracks T-A (`UX-1206` then `UX-1214`), T-B (`UX-1211` then `UX-1210`, after T-A), T-C (`UX-1207`), T-D (`UX-1213`).
- Architect B (`UX-1208` `UX-1209` `UX-1212` `UX-1215` `UX-1216` `UX-1217`): H (`UX-1215` `UX-1217`, first), M (`UX-1216`, parallel), C (`UX-1209` after H), P (`UX-1208` after H), F (`UX-1212` after H).
- E: `UX-1214`'s owner follow-up on T-A's commit.

## The merged tree

Ten picks onto `ec816233` (H, M, T-C, T-D, T-A, C, P, F) landed as `dfc7a104`;
T-B as `d4b992df`, E as `c20bdfb6`. The integrator's head `fa4ddf9e` (with
`49c4eb39` the `UX-1209` spacing token, `cb193189` the `UX-1216`
OffscreenCanvas; `fresh_history` removed, one tiers row 3 to LARGE): suite
11,624 passed, 2 failed (fixed); page half 158,149 of 160,000 B; macro_micro
controls 866/868; xl_both h 45,587, nodes 7,284.

Verifier B failed `UX-1208`: a wheel-notch climb lets scrollend lulls below the
rail overwrite the place, and Back lands near 300; `a69d1d88` (a higher stop
under the same hash is a climb and does not overwrite) fixed it.

## Verification

Verifier A (`UX-1206` `UX-1207` `UX-1210` `UX-1211` `UX-1213` `UX-1216`): 6
PASS. Verifier B (`UX-1208` `UX-1209` `UX-1212` `UX-1215` `UX-1217`): 4 PASS, 1
FAIL (`UX-1208`, fixed). Residue: 15 unseparated four-digit counts in sentences
and fold summaries (`UX-1213` partial); a filter matching every row read "25 of
1,202", the unfiltered text; the card's "Is a leaf" against the column's "Is
leaf"; `UX-1212`'s F5 case not reproduced (a weak probe). No verdict is recorded for
`UX-1214` in either verifier's list; the walk drove its links (N3-N5).

## The walk

On `a69d1d88`, the 1,202-element page and its `--workload binaries` variant,
1440x900 and 390x844. All five exploration tasks answered. New this round
N1-N8, pre-existing P1-P10; the walk's own record is `walk160-findings.md`.

N1-N8 were fixed in five residue tracks, R and W1-W4: R (`b3dca2ae` every
reader count carries its separator, `bf7cad62` the all-matched badge,
`ae9cb4b1` one leaf title and stray name words said back), W1 (`2384167f` N1
print draws every chain box, `a366b669` N6 map JSON Copy names its columns),
W2 (`9d01daaf` N7 and P1, a spaced unit is one value), W3 (`17b5edaa` N3-N5, +N
more keeps the View, focuses the filter and names its keys), W4 (`486db8af` N2
and N8, Back lands the last place read). `UX-1214`'s Outcome had a gap block
moved into its Motivation for the 80-line cap (W3); the record reads true.
`UX-1208`'s Decision still says "a dwell was rejected"; W4 reversed that and
the deviation says so.

The residue integrator's `c14ba043`: keys as `<code data-raw>`, three count
guards re-based, `measured_elements` into `_RESOURCE_COUNTS`, the card guard
clicks `a.inspect`, tiers narrow 51.6 to 171.1 s and card 4.9 to 6.6 s; `make
test` 11,654 passed, 0 failed, 211 skipped.

P7 (unseparated four-digit numbers, 69 at rest in the walk) re-measured on
`c14ba043` with the walk's census (`s13_digits.mjs`, cc and binaries pages):
the one match is a `dd` whose `textContent` runs the "Width at level" list
together, not a number; nothing filed.

Tier drift on 67 files the round did not touch was judged machine speed
(`integ160/drift.txt`: 30 files over a floor in the parallel report and under it
alone); `UX-420` is the row that covers drift against a clock of another speed
(CI against CI), so none was filed.

## The session mutation check

Mutation check (session, a scratch worktree at `c14ba043`, each row commit's `bga`/`tools`/harness diff reversed, its guard file run single-process): all 13 redden.
`a5233569` UX-1206 3 failed · `8af42bc8` UX-1207 3 failed · `fcf81194` UX-1208 18 failed · `87fc34e3`+`49c4eb39` UX-1209 4 failed · `d4b992df` UX-1210 3 failed · `802b3023` UX-1211 2 failed · `dfc7a104` UX-1212 2 failed · `727727f7` UX-1213 3 failed · `d46f0575` UX-1214 7 failed · `c20bdfb6` UX-1214 follow-up 1 failed · `5fba7b0c`+`8bd22137` UX-1215 4 failed · `8bd22137` UX-1217 2 failed · UX-1216 (test-only) `renderTrend`'s point title dropped 1 failed.
UX-1209 and UX-1215 read green alone: a later commit rewrote the lines the reverse looked for, so each was re-run with that commit reversed too.

## Budgets at close

Measured at `c14ba043` with the volume guard's own instrument
(`test_the_page_has_a_volume_budget.py`'s `looked` and `budget_for`) and
`view.page_half`:

```text
page half    159,147 of 160,000 B
macro_micro  h 38,965/39,188  words 13,068/13,200  controls 866/868  nodes 6,860/7,900
xl_both      h 45,587/46,822  words 12,841/13,200  controls 1,161/1,192  nodes 7,286/7,500
```

## What was filed

`UX-1219`-`UX-1232`, from the round-160 walk and verification, the residue
pass and the integration:

- `UX-1219` (Medium) Back after Collapse all reopens what it folded (P2)
- `UX-1220` (Medium) the narrow rail jump box keeps the place read for Back (P3)
- `UX-1221` (Low) Back after a card link restores the card offset (P4)
- `UX-1222` (Low) Focus is one step Back (P5)
- `UX-1223` (Low) returning to All rows restores the chain order, or the badge says sorted (P6)
- `UX-1224` (Low) a printed filtered table states its filter (P8)
- `UX-1225` (Low) a jump to a binary lands on the filtered by_binary list (P10)
- `UX-1226` (Low) a card label reads as its column title (P9, track R)
- `UX-1227` (Low) the palette's first ArrowDown lands on its first row
- `UX-1228` (Low) a transitive `downstream:` clause, dropped from `UX-1214` for budget
- `UX-1229` (Low) the touch keyboard after +N more is measured at 390
- `UX-1230` (Low) the all-N-matched arm and the owned-words rule have a mutation that reddens them
- `UX-1231` (Low) the styleguide states two rules: a filtering link moves focus to its filter, an entry naming no View is at the opening View
- `UX-1232` (Medium) the hang guard's sleeper took 49.9 s of wall at 2.05 s of user

## Review cadence

Review 33 recorded 1,142 closed rows; 1,167 are closed now, a distance of 25
against the bound of 25 (`tests/unit/test_the_review_has_a_cadence.py`,
green). No review is due; one more closed row makes it due.

## Agents

| round | agent | model | task | tokens | tool calls | wall | outcome | friction |
|---|---|---|---|---|---|---|---|---|
| 160 | architect | opus | architect: A, UX-1206 1207 1210 1211 1213 1214 | 169k | 86 | 10.3 m | see round-160 | cost: tracks T-A T-B T-C T-D; page half est +2,148 upper; Q UX-1214 dependents (arch160/A.md) |
| 160 | architect | opus | architect: B, UX-1208 1209 1212 1215 1216 1217 | 158k | 66 | 18.8 m | see round-160 | cost: tracks H M C P F; label-as-target Q, default a wrapping label counts (arch160/B.md) |
| 160 | implementer | opus | implementer: T-A UX-1206 UX-1214 | 178k | 127 | 26.8 m | see round-160 | cost: +900 B; filter link, depends_on hidden list column; residue: no-column sentence lists hidden Depends on |
| 160 | implementer | sonnet | implementer: T-C UX-1207 | 61k | 32 | 6.9 m | see round-160 | cost: -380 B; mapTitles, relabelHead gone |
| 160 | implementer | sonnet | implementer: T-D UX-1213 | 80k | 64 | 15.6 m | see round-160 | cost: +88 B; residue: fold summaries print unseparated counts (decision.js element.js sections.js views.js) |
| 160 | implementer | opus | implementer: T-B UX-1211 UX-1210 | 418k | 117 | 37.7 m | see round-160 | cost: +63 B; re-based chain fold guard |
| 160 | implementer | sonnet | implementer: H UX-1215 UX-1217 | 250k | 64 | 41.8 m | see round-160 | cost: driver resets history and clears localStorage; fresh_history kept as no-op; stale comment test_a_control_acts_on_what_it_names.py |
| 160 | implementer | sonnet | implementer: M UX-1216 | 55k | 44 | 6.1 m | see round-160 | cost: 0 B; node harness retired; test_a_mark_says_its_value 14.96 s, tier check |
| 160 | implementer | sonnet | implementer: C UX-1209 | 38k | 31 | 7.3 m | see round-160 | cost: +278 B CSS; make lint not run |
| 160 | implementer | sonnet | implementer: F UX-1212 | 60k | 34 | 8.7 m | see round-160 | cost: +130 B; (a) not reproduced; residue: palette first ArrowDown lands on row 1 |
| 160 | implementer | opus | implementer: P UX-1208 and its follow-up | 164k | 76 | 55.2 m | see round-160 | cost: +108 B then +48 B; verifier B wheel-climb FAIL fixed by e5933525 |
| 160 | implementer | opus | implementer: E UX-1214 follow-up, publish all | 157k | 127 | 25.3 m | see round-160 | cost: page +72 B, data +89 B big, +717 B xl_both; downstream: dropped, +236 B |
| 160 | integrator | opus | integrator: ten picks, T-B and E, head fa4ddf9e | 326k | 63 | 66.2 m | see round-160 | cost: suite 11,624 p / 2 f fixed; page half 158,149/160,000; fresh_history removed, tiers 3 to LARGE |
| 160 | verifier | sonnet | verifier: A UX-1206 1207 1210 1211 1213 1216, 6 PASS | 228k | 112 | 35.6 m | see round-160 | cost: residue: 15 unseparated counts, all-rows badge, Is a leaf vs Is leaf |
| 160 | verifier | sonnet | verifier: B UX-1208 1209 1212 1215 1217, 4 PASS 1 FAIL | 74k | 81 | 12 m | see round-160 | cost: UX-1208 wheel-notch climb FAIL (fixed a69d1d88); 1212(a) F5 not reproduced |
| 160 | walker | opus | walker: 5/5 tasks answered, N1-N8 new, P1-P10 pre-existing | 234k | 166 | 35.6 m | see round-160 | cost: walk160-findings.md |
| 160 | implementer | opus | implementer: residue R counts, all-matched badge, Is leaf | 207k | 190 | 37.2 m | see round-160 | cost: 773b5201 b3a1822a 12ba7342; page half +243 B; two arms unguarded (filed) |
| 160 | implementer | sonnet | implementer: residue W2 spaced unit (P1 N7) | 39k | 28 | 5.1 m | see round-160 | cost: cefdb790; 2 failed under mutation |
| 160 | implementer | sonnet | implementer: residue W1 print chain, JSON Copy names (N1 N6) | 68k | 31 | 10.2 m | see round-160 | cost: 885af833 cec1339d; 4 failed under mutation |
| 160 | implementer | opus | implementer: residue W3 +N more View, focus, keys (N3-N5) | 274k | 96 | 28.4 m | see round-160 | cost: 21cf393b +288 B; gap block moved to Motivation for the 80-line cap; touch keyboard at 390 unmeasured |
| 160 | implementer | opus | implementer: residue W4 390 Back place (N2 N8) | 237k | 69 | 35 m | see round-160 | cost: ecaab997 +140 B; guard 12 to 27 cases, 15 red on a69d1d88; tiers narrow 51.6 to 171.1 s |
| 160 | integrator | opus | integrator: residue picked, head c14ba043 | 384k | 107 | 43.6 m | see round-160 | cost: make test 11,654 p / 0 f / 211 s; page half 159,146/160,000; hang test intermittent (filed) |
| 160 | closer | sonnet | closer: UX-1206..UX-1217, UX-1219..UX-1232 filed | 129k | 55 | 7 m | see round-160 | cost: filing 14 rows from the walk and residue; P7 census on HEAD read 0; budgets measured with the volume guard's own instrument |
