# UX-448: the element-scoped pivot has no finding to arrive from

**Priority:** Low | **Status:** 🔴 Not Started | **Found by:** round 70, scoping `UX-433` against `UX-368`'s rule | **Serves:** the reader who has picked an element and wants to know what it is made of | **Topic:** viewer

## Motivation

`UX-433` built the pivot — cpu, wall and peak RSS per **program**, on
the key `debug.exe` it added — and drafted two questions:

| question | scope |
|---|---|
| `cost-by-executable` | the whole build |
| `executables-in-element` | one sandbox |

The first shipped. The second did not, and the reason is `UX-368`'s
rule: *a question no finding points at is a question nobody arrives
at.* `bga/provenance.py`'s `TRACE_QUERIES` maps a claim to the query
that opens it; there are **22 claims and 20 already carry one**, and
neither spare (`cache-hit-ratio`, `confidence`) is about what an element
ran. `test_every_library_query_is_reachable_from_a_finding` is the
guard, and it is right.

So the query was dropped rather than added unreachable, and
`test_the_element_scoped_twin_is_not_in_the_library` holds it dropped
until this item.

`latent-heavies` is the closest claim — elements whose commands are
heavy though the element looks light — and it already points at
`element-commands`, which lists the *invocations*. The two are the same
reader question at two grains, which is the shape of the decision this
item has to make.

## Required Fix

Decide, and build one of:

- **A claim the element pivot answers**, if the report should make one —
  "this element's time is one program" is a real finding and the
  analyzer has the data (`plane2.by_binary`, published since `UX-370`).
  Then the question lands behind it.
- **Or a second query per claim**, if `latent-heavies` should offer both
  grains. That changes `TRACE_QUERIES`'s shape from one-to-one and the
  page's control with it, which is why it is a decision rather than a
  line.

Whichever: the SQL is written and measured — it is in `UX-433`'s
Outcome — so this item is the decision plus the wiring, not the query.

## Out of Scope

- **`debug.exe`** and the build-wide pivot: `UX-433`, closed.
- **Relaxing the reachability guard**: it caught this correctly, and a
  library of questions nobody can arrive at is exactly what `UX-368`
  built it to stop.

## Acceptance Test

The element-scoped pivot is in the library and
`test_every_library_query_is_reachable_from_a_finding` is green without
being weakened; `test_the_element_scoped_twin_is_not_in_the_library` is
deleted in the same commit, with its reason recorded here.

## Outcome

_Not started._
