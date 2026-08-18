# UX-93: churn indicts rebuilds the cache was never given a chance to serve

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-92 (done), UX-55 (done)

## Motivation

UX-92's churn detector calls a rebuild-with-unchanged-key "waste by
definition rather than by judgement" (`bga/cache_effectiveness.py`,
`compute_cache_churn`'s own docstring). That definition holds only when
the artifact the key names was *available* — and nothing checks that it
was. Two real false accusations from round 11, both live:

- **A cold pair.** Comparing two deliberate full rebuilds of the same
  project (caches cleared between, the repo's own examples protocol):
  *"Cache churn: 10 element(s) rebuilt with an unchanged cache key,
  costing 36.5s … that time bought nothing."* It bought the entire
  build; the cache was empty because the operator emptied it.
- **The tool's own CI.** The fdsdk capture workflow warms the cache and
  then deliberately deletes the 25-element rebuild set — that is the
  capture's design. Every band-mode comparison of those captures now
  reports *"25 element(s) rebuilt with an unchanged cache key, costing
  4604.2s"*. Every future scheduled capture comparison will carry the
  same 4600-second accusation as permanent noise, about the mechanism
  that produces the data.

The exact same class of bug was already found and fixed once this
round, in `analyze`: the hit-ratio finding said "look for a volatile
cache key" about a cold build, and the fix conditioned it on `run_mode`
(UX-86's falsified finding). The churn path in `compare` did not get
the same treatment. Verified in the same session: on a *genuine*
incremental pair with continuous cache, the detector is exactly right —
zero false churn, and the invalidation root correctly named
(`Invalidated at core.bst … nothing it depends on changed, so the
change starts here`). The analysis is good; the applicability condition
is missing.

There is also a better answer than suppression for one sub-case: a
rebuild with an unchanged key on a *shared, supposedly-warm* cache is a
**cache retention/serving failure** (evicted artifact, remote that
stopped serving, never-pushed artifact) — a real CI health finding, but
about the cache infrastructure, not the project, and it must not say
"bought nothing".

## Required Fix

1. Condition churn on the candidate being an incremental run
   (`run_mode` is already computed and sits in the same result object —
   the same fix `analyze`'s hit-ratio finding received). On a `full`
   candidate: no churn block at all, same as the hit-ratio treatment.
2. On an incremental candidate, split the unchanged-key rebuilds into
   what the data can actually distinguish: if the *baseline run itself
   rebuilt the same element with the same key* (as in the warm/cut CI
   captures, where the cut is identical run to run), say so —
   "rebuilt in both runs with the same key: the artifact is being
   removed between runs (deliberate cut, eviction, or a remote that is
   not serving it) - a cache-retention question, not a project one" —
   instead of "bought nothing".
3. Keep the current wording only for the case it is true: an element
   the baseline had cached (skipped) and the candidate rebuilt with an
   unchanged key.

## Out of Scope

- Distinguishing eviction from never-pushed from remote-down (needs
  cache-server data the runs don't carry; the reframed wording covers
  all three honestly).
- The invalidation-root half of UX-92 (verified correct as shipped).

## Acceptance Test

1. Round-11 cold pair (`run-opt` vs `run-grow-good`, both full): no
   churn block.
2. Two fdsdk incremental captures from the per-run refs: the 25
   cut-set elements appear under the both-runs-rebuilt wording, with no
   "bought nothing" claim.
3. The round-11 true-positive protocol (cold A, tweak codegen → B,
   tweak core → C, compare B vs C): output unchanged — invalidation
   root named, zero churn.
4. A synthetic pair where the baseline skipped an element and the
   candidate rebuilt it with an unchanged key still gets today's full
   churn wording.

---

## Fix Implemented

`compute_cache_churn` now takes the baseline's built set and both runs'
`run_mode`, and refuses to judge before it has them. Three preconditions,
each with its own reason in the payload:

| precondition fails | `reason` | why the verdict cannot be made |
|---|---|---|
| candidate is a caches-off run | `candidate_run_is_full` | every element rebuilt by instruction |
| baseline is a caches-off run | `baseline_run_is_full` | it rebuilt everything, so it cannot say what a warm cache would have served |
| baseline publishes no per-element durations | `baseline_built_set_not_measured` | an element the baseline also rebuilt cannot be told from one it had cached |

Where they hold, an unchanged-key rebuild splits in two:

- **the baseline skipped it** → today's wording, unchanged. Waste.
- **both runs rebuilt it** → `rebuilt_in_both_elements`, and a different
  sentence: *"the artifact is not surviving between runs (deliberate cut,
  eviction, or a remote that is not serving it): a question about the
  cache, not about the project"*.

The two buckets stay separate all the way out to JSON, so a gate cannot
fail a build for its own CI's retention policy.

The round-11 defect was in the *wiring* — `compare` called the function
without the run modes that were sitting in the same two result objects.
No unit test of the accounting could have caught that, so the three new
`test_compare.py` tests go through `compare_runs`.

### The four acceptance cases, measured

**1. A cold pair.** `examples/06` built twice, cache directory deleted
between builds. Both runs: 11 processed, 0 skipped.

```text
Cache churn not assessed: the candidate is a caches-off run, so every element
rebuilt by instruction - an unchanged cache key there is the intended behaviour,
not waste
```

```json
{"comparable_elements": 11, "unchanged_keys": 11, "changed_keys": 0,
 "applicable": false, "reason": "candidate_run_is_full"}
```

Before: 11 elements accused of buying nothing with the whole build.

**2. Two real fdsdk incremental captures**, the ones the workflow
publishes, with the identical deliberate 25-element cut:

```text
Cache retention: 25 element(s) rebuilt in BOTH runs with the same cache key,
costing 4879.9s here - components/_private/buildsystem-cmake.bst, ... (+21 more).
The artifact is not surviving between runs (deliberate cut, eviction, or a
remote that is not serving it): a question about the cache, not about the
project
```

`churned_count: 0`, `wasted_rebuild_us: 0`. The 4600-second standing
accusation against the capture mechanism is gone, and the 25 rebuilds are
still reported — reframed, not suppressed.

**3. The true-positive protocol** (cold A, tweak `codegen` → B, tweak
`core` → C, compare B vs C), re-run from scratch. Output unchanged:

```text
Invalidated at core.bst: its cache key changed (b7c2e411 -> 3a634ee3) and
invalidated 8 element(s) below it, 25.7s of rebuilding in total. Nothing it
depends on changed, so the change starts here
```

`churned_count: 0`, one root, 9 changed keys of 11 comparable.

**4. Baseline cached, candidate rebuilt with an unchanged key.** From a
fully-cached baseline, `bst artifact delete app.bst` then rebuild:

```text
Cache churn: 2 element(s) rebuilt with an unchanged cache key, costing 3.3s -
app.bst, lib-a.bst. Nothing they depend on changed, so that time bought nothing
```

Worth stating plainly, because it bears on how much the split is worth:
this case *is* also a retention event — the artifact was deleted. What
separates it from case 2 is not ground truth but evidence: the baseline
skipped these elements, so the cache demonstrably could serve them and
demonstrably did not serve the candidate. Case 2 has no such
demonstration, and that is exactly why it must not borrow case 4's
wording.

(An earlier attempt at case 4 deleted `lib-a.bst` and produced *no*
rebuild at all — BuildStream builds only what an uncached target needs,
and `app.bst` was still cached, so nothing required `lib-a`. Recorded
because it is the sort of thing that reads as a broken test rather than
as BuildStream working correctly.)

Tests: 6 new in `test_cache_effectiveness.py`, 3 in `test_compare.py`.
Suite: 1246 → 1255.

## Verification Log

Fixed 2026-08-18. Every one of the four acceptance cases above was run
against real run directories — two of them (1, 3, 4) built for this fix
from `examples/06`, one (2) against the two real freedesktop-sdk captures
this repository has published. Quoted output is verbatim.
