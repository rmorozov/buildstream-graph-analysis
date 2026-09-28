# UX-1083: a build whose key set equals the baseline's reads its graph again

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-1082 | **Found by:** the snapshot and view performance audit on `39d89d4` (2026-09-28) | **Serves:** R5, R8 | **Topic:** capture | **Area:** tools | **Shape:** mechanical

## Motivation

After every build `extract_run` runs `bst show --deps all` for
`graph.json` (`tools/bst_show_to_graph.py:241-281`), even when nothing
the graph is made of changed. Cache keys cover each element's config,
variables, sources and dependencies, so an equal key set means an
equal graph. Measured with BuildStream 2.8.1:

```text
examples/06 warm (build 1.07s)   bst show --deps all 1.27s
1,201 elements                    11.21s
5,001 elements                    42.28s
```

The warm `examples/06` snapshot's `graph.json` is structurally identical
to the cold one's (every key and value). This is the incremental and
no-op review build, the most frequent snapshot a team takes.

## Decomposition

Input classes: key set equal to the baseline's, different, unread
(`UX-1082`); baseline without `graph.json`; different global options
with equal keys. Journey: `bga snapshot`'s tail.

## Required Fix

In `tools/bst_extract_run.py`: when the snapshot's key set is read and
equals the baseline snapshot's, `graph.json` is taken from the
baseline, and the resolved widths (`UX-894`) are re-applied from this
build; otherwise `bst show` runs as today. The snapshot records which
happened.

## Out of Scope

Reusing the analysis itself (`UX-1073`).

## Acceptance Test

`tests/unit/test_an_equal_key_set_reuses_the_graph.py`: two snapshots
with equal key sets issue one `bst show --deps all` between them (fake
`bst` recording argv), and the second `graph.json` equals the first; a
changed key issues the call. Mutation: skip the key-set comparison,
and the changed-key case reds.
