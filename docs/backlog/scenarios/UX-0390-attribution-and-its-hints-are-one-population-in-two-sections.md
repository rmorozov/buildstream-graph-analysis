# UX-390: attribution and its hints are one population in two sections

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-288 (a population is published once), UX-351 (the label prints the unit the value carries), UX-286 (the report has chapters) | **Serves:** anyone reading where a build's time went | **Topic:** viewer

## Motivation

The user asked whether `attribution` and `attribution_hints` could be
one section. Measured on the round 63 capture, they are one
population already — the key sets are identical:

```text
attribution        execution_on_chain_us dependency_wait_us resource_wait_us
                   scheduler_wait_us idle_us retry_wait_us
                   untracked_head_us untracked_tail_us
attribution_hints  (the same eight)
SAME KEY SET       True
```

Eight buckets, two `<h2>` sections, each carrying a different sentence
about the same field. The reader meets a number in one chapter and its
explanation in another, and nothing in either says they are the same
eight things — which is `UX-288`'s one-population rule at section
level rather than at payload level.

The hints half also renders its keys raw, unit suffix and all:

```text
Execution on chain us
Dependency wait us
Untracked head us
```

`UX-351` established that a label does not print the unit the value
already carries, and `UX-374` that the page does not show the reader a
key it invented. The hints section predates both and was never swept.

## Required Fix

One section. The bucket is the row; its measured value and its
sentence are two columns of that row, not two chapters.

- **Merge into a single attribution section**, keyed by bucket, so the
  number and the sentence that explains it arrive together.
- **The hint is a property of the bucket**, published once —
  whichever payload key survives, the other is not a second population
  of the same eight names.
- **Labels go through the page's own label rule**, so
  `execution_on_chain_us` reads "Execution on chain" with the unit on
  the value, not "Execution on chain us".

## Falsification

A guard that asserts no two rendered sections draw the same key set
from the payload, and that no rendered label ends in a unit suffix the
value already carries (`_us`, `_bytes`, `_s`). Today the first fails
on this pair and the second fails on eight labels.

The other direction: merging must not lose a sentence. Every hint
present before the merge is reachable after it — the count of
explained buckets does not drop, which is the property that would make
"merge" mean "delete the hints".

## Out of Scope

- The wording of the eight sentences. `UX-220` set the rule that a
  number needing a sentence has one; this item moves them, it does not
  rewrite them.
- Whether the eight buckets are the right decomposition. That is an
  analysis question and untouched here.
