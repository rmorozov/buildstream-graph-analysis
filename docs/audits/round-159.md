# Round 159 — round 158's walk residue, UX-1194..UX-1205

Run on 2026-10-01, from round 158's close (`9d257016`): the round-158 walk's
residue `UX-1194`-`UX-1205`, twelve rows in two waves, merged, verified,
walked, and a residue pass. Head `911b36d7` before the close commit;
push-check is run after it.

```text
closed   UX-1194 UX-1195 UX-1196 UX-1197 UX-1198 UX-1199 UX-1200 UX-1201 UX-1202
         UX-1203 UX-1204 UX-1205
filed    UX-1206 UX-1207 UX-1208 UX-1209 UX-1210 UX-1211 UX-1212 UX-1213 UX-1214
         UX-1215 UX-1216 UX-1217
open     UX-1206..UX-1217
         UX-1014 UX-1134 UX-1040 UX-902 (open before the round)
index    dev_close_task.py --counts: 1170 scenarios, 16 open, 1154 closed
spread   dev_touching.py --spread: 34-180 of 767 test files
```

## What closed

| row | commits | close |
|---|---|---|
| `UX-1194` | `5bdcc5fa`, `d729e962`, `3d323c2c`, `5add0d6c`, `4b68e5e8`, `4f75a41d`, `28bc8b92`, `911b36d7` | op: and a duration threshold meet on the task table's Duration; a share is marked and refused as a duration |
| `UX-1195` | `8068b52b` | a clause matches a constant column, the displayed word and the column's name |
| `UX-1196` | `f2d79fa5`, `5b3ee954`, `382da1d7` | a head-and-tail fold prints, copies and jumps to every row; a short table keeps its sort |
| `UX-1197` | `d830311a`, `6c8d96ac` | the Rows-shown bound holds across Next, sort and the link; a page step and a sort are announced and named |
| `UX-1198` | `7032a9c7`, `747893f7` | Focus shows the focused element's row in each keyed table; a focus link restores the bar |
| `UX-1199` | `d5670b69` | the element-keyed tables declare their key; leaves_detail is the elements table's Leaves view |
| `UX-1200` | `5d4f6044`, `8b00c9d3`, `d0443917`, `0e3da187` | every element card, ranked cards too, lists Blocks and Depends on as links with one count |
| `UX-1201` | `319fe213`, `0e92581f` | the compare table says In both runs and a negative duration scales |
| `UX-1202` | `e64363a9` | plotted values reach a reader as text bounded at 600 chars; no empty status at rest |
| `UX-1203` | `82370190`, `31b5971b`, `c31ada8b`, `a4de3567`, `11fc3675`, `1b11fae2` | the rail's tools and the pager read as one set; rail Next, Back and the card folds keep their order |
| `UX-1204` | `32d762b5` | the element-view uid box and an opened SQL paste fit at 390 |
| `UX-1205` | `aeb7925e` | a bst-marked guard captures fake sleeping binaries under the hook; rides bst-tests |

## The owner's decisions

- Ruslan, 2026-10-01 05:27: "let's take ux-1194..1205 as next batch".
- 05:48, "Ride bst-tests": `UX-1205`'s guard gates in the `bst-tests` job (pin 53 to 54).
- 05:49, "Full lists": Blocks and Depends on on all ranked cards, the bounds raised by the measured delta - class 50 height 38,400 to 39,188 and controls 800 to 868; class 4,100 height 44,629 to 46,822 and controls 1,020 to 1,192. The nodes raise to 7,720 was reverted to 7,500 (`0e3da187`): the merged tree reads 7,284.

## The waves

- Wave 1, base `27f21d10`: T1 `UX-1195` `UX-1197` `UX-1196`, T2 `UX-1194` `UX-1199`, B2 `UX-1200`, B3 `UX-1201`, B4 `UX-1202` `UX-1204`, B5 `UX-1205`.
- Wave 2, on the rows they needed: B1 `UX-1198` on T2's `UX-1199` (`d5670b69` here) plus T1's `UX-1195`; T3 `UX-1203` on T1's `UX-1196` (`f2d79fa5` here).

## The merged tree

Wave 1 merged at `ff46bf6b` (page 155,105 B; macro_micro h 38,965/39,188, words
13,068, controls 866/868; xl_both h 45,698/46,822, words 12,830, controls
1,160/1,192, nodes 7,284/7,720); suite 11,519 passed, 2 failed (the
verification log, fixed; the hang guard under load, 6/6 on rerun). B1 and T3
picked as `7032a9c7` and `82370190`. T3 found sortable headers printing blank
(pre-existing since `UX-1190`); `31b5971b` prints a sortable header's label.
Push-check red 4 at `31b5971b`: the verification-log anchor (re-grounded last
in this close) and `UX-1203`'s expand/collapse guard under full-suite load,
three times. Its root cause (`c31ada8b`): Chrome caps a tab's history at 50
entries, and the worker's shared tab pruned the guard's own pushState entries;
the guard opts in to `fresh_history`.

## Verification

Verifier A (`UX-1194`-`UX-1199`): 6 PASS. Verifier B (`UX-1200`-`UX-1205`): 6
PASS; `UX-1205`'s bst half is CI-only (54 collected, pin 54). 12/12 PASS, with
residue: an older payload's share head unmarked; rail Next after a toc click;
`duration(-400)` printing "-0 ms"; the nodes bound raise unneeded.

## The walk

On `31b5971b`, the 1,202-element page and its `--workload binaries` variant,
1440x900 and 390x844, console clean. All five review tasks answered: how long X
built, 2 actions; op BUILD over 60 s, 3 ("none of 1,202 match", true); 10
slowest in layer 12, 4; on the critical path and what it blocks, 2; elements
sharing binary Y, 3. New this round N1-N10, pre-existing P1-P9.

N1-N8 were fixed in three residue tracks: H (`11fc3675` N1 in-page links keep
filters, `747893f7` N2 Focus across Back, `1b11fae2` N3 Expand/Collapse all
entries keep folds and place), T (`d729e962` N4, the analyzer's share sweep
held a 0 ms task's share to the run's end; `6c8d96ac` N6; `4b68e5e8` N7;
`5add0d6c` N8; `3d323c2c` the older payload; `0e92581f` "-0 ms") and M
(`5b3ee954` N5, `a4de3567` rail Next after toc, `0e3da187` nodes 7,500). Pass 3
at `afd84bdc` regenerated analyze.json and re-timed tiers.

## The holds

Four holds at `afd84bdc`, fixed: `4f75a41d` sizes (analyzer.py +4 lines);
`382da1d7` the jump guard re-based (a jumped-to row's expected top is its
table's stuck tools, 158 vs 60; the code was right); `28bc8b92` only a narrow
table's header breaks between words in print (break-word overflowed 390 at 3
pages); `911b36d7` the Markdown copy guard leaves no copy format behind (one
Chrome per worker shares localStorage across files; JSONDecodeError at char 0).

## The session mutation check

Mutation check at `911b36d7`: undoing each row commit's `bga/` and `tools/` diff reddens its guard, 13 of 13. UX-1194's partial undo errors at setup (13 errors); its four one-line mutations each fail cleanly in the track.

## Budgets at close

```text
page half    156,708 of 160,000 B
macro_micro  h 38,965/39,188  words 13,068/13,200  controls 866/868  nodes 6,858/7,900
xl_both      h 45,683/46,822  words 12,830/13,200  controls 1,160/1,192  nodes 7,284/7,500
```

## What was filed

`UX-1206`-`UX-1217`:

- `UX-1206` (Medium) a column's whole displayed name reads as that column (N9)
- `UX-1207` (Low) every map table's key column has one name across header, cell label and Copy
- `UX-1208` (Medium) at 390 a rail link and Expand all keep the reader's place for Back
- `UX-1209` (Low) the rail's Markdown checkbox matches its 13 px tools (N10)
- `UX-1210` (Medium) the critical path's stub never sorts, counts or outlives a bound; no stale More (P1, P3)
- `UX-1211` (Medium) Copy follows the order on screen (P2)
- `UX-1212` (Low) Focus heads its investigation and names what the document holds (P4, P9)
- `UX-1213` (Low) a value reads the same in a card, a table, a badge and a sentence (P5, P6, P7)
- `UX-1214` (Low) a card's +N more Blocks reach every element it counts (P8)
- `UX-1215` (Medium) a Back-pushing browser guard runs on a fresh history
- `UX-1216` (Low) the store trend, comparison band and element history drawings are on a built test page
- `UX-1217` (Medium) a browser guard leaves no preference behind in the worker's shared Chrome

## Review cadence

Review 33 recorded 1,142 closed rows; 1,154 are closed now, a distance of 12
against the bound of 25 (`tests/unit/test_the_review_has_a_cadence.py`, green).
No review is due.

## Agents

| round | agent | model | task | tokens | tool calls | wall | outcome | friction |
|---|---|---|---|---|---|---|---|---|
| 159 | architect | opus | architect: A, UX-1194 1195 1196 1197 1199 1203 | — | — | — | see round-159 | cost: tracks T1 T2 T3; trades macro_micro Top-N selects (-3), share lead link (-1); page half est 156.1 KB (arch159/A.md) |
| 159 | architect | opus | architect: B, UX-1198 1200 1201 1202 1204 1205 | — | — | — | see round-159 | cost: tracks B1-B5; Q1 ranked-card Blocks +2,193 px/+172 controls, Q2 UX-1205 gate, both to the owner (arch159/B.md) |
| 159 | implementer | opus | implementer: T1 UX-1195 UX-1197 UX-1196 | — | — | — | see round-159 | cost: +1,250 B; mm controls 790, h 38,389; app.js revealAndLand near T3 popstate |
| 159 | implementer | opus | implementer: T2 UX-1194 UX-1199 | — | — | — | see round-159 | cost: +772 B; task_durations_us; leaves_detail to the Leaves view; mm controls 796/800; parseQuery data-share skip owed by T1 |
| 159 | implementer | opus | implementer: T3 UX-1203 rail tools and pager | — | — | — | see round-159 | cost: +499 B; tier LARGE; sortable headers print blank (pre-existing, fixed 31b5971b); guard red under full-suite load (fixed c31ada8b) |
| 159 | implementer | opus | implementer: B1 UX-1198 Focus filters each keyed table | — | — | — | see round-159 | cost: +604 B; base T2 UX-1199 + T1 UX-1195; 7 mutations red |
| 159 | implementer | opus | implementer: B2 UX-1200 Blocks lists as links | — | — | — | see round-159 | cost: +204 B; bounds raised on the owner's 05:49 decision; dev_sizes --adopt failed (pylint exited 32) |
| 159 | implementer | sonnet | implementer: B3 UX-1201 compare table words and negatives | ~45k | — | ~15m | see round-159 | cost: ~+0.2 KB; 2 mutations red; -0 ms residue |
| 159 | implementer | opus | implementer: B4 UX-1202 UX-1204 bounded values, 390 fit | — | — | — | see round-159 | cost: +706 B; longest aria-label 12,170 to 283; 390 pastes 17/17 to 0 |
| 159 | implementer | opus | implementer: B5 UX-1205 a real capture under the hook | ~100k | — | ~35m | see round-159 | cost: ci.yml pin 53 to 54; bst half unrun here, CI is evidence; conftest skip count 6 to 7 |
| 159 | integrator | opus | integrator: wave 1 merged, head ff46bf6b | — | — | — | see round-159 | cost: suite 11,519 p / 2 f / 211 s; verification-log entry credits UX-1194 (re-grounded at the close) |
| 159 | integrator | opus | integrator: B1 and T3 picked, head 31b5971b | — | — | — | see round-159 | cost: print th-sort display:contents; push-check red 4 (verif-log anchor, UX-1203 guard under load x3) |
| 159 | integrator | opus | integrator: residue picked, pass 3, head afd84bdc | — | — | — | see round-159 | cost: analyze.json regen, tiers re-timed; holds: sizes, jump guard, print th at 390, copy-fold JSONDecodeError; suite 11,548 p / 6 f / 211 s |
| 159 | verifier | sonnet | verifier: A UX-1194 1195 1196 1197 1198 1199, 6 PASS | — | — | — | see round-159 | cost: residue: older payload share head not marked data-share |
| 159 | verifier | sonnet | verifier: B UX-1200..1205, 6 PASS | — | — | — | see round-159 | cost: residue: rail Next after toc, -0 ms, nodes bound 7,720 unneeded; drawings on no built page |
| 159 | walker | sonnet | walker: 5/5 tasks answered, N1-N10 new, P1-P9 pre-existing | — | — | — | see round-159 | cost: walk159-findings.md; in-page links cleared every filter (N1) |
| 159 | implementer | opus | fixer: UX-1203 guard, Chrome's 50-entry history cap | — | — | — | see round-159 | cost: c31ada8b, --fresh-history opt-in; other Back guards exposed (filed) |
| 159 | implementer | opus | residue H: N1 N2 N3 history and focus | — | — | — | see round-159 | cost: app.js +922 B; 390 rail-link Back and Expand all scrollY 24,872 left (filed) |
| 159 | implementer | opus | residue T: old payload, N4 share sweep, N6 N7 N8, -0 ms | — | — | — | see round-159 | cost: analyzer bug, a 0 ms task held share to the run's end; UX-1192 guard re-based; other maps still Name (filed) |
| 159 | implementer | opus | residue M: N5 sticky tools, rail Next toc, nodes 7,500 | — | — | — | see round-159 | cost: test_print_and_find tiers row 13.5 s vs 30.9 s |
| 159 | implementer | opus | holds fixer: sizes, jump guard, print th, copy-format leak, head 911b36d7 | — | — | — | see round-159 | cost: localStorage shared across files in one Chrome per worker (filed) |
| 159 | closer | opus | closer: UX-1194..UX-1205, UX-1206..UX-1217 filed | — | — | — | see round-159 | cost: filing 12 rows from the walk and verifiers; verification-log re-ground row last |
