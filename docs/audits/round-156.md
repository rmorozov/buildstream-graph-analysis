# Round 156 — the round-155 walk's seven rows, and the rail's mark

Run on 2026-09-30 from round 155's filing: `UX-1161`-`UX-1167`, seven tracks,
merged, verified, walked, plus `UX-1168` from the verifier's one red. Head
`947f22de`, push-check run after the close commit.

```text
closed   UX-1161 UX-1162 UX-1163 UX-1164 UX-1165 UX-1166 UX-1167 UX-1168
filed    UX-1169 UX-1170 UX-1171 UX-1172 UX-1173 UX-1174 UX-1175
open     UX-1169 UX-1170 UX-1171 UX-1172 UX-1173 UX-1174 UX-1175
         UX-1014 UX-1134 UX-1040 UX-902 (open before the round)
index    dev_close_task.py --counts: 1128 scenarios, 11 open, 1117 closed
spread   dev_touching.py --spread: 34-180 of 746 test files
```

## What closed

| row | commit | close | page |
|---|---|---|---|
| `UX-1161` | `fd5a77e8` | print fits the sheet, no fold marker, label or dead control prints, every description prints | +142 B |
| `UX-1162` | `e8418fbf` | every control names what it acts on; a drawing's details carry its values | +316 B |
| `UX-1163` | `f5f7149a` | each round-155 repeat said once | +244 B |
| `UX-1164` | `a03f04ba` | rail keys, tick labels, chapter heads, SQL and tables of tables fit at 1440 and 390 | +336 B |
| `UX-1165` | `b71cb68f` | a no-match filter offers no copy; the strip counts K of M; the link keeps folds and All rows | +188 B |
| `UX-1166` | `d8e22853` | no key path, spaced hyphen or null dash in reader text; 395 spaced hyphens to em dashes | +152 B (guard read +395) |
| `UX-1167` | `d27c5b23` | `PAGE_BUDGET_B` 150,000 to 160,000 B; the ceilings table checked against the constants | none |
| `UX-1168` | `947f22de` | the rail's mark follows the reading line; 11 of 11 stale crossings to 0 | +72 B |

## The owner's decision

`UX-1167` asked whether the 150,000 B page budget stays. Ruslan chose
"Raise to 160 KB" on the round-156 card (2026-09-30). The 900-controls cap
on `xl_both` stays (886 measured). The page half at `947f22de`, measured
with `pagebytes.py` (the golden page minus its embedded data):
151,207 of 160,000 B, 8,793 B of headroom. The eight rows added about
1,450 B; the bound had been 238 B away at `3e6feb45`.

## The merged tree

Seven tracks merged at `11e1a905` with 4 holds left, fixed by the session:
`db848097` drops `UX-1161`'s strict xfail on `macro_micro` 390 ticks (`UX-1164`
fixed them); `b58ffeb4` sets the hint count to 23, names a skip reason and
derives `UX-1164` and `UX-1167` as mechanical. `11e1a905` tiers the two new
browser guards.

## The flake that became a row

The verifier's `make test` (7m38s on a loaded box) passed 6 rows and failed 1
of 11,232: `test_three_backs_restore_rail_and_chapters` at
`('two_plane', 390)`, `back_twice`, the rail's mark stale. It passed 3 of 3
alone. The session traced it to `scrollspy` marking only in an
`IntersectionObserver` callback; `UX-1168` adds a second observer on a
zero-height reading-line strip (+72 B, mutation 2 of 2 red). The Back flake
did not reproduce under load afterwards (5 of 5 alone).

## The session mutation check

On `b58ffeb4`, each track's `bga/` and `tools/` diff undone and its row guard
run: `UX-1167` 1 failed; `UX-1161` 22 of 31; `UX-1164` 17 of 39; `UX-1162`
13 of 16 (partial undo); `UX-1165` 4 of 10 (partial); `UX-1163` 17 of 42;
`UX-1166` 5 of 9. All 7 guards red.

## The walk

The walker drove the two-plane page (114 elements), `golden` and
`macro_micro` at 1440x900 and 390x844: 6 new defects (a row's own claim, or
two rows interacting, with its guard green) and 9 pre-existing, and a re-run
list with no finding (print through `page.pdf` at A4 and 390, overflow,
Back and Forward, filter round trips, copy readbacks).

## What was filed

`UX-1169`-`UX-1175`:

- `UX-1169` accessible names after `UX-1162` (11 of 17 `aria-details` reach nothing, 46 JSON names carry keys, the As-table name, the chapter label, the live count)
- `UX-1170` filter residue (threshold no-match keeps Copy, 1-row sentence, "25 of 114" badge, silent Ask and Jump, badge not re-hidden)
- `UX-1171` layout at 390 (tick over caption by 18.6 px, tables of tables, `#horizon` link, open rail, Forward)
- `UX-1172` text residue (spaced hyphens and a raw key, leading bullet, `->`, `[]`, asterisks, `cli.py:168`, unit-less µs, split chain names)
- `UX-1173` `#parallelism` structure (8 details on one id, 8 rail "Elements", 0-based levels, index column, repeated h3, untitled rail)
- `UX-1174` the process row: the size guard subtracts characters, not bytes (+395 B read against +152 B real)
- `UX-1175` the exported page ships indentation (5,148 B JS and about 3,480 B CSS)

## Agents

| round | agent | model | task | tokens | tool calls | wall | outcome | friction |
|---|---|---|---|---|---|---|---|---|
| 156 | implementer | opus | implementer: UX-1167 page budget raised to 160 KB | ~85k | — | ~25m | see round-156 | cost: xl_both controls breakdown; brief switched mid-track, new guard needs tiers.py and ci_reference rows, minifier yield 5,148 B JS + ~3,480 B CSS left for a later row |
| 156 | implementer | opus | implementer: UX-1161 print | ~120k | — | ~25m | see round-156 | cost: own PDF reader; +142 B, prints every .description (reverses UX-346), strict xfail naming UX-1164, .path-more hides in print with no fixture, raw **flows** in the Perfetto question |
| 156 | implementer | opus | implementer: UX-1165 filter and link state | ~140k | — | ~45m | see round-156 | cost: browser runs; +188 B golden, dev_sizes --adopt hit a pylint error, UX-1158 strip test and _FILTER re-based, applyTopN removed |
| 156 | implementer | opus | implementer: UX-1162 accessible names | ~178k | — | ~75m | see round-156 | cost: mutation matrix x3; +316 B golden, guard opens only the first question fold (cdp.mjs --ax unsettled await), As-table toggle loses its name after Show all |
| 156 | implementer | opus | implementer: UX-1164 layout at 1440 and 390 | ~150k | — | ~75m | see round-156 | cost: chapter-head second approach; +336 B golden, volume budget not run, 1161's xfail XPASSes now, #horizon link runs to x=387 |
| 156 | implementer | opus | implementer: UX-1166 key paths and dashes | ~210k | — | ~75m | see round-156 | cost: sourcing 219 dashes; +152 B page but +395 by the guard (subtracts data characters, not bytes), 395 spaced hyphens to em dashes, cli.py:168 no space |
| 156 | implementer | opus | implementer: UX-1163 said once | ~230k | — | ~2h | see round-156 | cost: page-byte base and 4 rebased guards; +244 B, M3b did not discriminate, headerless one-column table bends §3d sorting |
| 156 | integrator | opus | integrator: merged 7 at 11e1a905, 4 holds left | ~86k | — | ~40m | see round-156 | cost: push-check 8 min; session fixed the holds in b58ffeb4 (hint count 23, skip reason, UX-1164 and UX-1167 Shape mechanical) |
| 156 | verifier | sonnet | verifier: 6 PASS, 1 red of 11232 in the full suite | ~50k | — | ~13m | see round-156 | cost: make test on a loaded box (7m38s); test_three_backs two_plane 390 back_twice read a stale rail mark, passed 3/3 alone |
| 156 | implementer | opus | implementer: UX-1168 rail mark follows the reading line | ~75k | — | ~25m | see round-156 | cost: scripts via scratch; second IO observer on a zero-height line strip, 11 of 11 stale crossings to 0, +72 B, task file hand-written |
| 156 | walker | sonnet | walker: 6 new defects, 9 pre-existing | ~350k | — | ~37m | see round-156 | cost: sandbox refused object literals, drivers rewritten 4-6x |
| 156 | closer | opus | closer: UX-1161..UX-1168, UX-1169..UX-1175 filed | — | — | — | see round-156 | — |
