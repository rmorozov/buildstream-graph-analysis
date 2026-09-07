# UX-760: six more files build against the broken reserve

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-755 (the mechanism and the fix's shape) | **Serves:** the session that runs `make test` on a container with a large disk and little free space | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`UX-755` established the mechanism — BuildStream sizes its 5% cache
reserve against `disk_usage().total`, never `.free`, so on a 270 GB
filesystem with 13-17 GB free the reserve straddles what is left and
`bst build` refuses with `Cache too full` — and fixed one file with a
repo-owned `$XDG_CONFIG_HOME` carrying absolute values.

Its Required Fix named one file. The Motivation did not: the same
run that proved the mechanism reddened seven files at once, on a
branch touching nothing in the capture path.

```text
test_a_generated_project_builds.py       2 failures
test_blast_ranking_discriminates.py      1
test_bst_checkout_cost.py                1
test_bst_extract_run.py                  3
test_bst_extract_run_strict.py           2
test_build_root_override_join.py         2
test_shared_source_blast.py              1
                                        12 failed, 7606 passed in 593.08s
```

All twelve pass alone. `UX-755`'s verifier confirmed each of the six
remaining files invokes real `bst` and none sets the reserve, so the
gate is one-eighth repaired: a session running `make test` on this
container still gets failures it cannot act on, which is the defect
`UX-755` was filed on.

One of them is worth naming. `test_a_generated_project_builds.py`'s
`_isolated()` sets `XDG_CONFIG_HOME` to `home / "config"` and never
creates that directory, so BuildStream finds no file and falls back
to the 5% default — an isolation mechanism that looks like protection
and gives none.

## Required Fix

Reach the six with the same override `UX-755` proved, without copying
its two config files six more times — one fixture the real-`bst`
tests share, named once. `_isolated()`'s empty directory becomes that
fixture rather than a hole.

## Out of Scope

- The upstream arithmetic. `disk_usage().total` for a percentage
  reserve is BuildStream's, in `/usr/local/lib/python3.11/dist-packages`,
  and not ours to patch.
- `test_the_journey_has_an_answer_key.py`, already fixed by `UX-755`.
- A skip. `UX-755` established the fix works; skipping six files would
  hollow out the whole real-`bst` lane on any host of this shape.

## Acceptance Test

With the margin driven negative, all seven files pass where six
currently fail. Mutation: point the shared fixture at a config
carrying `reserved-disk-space: 5%` and they redden again — the
control `UX-755`'s verifier ran, applied to the six.

## Outcome

_Not started._
