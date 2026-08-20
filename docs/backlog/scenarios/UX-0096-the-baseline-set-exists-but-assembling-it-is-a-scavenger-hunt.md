# UX-96: the baseline set exists, but assembling it is a scavenger hunt

**Priority:** Medium | **Status:** 🟡 In Progress — the helper ships and is verified against the real refs; the second acceptance clause is a schedule that has not fired yet | **Depends on:** UX-81 (done)

## Motivation

UX-81 delivered exactly what it promised: per-run refs, three
same-config incremental fdsdk captures, and a live band-mode compare
that verifiably replaced the fixed 1% rule with a measured MAD band
(−0.8% correctly absorbed as noise). Doing that in round 11 took: one
`git ls-remote` to discover the refs, three `git archive` extractions,
two manual untars (the two older refs predate the uncompressed `run/`),
and a five-path `bga compare` invocation assembled by hand. That is a
scavenger hunt, and it is the workflow every CI owner is now expected
to run on every candidate build.

Two adjacent gaps surfaced by the same exercise:

- **Nothing checks the baseline set's own homogeneity.** The three
  captures were produced by three different `bga` revisions
  (recorded in each `capture-context.txt`, consulted by nothing).
  Capture-tooling drift inside a baseline set silently widens or biases
  the band — the exact class of unlike-things comparison `bga` refuses
  everywhere else.
- **Cold captures accumulate only by hand.** The weekly schedule
  dispatches the default (incremental) mode; cold history is n=1, so a
  cold baseline set — needed before any cold-vs-cold gate — has no
  automatic path to existence.

## Required Fix

1. A `bga baseline` helper (or `bga compare --baseline-refs <glob>`)
   that, given a repo remote and a ref glob
   (`captures/fdsdk/953683fb-incremental-b4j4-*`), fetches the newest N
   run directories (untarring where a ref predates the uncompressed
   `run/`), verifies they are same-config and same-mode, warns on
   `bga`-revision drift across the set, and runs the band compare
   against the named candidate — one command, suitable for a CI step.
2. Schedule the cold mode too, at a lower cadence (e.g. monthly, or
   alternating weeks), so a cold baseline set exists by accumulation
   rather than by someone remembering.

## Out of Scope

- Any change to the band arithmetic (verified working).
- Cross-forge portability (GitHub refs are the one publication channel
  today).

## Acceptance Test

From a bare clone with the refs present: one documented command
produces the band verdict for a candidate against the newest 3
incremental captures, including the two tarball-only older refs, and
prints a drift warning naming the differing `bga` revisions. After two
scheduled cycles, at least one cold capture exists that no human
dispatched (verify from the Actions ledger).

---

## Fix Implemented

`bga baseline` (`tools/bst_baseline_set.py`). One command, from a plain
checkout with a remote:

```console
$ bga baseline --glob 'captures/fdsdk/953683fb-incremental-b4j4-*' -n 3 \
      --candidate /path/to/candidate/run
============================================================
Baseline Set
============================================================
3 capture(s), newest first:
  captures/fdsdk/953683fb-incremental-b4j4-32122941503
      953683fb incremental builders=4 max_jobs=4  bga=1c268de9
  captures/fdsdk/953683fb-incremental-b4j4-32113933158
      953683fb incremental builders=4 max_jobs=4  bga=108be7b3
  captures/fdsdk/953683fb-incremental-b4j4-32064333551
      953683fb incremental builders=4 max_jobs=4  bga=1143f2b2
  DRIFT: 3 different bga_ref values across this baseline set - the captures were
  produced by different revisions of the capture tooling, which can widen or
  bias the band. Reported, not refused
============================================================
```

and then, from the same invocation:

```text
Judged against a noise band from 3 baseline run(s): 3307.03s .. 3561.82s -
median 3434.43s +/- 3x42.47s (scaled MAD)
```

That is the round-11 scavenger hunt — one `ls-remote`, three `git
archive` extractions, two manual untars, a five-path `bga compare`
assembled by hand — as one command, run here against the three real
published refs, two of which carry only `capture.tar.gz`.

### The bug in the obvious implementation, found by running it

The first version did what reads correctly: newest member as the
positional baseline, **the rest** as `--baseline-run`. Against the three
real refs it produced:

```text
No noise band: 1 baseline run(s) supplied, 3 required
```

`compute_band` reads only the `--baseline-run` population, so "the rest"
leaves a three-capture set one short and silently falls back to the
fixed 1% rule the band exists to replace — a helper for band-comparing
that quietly disables the band. Every member now supplies the band,
including the one that is also the positional baseline: that run is what
the candidate is compared *against*, and the band is the noise model of
the population it came from, so it belongs in its own population.

Recorded because this is exactly the failure this repository keeps
finding in its own gates (`UX-84`, `UX-87`, `UX-97`): a check that runs,
reports success, and checks nothing.

### Homogeneity, split by what it means

- **Refuses** (exit 6, the same code `bga compare` uses for "not
  comparable") when `fdsdk_ref`, `capture_mode`, `builders`, `max_jobs`
  or `target` differ across the set.
- **Reports** when `bga_ref` differs. Capture-tooling drift is a real
  risk to a band *and* completely normal in a repository under
  development; refusing would disable the helper exactly when it is most
  needed.
- **Ignores** a field absent from a capture's context, so refs published
  before a field existed stay usable — which is `target`'s situation
  today, on every ref already published.

`target` is new to `capture-context.txt` in this task, and it closes a
hole in this task's own subject: the ref name carries commit, mode,
builders and max_jobs, so before this, two captures of *different
targets* would have landed in one baseline set with nothing to notice.

A moving pointer ref (`captures/fdsdk-latest`) is skipped rather than
resolved — a baseline set containing one would change under whoever was
reading it.

### The cold schedule

The capture workflow gains a second cron, monthly, which selects the
cold mode from `github.event.schedule` (a `schedule:` trigger cannot
supply workflow inputs). Monthly rather than weekly because a cold
capture builds a whole closure from source, and the question it answers
— the project's real critical path — changes on the scale of months.

The concern `UX-86` recorded, that the default target's closure might
not fit a cold job's budget, is settled by measurement rather than by
assumption: the cold capture published at
`captures/fdsdk/953683fb-cold-b4j4-32133112003` ran the defaults to
`traced_build_exit=0`.

### Not yet discharged

The acceptance's second clause — *"after two scheduled cycles, at least
one cold capture exists that no human dispatched (verify from the
Actions ledger)"* — is a claim about the future that only time can
settle. The schedule is in place; the first monthly firing is what
closes it. Stated rather than declared done.

Tests: 9 new in `tests/unit/test_baseline_set.py`. Suite: 1274 → 1283.

## Verification Log

The verification evidence for this task is the pasted real output in
the section above — it was run, but filed without the heading the
fixing guide names, so a reader grepping for `## Verification Log`
found nothing on a 🟢 item. Heading added by audit round 12; the
evidence is the fixer's own.

## Re-checked 2026-08-20 (round-17 follow-through): checked, not yet dischargeable

The clause is *"after two scheduled cycles, at least one cold capture
exists that no human dispatched (verify from the Actions ledger)"*. The
ledger was read rather than waited on:

- `real-project-capture.yml` has **31 runs, none of them `schedule`** —
  every one is `workflow_dispatch` or the long-removed `push` trigger.
- The weekly incremental cron (`0 3 * * 0`) landed 2026-08-18 with
  `UX-81`; the monthly cold cron (`0 4 1 * *`) landed 2026-08-19 with
  this item. Both are younger than their own period.
- First weekly firing: **Sunday 2026-08-23**. First monthly firing:
  **Tuesday 2026-09-01**. Two *cold* cycles — what the clause asks for
  — therefore cannot be complete before 2026-10-01.

So the clause is not merely undischarged, it is not yet dischargeable,
and the date it becomes checkable is now written down instead of left
as "only time can settle".

Two mechanics worth naming while this waits, because either would make
the schedule silently not fire and the clause would look like a
tooling failure:

- GitHub runs `schedule:` **only on the default branch's copy of the
  workflow**. A cron that exists only on a feature branch never fires.
- GitHub **disables scheduled workflows after 60 days without repository
  activity**, and does not warn in the run list. This repository is far
  from idle today; the risk is real for a quiet month later.

Nothing to change in the workflow. Re-check after 2026-09-01 by
filtering the ledger on `event: schedule`; the item closes when a
`*-cold-*` capture ref exists whose run id belongs to a scheduled run.
