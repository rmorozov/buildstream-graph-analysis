# UX-643: a reader role that demotes rather than hides

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-347 (chapters that fold), UX-372 (the page has one reader), UX-305 (emphasis is a budget) | **Found by:** round 87, by the owner asking for a role filter | **Serves:** all five readers, each of whom currently gets the other four's page | **Topic:** viewer | **Area:** bga/viewer

## Motivation

The page has five declared readers and shows all of them everything.
`READERS` carries five roles with short ids `R1`-`R5`; the only thing
the selector at `decision.js:595` does with a choice is swap one lead
finding into one slot (`applyReader`, `:613-619`). The rail does not
read it — `grep reader bga/viewer/nav.js` finds only prose.

The obstacle to a filter is the mapping, measured:

```text
sections on the page                            51
sections a reader role can be derived for       11   (those carrying findings)
sections with no role at all                    40
```

"Hide what is not mine" over that map hides four-fifths of the page or
none of it, and it collides with two standing rules: focus never
*removes*, and marks are never a filter.

## Required Fix

The role **demotes** rather than hides. It decides what is promoted and
expanded versus collapsed into its chapter fold — reusing the fold
`UX-347` already built. An unmapped section simply stays folded, which
is what it does today, so the control works on day one over an
incomplete map and improves as the map fills. "Anyone" promotes
nothing, and the export stays Ctrl-F honest because nothing is removed.

Where the role is authored: `bga:readers` beside the existing
`bga:rail`, so the producer owns it, with the ~9 page-built sections
naming theirs at the call site.

The tag on a promoted block is the existing `R1`-`R5` id, not a colour
— five categories is past what colour carries alone, and `UX-305`'s
budget forbids spending emphasis on all 74 blocks. `sectionHead()` is
the single insertion point.

## Out of Scope

- Driving the element table's default preset, the Perfetto question
  library, or `report/text.py` and `ci_comment.py` from the same role.
  Each is a row of its own once the mapping exists; the terminal one
  matters most, because `readers` currently reaches only the JSON and
  the page, and R4 reads CI output.

- The nine page-built sections in `views.js`, `element.js` and
  `questions.js` — **deferred to UX-650, not declined.** The Required
  Fix names them; round 88's work order gave those three files to no
  owner, so the track holding the mechanism was forbidden them. All
  nine stay folded under every role and reachable under all, which is
  the designed behaviour for an unmapped section — but `blast` is the
  one a capacity-and-impact reader would most want promoted.

## Acceptance Test

With a role chosen, the sections that role owns are expanded and every
other section is folded; nothing is removed from the DOM; the export's
text is unchanged. A section with no declared role stays folded under
every role and is reachable under all of them.

## Outcome (round 88, 2026-09-04) — 🟢 Done

**The role demotes.** Choosing one expands the sections it serves and
folds every other one into the folds the document already has —
`UX-347`'s chapter and `UX-199`'s section — through their own controls,
so nothing here writes `data-collapsed` or `data-open` a second time.
Measured on the exported page, driven through the picker:

```text
                        R1     R2     R3     R4     R5
golden      promoted     6      1      2      2      -
   46         folded    39     44     43     43      -
macro       promoted     6      2      2      3      1
   66         folded    59     63     63     62     64
```

Promoted plus folded is not the section count: `decision` is neither,
because it holds the picker. `golden` offers four roles and
`macro_micro` five — `UX-372`'s dead-control rule, unchanged: a run
with no capacity numbers offers no capacity reader.

**Nothing is removed and the text does not change.** Every section's
words, minus the two controls' own labels (the `R1`-`R5` tag and
`UX-199`'s `▾`/`▸` caret), are byte-identical under all five roles and
back at "anyone"; the section list is identical; the node count moves
only *up*, by the four nodes of `UX-372`'s lead block. "Anyone"
restores the landed page exactly — 2,830 and 5,465 nodes, 6 of 7
chapters shut, no section collapsed, no tag worn.

**The map, derived rather than judged.** `schemas._SECTION_READERS`
is the join of `provenance._CLAIMS`' evidence paths with
`findings.FINDING_READERS`, published as `bga:readers` on eleven
schema nodes. The first guard recomputes the join, so a finding that
changes reader reddens here instead of leaving a stale role on the
page.

Five findings contribute nothing to it and each is the map being
incomplete: `graph-width` (R3) and `memory-envelope` (R5) publish an
empty path tuple, and `wait-category` (R1), `blast-radius-reach` and
`blast-radius-structural` (R2) compute their paths from the document,
so there is no static answer to read.

**The ~9 page-built sections name no role**, which is this round's one
deviation: `blast`, `overview`, `evidence` and `critical-path-drawn`
live in `views.js`, `whatif` and `horizon` in `element.js`, and
`perfetto-questions` in `questions.js` — three files another track's
diff also lands in this round, so the call sites were left alone. They
stay folded under every role and reachable under all of them, which is
the designed behaviour for an unmapped section; the row that maps them
is a row of its own.

`decision` is never folded: it holds the picker, and a control that
folds itself away is `UX-194`'s dead affordance made by hand.

**The tag** is the published index's own `R1`-`R5`, built empty by
`sectionHead` on the eleven sections that declare a role and filled
only on the ones a chosen role promotes — 6 blocks at most, never the
8 or 10 that declare, never all 46 or 66. `UX-305`'s budget spent once.

**The page grew 2,702 B**, all page and no data: 2,425 B of
`chapters.js`/`format.js`/`decision.js`/`style.css` and 277 B of
`bga:readers` on eleven nodes. That tripped three bounds that had
already stopped being budgets — golden was 577 B under 425,000 and
`macro_micro` 202 B under 475,000 — so all three moved with the
measurement recorded beside them, `UX-613`'s procedure.

**Mutations verified red and reverted (7):** `elements` declared `R2`
where the join says `R3`; a sixth role in `READER_ROLES` no section
serves; `foldSection(section, false)` — nothing folded; a `<p>` removed
from each folded section; the tag written on every declaring section
rather than every promoted one; `section.hidden = true` on the folded —
the hide-rather-than-demote defect, and the only one the reachability
clause catches; and "anyone" applying `R1`.

**A guard that did not discriminate at first:** the reachability clause
pressed the section's collapse control unconditionally, so it reddened
under the *fold* mutation too — for the opposite reason, a section that
was never folded being closed by the press. It presses only a shut fold
now, which is what a reader does, and the fold mutation leaves it green.
