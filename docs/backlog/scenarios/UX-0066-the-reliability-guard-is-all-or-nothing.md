# UX-66: the attribution guard demands 100% or nothing, so an 86.1%-correct join is refused — and a cancelled capture can overwrite a good one

**Priority:** High | **Status:** 🟢 Done | **Depends on:** `UX-64` (done — which raised real attribution to 86.1% and made this the blocker)

## Motivation

Round 8 took Plane 2's element attribution on a real `freedesktop-sdk`
build from **14.9% to 86.1%** of processes, with all eight resolved names
valid against the declared graph and zero unmatched sandboxes.

`bga correlate` still refuses the join, and its message now contradicts
itself:

```text
NO USABLE JOIN: Plane 2's element attribution is unreliable.
  only 109873 of 127629 traced processes (86.1%) carry a name that looks
  like a BuildStream element; the largest bucket is
  'components/bison.bst' with 42804 processes.
```

`components/bison.bst` **is** an element. The guard is citing a correctly
attributed bucket as evidence that attribution failed.

The rule is literal:

```python
reliable = bool(by_element) and recognized_processes == total
```

That was right when the measured answer was 0.6% and every per-element
figure was fiction — refusing everything was the only honest response.
It is wrong now, and it is the single thing standing between this project
and a working macro→micro loop on a real build.

## What the guard conflates

Two different situations currently produce the same verdict:

1. **A name that is not an element.** `buildstream-build`, `flit_core`,
   `expat` — round 7 measured all three coming out of bwrap's `--dir`,
   and `flit_core` matches no declared element at all. A per-element
   figure keyed on these is *fiction*, and refusing is correct.
2. **A process known to be unresolved.** After `UX-64`, the residue is
   not mislabelled — it sits in an explicitly unresolved bucket because
   its sandbox was reported `ambiguous`. Excluding it and joining the
   rest loses coverage, not correctness.

The second is the ordinary shape of a partial measurement, and this
codebase already knows how to report that: `UX-45` publishes CPU time as
"measured over N of M processes", `UX-63` does the same for peak memory,
`UX-57` reports dropped paths. None of them refuse to answer because
coverage is below 100%.

## Required Fix

1. **Judge validity, not completeness.** A join is usable when the names
   present are real element uids — checked against the declared graph,
   not against a `.bst` suffix, since round 7 found `flit_core` and
   `expat` passing a suffix test while being no such element.
2. **Exclude the unresolved, and say how much.** Report the join over the
   86.1% and state plainly what share was left out and why, the way every
   other partial measurement here does.
3. **Keep refusing the dangerous case.** If the largest bucket is not an
   element — the round 6/7 situation — the current refusal stays exactly
   as it is. This must not become "always join".
4. **Fix the message.** It currently names a valid element as evidence of
   failure, which would send a reader looking for a bug that is not there.

## The second defect: a cancelled run can publish over a good capture

Round 8 surfaced this independently. Run `32053016303` was cancelled
mid-capture when a newer dispatch superseded it (`cancel-in-progress` on
the ref). Its publish step runs `if: always()`, so it published anyway —
a 36 KB tarball with a **0-byte `native-trace.log`** and no
`native-report.json` — **overwriting round 7's good capture** at the tip
of `captures/fdsdk-latest`.

Nothing was permanently lost (round 7 survives at `df20544`), but for
~64 minutes the published "latest capture" was a broken partial with
nothing marking it as such, and this round's own audit nearly analysed it
by mistake.

`if: always()` is right for the *other* steps — a build that failed
part-way still yields a usable Plane 1 log, which is why it is there. It
is wrong for the publish, which is what everything downstream reads.

**Fix:** publish only when the capture actually produced
`native-report.json`, or gate the publish on the capture step's outcome.
A cancelled or empty capture should leave the previous one in place.

## A third defect: the plain-build fallback now crosses two builds

Raised by the user asking why the capture step appears to build twice.
It does not — the second build is conditional on the traced one failing
(`traced_build_exit=0` in both rounds 7 and 8, with no `plain_build_exit`
line, so neither ran it), and even when it fires it resumes rather than
restarts, because successful elements stay cached and `--retry-failed`
only redoes the failed ones. The fallback exists so that a build broken
*by tracing* still yields a Plane 1 capture, which is what saved round 6.

But it has acquired a hazard since it was written. When it fires:

```bash
mv capture/build.log capture/build-traced.log   # traced build's log
bst build --retry-failed ...                    # writes a NEW capture/build.log
```

`run/` is then extracted from the **plain** build's log, while
`native-report.json` came from the **traced** build. Before `UX-56` that
was untidy. Now `bga correlate` joins Plane 2 sandboxes against Plane 1
BUILD spans, so it would silently correlate one build's sandboxes against
a different build's timeline — and the sandbox ids would not even be
wrong in a detectable way, they would simply match the wrong spans.

It has not bitten, because the fallback has not fired since `UX-56`
landed. It would, silently, on the next traced failure.

**Fix:** when the fallback runs, the capture is a Plane 1 capture only.
Drop or clearly mark `native-report.json` so nothing downstream joins
across the two, and record in `capture-outcome.txt` that the two planes
describe different builds.

## Out of Scope

- The correlation itself (`UX-64`), which is working. The 16 ambiguous
  sandboxes are genuinely ambiguous — short elements whose spans open
  together — and reducing them further is a separate question.
- Lowering the reliability bar by a tuned percentage. The point is that
  *validity* and *coverage* are different properties, not that 86% is
  close enough to 100%.

## Acceptance Test

1. On round 8's capture, `bga correlate` produces a real join over the
   resolved elements and states the excluded share explicitly.
2. On round 6's or round 7's capture — where the largest bucket is not an
   element — it still refuses, with the current message.
3. A bucket name that is not a declared element uid never enters a join,
   even if it ends in `.bst`.
4. A cancelled capture run does not overwrite the previously published
   capture, and a published capture always contains `native-report.json`.

## Fix Implemented — and one acceptance test that was never met

The guard and both workflow defects were fixed in `b1c379d` / `4a35674`
and verified on round 9's capture. Re-checking the acceptance tests one
by one found the third had been missed:

1. ✅ The join renders over the resolved 86.1% and states the excluded
   share (`PARTIAL ATTRIBUTION - the rows below are correct for the
   elements they name, and say nothing about the rest`).
2. ✅ The refusal is kept for the round 6/7 shape, where the largest
   bucket is not an element.
3. ❌ **"A bucket name that is not a declared element uid never enters a
   join, even if it ends in `.bst`."** Not implemented, and demonstrably
   reachable: a Plane 2 bucket called `flit_core.bst` produced a "what to
   do next" row while the build's only real element was relegated to
   "not traced". Fixed now.
4. ✅ The publish is gated on `!cancelled()` and on `native-report.json`
   existing, and the plain-build fallback renames its report to
   `native-report-traced-only.json` so nothing joins across two builds.

### The fix for (3)

Plane 2's own test is syntactic — `assess_element_attribution` asks
whether a name ends in `.bst`, which is all Plane 2 can do alone. The
*declared graph* is a Plane 1 fact, so the join is the only place the
stronger check exists, and `_declared_elements` now makes it there.

Built from the per-element signals (`slack`, `downstream_count`,
`blast_radius`, `criticality_probability`, the critical path) rather than
from the critical path alone, because a real element that is off the path
and has no blast radius still belongs to the graph — over-refusing it
would be a worse error than the one being fixed. Tested both ways, plus
the degradation case: an analysis carrying none of those signals yields
an empty set and the check is skipped rather than rejecting every row.

On round 9's real capture it names exactly the three fictions and keeps
all eight real rows:

```text
  3 Plane 2 name(s) are not declared elements and are excluded from the rows
  below: buildstream-build, flit_core, unknown
```

`flit_core` is the same `--dir` segment round 7 measured and this task
cited — now caught by the tool rather than by hand.

## Verification Log

Filed 2026-08-17 (round 8). The 86.1% figure, the eight validated names
and the self-contradicting message are from the capture published to
`captures/fdsdk-latest` as `66a97e1` (run `32055047259`, `bga_ref`
`835e3d9`); the `reliable = recognized_processes == total` rule was read
from `tools/bst_native_build_tracer.py`. The clobbered capture is
`3bafee8` (run `32053016303`, cancelled), and round 7's surviving capture
is `df20544`.
