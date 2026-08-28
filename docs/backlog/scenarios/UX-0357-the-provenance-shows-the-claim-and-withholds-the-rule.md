# UX-357: the provenance section shows the claim and withholds the rule

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-229 (publish why bga believes what it believes) | **Serves:** the reviewer who has to decide whether to trust a number before acting on it | **Topic:** viewer

## Motivation

`UX-229` published the tool's reasoning: for every claim, the rule that
produced it, the evidence it read, the threshold it compared against,
and the inputs it wanted and did not have. `provenance` is drawn as a
section on both fixtures. Round 55 measured which of its sixteen fields
reach a rendered node:

```text
macro_micro, provenance (12 entries)          on page / not
  claim                                            12 / 0
  document                                         12 / 0
  kind                                             12 / 0
  evidence[].quantity                              26 / 0
  evidence[].value                                 25 / 0
  rule.threshold_quantity                           4 / 0
  rule.comparison                                  10 / 2
  evidence[].path                                   7 / 22
  rule.threshold                                    1 / 2
  rule.sentence                                     1 / 11
  rule.module                                       0 / 12
  rule.name                                         0 / 5
  rule.observed_path                                0 / 5
  unpublished_inputs[]                              0 / 3
```

`golden` is the same shape at its own scale (`rule.sentence` 1 of 5,
`evidence[].path` 2 of 11).

So the section renders the *conclusion* and the *numbers*, and drops
the four things that make it provenance:

- **`rule.name` and `rule.module`** — which rule fired, and where it
  lives. `CHAIN_BOUND_RATIO` in a named module is the difference
  between "the tool says so" and a claim a reader can go and read.
- **`rule.sentence`** — the rule stated in words, e.g. *"The critical
  path is 87.5% of wall-clock"*. Eleven of twelve are withheld.
- **`evidence[].path`** — *where* each number came from
  (`floors.t_infinity_observed`, `headline.chain_share`). The value is
  shown; the address that lets a reader check it is not. Twenty-two of
  twenty-nine.
- **`unpublished_inputs[]`** — the inputs the rule wanted and this run
  does not have. This is the one field whose whole purpose is to be
  read by a sceptic, and it is drawn zero times out of three.

A provenance section that shows the verdict and hides the rule is the
one section on the page whose job it fails by rendering.

## Required Fix

Styleguide §1b's second and third clauses, applied to `provenance`:

- Each entry names its rule — `name`, `module`, and the sentence — and
  each evidence row carries the payload path beside its value. The
  path is a `code` span, not a link: `UX-216`'s cross-reference is for
  elements, and a payload path is an address into a document, not a
  section on the page.
- `unpublished_inputs` renders as a stated absence — `UX-329`'s rule,
  *absence is stated, never drawn* — with the same wording discipline
  as the Plane 2 absence sentence.

The section is already 517 px on `macro_micro`, so this is not a bare
addition: `rule.comparison` and `rule.threshold` are today rendered as
loose values and read as noise. The four withheld fields plus the two
loose ones are one block — *this rule, in these words, fired because
this number crossed this threshold, and here is where each number
lives* — and it should render as one.

## Out of Scope

- `trace_query` (2 of 9). It is a Perfetto query string and belongs
  with the handoff, not the provenance block; see `UX-358`, which is
  about the handoff having no fixture to be measured on at all.
- The *number* of provenance entries, and whether twelve claims each
  deserve a block. That is `UX-360`'s volume question.
- `element_join`'s 142 misses — `UX-356`, filed separately because
  the promise it breaks is a different one.

## Acceptance Test

Booted, both fixtures: every field `provenance` publishes reaches a
rendered node, asserted against the payload rather than a list of
field names, with `trace_query` the single named exemption and its
reason written where the exemption is. And, as the other direction: a
run whose `unpublished_inputs` is empty draws no absence sentence, so
the clause is a distinction rather than a decoration.

## Outcome (round 56, 2026-08-28) — 🟢 Done

### The gap, measured — and its cause

```text
macro_micro, provenance (12 records)   before / after
  rule.module                            0/12 -> 12/12
  rule.name                               0/5 ->   5/5
  rule.observed_path                      0/5 ->   5/5
  rule.sentence                          1/12 -> 12/12
  evidence[].path                        7/29 -> 29/29
  unpublished_inputs[]                    0/3 ->   3/3
```

The cause was a **declaration**, not a renderer. The schema gives
`provenance` a `bga:columns` of `claim` and `kind`, so the section
renders as a two-column table — and a table takes the scalar columns
and drops everything nested. Every field that makes a provenance record
*provenance* is nested.

### The shape is the page's own

An **index table plus a detail block per row**, which is exactly what
`elements` and the element sections are, and what `UX-356` extended a
commit earlier. `renderProvenance` has existed since `UX-229`; nothing
reached it from the section path. `renderProvenanceRecords` appends one
block per claim, and the two-column index over twelve claims stays —
`test_the_index_table_survives` asserts it, because a fix that replaced
the table would be a different design and should have to say so.

### Three things the block never said

- **The observed path**, beside the comparison and the threshold:
  `CHAIN_BOUND_RATIO` `headline.chain_share >= 0.9` in
  `bga/findings.py`. It is the one address that says which published
  number the rule compared, and it was published from the first and
  rendered nowhere.
- **The document the paths resolve against.** The schema calls this
  load-bearing the moment a record travels — a `compare/v1` chain read
  beside an `analyze/v4` one resolves elsewhere.
- **The module, on a record with no named rule.** Six of
  `macro_micro`'s twelve publish a module and a sentence and no named
  threshold, because the claim is computed rather than gated. The old
  condition gated the whole paragraph on the name, so those six said
  where they came from nowhere. One of them —
  `cache-hit-ratio` — publishes an observed path and *no* threshold
  (`confidence.run_mode present`), which the block now says too.

### Mutations verified red and reverted (6)

Counts are what the run printed, not what was expected of it. Run
against the committed tree at `d443347`.

| # | mutation | reddened |
|---|---|---|
| S1 | the records are not drawn — the section is the table alone, the defect itself | 7 |
| S2 | the rule paragraph is gated on the name again | 1: the six nameless records |
| S3 | the observed path is an attribute again and not in the text | 2 |
| S4 | `unpublished_inputs` stops rendering | 2, including the coverage clause |
| S5 | the fold stops counting its evidence | 2 |
| S6 | the index table is removed and only the blocks remain | 2 |

**S3 survived the first draft**, and both reasons were the guard's.
The clause read `data-observed`, which the mutation did not touch — and
the coverage clause could not see the loss either, because
`headline.chain_share` is *also* published as an `evidence[].path` on
the same record, so the string was reachable however the rule
paragraph rendered. The clause now asserts the path is in the block's
rendered **text**, which is the claim being made: the block says which
number the rule compared.

Strengthening it also turned the clean tree red, on the one record
that publishes an observed path with no named rule — a defect the
first version of the renderer had and the first version of the guard
could not see.

### `trace_query` is the one named exemption

Two of nine reach the page, and both by coincidence: the id
(`element-time`) also names a query in the handoff's own library, which
the questions section prints. It is carried on the block as
`data-query` so the handoff can find it — a machine's channel, not a
reader's. `EXEMPT` names it with that reason written where the
exemption is, and `test_the_exemption_is_still_withheld` reddens if the
page starts drawing it, so the exemption cannot quietly cover the next
field to fall under it.

### Deviation from the Required Fix

- The Required Fix said the evidence path should render as "a `code`
  span, not a link", and it does — but the paths were **already**
  rendered as `code` spans by `renderProvenance`; what was missing was
  anything calling it for the section's records. The fix is a wiring
  change, not a rendering one, which is why it is eleven lines.
- The Required Fix expected `rule.comparison` and `rule.threshold` to
  be "rendered as loose values" that needed gathering. They were not
  rendered at all in the section; they were rendered in the *finding*
  blocks, which is where the round-55 measurement found its one hit of
  each. The gathering happened anyway — the rule now reads as one
  sentence — but the filing's description of the starting state was
  drawn from the wrong two records.
- Two guards outside this item moved with the change, both recorded in
  the commit: the no-derivation guard's `published` set gained four
  fields of the same record and its layout allowance became an explicit
  set of strings rather than a pattern; and `renderProvenance` builds
  its connectives with `span` rather than `createTextNode`, because
  thirty-four test stubs hand-build a `document` offering
  `createElement` and little else. That is `UX-264`'s complaint still
  half-true, and it is not this item's to fix.
