# UX-643: a reader role that demotes rather than hides

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-347 (chapters that fold), UX-372 (the page has one reader), UX-305 (emphasis is a budget) | **Found by:** round 87, by the owner asking for a role filter | **Serves:** all five readers, each of whom currently gets the other four's page | **Topic:** viewer

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

## Acceptance Test

With a role chosen, the sections that role owns are expanded and every
other section is folded; nothing is removed from the DOM; the export's
text is unchanged. A section with no declared role stays folded under
every role and is reachable under all of them.
