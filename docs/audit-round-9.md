# Audit round 9: the MVP verdict

Run [`32064333551`](https://github.com/rmorozov/buildstream-graph-analysis/actions/runs/32064333551),
`bga_ref` `1143f2b` (`UX-65` + `UX-66` + `UX-67`), `freedesktop-sdk` at
`953683fb`, BuildStream 2.7.0, 4-core runner, `--builders 4 --max-jobs 4`.
Traced build exit 0. Published as `5eda28a`.

The question is not "did the numbers move". It is whether a real user
would find real low-hanging fruit — whether the tool is what it claims to
be.

## The loop is closed

**`bga analyze` names where the time is:**

```
Biggest Opportunity: this build is execution-bound - no wait category
  exceeds 1% of wall-clock time, so there is no scheduling gap to close
Where the time is: 4 element(s) are 94.0% of the 3610.5s critical path
  components/_private/cmake-stage1.bst  1569.8s (43.5% of path)
  components/openssl.bst                 672.1s (18.6% of path)
  components/python3.bst                 639.8s (17.7% of path)
  components/doxygen.bst                 513.5s (14.2% of path)
```

Round 8's report, on the same build, led with
`0.1% of wall-clock time is UNTRACKED HEAD (3.47s)`.

**`bga correlate` joins the planes and says what to do:**

```
PARTIAL ATTRIBUTION - the rows below are correct for the
elements they name, and say nothing about the rest:
  109873 of 127627 traced processes (86.1%) are attributed to a named
  element; the remaining 17754 are in the unresolved bucket
  'buildstream-build' ...

Joined 11 element(s) on element UID (126 in Plane 1, 11 traced in Plane 2)

What to do next (ranked by Plane 1 impact):
  components/_private/cmake-stage1.bst:
    - declares 1 build dependency it never read (public-stacks/runtime-minimal.bst)
    (84% of this element's processes were measured)
```

Round 8 refused this join outright.

So the macro→micro loop runs end to end on a real project: Plane 1 says
`cmake-stage1` is 43.5% of the build, Plane 2 says what happened inside
it, the join ranks findings by Plane 1 impact, and every figure carries
its own measurement coverage.

## Steady state

| | round 8 | round 9 |
|---|---|---|
| processes attributed | 109,873 / 127,629 (86.1%) | 109,873 / 127,627 (**86.1%**) |
| sandboxes certain / ambiguous / unmatched | 9 / 16 / 0 | **9 / 16 / 0** |
| paths recorded / dropped | 88,373 / **0** | 88,363 / **0** |
| `max_concurrency` | 60 | **60** |
| confidence / failed gates / violations | 0.9996 / none / 0 | **0.9996 / none / 0** |
| `declared_vs_used` | 10 unused, 14 used | **10 unused, 14 used** |

Reproducible across two independent captures of the same commit.

## MVP verdict, claim by claim

| claim | verdict on real data |
|---|---|
| Finds where a real build's time goes | **True.** 4 elements, 94.0% of the chain, named at the top of the report. |
| Certified floors that never overstate | **True.** `T∞ = LB = T_C = 3610.5s` against 3614.2s wall clock; `I3` implemented and green; 0 violations. |
| Distinguishes the two CI scenarios | **Partly.** `run_mode` is correct and the report scopes its claims — but **only the incremental scenario has ever been captured**. See below. |
| Per-element intra-sandbox measurement | **True, with stated coverage.** 86.1% of processes, per-element peak RSS (`cmake-stage1` 1902 MB), all resolved names valid against the declared graph. |
| Joins the two planes into next actions | **True.** 11 elements joined, ranked by Plane 1 impact, coverage stated per element. |
| Finds unused declared dependencies | **True as evidence, over-claimed as advice.** See `UX-68`. |
| Regression gate for CI | **False-positives on real data.** See below — this is the sharpest finding of the round. |

**Verdict: yes, with two named gaps.** A user pointed at this capture
would come away knowing which four elements to attack, that the scheduler
has nothing left to give, that `cmake-stage1` peaks at 1.9 GB (so four
concurrent builders is ~7.6 GB), and which dependency edges are
candidates for removal. That is a real day's work identified from one
report.

## What round 9 found wrong

**`UX-68` — the recommendation over-claims.** The producer is careful:

> A candidate is an element/dependency pair where none of the
> dependency's staged files were opened. **This is evidence, not a
> verdict:** runtime-only dependencies, cached configure probes, and
> dependencies needed only for a directory's existence all look the same
> from here.

The consumer drops that and says:

> declares 1 build dependency it never read (`public-stacks/runtime-minimal.bst`)
> — **removing the edge is free** and widens the graph

And the distribution makes it worse: `public-stacks/runtime-minimal.bst`
accounts for **8 of the 10** candidates. A stack element with `runtime`
in its name, declared by nearly every component, is exactly the
runtime-only case the producer's own note says is indistinguishable from
here. The tool's most-repeated recommendation is most likely a false
positive, presented as free.

## What is still missing, honestly

**The caches-off nightly has never been captured.** Every real capture —
rounds 6 through 9 — is incremental: 25 elements built, 65 skipped. That
is scenario 2 of the two this project set out to serve, and the one where
the tool claims to *shine* is scenario 1. The critical path measured here
is the chain through 25 rebuilt elements, not the project's real one.

**13.9% of processes remain unattributed** — the 16 short sandboxes whose
spans open together at the build's start. Honest, reported, and a real
ceiling on Plane 2's coverage.

**The regression gate false-positives on real data — measured.** Two real
captures of the same commit now exist, so the cheapest validation in the
backlog became free to run:

```
$ bga compare round8/run round9/run
Verdict: REGRESSED  (total duration +101.22s, +2.9%, 3513.01s -> 3614.22s)
```

**Same commit. Same `run_mode`. Nothing changed.** Both runs at
confidence ~1.00, so `UX-40`'s fail-open does not save it either.

Run-to-run noise on this real build is **2.9%**, against a fixed
significance rule of **1%**. The local `examples/06` measurement behind
`UX-59` found 1.8%; a bigger, longer build on shared CI runners is
noisier still, in the direction that makes the fixed rule worse.

`UX-59` built the fix — a median ± k·MAD band over a baseline *set* — and
it is not reached here, because `MIN_BASELINE_RUNS` is 3 and only two
real captures exist. That floor is correct (a "band" over two points
restates them), which means the gate's **default** path is the one that
is wrong on real data, and the default is what a first user gets.

This is the honest counterweight to the verdict above: the analysis and
the reporting are MVP-ready on this evidence; **the CI gate is not**.
