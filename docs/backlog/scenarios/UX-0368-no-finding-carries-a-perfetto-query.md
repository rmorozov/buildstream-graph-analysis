# UX-368: no finding carries a Perfetto query

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-229 (why bga believes what it believes), UX-312 (the canned question library), UX-348 (the handoff) | **Serves:** anyone who reads a finding and wants to see it in the trace | **Topic:** viewer | **Area:** bga

## Motivation

The tool's distinguishing claim is that it hands a build to Perfetto
with both planes on one clock. The report states findings. The two are
not connected:

```text
macro_micro: 11 findings
finding keys: copy_text, detail, elements, evidence, id, indent, severity, title
findings carrying trace_query: 0 / 11
```

`trace_query` exists — `provenance` records carry it, and `UX-312`
built a library of thirteen queries. But the library sits in its own
section, addressed to nobody in particular, and a reader who has just
been told *"4 element(s) are 71.9% of the 43.2s critical path"* is given
no query that shows those four in the trace.

So the handoff is a section a reader visits, rather than the next step
of the finding they are reading. The queries are general; the finding is
specific; nothing joins them, even though every finding already names
its `elements`.

## Required Fix

Every finding that names elements carries the query that shows them.

- A `trace_query` on the finding, resolved against the same library
  `UX-312` published, with the finding's own elements substituted — see
  `UX-369`, which is about the substitution being hard-coded today.
- Rendered where the finding is, not only where the library is: the
  finding's fold gains "see this in the timeline", the way `UX-204`
  gave each finding a button that knows why.
- Findings that name no element (`confidence`, `efficiency-score`) carry
  none, and the absence is stated rather than drawn empty — `UX-321`'s
  rule.

The mapping is the deliverable: **every finding id to the query that
shows it**, published in the contract so the page does not derive it.

## Falsification

Assert over the payload: every finding carrying a non-empty `elements`
carries a `trace_query`, and the query names those elements. Today that
is 0 of 11, which is the finding.

The other direction, so the fix cannot be a decoration: the query a
finding carries has to differ between findings that name different
elements. One query pasted onto eleven findings passes a "has a query"
clause and helps nobody.

## Out of Scope

Running the query. The page hands over to Perfetto and does not execute
SQL — `UX-296` and the viewer/Perfetto boundary. This item ends at
handing the reader the right query for the finding in front of them.

## Outcome (round 59, 2026-08-28) — 🟢 Done

### The gap, measured — and it was not the one filed

The filing read the mapping as missing. It was not: `TRACE_QUERIES`
maps 20 finding ids to queries and `provenance[].trace_query` has
published it since `UX-229`. What was broken is the **joiner**.

`trace_context.js` read `finding.provenance.trace_query` — true when
`UX-229` wrote it, because the record was written *into* each finding.
`UX-344` moved the records out into one list, correctly, and this line
was not moved with them. Measured on `tests/fixtures/with_timeline`,
the one committed capture whose handoff button works:

```text
findings whose id is in TRACE_QUERIES:  6
Investigate boxes drawn on the page:    0
```

Four rounds of a dead control on every report, with
`test_buttons_that_know_why.py` green throughout — **because every
clause in it built its own finding object with the nested shape
inline**. A guard that constructs its input cannot notice that the
producer stopped producing it.

### After

```text
Investigate boxes on with_timeline:     9
distinct queries among them:            6
element-scoped ones, and their element: element-commands -> codegen.bst
                                        waited-on-flow   -> core.bst
empty substitutions (`= ''`):           0
boxes on the two captures with no timeline: 0   (UX-194's rule, held)
```

`provenance.attach` stamps `finding["trace_query"]` from the same table
in the same pass, so the record and the finding cannot disagree; the
schema declares the key; `queryFor` reads it. The golden snapshot moved
by exactly four values plus `document_shape.leaves` 462 → 466.

### Two decisions worth stating

**An element is substituted only where the query asks for one.**
`stalls` and `cpu-versus-wall` are questions about the run; handing
them a name the SQL never uses would put it in the Perfetto tab title
and nowhere else.

**`withElement` renders the token, not the empty string.** `UX-369`
removed the per-entry `example` and this fallback became `""`, so a
finding whose query asks about one element while naming none handed
over `= ''` — a query that runs and returns nothing.

### Mutations verified red and reverted (5)

Counts are what the run printed, not what was expected of it. Run
against the committed tree.

| # | mutation | reddened |
|---|---|---|
| M1 | `attach` stops stamping the finding — the state before this item | 12 failed, 15 passed |
| M2 | `queryFor` reads the nested shape again | 9 failed, 18 passed |
| M3 | one query on every finding — the decoration the filing warns about | 7 failed, 20 passed |
| M4 | an element handed to a query that does not ask for one | 1 failed, 26 passed |
| M5 | `withElement` back to the empty substitution | **0 failed at first**; with the clause added, 1 failed, 18 passed — `test_a_query_needing_an_element_it_was_not_given_shows_the_token` |

M5 is the instructive one: no finding on the committed captures is in
the state that exercises the path — an element-scoped query on a
finding naming no element — so the page-level clause never reaches it.
Asserted directly on `withElement` instead.

### Deviation from the Required Fix

- **The predicate is the table, not the element count.** The filing
  said "every finding that names elements carries the query" and
  "findings that name no element (`confidence`, `efficiency-score`)
  carry none". But `efficiency-score` *is* in the table, mapped to
  `cpu-versus-wall`, and names no element — following the filing
  literally would delete a mapping `UX-312` deliberately built. A
  finding carries what the published table says and nothing else;
  `confidence`, `mesh-graph` and `cache-hit-ratio` are in no table row
  and carry null.
- **"The query names those elements" holds only for element-scoped
  queries.** `time-concentration` maps to `element-time`, which ranks
  every element by time — it shows the four the finding names, among
  the rest. Re-pointing it at an element-scoped query would change the
  question `UX-312` chose. The clause asserted instead is that queries
  differ between findings (6 distinct across 9 boxes) and that
  element-scoped ones carry this run's own elements.
- **The instrument was wrong twice before the code was.** A first
  probe read `provenance[].claim_id` (the key is `claim`) and reported
  the mapping as entirely unpublished; a second read `#perfetto` as
  the handoff precondition, which is in `index.html` on every page —
  only the `#actions` wrapper around it is conditional — and made the
  two no-timeline captures look like the defect.
