# UX-382: the element entity has two shapes, and they share one attribute

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-288 (analyze/v2 publishes each population once), UX-216 (every element is one object), UX-356 (every field of the element join reaches a reader) | **Serves:** anyone writing a new view over an existing capture | **Topic:** contracts

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
