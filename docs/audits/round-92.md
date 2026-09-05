# Design round 92: the suite verifies what was built; the walk verifies what was promised

Run on 2026-09-05, after round 91 merged. A design round (§6a). The
user asked how to keep the tool in shape when hand exploration finds
a problem almost every time the suite does not — an exploratory
cadence on a cheaper model tied to the release, impact analysis at
the design stage, a hierarchical backlog, and a carefully planned
restructuring of the specification and the architecture document —
and asked to be challenged. One researcher inventoried the tree; the
argument is Direction 18; the filings are `UX-685`..`UX-692`.

## What exists today

```text
tests/unit                          472 files, one claim each · 7,206 tests collected
journey-shaped files                3   (test_e2e, installed_command_sweep, the journey with an answer key — real bst, 3 planted defects, unchanged since round 64)
browser-boot files                  36 = 42.8 % of CI's 1,497 s   (after UX-523's shared boot: 629 → 248 s serial)
enormous (bst) files                21
property-based / seeded tests       0
flake ledger                        none
release gate                        a contract moved + a review row after the last release; no walk, no exploration (release-guide.md:29-33)
impact analysis                     dev_touching (grep), dev_touch_map (CI coverage, empty locally), dev_js_deps; no module→contract→finding→guide index
backlog                             682 tasks · 8 topics (viewer 156) · no Area field · 563 name a Depends-on id · README + closed.md only
batch gate                          settled by UX-500: Regime B missed 4 of 9 defects outside the selector; §3 stays
spec / architecture                 3,051 / 1,648 lines · 16 / 19 guards · the spec's edge decisions taken (UX-564..UX-568)
```

## The five corrections

Argued in Direction 18: exploration finds what it finds because the
suite tests claims and a reader tests journeys, so the journey is the
unit and every finding grows the answer key; a cheaper model is right
for driving and wrong for judging; the release waits for the walk
that read its candidate, with the contract change as the clock; the
impact set is derived by one tool and the hierarchy is an area field
with generated pages, not a new tree of files; the specification is
layered and left, the architecture document's prose moved one area at
a time under the merge rules.

## Filed

`UX-685` (exploration as a seeded scenario — High), `UX-686` (the
release waits for the walk — High), `UX-687` (the impact set derived
— High), `UX-688` (areas as a view — High), `UX-689` (the
architecture document moved one area at a time — Medium), `UX-690`
(a shape budget and a filed test analysis — Medium), `UX-691` (a
flake ledger — Medium), `UX-692` (the invariants for any shape —
High).

## Agents

| agent | model | task | tokens | tool calls | wall | friction |
|---|---|---|---|---|---|---|
| researcher | sonnet | what landed of the test plan, the suite's shape, the release gate, the backlog's structure | 96k | 34 | 3.8 m | the brief grouped items from rounds 64, 78 and 80 as one plan; each file's own dateline had to be read |

## Standing

A design round produces no code; the one test edit is the direction
walk's count, 1-17 → 1-18. Verified in passing: the round-64 test
plan landed in full and found what it was built to find (`UX-400`
three defects, `UX-403` one hollow guard and a live tier defect,
`UX-402` all three planted defects surfaced).
