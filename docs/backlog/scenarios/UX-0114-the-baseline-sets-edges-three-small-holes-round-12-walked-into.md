# UX-114: the baseline set's edges — three small holes round 12 walked into

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-96, UX-108 (both done — this is their edges)

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

## Resolution

### 1. Absence is read per field, and is never silent

`HOMOGENEOUS_FIELDS` is now a mapping of field to **what an absent value
means**, not a tuple of names:

- a string — the capture workflow's own default, which a ref published
  before the field existed was necessarily taken under. The default
  participates in the comparison, so absent-vs-`true` is a mismatch.
  `trace_spine` (`false`) and `trace_opens` (`true`), the latter added
  here because it was never checked at all.
- `None` — absence has no defined meaning. The field is compared across
  the captures that record it and partial coverage is reported as
  `UNVERIFIED`, so "checked and equal" and "checked on three of five"
  stop printing identically. `fdsdk_ref`, `capture_mode`, `builders`,
  `max_jobs`, `target`.

**Before**, on the five live incremental refs — one of which
(`32223468993`, `bga_ref=7bdb7e6f`) records `trace_spine=true`:

```text
$ bga baseline --glob 'captures/fdsdk/953683fb-incremental-b4j4-*' -n 5
  DRIFT: 5 different bga_ref values across this baseline set - ...
EXIT=0
```

The spine capture — a different instrument reading the same build —
joined a four-run hook-only band with nothing said. **After**, same
command, same refs:

```text
  NOT COMPARABLE: trace_spine differs across the set (false, true); 4 recorded
      nothing and were taken as false
      32064333551, 32113933158, 32122941503, +1 more
  UNVERIFIED: 2 of 5 capture(s) do not record capture_mode, so the set was
      checked on 3 of them. Absence has no defined meaning for this field -
      it is unverified, not verified-equal
      32064333551, 32113933158
  UNVERIFIED: 4 of 5 capture(s) do not record target, so the set was checked
      on 1 of them. ...
      32064333551, 32113933158, 32122941503, +1 more
EXIT=6
```

**Beyond the Required Fix, deliberately.** Two things the task did not
ask for, both because the live data made them impossible to leave:

- The task named `target` as the ambiguous-absence case. `capture_mode`
  turned out to be one too — only 3 of the 5 refs record it — so the
  mode check, the one `bga compare` refuses hardest on, was itself
  running on a subset and reporting nothing about the rest.
- An assumed default is stated (`ASSUMED: N of M capture(s) do not
  record trace_spine; taken as trace_spine=false …`) even when it
  changes no verdict. Absent-means-default is the right rule going
  forward, but on today's corpus it is an assumption applied to four
  captures out of five, and "we defaulted it" must not read as "it
  recorded off". Suppressed where the field already mismatches, since
  the mismatch line carries the same sentence.

### 2. `-latest` moves only for the scheduled default instrumentation

The publish step's decision is now a `publish_decision` shell function
with three outcomes — `move-latest`, `non-default-instrumentation`,
`failed-build` — and the `git push --force` to the pointer lives in the
first branch only. A spine or opens-off capture still publishes its
per-run ref, because it is data; it does not become the project's
current state.

Kept as a function so it could be *run* rather than described:
`tests/unit/test_latest_ref_publish.py` extracts the definition from the
YAML and executes it under bash across the instrumentation combinations.
Verified by falsification — replacing the guard's condition with `false`
turns 6 of its 10 tests red.

### 3. The band's refusal carries exit 6, not exit 2

Fixed in `bga compare` rather than in the helper, so every
`--baseline-run` caller gets it and not only `bga baseline`:
`RunsNotComparableError(ValueError)` is raised by the band's run-mode
check and handled in `_execute_compare_and_write` ahead of the generic
`ValueError` arm. A `ValueError` subclass, so any caller already
catching the base class is unaffected.

Measured on the real refs — the cold fdsdk capture against the
incremental band, via the helper:

```text
$ bga baseline --glob 'captures/fdsdk/953683fb-incremental-b4j4-321*' -n 3 \
      --candidate <cold run>
Error: baseline run .../00-32177690506/run is a incremental run but the
candidate is full - a noise band may only be built from runs of the same
kind (UX-55)
EXIT=6      # was 2
```

Tests: 7 added in `tests/unit/test_baseline_set.py` (10 → 17), 10 new in
`tests/unit/test_latest_ref_publish.py`, 3 added in
`tests/unit/test_compare_mismatch_refusal.py` (9 → 12).

## Verification Log

Done 2026-08-19. All three clauses run against the live capture refs
rather than fixtures: the five-ref band before and after, the cold
candidate against the incremental band, and the publish guard executed
under bash. Clause 2's acceptance says "assert in the workflow's own
publish-step logic or its log" — the assertion is on the logic, executed,
because no dispatch was run.
