# UX-206: focused graphs, not a DAG viewer

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-202 (the overview these hang off), UX-199 (the anchors they link to), Direction 7 second iteration | **Topic:** viewer

## Motivation

The external review and Direction 7 arrived at the same restraint
independently: a general BuildStream DAG viewer answers no question
anyone asks, and the temptation to build one must lose to the two
graphs that *are* questions:

1. **The critical path, drawn**: the chain the report already prints
   as text, as a horizontal sequence — element boxes sized by
   duration, linked to their sections, the elided middle (UX-187's
   fold) expandable in place. It is the "where did the time go"
   spine, and it is a *list with widths*, not a graph layout
   problem.
2. **The blast tree**: the blast answer as an indented hierarchy —
   direct consumers, then closure by depth, each row carrying its
   kind badge and measured work — the review's own sketch, which is
   a `<details>` tree over data `blast/v1` already carries, not a
   renderer.

Both are DOM and small SVG in the existing no-library discipline;
neither needs layout algorithms. The general DAG stays deferred with
its vendoring decision, as Direction 7 already records.

## Required Fix

The two views, in the UX-196 pattern (published JSON only, no viewer
arithmetic, geometry asserted from data attributes); the critical
path linked from the overview's execution segment (UX-202), the
blast tree from each blast answer and Shared Sources row.

## Out of Scope

- Any general graph rendering, any layout library (the deferral
  stands until a concrete question defeats these two).
- Cross-run diff graphs.

## Acceptance Test

The critical-path view on the 1,202-element synthetic renders the
folded chain with widths proportional to published durations
(asserted from data attributes; mutation: uniform widths reddens)
and expands the fold in place; the blast tree on the monorepo
fixture nests closure depths correctly against the JSON (depth
asserted) and renders kind badges from the declared item shape. No
new files beyond the views module growing; the page-size guard
(`< 80,000 B`) still holds.

## Outcome

Both drawings, both under the no-arithmetic rule — and the second one
required refuting the filing's premise first.

**The critical path, drawn.** A flex strip: each box's `flex-grow` is
`share_of_path * 1000`, and `share_of_path` is a *published field*, so
no width here is derived from a duration. That is what makes the
geometry assertable — the harness reads each box's `data-share` and its
`style` back against the payload, on the real `examples/06` capture.
`UX-187`'s fold at 6 head + 3 tail, and it opens **in place**: the
middle boxes are rendered hidden between the two ends and unhidden on
click, rather than sending the reader somewhere else. Measured at 1,202
elements: 1,193 folded, 1,202 boxes after the click. Each box links to
`#signals`, `UX-199`'s anchor for the section that explains it.

**The blast tree — and the premise that was wrong.** The filing called
it "a `<details>` tree over data `blast/v1` already carries". It does
not carry it: the payload had `direct_elements` and `blast_elements`,
two flat lists, and **no per-element depth, kind or cost at all**. A
viewer could only have got the shape by walking the dependency graph in
JavaScript, which is precisely the second analysis Direction 7's rule
exists to prevent. So `blast_tree` entered `blast/v1` additively
(`UX-190`: an addition does not bump the version), each row carrying
`{element_uid, depth, element_kind, measured_seconds}`, and the viewer
reads it. The indentation is the published depth; the kind badge is the
published kind.

**A bug caught in the first attempt at that depth.**
`compute_reachability` returns the *transitive* closure, so a
breadth-first walk over it put every reachable element at depth 1 and
the "tree" was flat — measured, all eleven elements of `examples/06` at
one level. It walks the immediate successors from `build_element_graph`
now: `all.bst`, which consumes `app.bst`, is two hops from
`toolchain.bst` and says so. Breadth-first, so an element reachable by
two paths is listed at the shorter one — the depth at which rebuilding
it actually becomes unavoidable.

**The restraint, asserted rather than promised.** A guard checks that no
`bga/viewer/graph.js` exists, that `views.js` reaches for nothing at
runtime, and that none of `d3`, `cytoscape`, `dagre`, `elk` or
`vis-network` appears in it. The general DAG stays deferred with its
vendoring decision, as Direction 7 records.

**A harness limit found and removed on the way.** Inlining a
1,202-element payload into `node -e` is `OSError: [Errno 7] Argument
list too long` — a fact about the harness, not the renderer, and one
that would have quietly capped every scale test written after it at
whatever fits in a command line. The payload goes through a file now.

Tests: 14 new. Six mutations, each red, including the acceptance's named
one (uniform widths) and the transitive-closure bug that was really
there.

**Deviation from the Required Fix:** none, but note that item 2's
premise was false and the fix therefore includes a payload change the
filing did not ask for. Recorded here rather than folded in silently.
