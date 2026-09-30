# Round 154 — the review's fourteen rows, fixed

Run on 2026-09-30 from round 153's filing: `UX-1140`-`UX-1153`, the view UI
review's findings on a 114-element two-plane page, seven tracks, merged,
verified, walked, and a residue pass. Head `00a3fc1b`, push-check green.

```text
closed   UX-1140 UX-1141 UX-1142 UX-1143 UX-1144 UX-1145 UX-1146 UX-1147
         UX-1148 UX-1149 UX-1150 UX-1151 UX-1152 UX-1153
filed    UX-1154 UX-1155 UX-1156 UX-1157 UX-1158 UX-1159 UX-1160
open     UX-1154 UX-1155 UX-1156 UX-1157 UX-1158 UX-1159 UX-1160
         UX-1014 UX-1134 UX-1040 (open before the round)
index    dev_close_task.py --counts: 1113 scenarios, 11 open, 1102 closed
spread   dev_touching.py --spread: 34-180 of 736 test files
```

## What closed

| row | gap | close |
|---|---|---|
| `UX-1140` | 11 raw floats, 23 glued units at 1440 and 390 | 0 and 0; producer prose (`bga/shown.py`) prints as the page does |
| `UX-1141` | 20 bare-token nodes (two-plane), 17 `golden`, 31 `macro_micro` | 0 / 0 / 0, no repeated term |
| `UX-1142` | 15 nodes naming a task id or `docs/`; 36 schema descriptions | 0 nodes, 0 descriptions |
| `UX-1143` | first block `DL.pairs`, 7 repeated terms, 3 detail lines | first block `P.section-lead`, 0, 0 |
| `UX-1144` | 3 failed, 2 passed (8 concepts, several names each) | 5 passed; "Peak tasks at once" joins the table |
| `UX-1145` | 257 `dd` narrower than its `dt`; 11 chips over 30 px; sticky chrome 19.8% | 0; 0; 8.2% |
| `UX-1146` | 63 sentences, 4 said twice, `next_steps` drawn | 58, 0, section retired |
| `UX-1147` | 108 headings, 1 shared, 82 holding controls; 8 bad finding titles | 107, 0, 0; 0 |
| `UX-1148` | severity order `high medium info ...` interleaved | `high medium medium medium info ...` |
| `UX-1149` | 67 backtick nodes, 3 `->` | 0, 0 |
| `UX-1150` | 23 `true`, 66 `false`, 9 dashes; `#capacity_verdict` opens `DL.pairs` | 0, 0, 0; `P.section-lead` |
| `UX-1151` | 12 failed, 5 passed, 4 skipped | 17 passed, 4 skipped |
| `UX-1152` | 4 of 4 folds "N chars"; 5 of 5 short tables with a strip; 78 of 78 links off-title | 0; 0 of 4; 0 |
| `UX-1153` | 33 failed, 3 passed | 36 passed |

## The merged tree

Seven tracks merged into one tree: push-check found 30 reds, five fixers
took them (`UX-1140`/`1149`, `1143`/`1150`, `1144`/`1151`, `1145`/`1152`,
`1146`-`1148`) and it read 30 → 0. The residue pass's integrator found 7
more (page bytes, `xl_both`, the map, the shim, the rail split) and it read
7 → 0.

The verifier held 5 of 14 (`UX-1140`, `1141`, `1144`, `1145`, `1151`): the
residue pass closed them: key paths and task ids relabelled and the guards
that pinned them re-read (`1141`, `1144`), `said` redeclared and the
`duration_resolution` lead (`1149`, `1151`), producer prose in
`bga/shown.py` (`1140`), `1147`'s heads at 390 and the `both_scale`
pointer-travel budget re-based.

## Decisions carried

- Page-byte headroom is ~909 B on `golden` against the 150,000 B budget:
  the next row that adds text spends it.
- `tools/bga_view.py` `_uncommented_css` now strips indentation (`25ac5def`),
  which carried the page-bytes fix after the viewer dedup yielded 264 B
  (the integrator's flag); the exported stylesheet is smaller, the source
  is not.

## What was filed

`UX-1154`-`UX-1160`, from the walk's 14 defect classes on the merged page
(the walk's screenshots are the project's `round-154/`, outside the tree):

- `UX-1154` a print blanks inner folds and prints its controls
- `UX-1155` accessible names repeat or omit the thing they name
- `UX-1156` text still repeats across the page
- `UX-1157` compact layout leaves four defects at 390
- `UX-1158` filter and back-navigation state is not kept or told
- `UX-1159` key paths and schema descriptions reach reader text
- `UX-1160` the pointer-travel instrument reads a content-visibility placeholder, not page geometry

## Agents

| round | agent | model | task | tokens | tool calls | wall | outcome | friction |
|---|---|---|---|---|---|---|---|---|
| 154 | implementer | opus | implementer: ~240k? (Track A UX-1140, UX-1149 see report: formatter + typesetter | — | — | — | see round-154 | — |
| 154 | implementer | opus | implementer: Track B UX-1141, UX-1142 | — | — | — | see round-154 | — |
| 154 | implementer | opus | implementer: Track D UX-1144 | — | — | — | see round-154 | — |
| 154 | implementer | opus | implementer: Track C UX-1143, UX-1150 | ~240k | — | ~2h | see round-154 | cost: finding which commit moved J3 budget; classifier refused compound bash; node shim has no :scope |
| 154 | implementer | opus | implementer: Track G UX-1151, UX-1153 | ~270k | — | ~75m | see round-154 | cost: guards encoding the old shape; sandbox refused $VAR/compound commands |
| 154 | implementer | opus | implementer: Track E UX-1145, UX-1152 | ~270k | — | ~3.5h | see round-154 | cost: guards outside the touching selector; amend after reds, sandbox compound refusals |
| 154 | implementer | opus | implementer: Track F UX-1146..1148 | ~330k | — | ~3h | see round-154 | cost: re-basing 17 guards; two rows shipped red, amended |
| 154 | integrator | opus | integrator: merge 7 tracks | ~155k | — | ~75m | see round-154 | cost: push-check + attributing 30 reds; seven track holds reached the merge; brief's --check --write invalid |
| 154 | implementer | sonnet | fixer: UX-1140/1149 merged reds | ~90k | — | ~10m | see round-154 | nothing |
| 154 | implementer | sonnet | fixer: UX-1143/1150 merged reds | ~60k | — | ~6m | see round-154 | — |
| 154 | implementer | sonnet | fixer: UX-1144/1151 merged reds | ~110k | — | ~12m | see round-154 | — |
| 154 | implementer | opus | fixer: UX-1145/1152 merged reds | ~95k | — | ~40m | see round-154 | cost: node-shim lowercase tagName vs Chromium |
| 154 | implementer | sonnet | fixer: UX-1146..1148 merged reds | ~90k | — | ~12m | see round-154 | — |
| 154 | verifier | sonnet | verifier: 9 PASS 5 HOLD (1140 1141 1144 1145 1151 | ~600k | — | ~35m | see round-154 | worktree hook refused compound shell |
| 154 | walker | sonnet | walker: 14 defect classes, 6 screenshots | ~190k | — | ~45m | see round-154 | emulateMedia not page.pdf |
| 154 | implementer | opus | fixer: UX-1147 heads at 390 + both_scale budget re-base | ~125k | — | ~85m | see round-154 | cost: showing travel budget reads 600 px placeholder |
| 154 | implementer | sonnet | fixer: UX-1141/1144 residue | ~200k | — | ~75m | see round-154 | path relabel reverted, guards pin paths |
| 154 | implementer | sonnet | fixer: UX-1149/1151 residue | ~230k | — | ~40m | see round-154 | `said` redeclaration broke module load |
| 154 | implementer | sonnet | fixer: UX-1140 producer prose (bga/shown.py | ~1.2M | — | ~2h | see round-154 | cost: repeated full-suite runs; guard vacuous until dd description handled |
| 154 | integrator | opus | integrator: 7 merged-tree reds (page bytes, xl_both, map, shim, rail split | ~110k | — | ~45m | see round-154 | viewer dedup yielded 264 B, exporter indent strip carried the fix |
| 154 | closer | opus | closer: UX-1140..UX-1153, UX-1154..UX-1160 filed | — | — | — | 14 rows moved, round document | — |
