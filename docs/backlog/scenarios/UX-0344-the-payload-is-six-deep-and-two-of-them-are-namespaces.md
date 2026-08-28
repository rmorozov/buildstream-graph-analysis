# UX-344: the payload is six deep, and two of them are namespaces

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-229 (provenance, the deepest shape), UX-288 (publish each population once), UX-277 (what a deep value costs a cell) | **Serves:** anyone reading the JSON, and every renderer that walks it | **Topic:** contracts

## Motivation

Asked directly: can the documents be organised at most three levels
deep? Measured on the real emitted `analyze/v2`, counting a container
step per level:

```text
golden       497 leaves   depth 1:6  2:85  3:133  4:157  5:70  6:46
                          deeper than three: 273 (55%)
macro_micro 1482 leaves   depth 1:6  2:126 3:393  4:547  5:280 6:129  7:1
                          deeper than three: 957 (65%)
```

Re-measured on `analyze/v3` after `UX-343` and `UX-341` (the leaf count
moved because `top_opportunities` became named rows and the retired
units were renamed; the *shape* did not):

```text
golden       490 leaves   depth 1:5  2:80  3:124  4:151  5:76  6:54
                          deeper than three: 281 (57%)
                          deepest: findings.[].provenance.evidence.[].path
macro_micro 1447 leaves   depth 1:5  2:118 3:353  4:533  5:286 6:151  7:1
                          deeper than three: 971 (67%)
                          deepest: findings.[].evidence.steps.[].entering.[]
```

The depth is not spread evenly — it is a handful of shapes:

```text
6   81 leaves  findings.[].provenance.evidence.[]
5   69 leaves  element_join.[].recommendations.[]
5   64 leaves  findings.[].provenance.rule
4   60 leaves  signals.critical_path_detail.[]
4   55 leaves  findings.[].provenance
4   45 leaves  element_join.[].dominant_binary
5   45 leaves  element_join.[].worst_redundancy.elements
```

and one leaf at depth **seven**:
`findings.[].evidence.steps.[].entering.[]`.

**Two of those levels are namespaces, not data.** `signals` is a map of
five named tables; `structural` is a map of named sub-objects. Neither
carries a value of its own — they exist to group, and they cost every
table below them a level. Lifting the five `signals.*` tables to the
top level takes `critical_path_detail` from 4 to 3 with no information
moved.

**One is a map keyed by data.** `findings.[].evidence.blast_radius` is
keyed by *element name*:

```text
findings.[].evidence.blast_radius.app.bst.risk_score          (depth 6)
findings.[].evidence.blast_radius.lib.bst.downstream_count    (depth 6)
```

A map whose keys are values is the one shape that cannot be flattened,
declared or tabulated — the schema cannot name `app.bst`, so it cannot
say what `risk_score` is either. As a list of rows with an
`element_uid` field it is depth 5 and declarable.

**And the deepest shape is a join nested inside one of its sides.**
`findings[].provenance` is `UX-229`'s explanation of one claim, nested
inside the claim. It already carries `claim`, `kind` and `document`.
Published as a top-level `provenance` list keyed by claim,
`provenance[].evidence[]` is depth 3 and findings link to it by id.

> **The deduplication half of this argument no longer holds, measured
> after `UX-343`.** This item was filed saying the block repeats — *3
> identical 145-byte `provenance` objects in the golden report* — and
> `UX-342` handed over 4,046 B of repeated prose as "all of it the
> provenance block written three times". Re-measured on the emitted
> `analyze/v3`:
>
> ```text
> golden       4 provenance blocks, 4 distinct, 2,601 B
> macro_micro 11 provenance blocks, 11 distinct, 7,442 B
>
> repeated object bytes (objects ≥60 B appearing more than once)
> golden      1,374   largest: a 308 B provenance fragment x3, then a
>                     280 B element record x3, then a 236 B one x3
> macro_micro 3,054   largest: an 812 B element record x8
> ```
>
> `UX-343` gave every evidence row a `quantity` and every rule a
> `threshold_quantity`, which are drawn from the row's own path — so no
> two provenance blocks are identical any more. What repeats now is
> mostly **element records**, republished across sections, which is a
> different item's shape. The normalisation is still worth doing for
> *depth*; it is no longer worth doing for *bytes*, and the figure
> `UX-342` handed over should not be quoted as if it were.

**Three deep is not reachable everywhere, and should not be claimed.**
`findings[].evidence.steps[].entering[]` is four real relations. What
*is* reachable is that no level exists purely to group, no map is keyed
by data, and nothing is nested inside a record it is only joined to.

## Required Fix

In the next contract version:

- `provenance` is published once, at the top level, keyed by the claim
  it explains; `findings[]` and `headline.top_actions[]` carry the claim
  id they already carry today. **`UX-342` left this saving here**: after
  the export stopped carrying six unreachable schemas, the repeated
  prose still inside `analyze/v2` is 4,046 B and *all* of it is the
  provenance block written three times, so normalizing the shape is
  also the deduplication, with no `$ref` indirection for the viewer to
  resolve;
- the `signals.*` and `structural.*` namespaces are lifted — each named
  table becomes a top-level key, which is also what `bga:rail` already
  groups them by for the reader;
- `findings[].evidence.blast_radius` becomes a list of rows with
  `element_uid`, so its columns can be declared (`UX-343`).

The measured depth is published with the document — the deepest path
and the count over three — so the next round can see the drift the way
this one had to measure it.

## Out of Scope

- Flattening for its own sake. A record with genuinely nested parts
  (`element_join[].dominant_binary`) stays nested; the rule is *no
  level that carries nothing*, not a number.
- The viewer's rendering of depth. `UX-318` already announces how deep
  a fold goes and `UX-277` bounds what a cell may print; those are
  about reading a deep value, this is about not publishing one.

## Acceptance Test

On both committed fixtures, no emitted document has a container level
whose only role is grouping — asserted as: every non-leaf key either
holds a value of its own or is a list. No map in any published document
has keys the schema does not name. The deepest path in the golden
report is at most 5, down from 6, and the fraction of leaves deeper
than three is pasted before and after. `provenance` appears once per
claim in the payload, asserted by count, and every `findings[].claim`
resolves into it.
