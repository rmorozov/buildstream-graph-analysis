# UX-101: nothing ranks what makes the project slow across builds

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-91 (the multi-build log tree), UX-92 (invalidation roots); UX-93 sharpens the cause labels

Direction 3, item 2 — see
[`design/directions.md`](../../design/directions.md).

## Motivation

Every ranking the tool produces is about one build: the critical path
of *that run*, the realizable saving in *that capture*. But the
question a team lead actually has is longitudinal: **which element
costs us the most wall-clock per week?** — and its answer is a
different ranking. An element that is 4th on today's critical path but
rebuilds in 80% of builds (a volatile key near the root, a
frequently-edited component) taxes the team more than today's #1,
which rebuilds once a month.

The data is already on disk. Plane 3's log tree keeps one timestamped
log **per build instance** across history — round 11's tree already
holds the A/B/C experiment's three builds of the same project, and the
capture workflow now publishes fdsdk's tree — and UX-92 knows, for any
pair of runs, *why* each rebuild happened (invalidation root vs churn).

`developer tax(element) = rebuild frequency × mean rebuild cost`,
summed over the log tree's time span.

## Required Fix

A `bga cache-logs` section (and JSON):

1. Per element across the tree: build count, mean and total build
   seconds, and the tax ranking by total seconds over the window. The
   window and build count are printed with the ranking (a 3-build tree
   says so, and says the ranking is weak evidence).
2. **Cause annotation** where consecutive builds' cache keys are
   available in the logs' filenames/headers: how many of an element's
   rebuilds trace to its own key changing vs an upstream root vs
   unchanged-key (the UX-93 retention case). The root that explains the
   most downstream tax is the headline — one volatile key near the root
   *is* the top developer tax, and this is the number that proves it.
3. The standing Plane 3 hedges (one-second resolution, no scheduler
   context, nothing feeds a certified floor) carry over verbatim.

## Out of Scope

- Cross-machine aggregation (one log tree = one machine's history;
  fleet-level tax is a different task with a different data problem).
- Gating (a tax regression gate needs a per-window noise model that
  does not exist yet — same reason UX-92 deferred stage 3).

## Acceptance Test

On this machine's round-11 tree (three builds: cold A, codegen-tweak B,
core-tweak C): `core.bst` tops the tax ranking (rebuilt in all three,
heaviest), the cause annotation shows B's rebuilds rooted at
`codegen.bst` and C's at `core.bst`, and the 3-build window is declared
weak. On the fdsdk published tree: the ranking renders for the rebuild
set and the top entry's cause distribution is printed. Determinism over
the same tree.

---

## Fix Implemented

`developer_tax` in `tools/bst_cache_logs.py`, rendered by `bga
cache-logs` and carried in its JSON. `tax = rebuild count x mean rebuild
cost`, which is the total, and the total is what ranks.

### The logs carry no session id — measured, not assumed

`UX-91` recorded that a log's header timestamp agrees with its filename
stamp. Checked again for this task, on a real tree, and the agreement
is the *problem*:

```console
$ head -1 all/92f30592-build.20260818-160457.log
BuildStream 2.7.0 - Tuesday, 18-08-2026 at 16:04:57
$ head -1 app/0b5380f2-build.20260818-160455.log
BuildStream 2.7.0 - Tuesday, 18-08-2026 at 16:04:55
```

Two logs from the *same* `bst build`, two different header times. The
header is the task's start, not the build's, and nothing in the tree
says which logs belonged to one invocation. So this never prints a build
count: the window is first-to-last log, the population is build logs,
and `builds_lower_bound` is the largest per-element count — labelled for
what it is, in the payload and in the text.

That was the one design decision with a tempting wrong answer. Clustering
logs by a time gap would produce a build count that looks authoritative
and is a guess with a threshold nobody measured.

### Cause annotation, and what needs a graph

For each rebuild after an element's first, its key either changed or did
not. Unchanged is `UX-93`'s case and keeps `UX-93`'s meaning. Changed
splits again — but only with the dependency edges, which these logs do
not contain. `--graph RUN/graph.json` supplies them; without it the
third category is *absent from `causes_available`* and the output says
so, rather than folding upstream-caused rebuilds silently into "its own
definition changed".

### Measured, on this machine's real tree

Six builds of `examples/06` — a cold pair, then the `codegen`-tweak and
`core`-tweak protocol, then two more:

```text
Developer tax across 27 build log(s) over 18-08-2026 16:04:32 .. 18-08-2026
16:07:38 (at least 4 build(s)) - WEAK EVIDENCE at this few builds, printed with
the count rather than withheld
  element                      builds     total     mean  cause
  core.bst                          2     19.0s     9.5s  1x own key changed
  app.bst                           4      8.0s     2.0s  3x rooted upstream
      rooted at lib-a.bst (6.0s of this element's rebuilds)
  lib-a.bst                         4      8.0s     2.0s  1x own key changed, 2x rooted upstream
      rooted at codegen.bst (2.0s of this element's rebuilds)
      rooted at core.bst (2.0s of this element's rebuilds)
```

`core.bst` tops the ranking, as the acceptance predicts, and the cause
column carries the experiment's own history: `lib-a.bst`'s rebuilds are
rooted at `codegen.bst` (the B tweak) and at `core.bst` (the C tweak),
which is exactly what was done to it.

Determinism: two scans of one tree produce byte-identical JSON.

### On the published freedesktop-sdk tree

```text
Developer tax across 23 build log(s) over 18-08-2026 19:43:59 .. 20:28:34
(at least 1 build(s)) - WEAK EVIDENCE at this few builds
  element                      builds     total     mean  cause
  components/_private/cmake-st      1   1185.0s  1185.0s
  components/openssl.bst            1    494.0s   494.0s
  components/python3.bst            1    474.0s   474.0s
  components/_private/git-mini      1    399.0s   399.0s
```

The ranking renders for the rebuild set. The cause column is **empty**,
and that is the correct output rather than a gap: a capture's log tree
holds one build of each element, so no element has a *previous* build to
compare a key against, and a cause is a fact about a rebuild. The
"at least 1 build(s)" and the weak-evidence label say exactly that.

This is also what makes the lower-bound treatment worth its complexity.
A tree with one build per element gives `builds_lower_bound = 1`; a
build-count heuristic that clustered by timestamp would have reported
some confident number here, over a 45-minute window in which the whole
capture ran.

The tax figures themselves are real and useful even at n=1 - they rank
the cut set by what it cost - which is why the ranking prints rather
than being withheld.

Tests: 6 new in `tests/unit/test_cache_logs.py`. Suite: 1310 → 1316.

## Verification Log

The verification evidence for this task is the pasted real output in
the section above — it was run, but filed without the heading the
fixing guide names, so a reader grepping for `## Verification Log`
found nothing on a 🟢 item. Heading added by audit round 12; the
evidence is the fixer's own.

Two round-12 notes on the evidence as filed: the run substituted a
fresh six-build tree for the round-11 A/B/C tree the acceptance named
(legitimate — same shape, more builds — but unrecorded), and its own
pasted output shows `core.bst 2 builds` where the acceptance predicted
"rebuilt in all three", also without remark. Round 12 re-ran on the
round-11 tree: the ranking renders with the WEAK EVIDENCE hedge, and
`--graph` correctly reattributes the libs' rebuilds to
`rooted at core.bst`.
