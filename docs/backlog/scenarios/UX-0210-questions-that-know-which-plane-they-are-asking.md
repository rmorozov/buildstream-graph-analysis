# UX-210: questions that know which plane they are asking

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-204 (the library these live in)

## Motivation

The question library (`bga/viewer/questions.js`) is the round-23
review's "good, mostly presentation work" — and the review did not
read the SQL. Four of the six queries are written as if the trace
had one track, and `bga timeline`'s whole point is that it does
not: the merged output puts Plane 1's element spans and Plane 2's
`native: <element>` process lanes into the same `slice` table.

- **`element-time`** (`group by name` over all of `slice`): on a
  two-plane trace "the time per element" is polluted by every
  Plane 2 command name; the top-25 the reader is told to trust can
  be dominated by commands, not elements.
- **`stalls`** (`lead(ts) over (order by s.ts)` with no track
  filter): the gap after an element span is measured to the next
  slice *on any track* — thousands of interleaved native slices
  zero out exactly the element-track gaps the question promises to
  find.
- **`sandbox-tax`** (containment by time only, `c.ts >= p.ts and
  c.ts + c.dur <= p.ts + p.dur`, no track constraint): any slice
  that nests *in time* is subtracted — including other elements
  building in parallel on other tracks. The "unaccounted" figure
  is wrong even on a Plane-1-only trace the moment two elements
  overlap, and every slice, commands included, appears as an
  "element" in the output.
- **`dependency-wait`** matches `{element}` by name across all
  tracks, so a command that shares the name shape joins the answer.

These answer wrongly precisely on the trace shape the tool is
proudest of — both planes in one timeline — and they answer
*confidently*: a top-25 table with plausible numbers, nothing
flagging that the frame is mixed.

## Required Fix

Every query is track-scoped: element-plane questions join `track`
and exclude `native:%` lanes (or select them, for Plane 2
questions) explicitly; the containment join in `sandbox-tax`
constrains child slices to the element's own lane; `stalls`
windows over the element track only. Each `why` says which plane
it reads. A static guard over `QUESTIONS` asserts every entry
references track scoping, so a future question cannot ship
unscoped; one manual run against a real two-plane capture is
recorded in the log.

## Out of Scope

- New questions, or a query runner in the page.
- Changing how `bga timeline` names tracks (the queries adapt to
  the published naming, not the reverse).

## Acceptance Test

The static guard reddens when any query loses its track scoping
(mutation: strip the track join from `stalls` → red; from
`sandbox-tax`'s containment → red). On the recorded two-plane run,
`element-time` returns only element spans (no command names in the
top 25) and `stalls` returns element-track gaps rather than
micro-gaps to interleaved native slices — both checked against the
same numbers in the published report.
