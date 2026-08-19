# UX-114: the baseline set's edges — three small holes round 12 walked into

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-96, UX-108 (both done — this is their edges)

## Motivation

Round 12 exercised the new baseline/trend machinery against the live
refs and hit three edges, each verified by running it:

1. **The homogeneity check skips absent fields — and that skip just
   failed in practice.** `trace_spine` is in `HOMOGENEOUS_FIELDS`, but
   captures that predate the field are ignored by the check
   (`if m['context'].get(field)`), so the one spine capture — 127,632
   processes, measurably different instrumentation — **joined a
   five-run hook-only band with no warning at all**. The skip
   semantics were written for `target` back-compat; for `trace_spine`
   (and `trace_opens`), absent has a known meaning ("off"), and
   absent-vs-`true` must mismatch. Fields whose absence is genuinely
   ambiguous should *warn* ("2 of 5 captures do not record X"), not
   pass silently.
2. **`captures/fdsdk-latest` now points at that spine capture**, moved
   by a dispatch from a working branch running non-main tooling
   (bga_ref `7bdb7e6f`). Cold got its own pointer precisely so modes
   never mix through a shared ref; differently-instrumented captures
   need the same treatment (an instrumentation-qualified pointer, or
   `-latest` reserved for the scheduled default configuration).
3. **A cross-mode candidate exits 2, not 6.** Feeding a cold candidate
   to an incremental band via `bga baseline --candidate` surfaces
   compare's UX-55 refusal as a generic error (exit 2) instead of the
   documented "not comparable" (exit 6) that mixed *sets* correctly
   produce. A CI job keying 6 = plumbing, 1/4/5 = verdicts misreads
   this case. (Nothing passes wrongly — both are non-zero — but the
   exit-code contract is the product here.)

Also observed, recorded for the ledger rather than filed: a manual
dispatch burned ~58 runner-minutes to a same-group cancellation
(32157665627) — the UX-90 concurrency group still cancels racing
dispatches mid-capture.

## Required Fix

1. Per-field absence semantics in the homogeneity check: fields with a
   defined default (`trace_spine`, `trace_opens`) treat absent as that
   default and mismatch accordingly; fields without one (`target`)
   warn on partial coverage instead of skipping. A drift warning names
   the runs, as the bga-revision one already does.
2. The publish step moves `fdsdk-latest` only for captures taken with
   the scheduled default instrumentation (hook-only, opens on);
   non-default instrumentation publishes its per-run ref and, if
   wanted, an explicitly-named pointer.
3. `bga baseline --candidate` maps compare's not-comparable refusal to
   exit 6, matching the mixed-set path and `docs/guides/cli.md`'s
   exit-code table.

## Out of Scope

- The trend gate (UX-92 stage 3's deferral stands).
- Cold baseline accumulation (monthly cron, time-bound).

## Acceptance Test

1. A synthetic context pair {absent} vs {`trace_spine: true`} fails
   homogeneity naming the field; {absent} vs {`false`} passes; a
   `target`-absent member yields a warning naming the runs. Re-running
   round 12's live five-ref command warns about the spine capture.
2. A workflow dispatch with `trace_spine=true` does not move
   `fdsdk-latest` (assert in the workflow's own publish-step logic or
   its log).
3. Cold candidate vs incremental band via the helper: exit 6, message
   naming the run-mode check.
