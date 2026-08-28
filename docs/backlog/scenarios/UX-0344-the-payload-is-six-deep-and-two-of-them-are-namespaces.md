# UX-344: the payload is six deep, and two of them are namespaces

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-229 (provenance, the deepest shape), UX-288 (publish each population once), UX-277 (what a deep value costs a cell) | **Serves:** anyone reading the JSON, and every renderer that walks it | **Topic:** contracts

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

## Outcome (round 53, 2026-08-28) — 🟢 Done

`analyze/v4`. Three removals and two renames, which is what a version
move is for, and `analyze/v3` joins the read-never-written set.

### The shape, before and after

Measured on the two committed fixtures, counting a container step per
level - the same walk this item was filed with, published with the
document now:

```text
                     leaves   deeper than three   deepest
golden      before      489         281 (57%)        6  findings.[].provenance.rule.threshold.[]
            after       462         184 (40%)        5  provenance.[].evidence.[].path
macro_micro before     1442         967 (67%)        7  findings.[].evidence.steps.[].entering.[]
            after      1433         771 (54%)        7  (the same path)
```

`macro_micro` keeps its seventh level and the item said it would:
`findings[].evidence.steps[].entering[]` is four real relations, not a
namespace. The golden report reaches the five the acceptance asked for.

### What moved, and why each one

**The two namespaces are gone.** `signals` held nineteen tables and
`structural` nine; neither carried a value of its own, and both cost
every table below them a level. Each table is a top-level key with the
`bga:rail` its namespace used to carry for it - which is what `UX-286`'s
chapters place a section by, so eighteen new sections landed in the
chapters they belong to with the table naming only the ones whose rail
is a poor proxy (the ready queue is about the machine, not about which
element to fix). Two were renamed: `metrics` and `summary` would have
been two of the most generic keys in the document, and the page already
draws a `summary` section - the run's own scalars - that a second
`data-section="summary"` would have collided with. They are
`graph_metrics` and `graph_summary`.

**The element population is one key, not six.** Lifting the six
element-keyed maps to the top level would have published one population
as six sections, which is exactly `UX-338`. They are members of
`elements`, with `zero_slack_share`, `top_blast_radius` and
`blast_radius_ranked_by` beside them because each describes the
population rather than any one element - and a scalar at the top level
is drawn into the run-identity summary beside the run id. The page kept
its **own list** of which signals were element-keyed to do `UX-268`'s
join; it reads the document now, and `ELEMENT_KEYED_SIGNALS` and the
note arguing `wall_clock_share_us` out of it are gone from
`structured.js`.

**`provenance` is published once per claim.** It used to be written
into the headline, into every finding, and - as a `see` path pointing
back at the finding's copy - into every top action: the document's
deepest shape, nested inside the record it explains, three times.
`findings[].id` and `headline.top_actions[].finding_id` are the claim
ids; `provenance.for_claim` is the lookup, and the terminal, the page,
the CI comment and `compare/v2` all use it. `reference()` and the `see`
field are gone, and `unresolved_references` now reports a claim that
resolves into nothing, which is the dangling shape that replaced them.

**`findings[].evidence.blast_radius` is gone rather than tabulated.**
The Required Fix asked for rows with an `element_uid` "so its columns
can be declared". Measured: as a row list inside `findings[].evidence`
its fields sit at depth **six**, exactly where the map's did - the
item's "depth 5 and declarable" counted a level the shape does not
lose. And the rows were a slice of `elements.blast_radius`, keyed by
the same uids, inside the finding that already names those elements in
its `elements` field - `UX-288`'s rule. So the population is published
once and the finding cites membership. The finding's prose already
carried the numbers (*"app.bst (7 downstream elements, at or above p90
of this run)"*), so no reader lost one.

### The document publishes its own shape

`document_shape` carries the leaf count, the deepest path, the count
over three levels and that count as a share - **counting itself**, so a
consumer that re-measures gets these numbers back. This item had to
write a script against two fixtures to find out the depth; the next
round reads it off the document, and a guard re-measures and compares,
which is the clause that catches a level coming back.

### Where the clauses landed

`test_no_level_carries_nothing.py`, eleven clauses over both fixtures.
Two acceptance clauses were **not** implemented as written, with the
measurement that decided it:

- *"every non-leaf key either holds a value of its own or is a list"*
  does not separate what this item is about: `signals` carried
  `zero_slack_share`, so it passes that test, and `bottleneck` - which
  nobody proposed lifting - fails it. The clauses assert the properties
  the item's own prose states: the namespaces are gone, every table
  they held is still published, and the element population is one key.
- *"no map has keys the schema does not name"* is unreachable and
  `UX-343` had already settled why: a map keyed by element uid cannot
  name `app.bst` in `properties`, so it declares what a *value* is
  under `additionalProperties` and every key resolves to that. The
  clause asserts that instead - and found `leaf_analysis.leaves_detail`
  on its first run, an element-keyed map of four-field records
  declaring nothing at all.

### Mutations verified red and reverted (7)

Run against the committed tree at `0ee6f17`.

| # | mutation | reddened |
|---|---|---|
| M1 | `signals` is published as a namespace again | 8 clauses, including *"`['signals']` is back - a level that holds only other levels"* |
| M2 | `document_shape` stops counting its own leaves | `test_the_published_shape_is_the_measured_shape`, both fixtures |
| M3 | the record is written back into each finding as well | `test_no_claim_carries_a_copy_of_its_chain`, and the depth and share clauses with it |
| M4 | the blast-radius slice returns to `findings[].evidence` | `test_no_finding_republishes_the_element_population`, plus the undeclared-map and deepest-leaf clauses |
| M5 | `leaves_detail` declares `properties` instead of `additionalProperties` | `test_every_map_keyed_by_a_uid_declares_its_values` - the clause that found it |
| M6 | one finding's record is not published | `test_the_chain_is_published_once_per_claim` and `test_every_id_a_claim_carries_resolves_into_it` |
| M7 | the six element-keyed maps are lifted individually | `test_the_element_population_is_one_key_rather_than_six` - added *because* the first run of this mutation reddened only a provenance path, which is not the property being claimed |

### Guards that moved with the shape, each for a reason

- `test_the_fold_says_how_deep_it_goes`: the expand control's threshold
  was `depth > 1` because `signals.leaf_analysis.leaves_detail` sat two
  levels inside its section. Lifting made `leaf_analysis` a section and
  the same cramped table one level nearer the top, so the number moved
  to `depth > 0`; the rule - a table inside a cell offers the way out -
  is unchanged. Measured after: five expand controls on golden, nine on
  `macro_micro`, where there had been zero.
- `test_the_page_has_geometry`'s padding clause measures the chapter's
  own chrome (head and tail) rather than the whole difference from the
  sum of its sections. With thirteen sections in the `elements` chapter
  the *gaps between them* were 0.42 screens of that difference at
  390px, and a gap is layout, not padding.
- `test_the_order_the_page_has` and `test_the_report_has_chapters`: the
  identity chapter closes on four blocks, because `document_shape` is a
  fact about the artifact, like the producer stamp above it.
- `test_a_sentence_lives_on_its_door` counts inline renders rather than
  distinct keys: `sum_of_individual_us` is drawn in a finding's
  evidence *and* in the lifted `joint_saving` section, and two renders
  are two doors that are not there.
- `test_the_structural_block_is_reachable` walks the three sections the
  namespace's tables became, rather than one section that no longer
  exists.
- `test_output_schemas` gains a third pinned list: lifting turned one
  always-present key into fourteen, four of which depend on what the
  run has (`cache` and the two distributions need a population;
  `fetch_build_overlap` needs both phases).

### What this leaves

`element_join[].recommendations[]` and `element_join[].worst_redundancy`
are the deepest shapes left on `macro_micro` after the findings, and
both are records with genuinely nested parts - the case the item's Out
of Scope names. The 54% still deeper than three is mostly `findings[]`
and `element_join[]`, one row per element and per claim; the levels
that carried nothing are gone.
