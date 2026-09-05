# UX-382: the element entity has two shapes, and they share one attribute

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-288 (analyze/v2 publishes each population once), UX-216 (every element is one object), UX-356 (every field of the element join reaches a reader) | **Serves:** anyone writing a new view over an existing capture | **Topic:** contracts | **Area:** bga

## Motivation

Round 60 asked whether the data model should be normalised so that
experimenting in `bga view` gets cheaper. Measured on a 40-element
capture, `analyze/v4` carries the element entity twice, in two shapes,
and the two halves barely overlap:

```text
attributes of the element entity, by where they live

  elements.<map>   ( 8): blast_radius, criticality_probability, downstream_count,
                         element_durations, slack, top_blast_radius,
                         unweighted_depth, zero_slack_share

  element_join row (18): aggregating_dependencies, blast_radius, cores_busy,
                         cpu_coverage, critical_path_share, declared,
                         dominant_binary, native_findings, on_critical_path,
                         peak_rss_bytes, potential_saving_us, recommendations,
                         redundancy_count, requested_jobs, saving_share,
                         serial_binary, unused_dependencies, worst_redundancy

  in both          ( 1): blast_radius
  only as a map    ( 7)
  only as a row    (17)
```

Twenty-four attributes of one entity, one of which is in both places.
The column form is six full maps keyed by uid; the row form is a
42-record table. Neither is a superset of the other, so **any question
spanning them has to be joined in the viewer**. "Which elements are at
depth 3, on the critical path, and peaked above a gigabyte" reads
`unweighted_depth` from one shape and `on_critical_path` and
`peak_rss_bytes` from the other, and there is no join key published as
such — only the convention that both are keyed by uid.

The redundancy is visible in the payload's own bytes:

```text
payload                              140,798 B
element-name occurrences               2,178
bytes spent re-spelling uids          23,442   (16.6%)
occurrences per element                 51.9
```

Fifty-two spellings of each element name, for forty-two elements.

**This is not an argument that the column form is wrong.** It is
deliberate and it earns its place: a map keyed by data declares its value
type once under `additionalProperties` (`UX-343`), which is what lets
one schema describe a population of any size, and `UX-288` chose it to
stop the same population being published several times over. The defect
is not the shape — it is that **there are two shapes and no rule saying
which attribute belongs to which**, so every new view starts by
discovering where its columns live.

In relational terms: six single-attribute relations sharing a primary
key, beside a wide table on the same key, with no declared foreign key
between them. Third normal form is not the goal here — the goal is one
statement of *what an element is*, and one place a new attribute goes.

## Required Fix

Not a rewrite of the payload. A rule, declared and guarded.

- **The schema declares the element entity's key**, so `element_join`'s
  `element` and every `elements.*` map key are stated to be the same
  identifier rather than conventionally so. `UX-216` made every element
  one object for the *reader*; this makes it one object for the
  *schema*.
- **One rule for where an attribute goes**, written where a contributor
  will meet it — the natural line is that a scalar per element is a
  column map, and anything with structure (a list, a record, a nullable
  join result) is a join field, which is what the current split almost
  is. Then `blast_radius`, the one attribute in both, resolves to one
  side.
- **The viewer gets the join once**, rather than each section
  re-deriving it. `element.js` already knows the column maps and
  `element_join` already knows the rows; one resolved element record,
  built once, is what a new view should be able to ask for.

The payload keeps both shapes and stays byte-compatible; what changes is
that the relationship between them is declared instead of implied.

## Falsification

A guard that reads `analyze/v4` and asserts every attribute of the
element entity is reachable from one resolved record, and that no
attribute appears in both shapes. Today the second fails on
`blast_radius` and the first has no record to reach from.

The other direction, so the fix is not "flatten everything into rows":
the column maps still declare their value once under
`additionalProperties`, and the payload's byte count does not grow —
which is the property `UX-288` bought and this must not spend.

## Out of Scope

- Plane 2's own shapes. `plane2/v2` is keyed by element too, and
  whether it joins here is a real question and a later one.
- The store's cross-run shape (`store/v1`). That is a different entity
  keyed by run rather than by element, and folding it in would widen a
  question that is already about two shapes too many.

## Outcome

Done, and the answer is not "flatten one shape into the other". The
key is declared, the rule is written where the code that follows it
lives, both denormalisations are named and held equal to their source,
and the viewer builds one resolved record. The payload does not change
by a byte.

**The rule is not the one this filing proposed.** It offered
scalar-versus-structured; the data falsifies that - ten of the join's
eighteen fields are scalars. The tree's real rule was already in the
schema's own sentence for `element_join` ("there is no join with one
plane"), just never stated as a rule: **an attribute the analysis
knows from the graph and Plane 1 alone is a map under `elements`, on
every capture; an attribute that needs Plane 2 to exist is a field on
an `element_join` row.** That is now `schemas.ELEMENT_PLACEMENT_RULE`,
and `bga/correlate.py`'s two copying sites carry a comment pointing at
it.

**Two denormalisations, and the filing counted one.** `blast_radius`
is the one shared *name*, and the two do not even share a type -
`elements.blast_radius[uid]` is a record and `element_join[].blast_radius`
is that record's own `downstream_count` as an int, which
`elements.downstream_count[uid]` publishes a third time.

The second is invisible to a count of names, because it is one fact
under two of them: `element_join[].on_critical_path` is
`elements.criticality_probability[uid].observed_critical`. They agree
on every element of every capture measured here, and nothing derived
one from the other or held them equal - `on_critical_path` comes from
`schemas.critical_path_uids` and `observed_critical` from the
criticality map, so they agreed by both descending from the same
critical path rather than by construction.

Both are kept: the join table sorts on them, and deleting a rendered
column to tidy the model would be a regression for a reader. Both are
now declared as denormalisations, guarded equal to their map, and the
resolved record takes the map's - which is what "resolves to one side"
means once the join table's need is admitted.

**A recorded deviation.** The Falsification asks that no attribute
appear in both shapes. Two do, deliberately, for the reason above. The
guard asserts the stronger property in its place: each is equal to the
map it was copied from, on every element, and neither reaches the
resolved element record twice.

## Verification Log

**The viewer-side defect, measured before and after.** `elementFactsFor`
returned the `SOURCES` record where the report's ranking had reached an
element and built from the column maps only where it had not, so no
element ever had both:

```text
                                      before      after
examples/06 (11 elements)
  fields on a ranked element's record     12         20
  records answering depth+critical+RSS   0/11       9/11

synthetic (1,202 elements, Plane 1 only)
  fields on a ranked element's record      1         10
  fields on an unranked one               10         10
```

The two of eleven that still cannot answer are `all.bst` and
`toolchain.bst`: no sandbox process was billed to either, so they carry
no `peak_rss_bytes`. That is an absence rather than a gap (`UX-308`'s
rule), and the guard asks the question of the elements Plane 2 measured
rather than of all of them.

At scale the before-figures are the item's own point in one line: the
report's top twenty-six elements had **one** field each and the 1,176
it never ranked had ten. Both are ten now.

**The two denormalisations, on the committed fixture:**

```text
element_join[].blast_radius      vs elements.blast_radius[uid].downstream_count
                                    11 rows, 0 disagreements
                                 vs elements.downstream_count[uid]
                                    11 rows, 0 disagreements
element_join[].on_critical_path  vs elements.criticality_probability[uid]
                                      .observed_critical
                                    11 rows, 0 disagreements
```

**The payload does not grow** - `UX-288`'s property, which the Out of
Scope section says this must not spend:

```text
bga analyze tests/fixtures/macro_micro/run --format json | wc -c
  before   88,424 B
  after    88,424 B
```

Nothing moved in the document. What changed is that the relationship
between its two shapes is declared, and the viewer resolves it once.

**Mutation sweep**, eleven mutations against the committed tree, each
run against `tests/unit/test_one_element_one_record.py`:

```text
M1  elementFactsFor returns the ranked record alone     CAUGHT (2 failed)
M2  a field already held is written twice               CAUGHT (1 failed)
M3  the join's blast_radius returns beside the map's    CAUGHT (1 failed)
M4  the declared key names a field the join has not     CAUGHT (6 failed)
M5  the rule stops saying what decides the split        CAUGHT (1 failed)
M6  blast_radius stops naming the map it copies         CAUGHT (1 failed)
M7  on_critical_path stops naming observed_critical     CAUGHT (1 failed)
M8  ELEMENT_KEYED gains a name that is not a map        CAUGHT (2 failed)
M9  the join's blast_radius is derived differently      CAUGHT (2 failed)
M10 the rule stops naming the two denormalisations      CAUGHT (1 failed)
M11 on_critical_path comes from a different source      CAUGHT (1 failed)
```

**One mutation was rejected rather than counted.** Removing
`blast_radius` from `ELEMENT_KEYED` reddens the file, but by raising
`KeyError` at import - the tree does not build, so the guard is not
what caught it. M8 above replaces it with one that leaves the module
importable: a seventh name in `ELEMENT_KEYED` that is not a map, which
two clauses discriminate on.

M9 and M11 are the pair the item is really about: they make one
denormalisation disagree with its source, which is the failure mode a
declared-but-unguarded copy has and the reason the two clauses exist.

**And what the export costs**, which the size discipline in
`tests/unit/test_the_report_you_can_attach.py` made me measure rather
than assert. Split into the page (the hand-written modules and the
stylesheet) and the data (the embedded documents and their schema):

```text
                        total       page       data
80097a5 (round start)  359,421    267,830     91,591   golden
UX-380                 360,674    269,083     91,591   +1,253 page
UX-382                 361,524    269,226     92,298   +143 page, +707 contract
```

`macro_micro` moved by the identical 2,103 B, split identically -
which is what a source-and-schema change looks like from here: neither
item added a row to any payload, and the prose travels whether or not
a run has the data. Golden carries no `element_join` at all and still
pays the 707 B, the same fact `UX-370`'s note in that file records.

Both bounds are restated with that split rather than the two schema
sentences trimmed to fit a number nobody argued.
