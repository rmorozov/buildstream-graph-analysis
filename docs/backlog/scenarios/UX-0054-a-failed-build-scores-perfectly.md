# UX-54: a build in which every attempted element **failed** is scored 1.00, and nothing in the report says the build failed at all

**Priority:** High | **Status:** 🟢 Done | **Depends on:** — (pre-existing; `UX-39`/`UX-03` made it consequential by putting a gate on top of the score) | **Topic:** analysis

## Motivation

Found in round 6, on a real `freedesktop-sdk` capture taken on a
GitHub-hosted runner whose sandbox could not start. Four elements were
attempted. **All four failed.** `bga analyze` on the resulting run
directory opens:

```text
Total Duration: 5.3s

Key Findings:
  Confidence: 0.14 (low) - see 1 violation(s) below
  Biggest Opportunity: 65.2% of wall-clock time is UNTRACKED HEAD (3.46s)
  ...
  Efficiency Score: 1.00 (scheduling is near the certified floor for this graph
    - further gains need the graph or the work itself to change, not the
      scheduler)
```

The word "failed" appears nowhere. The four spans in `trace.json` —
`components/openssl.bst`, `components/which.bst`, `components/ninja.bst`,
`components/_private/python3-flit-core.bst` — are the four failed builds,
recorded as ordinary BUILD work with real durations.

And the score is not merely uninformative, it is *maximal*: a build that
does almost nothing before dying looks, to a scheduling model, exactly
like a build with nothing left to optimize.

## Why this matters more than a cosmetic omission

`UX-03` and `UX-39` built a CI gate on top of these numbers, for the
scenario this project exists to serve: *"it is ok to make the build
slower, but a big regression must be spotted and stopped."*

Trace the failed run through that gate:

1. `efficiency_score` = 1.00 — the best value it can take.
2. `confidence` = 0.14, so `low_confidence` is true.
3. `_compare_exit_code` **fails open** on low confidence (`UX-40`'s
   deliberate rule: never block a pipeline on a signal you do not trust)
   and returns 0.

A broken build passes the gate, quietly, on scheduling grounds. The
fail-open rule is right for a *noisy* signal — but a build that did not
complete is not a noisy signal, it is a definite fact, and the two need
opposite treatment.

## The information was never missing

BuildStream states each task's terminal status in its own log, and
`tools/bst_log_to_chrome_trace.py` already carries it through — every End
event in the chrome trace of this capture has `args.Status`:

```text
components/openssl.bst [...]  FAILURE
components/which.bst [...]    FAILURE
components/ninja.bst [...]    FAILURE
components/_private/python3-flit-core.bst [...] FAILURE
```

`chrome_events_to_bga_spans` reads `args.action` and `args.element` from
the Begin event and never looks at the End event's `Status`. The fact was
carried three-quarters of the way and dropped at the last hop.

**No fixture in this repository contains a failed task**, which is why
nothing could notice. Every example project in `examples/` is written to
build cleanly; the synthetic generators emit successes by construction.
It took a real project on a machine where the sandbox did not work.

## Required Fix

1. **Record the outcome.** `failed_elements(events)` in
   `tools/chrome_trace_to_bga_trace.py`, written into run-context.json
   as `build_outcome: {failed_elements, failed_count}` by
   `tools/bst_extract_run.py` — always, including when nothing failed,
   so that an **absent** field keeps meaning "this producer did not
   record it" and captures taken before the field existed are never
   mistaken for known-good runs.
2. **Say it first.** A `build_failed` violation, and a line at the very
   top of Key Findings — above the confidence headline and every
   efficiency number, because all of them describe a build that did not
   complete.
3. **Fail the gate closed.** `_compare_exit_code` checks for a failed run
   *before* the low-confidence fail-open, and returns the regression exit
   code. Not gated behind a new flag: there is no reading under which a
   pipeline asked to gate on efficiency wants a failed build waved
   through.

## Out of Scope

- **Per-span status in trace/v9.** Recording each task's terminal status
  on the span itself is the more complete model, and would let
  attribution treat a failed task's time differently from useful work.
  It is a schema change to trace/v9 touching every fixture, and the
  run-level fact is what closes the hazard, so it is deliberately not
  attempted here.
- **Whether a failed task's duration should count as `EXECUTION_ON_CHAIN`
  at all.** It currently does. Arguably it is closer to waste than to
  work, but changing it moves I4's attribution identity, and the honest
  first step is to make the failure visible rather than to silently
  re-bucket time.
- `--retry-failed` semantics and re-run detection, which
  `bga/utilisation/detection.py` already models separately.

## Acceptance Test

1. On the real failed capture, `bga analyze` leads with `THIS BUILD
   FAILED: 4 element(s) ended in FAILURE (...)`.
2. `bga compare --fail-on-regression` returns the regression exit code
   when either run failed, **including** when confidence is low — the
   ordering is the point.
3. A run with `build_outcome` absent is distinguishable from one recorded
   as clean; neither reports failures.
4. Every existing fixture's output is unchanged (none contains a failed
   task). Full suite green.

## Fix Implemented

`failed_elements` reads the status the log already stated;
`bst_extract_run` writes `build_outcome` unconditionally and emits an
extraction warning naming the failed elements; `RunContext.build_outcome`
plus a `failed_elements` accessor keep "unknown" and "clean" distinct;
`BuildEfficiencyAnalyzer` raises a `build_failed` violation; the text
report leads with it; `_compare_exit_code` fails closed on it before the
low-confidence fail-open.

Verified on the real capture:

```text
Key Findings:
  THIS BUILD FAILED: 4 element(s) ended in FAILURE (components/_private/
  python3-flit-core.bst, components/ninja.bst, components/openssl.bst, ...)
  - every figure below describes a build that did not complete ...
  Confidence: 0.14 (low) - see 2 violation(s) below
```

Tests: 13 new (`tests/unit/test_build_failure_visibility.py`), covering
the producer (including that BuildStream's own `bst-invocation` bracket
is not mistaken for an element, and that one element failing twice is
named once), the "absent is not clean" distinction, and the gate ordering
— specifically that a failed run fails closed *at low confidence*, which
is the exact combination the real capture produced and the one the old
order got wrong.

Suite: 925 → 938.

## Verification Log

Filed 2026-08-17 (round 6). The report text quoted above is the real
`analyze.txt` from GitHub Actions run `32026123204`, published to the
`captures/fdsdk-latest` branch by
`.github/workflows/real-project-capture.yml` and fetched back; the four
element names are from that run's own `trace.json` and `chrome_trace.json`.

The failure that produced this capture was itself diagnosed rather than
assumed: `bwrap: loopback: Failed RTM_NEWADDR: Operation not permitted`
appeared on all four elements, and the workflow was changed to retry the
same build **without** the Plane 2 tracer, which failed identically (exit
255 both ways). For contrast the same dual-plane capture, with
`--trace-opens`, runs to exit 0 against `examples/06` in the development
container on bubblewrap 0.9.0 — so the tooling was exonerated and the
cause is Ubuntu 24.04's
`kernel.apparmor_restrict_unprivileged_userns=1`, which leaves bwrap
without `CAP_NET_ADMIN` in the network namespace it just created.

A capture nobody wanted turned out to be the only one that could show
this: the round set out to measure a real timeline and instead found
that `bga` cannot tell a build that failed from one that succeeded.
