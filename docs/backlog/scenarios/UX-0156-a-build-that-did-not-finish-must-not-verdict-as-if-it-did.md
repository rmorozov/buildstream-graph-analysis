# UX-156: a build that did not finish must not verdict as if it did

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-126 (snapshot's auto-compare), UX-78 (the refusal grammar this extends) | **Topic:** analysis

## Motivation

Round 16 reproduced the exact session the user is about to have — a
long build on a big project, snapshotted — with one element failing to
compile. What the terminal ends with, live output pasted:

```text
Verdict: IMPROVED  (total duration -26.35s, -65.6%, 40.15s -> 13.80s)
```

The build **failed**. lib-d did not compile; four elements never ran;
of course it was "faster". The extraction *knows* — `run-context.json`
records `build_outcome: {failed_elements: ['lib-d.bst'],
failed_count: 1}` — and nothing consults it: not the analysis banner,
not the comparison, not the verdict line. The only hints are a
confidence caveat ("below the 'high' band — treat with caution") and a
`WARNING ... critical_path_coverage_full` log line, neither of which
says the one true sentence: *this build did not finish*.

The exit code is honest (the build's own, per UX-126) — but the user
returning to a scrolled terminal after three hours reads the verdict,
not `$?`.

It compounds: the failed run then **silently becomes `@prev`**. Round
16's next healthy snapshot compared against the failed one — baseline
confidence 0.57, no mention that the baseline is a build that died —
so the "IMPROVED" that should have appeared against the last *healthy*
run was measured against wreckage instead. In CI the same silence
inverts the gates: a `--fail-on-*` compare where either run carries
failed elements is comparing measurements that are not there.

## Required Fix

1. **The verdict names the incompleteness first.** When the candidate
   (or baseline) run's `build_outcome` has failed elements, the
   comparison's first line is not IMPROVED/REGRESSED but
   `NOT COMPARABLE: the candidate build failed (lib-d.bst; 3 of 7
   scheduled elements built) - duration deltas of an unfinished build
   are not a measurement`, with the UX-78 refusal exit code (6) when
   gates are requested. The full report can still follow for a reader
   who wants the partial numbers — the *verdict* is what must refuse.
2. **The analysis banner says it too**: `analyze` on a run with failed
   elements opens with the failure count and names, before any
   efficiency number.
3. **Auto-compare picks the last healthy baseline**: `@prev` keeps its
   meaning (previous snapshot, as filed in UX-126), but snapshot's
   automatic comparison skips runs with failed elements when choosing
   its baseline and says which snapshot it used and why — one line.

## Out of Scope

- The interrupted (Ctrl-C) capture — UX-157; this item is about builds
  that ran to a failing end and were then presented as measurements.
- BuildStream's own failure reporting (already verbose and correct).

## Acceptance Test

Round 16's reproduction, re-run: sabotage one element of
`examples/06`, snapshot twice (healthy, then failing). The failing
snapshot's output leads with NOT COMPARABLE naming lib-d and the
element count, exit unchanged (the build's own); `bga compare` of the
two run dirs with any `--fail-on-*` flag exits 6, not 0/4/5. A third,
healthy snapshot auto-compares against the *first* snapshot, names the
skip, and verdicts normally. The docs-commands test covers the new
wording's home in `real-project.md` (one sentence: a failed build's
snapshot refuses its verdict).

---

## What was built

Reproduced first, on a sabotaged `examples/06` where lib-d fails to
compile and 0 of 7 elements build:

```text
Verdict: IMPROVED  (total duration -53.25s, -93.0%, 57.23s -> 3.98s)
rc=0
```

Now:

```text
Verdict: NOT COMPARABLE
  the candidate build failed (lib-d.bst; 0 of 7 scheduled elements built) -
  duration deltas of an unfinished build are not a measurement
  Not a verdict, for reference only: total duration -53.25s, -93.0%, ...
```

The partial numbers stay for a reader who wants them; the *verdict*
refuses. `analyze` opens with `THIS BUILD DID NOT FINISH` before any
efficiency figure, and snapshot's automatic comparison walks back to the
last healthy run and says which it used.

The gate's exit code moved from 4 to 6, deliberately: `UX-54` made it
fail closed, which stands, but it borrowed "your build got slower" to
say "your build did not finish". Both `UX-54` tests that pinned 4 are
updated with the reason.

Element counts are recorded on the `build_failed` violation by the
analyzer rather than read downstream, because `AnalysisResult` exposes no
`run_context` - the first attempt's `getattr` would have returned `None`
on every real run and silently dropped the clause. A test pins that
absence.

### Falsified

Four mutations, each red. The first attempt at the verdict falsification
reddened **nothing**: every test built the comparison by hand with a
ready-made verdict string, so none exercised the decision. Four tests now
drive the real `compare_runs` over run directories.
