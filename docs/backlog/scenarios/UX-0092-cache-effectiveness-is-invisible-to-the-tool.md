# UX-92: cache effectiveness — hits, misses, churn, trends — is invisible to the tool

**Priority:** Medium | **Status:** 🟡 In Progress — stages 1 and 2 done; stage 3's trend shipped as `UX-103`, its gate is deferred on evidence | **Depends on:** UX-55 (done), UX-81 (history to trend over)

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

---

## Fix Implemented — stages 1 and 2

**Status:** 🟡 In Progress — stages 1 and 2 done, stage 3 (trend + gate) not started

### Stage 1: per-run cache accounting

`bga/cache_effectiveness.py`. Nothing is modelled: BuildStream's own
closing Pipeline Summary says how many elements it built and how many it
skipped, and the run's own spans say where transfer time went. On the
published fdsdk capture, exactly the acceptance test's numbers:

```text
Cache hit ratio: 72% (65 cached, 25 rebuilt) - the cache did most of the work
  -> for components/libxml2.bst's own closure it is 80% (101 of 126 elements cached)
```

Published as `signals.cache` and as a `cache-hit-ratio` finding with a
stable id, so both report formats render from one computation
(`UX-75`'s rule). The target's own closure is accounted separately
because a project-wide 72% says little when the thing being shipped
rebuilt entirely; that walk includes `runtime` edges, unlike the
critical-path walk that correctly excludes them, because shipping a
target requires them.

**The finding is not gated on the ratio being bad.** Every other signal
in the report describes the work the build did; on an incremental build
the cache decides how much work that was, so it is context for reading
the rest. What a good ratio changes is the sentence and the severity,
not whether the line appears.

Absent rather than zero-filled when a capture has no Pipeline Summary,
and `None` rather than `1.0` for an empty queue: a queue that processed
nothing did not achieve a perfect hit ratio.

### Stage 2: churn and invalidation roots

A cache key is a hash over an element's own definition **and** its
dependencies' keys, so comparing two runs' keys answers "did anything
that affects this element change" exactly — no source-ref diff needed,
and `graph.json` already carries the keys.

Two facts fall out:

- **Churn** — an element the candidate rebuilt whose key is *identical*
  to the baseline's. Waste by definition rather than by judgement.
- **Invalidation roots** — among elements whose key *did* change, those
  all of whose dependencies' keys are unchanged. The change started
  there. This is the failure mode the task was filed for, and naming the
  root is the whole value: the list of elements it invalidated is a
  symptom.

Measured on real `examples/06` builds with bst 2.7.0. Built twice with
caches on, nothing touched:

```text
comparable_elements = 11   changed_keys = 0   churned_count = 0   invalidation_roots = []
```

Then **one comment added to one source file** (`files/src/core/unit_0.cpp`):

```text
Build Queue: processed 9, skipped 2
```

Nine of eleven elements rebuilt — and the report says why in one line:

```text
Invalidated at core.bst: its cache key changed (b7c2e411 -> 84331b67) and
invalidated 8 element(s) below it, 34.2s of rebuilding in total. Nothing it
depends on changed, so the change starts here
```

### Two corrections to this task's own text

**The acceptance test's suggested probe does not work.** It says "force
a key change (e.g. a comment in `core.bst`)". A YAML comment does not
change a BuildStream cache key — the key is computed over the *parsed*
element configuration, not the file bytes. Verified: appending a comment
to `core.bst` rebuilt nothing (`processed 0, skipped 2`). Adding an
unused `variables:` entry did not either. Only a change to a real input
— a source file — moved the key. That is BuildStream behaving correctly,
and the probe in the acceptance test was wrong.

**A first implementation produced a false positive**, caught before it
shipped. Churn was derived from `compare.py`'s `_element_durations`,
whose pre-`UX-79` fallback degrades to the *critical path* — and path
membership is not a built list. On a run that built nothing it reported
`toolchain.bst` as churn with a wasted time of 0. It now reads
`signals.element_durations` directly and produces **no churn block at
all** when that signal is absent: "not measured" and "nothing rebuilt"
are different facts and only one of them is an all-clear.

### Stage 3, split by what it was waiting for

Stage 3 was one line — "the trend projection and
`--fail-on-cache-regression` gate" — and the two halves turned out to be
blocked on different things.

**The trend shipped, as `UX-103`.** `bga cache-trend` reads a series of
run directories, reports each one's hit ratio, transfer seconds, seconds
per artifact and churn against its predecessor, and fires a finding when
the newest reading leaves the band its trailing window describes. It
reuses `bga compare`'s band rather than inventing a second noise model,
including the widening rule that keeps a near-zero MAD from making every
delta significant. See that task for the measurements.

**The gate is still deferred, and now for a sharper reason.** Building
the trend produced the evidence stage 3 was waiting on, and it argues
against the gate rather than for it:

- The three preserved fdsdk captures sit at hit ratio **72%, three times
  over**, with zero churn — because they are the same commit, built the
  same way, with the cut set deleted identically each time. That is
  noise measured at a single point of a one-dimensional space.
- The one quantity that *did* vary across those runs, total duration,
  spans 3405.78s .. 3614.22s — a 6.1% spread on runs that differ in
  nothing. A gate keyed on a cache ratio would inherit that variance
  without inheriting an explanation for it.
- Every published capture ignores remotes by design, so **transfer time
  is not merely stable across the history, it is absent**. The metric
  most worth gating (a remote that slowed down) has n=0, not n=3.

What would close it is history across *different* commits, where the
hit ratio has room to move for a reason a gate should catch. `UX-96`'s
monthly cold schedule and the weekly incremental one accumulate that
without a human; the gate is a decision to take when the spread it must
clear has been measured, not before. `UX-39` set that discipline and it
holds here.

Recorded rather than left implicit: shipping
`--fail-on-cache-regression` today would mean picking a threshold from
nothing, in a tool whose central claim is that it does not do that.

### Verification

Suite 1215 (+14). `make lint`, `make check-clean` green. The end-to-end
numbers above are real builds, not fixtures; the fdsdk figures are the
published capture's own.
