# Round 157 — the round-156 walk's seven rows

Run on 2026-09-30 from round 156's filing: `UX-1169`-`UX-1175`, seven tracks on
base `83f10ca8`, merged, verified, walked. Head `73af3af3` before the close
commit, push-check run after it.

```text
closed   UX-1169 UX-1170 UX-1171 UX-1172 UX-1173 UX-1174 UX-1175
filed    UX-1176 UX-1177 UX-1178 UX-1179 UX-1180 UX-1181
open     UX-1176 UX-1177 UX-1178 UX-1179 UX-1180 UX-1181
         UX-1014 UX-1134 UX-1040 UX-902 (open before the round)
index    dev_close_task.py --counts: 1134 scenarios, 10 open, 1124 closed
spread   dev_touching.py --spread: 34-180 of 748 test files
```

## What closed

| row | commit | close | page |
|---|---|---|---|
| `UX-1169` | `d3095c04` | every drawing's details reach the accessibility tree; JSON, fold and badge names say what they are; 6 of 16 drawings with a details relation to 16 of 16 | +171 B |
| `UX-1170` | `42e19757` | a threshold, a short filter and the two search boxes say what they kept; the badge re-hides; badge "25 of 112 matched, of 114" | +252 B |
| `UX-1171` | `808fa5f4` | ticks, stacked tables, `#horizon`, the rail fold and Forward fit at 390; Forward re-lands on its press's y | +359 B |
| `UX-1172` | `4a67a718` | no dash, bullet, arrow, asterisk or YAML key in reader text; chain names break at their separators | +29 B |
| `UX-1173` | `f939c94c` | one id and rail label per level fold, levels counted from 0, no index column | +376 B |
| `UX-1174` | `8f17bd1e` | the page-size guard reads the page half in bytes | none |
| `UX-1175` | `1d46815d` | the export drops indentation outside literals and tightens its CSS | -8,400 B (agent) |

## The page half

`UX-1175` moved the page half from 151,228 B to 144,196 B (the session's
reading at `73af3af3`; `export()`'s `page_bytes` reads 144,197 B and
`pagebytes.py` 144,179 B on the same tree, run at close; the instruments
disagree by 169 B at `UX-1174`'s residue, filed as `UX-1181`). 15,804 B under
the 160,000 B budget; round 156 left 8,793 B. The five viewer rows added
1,187 B and the export took 8,400 B at the track, so the merge (144,173 B at
`f939c94c`) is not the sum of its parts.

## The merged tree

Seven picks merged clean at `f939c94c`; push-check there read 8 red, all
single-track (`UX-1172` x2, `UX-1170`, `UX-1171`, `UX-1173`). The fix pass
(integrator, opus): `55a17f69` makes `deepest_path`'s description a sentence
worth showing; `25ae279c` moves `UX-1172`'s CLI unit test into
`test_the_cpu_floor_divides_by_cores.py`, taking the touching selector from
181 to its 180 ceiling; `0016e861` pins the badge call's third argument on
purpose (`UX-1170`); `1bb57426` drops the one-column list's header, as
`UX-1163` rules (`UX-1173`). `73af3af3` is the session's decision: a
chapter-row press at 390 keeps the rail open, because the pointer-travel J2
journey needs its section links; a section link, a step or Expand/Collapse all
still folds it. The decision is written into `UX-1171`'s Outcome, with its
mutation (J2 at 390 and the new chapter-row guard red, 3 failed).

The full suite on the merged tree: 11,327 passed, 0 failed.

## The session mutation check

On `73af3af3`, each track's `bga/` and `tools/` diff undone and its row guard
run: `UX-1175` 28 of 29 red; `UX-1172` 5 of 16 (partial undo); `UX-1169` 11
of 28; `UX-1170` 5 of 19; `UX-1171` 4 of 48 (partial); `UX-1173` 4 of 6;
`UX-1174` is guard-only, so its two mutations are the agent's. All 7 guards
red.

## The walk

The walker drove the two-plane page (114 elements), `golden` and
`macro_micro` at 1440x900 and 390x844: 5 new defects (a row's claim, or two
rows interacting, with its guard green) and 9 pre-existing; `UX-1175`'s layout
diff against `83f10ca8` read zero style differences (5,277 of 5,697 elements
matched at 1440, 5,215 of 5,635 at 390). The re-run list with no finding: ids
unique (239, 0 duplicates), 0 empty names on 348 buttons and 267 links,
0 spaced hyphens, bullets, arrows or asterisks in reader text, print through
`page.pdf` at A4 and 390, Back and Forward over five presses.

## What was filed

`UX-1176`-`UX-1181`:

- `UX-1176` announcements after `UX-1169` and `UX-1170` (Jump and Ask no-match lines outside a live region, 26 of 29 badges `display:none` at rest, 33 of 33 tables unnamed, the drawing-values clip rule unguarded)
- `UX-1177` Jump and the rail after `UX-1173` (Jump misses "level 3", "critical", "leaves"; a rail press leaves a level fold closed; 8 folds read alike; the select name; the fold name against `UX-1025`, a decision the row takes)
- `UX-1178` layout and history (an 87 px detached header on a labelled stacked table at 390, hyphen breaks in CODE, Expand all leaves the chapter 686 px below the top, a duplicate history entry)
- `UX-1179` print and find (long paragraphs print twice, "+81 More blast elements" prints without its elements, twins and SQL `hidden=true`)
- `UX-1180` values and console ("Cores busy 983564.29x" for 0 ms, an epoch as "496481.0 h", a tooltip-only threshold explanation, `cli.py:1416`, 7 `bga:quantity` console warnings)
- `UX-1181` the process row: two page-half instruments differ by 169 B and two tests still count characters

## Review cadence

Review 32 recorded 1,109 closed rows; 1,124 are closed now, a distance of 15
against the bound of 25 (`tests/unit/test_the_review_has_a_cadence.py`). Review
33 is not due.

## Agents

| round | agent | model | task | tokens | tool calls | wall | outcome | friction |
|---|---|---|---|---|---|---|---|---|
| 157 | implementer | opus | implementer: UX-1174 page-size guard reads bytes | ~60k | — | ~15m | see round-157 | cost: data is ASCII (json.dumps escapes), the real defect is the page half counted in characters (14 non-ASCII in the page, 18 B low); guard in test_the_report_you_can_attach.py, not the Acceptance's file; 0 B page; two page-half instruments differ by 169 B, two tests still count characters |
| 157 | implementer | opus | implementer: UX-1172 text residue | ~100k | — | ~40m | see round-157 | cost: 36-file related run; +29 B golden, guard extended in test_a_key_path_stays_where_it_is_copied.py (Acceptance named test_a_reader_sees_labels_not_keys.py), 8 mutations red, analyses and rendered strings regenerated; the What these mean door name from nav.js left |
| 157 | implementer | opus | implementer: UX-1175 export drops indentation | ~100k | — | ~35m | see round-157 | cost: cdp.mjs blank-page wait; -8,400 B page half (151,228 to 142,828: JS -4,992, CSS -3,408), 29-test guard with 4 mutations red, the CSS-in-string mutation caught only by the built case, tiers.py MEDIUM row added |
| 157 | implementer | opus | implementer: UX-1170 filter residue | ~130k | — | ~45m | see round-157 | cost: 6-mutation matrix; +252 B, all 6 red including M3b, badge "25 of 112 matched, of 114" (styleguide §2b amended), test_a_filter_is_a_property_of_a_table rebased; Ask box partial uid matching several changes nothing, count still said twice |
| 157 | implementer | opus | implementer: UX-1169 accessible names | ~105k | — | ~50m | see round-157 | cost: 27-file related run; +171 B, values span visually clipped (role=note) not hidden, two guards rebased, cdp.mjs --ax gains a details count, guard extended in test_every_control_and_drawing_names_what_it_shows.py (Acceptance named a new file), history sparkline mutation non-discriminating (no fixture) |
| 157 | implementer | opus | implementer: UX-1171 layout at 390 and Forward | ~140k | — | ~70m | see round-157 | cost: reproducing Forward; +359 B, 7 mutations red, data-label on every td, test_a_rail_click_lands_on_its_section rebased (revealAndLand 3 to 4), first cut reopened a shut chapter (caught by test_back_after_a_reveal_re_folds) |
| 157 | implementer | opus | implementer: UX-1173 parallelism structure | ~165k | — | ~75m | see round-157 | cost: neighbour runs x3; +376 B, levels from 0 per the schema, level folds get rail labels and ids, tiers.py MEDIUM row added, 3 guards rebased, the -2 suffix loop non-discriminating; fold name inside a labelled cell conflicts with UX-1025 |
| 157 | integrator | opus | integrator: 7 picks merged clean at f939c94c | ~60k | — | ~45m | see round-157 | cost: push-check 8m46s and alone runs; page 144,173 B; push-check 8 red, all single-track (1172 x2, 1170, 1171, 1173), a fixer launched |
| 157 | integrator | opus | integrator: fixer for the 4 holds, 1bb57426 | ~95k | — | ~40m | see round-157 | cost: 2 push-checks; fixed 4 (schema description 55a17f69, selector 181 to 180 by moving a CLI test 25ae279c, badge literal rebase 0016e861, one-column header 1bb57426); J2 against UX-1171's rail fold conflicted |
| 157 | integrator | opus | integrator: fixer resumed at 73af3af3 | — | — | — | see round-157 | cost: the session's decision that a chapter-row press keeps the rail open (J2 needs its section links); J2 green, push-check rc=0 |
| 157 | session | opus | session: mutation check on 73af3af3 | — | — | — | see round-157 | cost: each track's bga and tools diff undone, its guard run: 1175 28 of 29 red, 1172 5 of 16 (partial), 1169 11 of 28, 1170 5 of 19, 1171 4 of 48 (partial), 1173 4 of 6, 1174 guard-only (the agent's 2 mutations) |
| 157 | verifier | sonnet | verifier: pass 1, full suite 11,327 passed, 0 failed | — | — | ~40m | see round-157 | cost: the brief named the wrong rows (1161..1167, a session error); UX-1175 literals byte-identical (5,127 via acorn), UX-1169 values span empty and clipped with the clip rule unguarded (about 110 B dead), 7 console warnings on the two-plane boot (pre-existing, the console guard reads golden only) |
| 157 | verifier | sonnet | verifier: pass 2, 7 of 7 PASS on UX-1169..UX-1175 | — | — | ~15m | see round-157 | cost: resumed for 1169..1175; residue cli.py:1416 spaced hyphen and "1.5s" in the marginal gate message, the drawing-values clip rule unguarded (129 tests green without it) |
| 157 | walker | sonnet | walker: 5 new defects, 9 pre-existing | ~190k | — | ~35m | see round-157 | cost: sandbox refused # and brace blocks; UX-1175 layout diff zero style differences (walk157-findings.md) |
| 157 | closer | sonnet | closer: UX-1169..UX-1175, UX-1176..UX-1181 filed | — | — | — | see round-157 | — |
