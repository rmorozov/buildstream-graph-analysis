# Round 142 — the styleguide audit's rows, nine tracks on one page

Run on 2026-09-26 off main at `babba3e5` (`#294`, the styleguide audit),
on its 22 filings plus `UX-921` from round 130's design review.

```text
closed   UX-921 UX-1015 UX-1016 UX-1017 UX-1018 UX-1019 UX-1020 UX-1021
         UX-1022 UX-1023 UX-1024 UX-1025 UX-1026 UX-1027 UX-1028 UX-1029
         UX-1030 UX-1031 UX-1032 UX-1033 UX-1034 UX-1035 UX-1036
filed    UX-1037 (26 unbounded growers, from UX-1031), UX-1038 (CLI plurals,
         from UX-1020), one coverage line (UX-1020's inventory reach)
index    dev_close_task.py --counts: 999 scenarios, 17 open, 982 closed
spread   dev_touching.py --spread: 33-171 of 640 test files
```

## The page, measured before and after

```text
controls under 24px (golden, fine pointer)     93 of 98 -> 0
unnamed svg[role=img] (macro_micro)            20 of 23 -> 0
? doors (macro_micro)                          191 -> 39
distinct spacing lengths (style.css)           98 -> 8 tokens
computed font families                         4 -> 2
computed font sizes                            5 -> 4
hidden-finding controls at 120 findings        121 -> 40
largest JSON door, 4,002 elements              3,591,520 -> 20,000 chars
```

## Nine tracks met on one stylesheet

Each track measured against `babba3e5`; merged, the page read
339,237 B (+10,841) and `macro_micro` landed at 7,471 px, so the
landed bound moved 7,300 -> 7,600 and `CHAPTER_HEADING_SCREENS`
8.5 -> 9.0 (`320df09f`, `a124bc56`). `structured.js` crossed the viewer
line ceiling and the pair list moved to `bga/viewer/pairs.js`
(`UX-1028`); `bga/schemas.py` crossed its size cell and the view-hint
vocabulary moved to `bga/schema_hints.py` (`UX-1031`). Six new browser
guards landed untiered (`f71a4831`).

## Folding became hidden, not display:none

`hidden="until-found"` lets find-in-page open a chapter (`UX-1015`), and
five guards that opened chapters by `data-open` alone went red on it;
`textContent` and `innerText` now disagree across the fold, which two
more tracks met (`UX-1023`, the header guard).

## Agents

| agent | model | task | tokens | calls | wall | friction |
|---|---|---|---|---|---|---|
| researcher | sonnet | map the round's UI rows to their surfaces and guards | 56k | 22 | 2.5 m | UX-1027's task file cited the wrong test; cross-checking every "extends test X" cost most |
| implementer | sonnet | UX-1036, then UX-1031 (mechanical) | 72k | 90 | 11.5 m | no deps installed; UX-1031 stopped as judgement at 91 containers |
| researcher | sonnet | UX-1031 classify 91 payload containers' growth | 143k | 80 | 9.1 m | growth constants scattered one per module |
| implementer | sonnet | UX-921 hidden findings keep a shell (judgement) | 217k | 199 | 30.7 m | PAGE_BUDGET_B had 604 B headroom against 132 KB documented |
| implementer | sonnet | UX-1019 UX-1034 UX-1024 UX-1025 UX-1021 reader strings (bounded) | 351k | 412 | 56.8 m | the volume budget caught words late |
| implementer | sonnet | UX-1016 UX-1015 UX-1017 keyboard and accessibility (mechanical) | 458k | 337 | 63.1 m | hidden=until-found broke 5 guards |
| implementer | sonnet | UX-1032 UX-1028 UX-1029 UX-1030 bounded populations (bounded) | 409k | 337 | 77.1 m | the census reads token deltas, not a class name |
| implementer | sonnet | UX-1026 UX-1035 UX-1033 UX-1022 UX-1018 UX-1027 CSS (mechanical) | 328k | 385 | 81.4 m | UX-1018 broke tests/dom_shim.mjs; UX-1027 cited the wrong test |
| implementer | sonnet | UX-1020 sentence case (mechanical) | 321k | 473 | 62.9 m | 4-core box saturated; test-touching timed out twice |
| implementer | sonnet | UX-1023 a compact size class (mechanical) | 151k | 144 | 39.9 m | textContent read through hidden |
| implementer | sonnet | UX-1031 growth declared in the schema (judgement) | 590k | 659 | 88.7 m | a guard requiring items fought the COLUMNS-only convention |
| general-purpose | opus | the merged tree's gate reds | 486k | 107 | 35.9 m | structured.js crossed the viewer ceiling |
| general-purpose | opus | UX-1031 split schemas.py under its size cell | 291k | 38 | 38.2 m | moving _check_hint re-keyed 3 lint-baseline findings |

No `verifier` ran this round: nine tracks merged unread, which
`test_a_merged_track_names_its_verifier.py` names.
