# UX-1311: a junctioned element's jobserver annotation never reaches the shim

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — | **Found by:** debugging the owner's junctioned element (2026-10-03) | **Serves:** R1, R2 | **Topic:** capture | **Area:** tools | **Shape:** bounded | **Reading:** container

**Guard:** `tests/unit/test_a_junctioned_elements_annotation_reaches_the_shim.py`

## Motivation

The tracer keys the `public: bga: jobserver-auth:` map by `bst show`'s
`%{name}`, junction-qualified (`toolchain.bst:my_recipe.bst`);
`_annotation_style` looks up `element_from_build_root` of bwrap's
`--dir`, which never carries the junction. The lookup misses, silently.
`_parse_element_kinds` solved the same for kinds (`UX-871`).

```text
$ python3 -c "from tools.bst_native_build_tracer import _parse_jobserver_show_records as p, FIELD_SEP as F, RECORD_SEP as R; print(p(F.join(['toolchain.bst:my_recipe.bst','make','{}','bga:\n  jobserver-auth: off\n','[]','[]'])+R)[2])"   # 5faa7c3e
{'toolchain.bst:my_recipe.bst': 'off'}
```

## Decomposition

Input classes: top-level annotated element; junctioned annotated; two junctions sharing a short name (annotated first, unannotated first); a top-level element and a junctioned one sharing a short name (either order, either annotated). Journey: `bst show` records -> auth map file -> `_annotation_style(element_from_build_root(...))`.

## Required Fix

The auth map also carries each junctioned element's short name, ownership
derived over all names in the show output.

**Decision:** one helper, `_claim_short_names`, shared with
`_parse_element_kinds`. A top-level element owns its own name whether or
not it is annotated, so an unannotated top-level element is never given a
junction's annotation, and an annotated one beats it. Among junctions the
first claimant wins; a later one is a collision, not stored. Ownership
counts unannotated elements, so a later junction's annotation does not
leak onto an earlier junction's unannotated same-named element.
`element_notparallel`/`element_deps` are keyed by full name and read
only against full names inside the tracer (`structural_ranking`): no
mismatch, nothing changed.

## Out of Scope

Two junctions' same-named elements still cannot be told apart by the
shim, which sees only the short name (`UX-871`'s collision).

## Acceptance Test

The guard feeds `_parse_jobserver_show_records` a record set, writes the
map to a temp file, sets `BST_TRACE_ELEMENT_AUTH_MAP` and resolves via
`_annotation_style`; it reddens under each mutation below.

## Outcome

## Outcome (round 168, 2026-10-03) — 🟢 Done

**Premise:** held — the auth map named only the junction-qualified spelling.

### The gap, measured

```text
$ python3 -c "...p(F.join(['toolchain.bst:my_recipe.bst','make','{}','bga:\n  jobserver-auth: off\n','[]','[]'])+R)[2]"   # 5faa7c3e
{'toolchain.bst:my_recipe.bst': 'off'}
```

### After

```text
$ (same command)
{'toolchain.bst:my_recipe.bst': 'off', 'my_recipe.bst': 'off'}
$ python -m pytest -q -p no:randomly tests/unit/test_a_junctioned_elements_annotation_reaches_the_shim.py
6 passed
```

`_claim_short_names` is shared with `_parse_element_kinds`;
`jobserver.md` gains two sentences in "One element, not the whole build".
`element_notparallel`/`element_deps` stay full-name keyed end to end
(`structural_ranking`): no mismatch there.

### Mutations verified red and reverted (4)

| # | mutation | reddened |
|---|---|---|
| M1 | auth map never gets short names | 2 of 6 |
| M2 | last junction wins a short name | 4 of 6 |
| M3 | top-level element does not own its name | 2 of 6 |
| M4 | ownership over annotated names only | 3 of 6 |
| M5 | a top-level clash counted as a collision (`":" in owner` dropped; the verifier's unguarded clause, guarded after) | 2 of 9 |
