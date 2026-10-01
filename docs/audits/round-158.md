# Round 158 — the data-exploration review and round 157's residue

Run on 2026-10-01, from round 158's filing on 2026-09-30 (`8a531cbb`): the
data-exploration review's `UX-1182`-`UX-1193` and round 157's residue
`UX-1176`-`UX-1181`, eighteen rows in three waves, merged, verified, walked.
Head `b710be58` before the close commit, push-check run after it.

```text
closed   UX-1176 UX-1177 UX-1178 UX-1179 UX-1180 UX-1181 UX-1182 UX-1183 UX-1184
         UX-1185 UX-1186 UX-1187 UX-1188 UX-1189 UX-1190 UX-1191 UX-1192 UX-1193
filed    UX-1194 UX-1195 UX-1196 UX-1197 UX-1198 UX-1199 UX-1200 UX-1201 UX-1202
         UX-1203 UX-1204 UX-1205
open     UX-1194..UX-1205
         UX-1014 UX-1134 UX-1040 UX-902 (open before the round)
index    dev_close_task.py --counts: 1158 scenarios, 16 open, 1142 closed
spread   dev_touching.py --spread: 34-180 of 764 test files
```

## What closed

| row | commits | close |
|---|---|---|
| `UX-1176` | `ddcd8a32` | the no-match lines, the badges and the tables reach a screen reader; the clip rule is guarded |
| `UX-1177` | `d36ae1b9`, `1901e8a7` | Jump and the rail agree on level folds and presets; Jump lands on its target's row |
| `UX-1178` | `321482f8`, `bbac8143` | the narrow page keeps its place; a landing yields to the reader who moves first |
| `UX-1179` | `6a780d77`, `474f4eb3` | print and find-in-page reach folded content; Jump opens and lands on the element's card |
| `UX-1180` | `f953ad5d` | a ratio needs a span, an instant is a date, the gate line is spaced, the two-plane console is read |
| `UX-1181` | `108d8f7f` | one page-half instrument, in bytes (`view.page_half`) |
| `UX-1182` | `4fdbc5d0` | `gen-synthetic --workload binaries`, hundreds of fake binaries per element |
| `UX-1183` | `ba79341b`, `b710be58` | every (element, binary) pair Plane 2 saw reaches the page; "+N more" lands on binary_cost filtered |
| `UX-1184` | `3857106d` | the task table's share column says it is a share |
| `UX-1185` | `ca5a077f`, `c0c4c2c2` | paging continues the ranking; a filter edit returns the pager to its first rows |
| `UX-1186` | `e6019f88` | the element, task and binary tables join Focus, Inspect and the jump box |
| `UX-1187` | `196db391`, `1d1cd1b4`, `bc7b769e` | every element view carries duration and level; the card lists what an element blocks |
| `UX-1188` | `1877c00d` | the compare chapter states how many moved, and is one table |
| `UX-1189` | `7ee5d207` | Copy takes the matched population; one page-wide Markdown box |
| `UX-1190` | `cff2019a` | a sortable header is a button that ranks the population |
| `UX-1191` | `a83c966a` | a key column matches exactly; a one-op task table says its op once |
| `UX-1192` | `907a6b60` | a mark says its value; a strip survives an outlier |
| `UX-1193` | `a2d7170c` | the Latent heavies preset reads the section's population |

## The owner's decisions

- D1 to D4 (Ruslan, 2026-09-30 19:04, "your defaults looks good to try"): D1 unroll at 80 rows or fewer, D2 population maps are tables with a linked key, D3 every element-binary pair published, D4 the pager walks the opening ranking.
- Controls, "Consolidate + raise" (19:26): one page-wide Markdown toggle (`UX-1189`), and xl_both's controls bound 900 to 1,020, with 1,006 measured.
- xl_both height 43,500 to 44,629 px, on D1.
- The small page's opened height 38,200 to 38,400 px, on D1.
- golden's deep-leaf bound 0.52 to 0.53 (`1d1cd1b4`), on a card Ruslan has not yet answered; the default taken.
- `UX-1188`'s table replaces the culprit lists, on the session's default (unanswered).
- Route (b) of `UX-1182`, a real capture, is a follow-up row (`UX-1205`).

## The waves

- Wave 1, base `8a531cbb`: A1 `UX-1182`, A2 `UX-1181`, B1 `UX-1185` `UX-1190` `UX-1189`, C2 `UX-1188`, C3 `UX-1192`, C4 `UX-1178`, C5 `UX-1180`.
- Wave 2, early, on A1's `UX-1182` commit: A3 `UX-1193` `UX-1183` `UX-1187` (partial), B2 `UX-1184` `UX-1186`.
- Wave 3, on `9e9ef410`: D1 `UX-1191`, D2 `UX-1187` (the Blocks list), D3 `UX-1176` `UX-1177` `UX-1179`.

## The merged tree

Waves 1 and 2 merged at `79aa4520` (page 148,272 B; xl_both controls
1,006/1,020, height 43,706/44,629 px; macro words 12,994/13,200, opened
38,307/38,400). The container restarted mid-integration; the integrator's
commits survived at `df55fc8b` and a second integrator resumed from there.
Integrator fixes: `978d5a77`, `c36cc41a`, `d528c860`, `bbac8143`, `ec571685`,
`df55fc8b`, `c72c23c7`, `961185e1`, `d7d2ece3`, `82fa1d91`, `79aa4520`. The fix
pass to `9e9ef410` (`589a681f`..`9e9ef410`, ten commits) cleared A1's lint, B1's
label, C3's print golden, C5's vocabulary, the styleguide rows and A3's
factory: push-check green, page 148,380 B, xl_both 43,730/44,629 px,
1,007/1,020 controls, 7,487/7,500 nodes. Wave 3 merged with `45357ae4`,
`dbf5f7bf`, `97b7da75` and `43397b70`.

## The session mutation check

Each track's diff undone and its row guard run: 18 of 18 guards redden.
`UX-1193`'s by hand: 2 failed; the scripted undo was partial (`mut158.log`).

## Verification and the residue pass

VERIFY-1 (`UX-1182`-`UX-1190`): 9 PASS. VERIFY-2 (`UX-1176`-`UX-1181`,
`UX-1191`-`UX-1193`): 8 PASS, `UX-1179` FAIL: a Jump press on an unmounted
element built its card `hidden=until-found` at height 0 in a closed chapter
and landed about 700 px past it. The residue pass (`474f4eb3`, `1901e8a7`,
`c0c4c2c2`, `b710be58`) fixed it and three walk findings (`UX-1177`'s Jump
landing, `UX-1185`'s pager reset, `UX-1183`'s "+N more"); push-check green at
`b710be58`. `test_jump_finds_what_the_rail_lists.py` went 2.7 s to 9.7 s;
re-tiered at the close.

## The walk

The walker drove the 1,202-element page and its `--workload binaries` variant,
`golden` and `macro_micro`, at 1440x900 and 390x844, on `43397b70`: 17 new
findings, 6 pre-existing; console clean. The review's five tasks went from
dead-ends to 3 answered (how long X took, 2 actions; the 10 slowest in layer
12, 4; elements sharing binary Y, 3), 1 half (on the path yes, Blocks drawn
only on an on-demand card) and 1 wrong (`op:BUILD > 60s` returns toolchain.bst
at its 4.9 min share).

## What was filed

`UX-1194`-`UX-1205`:

- `UX-1194` (High) op: and a duration threshold meet on the table that holds durations
- `UX-1195` (High) the filter grammar matches what the page shows
- `UX-1196` (High) a head-and-tail fold prints, copies and jumps to every row it holds, and a short table keeps its sort
- `UX-1197` the Rows-shown bound across Next, sort and the link; announcements and names
- `UX-1198` Focus shows the focused element's row in each keyed table, and a focus link restores the bar
- `UX-1199` the element-keyed tables declare their key; by_binary, binary_cost and serial_chains rank and name their quantity
- `UX-1200` every element card lists what it blocks, as links, with one count
- `UX-1201` the compare table says "both" in words and scales negative durations
- `UX-1202` plotted values as bounded text; an empty status at rest
- `UX-1203` the rail's tools and the pager; rail Next, Back and the card folds
- `UX-1204` the uid box and SQL paste at 390; views.js and element.js titles
- `UX-1205` (Low) a real capture of fake sleeping binaries under the LD_PRELOAD hook

## Review cadence

Review 32 recorded 1,109 closed rows; 1,142 are closed now, a distance of 33
against the bound of 25 (`tests/unit/test_the_review_has_a_cadence.py`, red).
Review 33 is due.

## Agents

| round | agent | model | task | tokens | tool calls | wall | outcome | friction |
|---|---|---|---|---|---|---|---|---|
| 158 | filer | opus | filer: the data-exploration review filed as UX-1182..UX-1193 | — | — | — | see round-158 | cost: owner decisions D1-D4 recorded as Decisions; 8a531cbb |
| 158 | architect | opus | architect: group A, UX-1181 UX-1182 UX-1183 | — | — | — | see round-158 | cost: shaped at 8a531cbb, read only (arch158/A.md) |
| 158 | architect | opus | architect: group B, UX-1184 1185 1186 1189 1190 1191 | — | — | — | see round-158 | cost: shaped at 8a531cbb, read only (arch158/B.md) |
| 158 | architect | opus | architect: group C, UX-1176..1180 1187 1188 1192 1193 | — | — | — | see round-158 | cost: shaped at 8a531cbb, read only (arch158/C.md) |
| 158 | implementer | sonnet | implementer: A2 UX-1181 one page-half instrument | — | — | ~12m | see round-158 | cost: page net 0; test_a_page_half_is_read_once.py stays small; 4 mutations red; _halves re-based in test_the_exports_data_half_has_a_budget.py |
| 158 | implementer | opus | implementer: A1 UX-1182 gen-synthetic --workload binaries | ~100k | — | ~35m | see round-158 | cost: tests.pages.heavy_binary_run; 112 elements, top-8 200-500 binaries; tiers row owed; 8 mutations red |
| 158 | implementer | sonnet | implementer: C4 UX-1178 the narrow page keeps its place | ~100k | — | ~45m | see round-158 | cost: +234 B; re-based test_focus_keeps_the_reading_position.py with a 600 ms wait; the Expand-all landing pulled a scrolling reader back (fixed at integration, bbac8143) |
| 158 | implementer | opus | implementer: C2 UX-1188 the compare chapter is one table | ~150k | — | ~60m | see round-158 | cost: xl_both +27 controls (913), +818 px (42,855), +28 B; Change cells lack a + sign; guard fixture 12.6 s |
| 158 | implementer | sonnet | implementer: C5 UX-1180 values and console | — | — | — | see round-158 | cost: +~430 B; test_a_value_is_what_it_names.py MEDIUM; console guard gained an 8th boot; bga:instant hint; 5 mutations red |
| 158 | implementer | opus | implementer: C3 UX-1192 a mark says its value | ~185k | — | ~75m | see round-158 | cost: +732 B; titles 115/50/132; UNRESOLVABLE 80 to 81; views.js/element.js drawings untitled (residue); dev_sizes --adopt failed pylint |
| 158 | implementer | opus | implementer: B2 UX-1184 UX-1186 share column and keyed tables | ~230k | — | ~2h | see round-158 | cost: +848 B; xl_both controls +79 (965), height +171; UNRESOLVABLE 80 to 82; serial_chains Duration to Total; rendered strings regenerated |
| 158 | implementer | opus | implementer: B1 UX-1185 UX-1190 UX-1189 pager, sort, copy | ~270k | — | 2h40m | see round-158 | cost: +1,167 B; controls 895 after consolidation; height +1,037 (consolidation_candidates unrolled by D1); small bound 38,200 to 38,400 (D1) |
| 158 | implementer | opus | implementer: A3 UX-1193 UX-1183 UX-1187 (partial) | ~310k | — | 2.5h | see round-158 | cost: +420 B; Blocks list held, golden deep-leaf share 0.5193 to 0.5226 over 0.52; card paging of binaries dropped (words over) |
| 158 | integrator | opus | integrator: waves 1-2 merged, head 79aa4520 | — | — | — | see round-158 | cost: container restart mid-integration, resumed at df55fc8b; holds A1 lint, B1 label, C3 print golden, C5 vocabulary, styleguide rows, A3 factory; xl_both controls 1,006/1,020, height 43,706/44,629 |
| 158 | integrator | opus | integrator: fix pass, head 9e9ef410 | — | — | — | see round-158 | cost: push-check green; page 148,380 B; xl_both 43,730/44,629 px, 1,007/1,020 controls |
| 158 | implementer | opus | implementer: D2 UX-1187 Blocks list | ~110k | — | 1.2h | see round-158 | cost: +96 B; depth bound 0.52 to 0.53 default taken; test_an_element_view_answers_whole.py 4.5 s to 16 s; +N more never drawn on a real page (residue) |
| 158 | implementer | opus | implementer: D1 UX-1191 a key column matches exactly | ~215k | — | 1h50m | see round-158 | cost: +1,283 B; controls -9; retired test_a_capped_table_filters_what_it_sorts.py; element-view uid box overflows at 390 (residue) |
| 158 | implementer | opus | implementer: D3 UX-1176 UX-1177 UX-1179 | ~300k | — | 3.5h | see round-158 | cost: +1,717 B; edited OPEN_EVERY_DOOR_JS; opened SQL paste overflows .investigate at 390 (residue); real Ctrl+F unguarded |
| 158 | verifier | sonnet | verifier: VERIFY-2 UX-1176..1181 1191..1193, 8 PASS 1 FAIL | — | — | — | see round-158 | cost: UX-1179 FAIL, Jump on an unmounted element lands ~700 px past a height-0 card; #handoff-refusal empty status; badge of 4,057; binary: make no hint |
| 158 | verifier | sonnet | verifier: VERIFY-1 UX-1182..1190, 9 PASS | — | — | — | see round-158 | cost: by_binary title; serial_chains Top 10 by Rank; <=10-row tables unsortable after UX-1190; binary_cost strip label 4,057 values |
| 158 | session | opus | session: mutation check, 18 of 18 red | — | — | — | see round-158 | cost: UX-1193 by hand, the scripted undo partial (mut158.log) |
| 158 | walker | sonnet | walker: 17 new findings, 6 pre-existing, task walk 3 yes 1 half 1 wrong | — | — | — | see round-158 | cost: walk158-findings.md; op:BUILD > 60s answers from the share table |
| 158 | implementer | opus | residue pass: UX-1179 UX-1177 UX-1185 UX-1183, head b710be58 | — | — | — | see round-158 | cost: 474f4eb3 1901e8a7 c0c4c2c2 b710be58; push-check green; test_jump_finds_what_the_rail_lists.py 2.7 s to 10 s |
| 158 | closer | opus | closer: UX-1176..UX-1193, UX-1194..UX-1205 filed | — | — | — | see round-158 | cost: filing 12 rows from the walk; tiers re-timed (jump 9.7 s, print 13.5 s, pager 10.3 s) |
