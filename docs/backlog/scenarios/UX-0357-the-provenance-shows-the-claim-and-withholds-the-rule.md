# UX-357: the provenance section shows the claim and withholds the rule

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-229 (publish why bga believes what it believes) | **Serves:** the reviewer who has to decide whether to trust a number before acting on it | **Topic:** viewer

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
