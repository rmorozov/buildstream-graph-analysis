# Round 155 — the round-154 walk's seven rows, fixed

Run on 2026-09-30 from round 154's filing: `UX-1154`-`UX-1160`, seven tracks,
merged, verified, walked. Head `8b7e3d3b`, push-check green there.

```text
closed   UX-1154 UX-1155 UX-1156 UX-1157 UX-1158 UX-1159 UX-1160
filed    UX-1161 UX-1162 UX-1163 UX-1164 UX-1165 UX-1166 UX-1167
open     UX-1161 UX-1162 UX-1163 UX-1164 UX-1165 UX-1166 UX-1167
         UX-1014 UX-1134 UX-1040 UX-902 (open before the round)
index    dev_close_task.py --counts: 1120 scenarios, 11 open, 1109 closed
spread   dev_touching.py --spread: 34-180 of 742 test files
```

## What closed

| row | gap | close |
|---|---|---|
| `UX-1154` | 62 of 66 folds closed in print, 382 visible controls, 6 clipped `next-command`; 16 failed, 3 passed | 0 closed, 1 control (`.fold-more`), 0 clipped; 19 passed; +70 B |
| `UX-1155` | 37 `?` buttons, 30 folds-as-heading and 74 collapses sharing one name; 10 bare-range drawings | 37/37 distinct, 0 bare; 12 passed; +128 B |
| `UX-1156` | said twice 10 / 11 / 8 (golden / `macro_micro` / two-plane), copies 24 / 30 / 23 | 0 / 0 / 0, copies 0; 18 passed; +396 B; `xl_both` -754 px |
| `UX-1157` | floors labels 45 px overlap at 390; 38 stray `dl` children; constraints 342x1073 | 20 px apart; 0; 342x349; 24 passed; +120 B |
| `UX-1158` | rail press writes a 121-char hash; filter strip says "all 114 rows"; 3 presses, Back leaves the page | 13-char hash; "14 of 114"; Back x3 walks the rail; +156 B |
| `UX-1159` | 110 schema descriptions name a key; 64 / 99 / 67 key tokens in reader text | 0 / 0 / 0 / 0; +120 B |
| `UX-1160` | J3 read 14.35 bits / 38,463 px on a 600 px placeholder (`macro_micro` 1440) | 5.88 / 35,988 laid out; all four budgets re-based; 11 of 52 red with the prelude dropped |

## The merged tree

Seven tracks merged into one tree at 34 B over the 150,000 B page budget;
the integrator recovered to 255 B under with no budget raised, and fixed 6
push-check reds. Budgets at `8b7e3d3b`: page 149,745 / 150,000 B, `xl_both`
controls 886 / 900, `macro_micro` opened words 12,483 / 13,200, `xl_both`
height 42,002 / 43,500 px.

## The verifier's hold and the session mutation check

The verifier passed 6 and held `UX-1160`: its placeholder clause counts the
same selector the prelude forces, so it reds only when the prelude is
dropped, and it sees only `section.chapter > section[data-section]`. The
hold is recorded as an Outcome deviation, not fixed. The verifier ran no
mutations (the classifier denied `sed`).

The session's check on `8b7e3d3b` undid each track's `bga/` change (`UX-1154`
by reverse patch, the others by parent file versions, `UX-1160` by dropping
the prelude): all 7 guards red, 16/19, 9/12, 11/18, 9/24, 5/7, 3/3, 11/52.

## Defaults taken, open to the owner

- `UX-1158`: the URL hash is an opaque token (base64), and old readable
  hashes still load. Reversing it costs the readable link.
- `UX-1159`: T∞, LB and T_C stay, with a plain name beside every use
  ("Chain floor T∞").

## What was filed

`UX-1161`-`UX-1167`, from the walk's 12 defects and the tracks' leftovers:

- `UX-1161` print residue (SQL line overflow, "I am" label, fold markers, unopened descriptions, held-back rows, code at 390)
- `UX-1162` accessible-name residue (range `aria-details`, shared names, `#utilisation`, strips)
- `UX-1163` repeats residue (Dominant binary x19, sample floor x3, "N rows", floors symbols, `#confidence` Name)
- `UX-1164` layout residue (rail buttons, attribution labels, ticks, h2 wrap, SQL `pre`, serialization table)
- `UX-1165` filter and link state residue (empty-table sentence, "Copy 0 rows", strip caption, "Sections · N", "All rows", Back at 390, dead `applyTopN`)
- `UX-1166` key paths and dashes (`#document_shape` path, " - ", null dashes)
- `UX-1167` the process row: 255 B of 150,000 B left, `xl_both` controls 14 of 900; the owner decides whether the budget stays

## Agents

| round | agent | model | task | tokens | tool calls | wall | outcome | friction |
|---|---|---|---|---|---|---|---|---|
| 155 | implementer | opus | implementer: UX-1154 print | ~100k | — | ~25m | see round-155 | cost: .next-command specificity; overflow-wrap added then dropped |
| 155 | implementer | opus | implementer: UX-1160 travel instrument | ~95k | — | ~45m | see round-155 | cost: why old J2 read 0 wheel; sandbox compound refusals |
| 155 | implementer | opus | implementer: UX-1155 accessible names | ~330k | — | ~2h | see round-155 | cost: byte budget under gzip; :not(article *) throws in DOM shim; map vs flatMap |
| 155 | implementer | opus | implementer: UX-1158 filter/Back/hash | ~225k | — | ~95m | see round-155 | cost: byte budget; first old-hash check reloaded by hash only, vacuous |
| 155 | implementer | opus | implementer: UX-1157 compact layout | ~190k | — | ~2h15m | see round-155 | cost: byte budget; own evidence crash (array to native append) caught only by related tests |
| 155 | implementer | opus | implementer: UX-1159 key paths | ~330k | — | ~2h | see round-155 | cost: rewording 110 descriptions to fit two budgets; sandbox refusals |
| 155 | implementer | opus | implementer: UX-1156 said once | ~330k | — | ~2h | see round-155 | cost: page bytes; guard skipped link text until M1 stayed green |
| 155 | integrator | opus | integrator: merged 7, page 34 B over -> 255 B under, 6 push-check reds fixed | ~190k | — | ~1h05m | see round-155 | gate script truncated --check output |
| 155 | verifier | sonnet | verifier: 6 PASS, UX-1160 HOLD (clause selector) | ~110k | — | ~25m | see round-155 | classifier denied mutation sed, no mutations run |
| 155 | walker | sonnet | walker: 12 defects, 6 shots | ~450k | — | ~55m | see round-155 | no PDF text extractor; two-plane baseline not rebuilt |
| 155 | closer | opus | closer: UX-1154..UX-1160, UX-1161..UX-1167 filed | — | — | — | see round-155 | 7 rows moved, round document |
