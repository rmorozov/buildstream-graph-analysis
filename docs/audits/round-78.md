# Round 78 — the three field reports, implemented

Input: `UX-518`, `UX-521`, `UX-519`, `UX-520` — round 77's filings, in
the order the requester chose. `UX-520`'s open question was decided by
them and not by this round: **everything ships by default**, and a
switch excludes the Plane 2 capture.

## Decomposition

Derived per the `decompose` skill.

| item | surfaces | guards (input classes) | track |
|---|---|---|---|
| `UX-518` | `tools/bst_native_build_tracer.py` (`read_artifact_contents`) | new file (0 elements · 1 · many · a group with one bad name · a whole-group failure) | first |
| `UX-521` | `bga/viewer/app.js` · `tools/bga_view.py` (a served fact) | `test_the_handoff_box_is_measured_served.py` (under threshold · over · over-and-unfetchable · fetched · not-yet-fetched) | **serial after nothing**, but its own file |
| `UX-519` | `tools/bst_native_build_tracer.py` (same function) | the `UX-518` file, extended (TTY · piped) | **serial after `UX-518`** — same function |
| `UX-520` | `tools/bga_snapshot.py` · `bga/run_store.py` | new file (every layout member · a missing conditional · `--without-plane2` · a stamp collision · an unreadable contract version) | last — it reads the layout the others do not touch |

**gap:** `read_artifact_contents` has no guard at all today —
`git grep -l read_artifact_contents tests/` is empty. `UX-518` writes
the first one, so its "unchanged result" clause is against a
freshly-captured baseline rather than an existing assertion.

**gate:** one PR, opened before the first commit (`UX-426`, `verify`
§7), one `make test` here.

## The batching contract, measured before it was relied on

`bst artifact list-contents` takes many elements, and the failure mode
is the part that decides the design. `bst` 2.7.0, `examples/06`:

```text
core.bst                            rc=0    stdout_lines=7   headings=['core.bst:']
all.bst                             rc=0    stdout_lines=3   headings=['all.bst:']
core.bst all.bst                    rc=0    stdout_lines=9   headings=['core.bst:', 'all.bst:']
core.bst nope-does-not-exist.bst    rc=255  stdout_lines=0   headings=[]
  stderr: Could not find element 'nope-does-not-exist.bst' in elements directory '...'
```

A group is all-or-nothing: **one unresolvable name loses every element
in it**, where the per-element loop lost only that one. Since the
docstring's contract is that an unreadable element maps to an empty set
the caller reads as *unknown*, a naive batch would be safe but lossy —
it would quietly downgrade `declared_vs_used` for every element that
shared a group with a bad name.

So batching is paired with a fallback: a group that fails is retried
element by element, which pays the old cost only when something is
actually wrong. That is the clause the mutation table has to redden.
