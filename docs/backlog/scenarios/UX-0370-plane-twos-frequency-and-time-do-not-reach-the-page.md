# UX-370: Plane 2's frequency and time do not reach the page

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-356 (every field of the element join reaches a reader), UX-102 (configure tax, both planes side by side) | **Serves:** anyone asking what the build spends its time running | **Topic:** viewer

## Motivation

The round's question was concrete: can a reader tell what cmake
configure costs, or what generating a test image costs, in calls and in
seconds? Plane 2 measures both. `tests/fixtures/macro_micro/plane2.json`
publishes:

```text
binary_cost[app.bst].by_count   cmake x26, sh x16, make x11, c++ x10, ld x7
binary_cost[app.bst].by_cpu     cc1plus  5 calls, 70.6% of this element's CPU
by_binary                       ar as c++ cc1plus cmake collect2 ld make
configure_phase                 configure_cpu_us 4,481,317 (6.42% of CPU),
                                with a note on how parentage classifies it
```

Booted, the exported page contains the *names* — `cmake`, `make`,
`cc1plus` all appear — and **none of the numbers**:

```text
6.42% / 4.48s configure figure on the page   no
a by_binary or binary_cost section           no
sections matching binar|configure            none (only plane2_coverage)
```

This is `UX-356`'s shape one document over: published, and not rendered.
A reader who wants "what does configure cost me" has the answer in the
JSON beside the run and no way to reach it from the report.

**Test image generation is a real gap, not a rendering one.**
`configure_phase` classifies by parentage from a named set of configure
entry points; nothing classifies image or artifact assembly. That is a
second, smaller item's worth of work and is named here so the two are
not confused.

## Required Fix

Render what Plane 2 already measures, in the two axes the question asks
for:

- **Frequency and time per binary**, for the run and per element —
  `binary_cost.by_count` and `.by_cpu` are already shaped for a table
  with a share column.
- **The configure phase as a number**, beside the sandbox tax it belongs
  with (`UX-102` put toll and work side by side; this is the same
  drawer). Its note already says what it counts, which is `UX-346`'s
  door.

Both are populations with a share, so `UX-303`'s strip and `UX-289`'s
preset table apply unchanged.

## Falsification

The `UX-356` clause, pointed at Plane 2: every scalar under
`binary_cost`, `by_binary` and `configure_phase` reaches a rendered node
or is named in a redirect sentence that says why not. It fails today on
all of them.

## Out of Scope

- Classifying test-image or artifact-assembly work. Named above,
  belongs in its own item, and needs a capture that does it.
- `plane2_coverage`, which already renders and is a different question
  (how much of the run Plane 2 saw, not what it saw).

## Outcome (round 59, 2026-08-28) — 🟢 Done

### The gap, measured — and it was one step earlier than filed

The filing read this as "published and not rendered". It was worse:
**the Plane 2 document does not reach the viewer at all.** `bga view`
publishes `report.json` and nothing else, so a number left in
`plane2.json` beside the run has no reader on the page.
`plane2_coverage` and `element_join` are there because the *analysis*
projects them into `analyze/v4`; these three were never projected, so
there was nothing for the renderer to be blamed for.

```text
before:  sections matching binar|configure   none
         the 6.42% / 4.48 s configure figure  not on the page
```

### After

```text
sections            by_binary, binary_cost, configure_phase
configure, drawn    "Configure cpu 4.5 s"   "Configure 6.4%"
by_binary           cmake 248, sh 150, make 99, c++ 88, cc1plus 51, …
binary_cost         71 rows, one per (element, binary)
```

The renderer needed no change: with `QUANTITY` declared, 4,481,317 µs
draws as `4.5 s` and 0.0642 as `6.4%`. `configure_phase.note` — the
caveat that makes the share a floor — sits on `UX-346`'s door.

### Four contract rules said the projection was the wrong shape

Projecting the Plane 2 objects verbatim broke four of this document's
own rules at once:

```text
deeper than three levels   0.626 of leaves, against a 0.58 bound (UX-344)
one population, twice      configure_phase.per_element and binary_cost,
                           the same 9 elements                 (UX-288)
table width                configure_phase[] at 9 columns, cap 8 (UX-289)
export size                golden +741 B, macro_micro +11,517 B
```

Four rules saying one thing: **this document is flat, publishes each
population once, and draws tables a reader can read.** So the two
rankings became one row per `(element, binary)` — which is also the
shape the filing described, "a table with a share column" — and
`configure_phase.per_element` was dropped rather than published as a
second copy of the element population. The per-element split stays in
`plane2.json`, where `bga correlate` reads it.

`wall_s` becomes `wall_us` at the boundary: Plane 2 publishes seconds
and this vocabulary carries one time member, in microseconds
(`UX-341`). Converting there is `bga/units.py`'s own stated rule; the
alternative was a number the page renders from a name-sniffed guess,
which `UX-343` made a failure. It is the *only* field that changes
across the boundary, and a clause holds that.

### Two guards were reading one of the two conditions they guard

Both passed on the committed tree and failed on this change, and in
both cases the code was right.

**`test_a_served_page_offers_it_on_the_nested_tables`** asserted every
focus control sits on a nested table. `structured.js` says
`nested || total > TABLE_OPENS_BOUNDED_ABOVE`; no *top-level* table had
ever exceeded 40 rows, so the second half had never been exercised.
`binary_cost` is 71 rows at the top level. The clause now asserts the
rule rather than half of it.

**`test_no_table_under_the_cap_carries_a_filter`** scoped a table's
tools as `t.parentElement.parentElement` — a fixed two levels up. With
a 71-row table beside a 10-row one under a shared grandparent, the long
table's filter was reported against the short one, and the clause read
as "a short table carries a filter" when nothing of the sort had
happened. It walks to the nearest ancestor holding this table and no
other now.

### Mutations verified red and reverted (4)

Counts are what the run printed, not what was expected of it. Run
against the committed tree.

| # | mutation | reddened |
|---|---|---|
| M1 | the projection removed — the state before this item | 12 failed, 1 passed |
| M2 | `configure_phase.per_element` published again | 1 failed, 48 passed — `test_every_map_keyed_by_a_uid_declares_its_values[macro_micro]`, in the contract's own guard rather than this item's |
| M3 | `wall_s` left unconverted | 2 failed, 32 passed — this item's projection clause and `test_what_cannot_resolve_is_named_with_a_reason` |
| M4 | a binary ranked by calls alone dropped from the rows | 2 failed, 11 passed — `test_every_measured_element_and_binary_has_a_row`, `test_a_binary_ranked_by_calls_alone_keeps_its_count` |

M2 is worth noting: the mutation is caught by the **contract's** guard,
not by this item's file. That is the right owner — one population
published once is a rule about the document, and a per-item clause
restating it would be a second copy of the thing it asserts.

### Deviation from the Required Fix

- **"Frequency and time per binary, for the run and per element"** is
  met by `by_binary` (run, counts) and `binary_cost` (per element and
  binary, counts *and* CPU). A run-level *time* per binary would be a
  sum this document does not publish, and summing across elements is a
  computation rather than a projection — Direction 7's boundary.
- **`configure_phase.per_element` is not published**, for the
  one-population-once rule above. The filing asked for "the configure
  phase as a number", which is met at run level.
- Test-image classification remains out of scope and unfiled, as the
  filing says.
- **`UX-374` was filed from this work**: the map renderer capitalises
  every key, so `cmake` draws as `Cmake` and `codegen.bst|BUILD|BUILD|0`
  as `Codegen.bst|…`. Pre-existing, wider than this item, and the tool
  renaming a name it was given.
