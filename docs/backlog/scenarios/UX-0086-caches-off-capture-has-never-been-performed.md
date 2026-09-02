# UX-86: the caches-off scenario has never been captured, so half the product is untested on real data

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-81 (done), UX-55 (done) | **Topic:** capture

## Motivation

Round 9's honest gap, still open and still admitted in three documents:
*every real capture so far is incremental*. The published fdsdk
critical path is the chain through the 25 rebuilt elements, not the
project's real one; coverage, floors, and both efficiency signals have
never been exercised against a full cold build of a real project. The
"caches-off nightly" is one of the two CI scenarios the tool's own
design doc argues it serves — and it is the one where the whole-graph
structural findings (blast radius, choke points, stack consolidation)
mean what they claim.

The workflow's warm-then-cut design exists because a full fdsdk cold
build cannot fit a runner. That constraint bounds the *target*, not the
scenario: a cold capture of a bounded subtree (the existing 25-element
cut built with an empty local cache and remotes ignored from the start,
rather than on top of a warmed base) — or a smaller real project built
cold end-to-end — both produce a genuine caches-off run.

## Required Fix

1. Add a `capture_mode: cold` input to
   `.github/workflows/real-project-capture.yml`: skip the warm phase,
   build the chosen target with empty caches and
   `--ignore-project-artifact-remotes`, publish with `run_mode`
   provenance alongside (not over) the incremental captures (UX-81's
   history makes this non-destructive).
2. Pick a target that fits the 250-minute budget by measurement (start
   from the existing cut set; shrink if needed).
3. Run `bga analyze` + `correlate` on the result in-job, as today, and
   record the first real cold-vs-incremental pair — which is also the
   first real input `bga compare`'s cache-scenario check (UX-78) has
   ever had.

## Out of Scope

- A full 1089-element fdsdk cold bootstrap (does not fit a runner; the
  scenario does not need it).
- Scheduling cadence (UX-81).

## Acceptance Test

One published cold capture whose `run-context` records the mode, with
zero cached elements in its closure, analyze confidence "high", and no
incremental-run caveat in the report. `docs/guides/real-project.md`'s
"the honest gap" paragraph updated to point at the capture instead of
apologizing for its absence.

## Fix Implemented (part 1 of 2: the mechanism)

`capture_mode: cold` exists and is dispatchable. In that mode the
workflow:

- **skips the warm and cut phases entirely** — "cold" means no cached
  base, so every step that reads `state-after-warm.txt` is conditioned
  rather than handed an empty file to draw conclusions from;
- **pre-fetches every source in the closure** (`source fetch --deps all`)
  for the same reason the incremental path pre-fetches the cut set: the
  timed build should be dominated by real build work, not by downloads;
- **fails fast if anything is cached at the start** — a cold capture with
  a warm cache is not a cold capture, and finding that out from the
  numbers afterwards is much worse than finding out in twenty seconds;
- **records `capture_mode` in `capture-context.txt`**, so what was *asked
  for* is visible beside the `run_mode` the run directory derives from
  BuildStream's own Pipeline Summary. A cold capture that silently found
  a warm cache then shows up as a disagreement rather than as a fact;
- **publishes to its own pointer** (`captures/fdsdk-cold-latest`) and
  carries the mode in its per-run ref name, so a cold and an incremental
  capture of the same commit — which measure different builds, and which
  `bga compare` refuses to compare (`UX-78`) — cannot land in one
  baseline set through a shared ref glob.

## What is not done, and why

**No cold capture has been taken.** That needs a GitHub runner and hours
of it, which this session does not have; the acceptance test's *"one
published cold capture"* is not met and this task stays open until it is.

The open question the first dispatch answers is Required Fix item 2:
**which target fits the budget.** The default (`components/libxml2.bst`)
certainly does not — freedesktop-sdk roots everything in a full compiler
bootstrap, which is the constraint that produced warm-then-cut in the
first place. The mechanism is deliberately target-agnostic so that
question can be answered by measurement rather than by argument: dispatch
with `capture_mode: cold` and a small target, read the wall clock,
adjust.

Nothing about the mechanism can be verified beyond YAML validity and a
read of the conditions until that dispatch happens, and this task should
be re-checked against a real cold capture rather than closed on the code.

## Verification Log

Mechanism added 2026-08-18; YAML validated, step conditions and the
publish path read directly. No cold capture has been produced, and the
"honest gap" paragraphs in `README.md`, `docs/guides/real-project.md` and
`docs/design/architecture.md` are deliberately **unchanged** — they will be
accurate until a cold capture exists, and editing them first would be
the exact kind of documentation-ahead-of-code this round's `UX-88` was
filed for.

---

## Part 2 of 2: Required Fix item 2, answered by measurement

The open question was *which target fits the budget*. Answered by
cloning `freedesktop-sdk` at the pinned ref and reading real closure
sizes with `bst show --deps all`, rather than by dispatching a guess and
watching a 250-minute job time out.

| target | closure |
|---|---|
| `components/libxml2.bst` (the workflow default) | **126** |
| `components/gperf.bst` | 110 |
| `components/zlib.bst` | 85 |
| `public-stacks/runtime-minimal.bst` | 84 |
| `bootstrap/build/gcc-stage1.bst` | **18** |
| `bootstrap/base-sdk/bison.bst` | 10 |
| `bootstrap/base-sdk/m4.bst` | 4 |
| `bootstrap/base-sdk/binary-seed.bst` | 2 |

**The task's premise is confirmed and sharper than it was stated.** Of
`runtime-minimal`'s 84 elements, **64 are `bootstrap/`** — every
`components/*` target roots in the full compiler bootstrap, which is
exactly why warm-then-cut exists. No `components/` target is a candidate
for a cold build inside a runner budget, and the default
(`components/libxml2.bst`, 126) is the worst of them.

**What the table also shows is a way through.** The bootstrap is not a
single indivisible block: `bootstrap/base-sdk/*` is rooted at
`binary-seed.bst`, a 2-element pair (`import` + `compose`) of
*pre-built binaries*. So a bounded subtree can be built genuinely from
nothing — which is precisely the "cold capture of a bounded subtree" the
Motivation allows.

### The chosen target: `bootstrap/build/gcc-stage1.bst`

18 elements, and real ones rather than a trivial tail:

```text
bootstrap/base-sdk/binary-seed-x86_64.bst (import)     bootstrap/base-sdk/gettext.bst   (autotools)
bootstrap/base-sdk/binary-seed.bst        (compose)    bootstrap/base-sdk/bison.bst     (autotools)
bootstrap/gnu-config.bst                  (manual)     bootstrap/base-sdk/pkg-config.bst(autotools)
bootstrap/base-sdk/m4.bst                 (autotools)  bootstrap/base-sdk/zstd.bst      (make)
bootstrap/base-sdk/perl.bst               (make)       bootstrap/build/binutils-stage1.bst (autotools)
bootstrap/base-sdk/autoconf2.69.bst       (autotools)  bootstrap/build/python3.bst      (autotools)
bootstrap/base-sdk/autoconf.bst           (autotools)  bootstrap/build/gcc-stage1.bst   (autotools)
bootstrap/base-sdk/automake.bst           (autotools)
bootstrap/base-sdk/libtool.bst            (autotools)
bootstrap/base-sdk/flex.bst               (autotools)
bootstrap/base-sdk/tar.bst                (autotools)
```

Chosen over the smaller candidates deliberately. `bison.bst` (10) or
`m4.bst` (4) would also be genuine cold captures and would certainly
fit, but a capture whose point is to exercise whole-graph structural
findings — blast radius, choke points, consolidation — needs a graph
with real shape and real compute in it. This one has a genuine
dependency chain (seed → m4 → autotools → flex/bison → binutils → gcc),
one clear heavy element, and a comparable element count to round 9's
25-element incremental cut, so the two are readable side by side.

### Dispatched

```text
workflow: real-project-capture.yml   ref: main
target: bootstrap/build/gcc-stage1.bst   capture_mode: cold
fdsdk_ref: 953683fb...   builders: 4   max_jobs: 4   trace_opens: true
```

Same `fdsdk_ref` as all three incremental captures, on purpose: the
cold-vs-incremental pair the Required Fix item 3 asks for is only
meaningful at one commit. Note that `bga compare` will (correctly)
**refuse** that pair under `UX-78`'s cache-scenario check — which is
itself the first real exercise that check has ever had, and the reason
item 3 names it.

The wall clock this produces is the number that decides whether a larger
cold target is reachable later. Until the run finishes, this task stays
🟡 — the acceptance test asks for a *published* capture, and a dispatch
is not one.

---

## The capture, taken

**Status:** 🟢 Done

Run `32133112003`. `capture_mode=cold`, `traced_build_exit=0`, published
to `captures/fdsdk/953683fb-cold-b4j4-32133112003` with
`captures/fdsdk-cold-latest` moved to it — and all three incremental
captures untouched, which is the separation `UX-81` and this task's own
publish path were built for.

### Acceptance test

| requirement | result |
|---|---|
| run-context records the mode | `capture_mode=cold`; `queue_summary.build = {processed: 18, skipped: 0}` |
| zero cached elements in its closure | **0 of 18** |
| analyze confidence "high" | **1.00** |
| no incremental-run caveat in the report | absent — `run_mode` is `full` |

**34.2 minutes** against a 250-minute budget. That is the answer Required
Fix item 2 wanted, and it means a considerably larger cold target is
reachable next time.

### What only a cold capture could show

```text
Where the time is: 3 element(s) are 99.7% of the 1980.5s critical path
  bootstrap/build/gcc-stage1.bst  1248.7s (63.0% of path)  -> fixing it saves 1248.7s (60.8%)
  bootstrap/base-sdk/gettext.bst   725.9s (36.6% of path)  -> fixing it saves  110.1s ( 5.4%)
  bootstrap/gnu-config.bst            1.1s ( 0.1% of path) -> fixing it saves    1.1s ( 0.1%)
```

`gettext` holds **36.6%** of the critical path and is worth **5.4%** of
the build — a 6.8x gap between share-of-path and realizable saving, on a
chain where it sits behind `gcc-stage1`. Every previous capture measured
a chain through a rebuilt subset; this is the target's real one.

Efficiency Score 0.97, Dispatch Occupancy 39.4%: the pairing `UX-27`
exists to make readable — the scheduler is at the certified floor for
this graph, and the graph is a chain, so the occupancy is low and
nothing about the scheduler can fix that.

### Required Fix item 3: the cold-vs-incremental pair

`bga compare` between the cold capture and an incremental one refuses,
on **both** checks, which is the first real exercise `UX-78`'s
cache-scenario check has ever had:

```text
Refusing to compare these runs (shared_elements, run_mode):
  - baseline has 126 element(s), candidate has 18 - only 18 shared element UID(s)
    (less than half) - these runs may not be the same project
  - baseline is a incremental run and candidate is a full run - their durations and
    floors differ by however much the cache happened to hold ...
```

Both reasons are correct and neither is redundant: the element-overlap
check fires because a cold capture of a bounded subtree is a *smaller*
graph, and the run-mode check fires because the two measure different
builds. A pipeline that pointed at the wrong artifact would see the
first; one that mixed the two scenarios would see the second.

### It falsified a finding written the same day

The cold capture's first `bga analyze` reported:

> Cache hit ratio: 0% (0 cached, 18 rebuilt) - **barely incremental - most
> of the project rebuilt. Look for a volatile cache key near the root**

That is confidently wrong about a build that was *told* not to use the
cache. `UX-92`'s hit-ratio finding, shipped hours earlier, banded the
ratio without consulting `run_mode` — which `UX-55` already derives and
which was sitting in the same result object. Fixed: on a `full` run the
finding reports the fact at `info` (*"Caches off: all 18 element(s)
built from source, none reused - this is the nightly scenario, so a 0%
hit ratio is the intent rather than a finding"*), and the banding still
fires on an incremental run that reused nothing, which is the failure
mode it exists for. Two regression tests.

Worth stating plainly: no amount of review would have caught this. It
took the first capture of a scenario the tool had never seen.

### Note on the log tree

This run does not carry `bst-element-logs.tar.gz`: it was dispatched
from `main` at `a5245ef`, before `UX-91` added log publication. The next
capture will.
