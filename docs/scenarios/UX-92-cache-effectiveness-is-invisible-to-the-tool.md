# UX-92: cache effectiveness — hits, misses, churn, trends — is invisible to the tool

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-55 (done), UX-81 (history to trend over)

## Motivation

For an incremental CI build — which round 6 established is *every* CI
build — the cache is the dominant efficiency mechanism, and `bga` treats
it as a footnote: UX-55 taught the report to stop miscounting cached
elements as coverage gaps, and that is the tool's entire cache story.
A build owner's actual cache questions are unanswered:

- **Hit ratio, per run and per subtree.** Plane 1 already knows which
  elements were skipped-cached vs built; it never aggregates, splits by
  subtree, or compares against the previous run.
- **Cache-key churn**: elements that rebuild *without a meaningful
  change* — the signature is a cache miss whose upstream closure
  contains no changed source ref. One volatile cache key near the root
  (a timestamp leaking into an artifact, an over-broad `project.conf`
  variable) silently converts every incremental build into a near-full
  one; today nothing would ever point at it. This is plausibly the
  single largest real-world BuildStream efficiency failure mode, and it
  is undetectable by everything the tool currently measures — a fast
  build with terrible cache behavior looks *efficient* per occupancy.
- **Pull/push economics**: time spent pulling artifacts vs rebuilding
  them (the DOWNLOAD/UPLOAD resources exist in the model; a "pulling
  this artifact repeatedly costs more than caching it locally" or
  "pushing X took Y% of the build" finding does not).
- **Trends**: hit ratio and churn over a run history (UX-81), so a
  regression in cache effectiveness — the invisible sibling of the
  duration regression — is visible and gateable.

## Required Fix

Staged:

1. **Per-run cache accounting** in `analyze`: elements cached / built /
   fetched, hit ratio overall and for the requested target's closure,
   pull/push time share from the existing task kinds. Published as
   findings with ids, like everything else.
2. **Churn detection** in `compare` (two runs of the same project):
   elements that were rebuilt in the candidate whose declared inputs'
   refs are unchanged from the baseline — named, counted, and summed as
   wasted rebuild time. (`graph.json` already carries cache keys and
   refs; the comparison is set arithmetic.)
3. **A trend projection** over ≥3 runs (consumes UX-81's history): hit
   ratio and churn per run, with a `--fail-on-cache-regression` gate
   once the noise band for these ratios is measured — same
   derive-the-threshold discipline as UX-39.

## Out of Scope

- casd/CAS-internal statistics (dedup rates, disk) — a fourth data
  source, worth a separate filing if (1)-(3) prove out.
- Fixing any churn found (the tool names the element; the fix is the
  project's).

## Acceptance Test

(1): on the fdsdk capture, analyze reports 65 cached / 25 built and the
pull-time share, as findings with stable ids. (2): touch nothing,
rebuild `examples/06` twice with caches on; churn is zero. Then force a
key change (e.g. a comment in `core.bst`) and the churn report names
`core.bst`'s closure and its rebuild cost. (3): over three preserved
fdsdk captures, the trend row renders with real numbers and the gate
fires only on a deliberate cache-disabled run.
