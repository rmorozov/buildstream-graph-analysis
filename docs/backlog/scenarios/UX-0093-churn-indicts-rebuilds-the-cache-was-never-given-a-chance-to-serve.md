# UX-93: churn indicts rebuilds the cache was never given a chance to serve

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-92 (done), UX-55 (done)

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
