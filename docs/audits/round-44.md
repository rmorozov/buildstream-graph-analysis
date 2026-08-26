# Audit round 44: the report, read at arm's length

Run on 2026-08-26. Two inputs: the sibling's landing of the
trace-enrichment slate (UX-308..312, plus UX-314's deep-link find
and the UX-294/295 closures), and the user's thirteen field
observations from reading the report on a real capture — the
second field pass the visual contract has faced, and the first
since it became code.

## The landing, verified

Seven for seven, seventeen mutations, seventeen discriminating —
and the agent went past the brief, fetching the real
`trace_processor` and passing all twelve round-trip clauses against
Perfetto's own SQL. The annotations, flows, counters and identity
all hold under mutation (a skewed `cpu_us`, an invented
cross-element flow, a reversed fold tie, a dropped interruption
name — each red); `UX-314`'s finding was real and sharp: Perfetto's
`connect-src` matches host *names* over plain http, so every
ephemeral `127.0.0.1` bind was refused before the request left the
browser and the CORS grant had never mattered — the fix's
served-means-fetchable rule reds four clauses when mutated, and the
deployed-UI verification is recorded with its honest caveat.
`d849c10`'s confession deserves its line: every canned question had
returned **zero rows in silence for two rounds** (the queries were
written for Chrome-JSON's `args.*`; UX-298 moved the facts and
nobody's guard noticed, because an absent key is NULL, not an
error). Suite: **3,833 passed, 0 failed**; lint clean; all markers
agree.

And one survivor of exactly that class, filed as **UX-321**:
`element-commands` filters Plane 2 slices on `debug.element` — a
key Plane 2 never emits — so it returns empty on every trace this
emitter can write, silently, and the dictionary guard cannot see it
because it checks the union contract, not per-plane scope. Three
smaller seams ride in the same filing: a docstring claiming decoder
independence the mechanism lacks, a cross-file disagreement about
whether the ui.perfetto.dev debt is closed (it is — `UX-314`), and
two trace_processor clauses gated inconsistently.

## The thirteen observations, ground-truthed into four classes

Each complaint was traced to its mechanism before anything was
filed; they collapse into four classes, and each class became a
style-guide section (§2a/§2b/§3a/§3b) plus a filing:

1. **Exhibits drawn at annotation size** (`UX-316`). The
   blast-radius distribution, the store diagram and the
   element-duration distribution are all invisible for one
   measured reason: every drawing shares `SPARK_HEIGHT = 20` /
   `STRIP_HEIGHT = 8` (`drawings.js:36-38`) — a geometry
   calibrated for the sparkline beside a table cell, applied to
   drawings that are their section's whole answer. §2a splits the
   grades (annotation vs exhibit) exactly as §4.5 split the color
   tokens, adds the size scale as tokens, and gives every exhibit
   its **table twin** — which also answers the graph-shape request
   for visual *and* table representations, generically.
2. **Apparatus out of place** (`UX-317`). The save-the-trace
   sentence renders in the *header* (`index.html:40`), two blocks
   from the Perfetto control it explains — the exact line the user
   flagged twice now. And attribution's descriptions hide behind
   hover on the term. §2b: a control's explanation lives with the
   control, the header carries identity within a measured budget,
   and a described value shows a visible `?` whose sentence opens
   beside the value — the user's proposal, adopted as the generic
   mechanism for every described value.
3. **The unannounced rabbit hole** (`UX-318`). Nested tables say
   nothing about their depth; the blast table's nested scroll
   cannot reach all rows inside its scrolling parent; the user
   asks for an enlarge button. One mechanism answers all three:
   §3a — depth and row counts on every fold, one nested level
   inline, and **table focus** (full column width, in flow,
   breadcrumb back — not an overlay; round 24's
   export-survivability argument stands), with the enlarge
   affordance entering the same state and nested scrollboxes
   abolished outright.
4. **Unpriced reading costs** (`UX-319`). The chain section lists
   every element unfolded — UX-187's rule never reached this
   surface — and chapter traversal cost has never been measured.
   §3b sets the click budget (two interactions from rail to any
   section's content) and demands the measurement be a guard.

`UX-320` is the conformance pass — the UX-305 precedent applied to
the new sections, with the four walks joining the suite.

## Standing

Priority: **UX-316 and UX-318 first** — they are the two the user
cannot read around today (invisible exhibits, unreachable nested
rows), and UX-318 also deletes a defect rather than decorating it
(nested scrollboxes go). Then UX-317 and UX-319, then UX-320's
conformance pass sealing all four, with UX-321 riding whichever
lands near the questions. The pattern across two field passes is
worth standing on: the visual contract absorbs each complaint as a
*rule*, not a patch — §2a/§2b/§3a/§3b took thirteen observations
and produced four sections and one mechanism each — and the page
should now be audited at arm's length once per axis, not once per
round; the click and size walks make that audit a guard.
