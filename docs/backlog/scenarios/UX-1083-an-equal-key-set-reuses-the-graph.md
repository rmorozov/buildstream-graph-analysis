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
to the cold one's (every key and value), but that is one pair, not a
general equivalence. `graph.json` also carries fields the key set does
not decide: `requested_target` follows the invocation's targets
(building B, which depends on A, and building A and B name the same
keys), `extract_run` adds the project's `bga-foundation` tier
(`UX-683`), and `max_jobs`/`notparallel` are resolved from the build's
options and configuration, which BuildStream keeps out of cache keys.
This is still the incremental and no-op review build, the most
frequent snapshot a team takes.

## Decomposition

Input classes: key set equal to the baseline's, different, unread
(`UX-1082`); baseline without `graph.json`; different global options
with equal keys. Journey: `bga snapshot`'s tail.

## Required Fix

In `tools/bst_extract_run.py`: the baseline's `graph.json` is reused
only when the whole graph fingerprint matches: the key set, the
requested targets, the `bst` global options, the resolved max-jobs
configuration, and the `bga-foundation` tier. `requested_target`,
`foundation` and the resolved widths (`UX-894`) are then re-applied
from this build rather than copied. Any difference or unread term runs
`bst show` as today. The snapshot records which happened and why.

## Out of Scope

Reusing the analysis itself (`UX-1073`).

## Acceptance Test

`tests/unit/test_an_equal_key_set_reuses_the_graph.py`: two snapshots
with the same fingerprint issue one `bst show --deps all` between them
(fake `bst` recording argv), and the second `graph.json` equals the
one a fresh `bst show` would write. Each of these issues the call or
re-derives the field, and matches a fresh extraction: a changed key;
the same keys under different targets (build B vs build A and B, where
B depends on A, so `requested_target` differs); a changed
`bga-foundation`; a changed `--max-jobs`. Mutation: drop any one
fingerprint term, and its case reds.
