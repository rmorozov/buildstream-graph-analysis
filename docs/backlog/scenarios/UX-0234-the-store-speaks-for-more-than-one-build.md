# UX-234: the store speaks for more than one build

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-203 (store/v1), UX-186 (the comparability grammar), Direction 9 | **Serves:** R5, R7 — first instrumentation for the unserved half of the role model | **Topic:** store

## Motivation

Direction 9's anchor. Every question R5 and R7 ask begins with a
distribution bga already holds the samples for and never aggregates:
a store of captures is a measured service-time distribution with
host manifests, hit rates and resource profiles attached — and
today its only cross-run reading is a trend line of medians. "What
does a build cost", "how much does it vary", "what is the p95",
"what do we actually utilise" — the fact-base for every capacity
answer, none of it published.

## Required Fix

An aggregate contract over a store (extending `store/v1` or beside
it): duration distribution (min/median/p95/max, MAD), cache-hit
trend, resource-profile percentiles where Plane 2 profiles exist,
grouped by the host classes `UX-186`'s manifests already
distinguish — with the refusal grammar for what a mix cannot
support (a cross-host aggregate says so, per the house honesty
rules; fewer than the minimum samples defines no distribution, the
`MIN_BASELINE_RUNS` pattern). The CLI reads it (`--list`'s
aggregate sibling); the viewer's trend gains the band it implies.
The **capacity model** (builders, arrival rates, wait
distributions) is explicitly the *next* task, on top of this one —
its assumptions deserve their own argued filing.

## Out of Scope

- The queueing model itself, cost translation, and any
  fleet/multi-store federation (Direction 9's later steps).
- Monitoring, daemons, anything continuous — this reads a store on
  demand like every other command.

## Acceptance Test

On a fixture store of mixed runs: the aggregate reproduces
hand-computed percentiles exactly; incomplete runs are excluded
from distributions and counted separately (the UX-156 honesty
rule); a cross-host mix aggregates per class and refuses the
blended number without an explicit flag (exit and sentence per
UX-186's grammar); the payload is schema-stamped and round-trips
the UX-190 guard.

## Outcome (round 28)

`store-aggregate/v1`, from `bga/store_aggregate.py`, read by
`bga snapshot --aggregate` and drawn behind the viewer's trend.

```text
$ bga snapshot --aggregate            # fixture: 6 finished runs, two machines
Store: /tmp/...
  6 measured run(s) of 7 snapshot(s)
  1 excluded:
    1 x interrupted

  Ryzen 9 7950X · 32 cores · 64000 MB - 3 run(s)
    Duration: min 10.0s, median 12.0s, p95 14.0s, max 14.0s (MAD 2.0s, n=3)

  Xeon E5-2680 · 16 cores · 32000 MB - 3 run(s)
    Duration: min 50.0s, median 55.0s, p95 60.0s, max 60.0s (MAD 5.0s, n=3)

  This store holds finished runs from 2 host classes (...). Durations are
  not scaled across machines here and should not be, so a blended
  distribution is not published: read the per-class figures, or pass
  --blend to state the mixed claim yourself.
$ echo $?
6
```

Exit 6 is `EXIT_CODE_MISMATCHED_RUNS` — the same code `bga compare`
refuses a cross-host pair with, because it is the same refusal.

### The percentile definition is the contract

Nearest-rank, published in the schema and checked against hand-computed
values: for `n` sorted samples, `p` is the value at index
`ceil(p × n) − 1`. On 1..20 the p95 is 19; on `[10, 11, 12, 14, 30]` the
median is 12, the p95 is 30 and the MAD is 2, all asserted literally.
Interpolation would invent a duration no build ever took, which is a
small lie in a document whose whole claim is that it aggregates
measurements — and the reason is the same one that put a median and a
MAD in `compute_band` rather than a mean and a σ.

### Three refusals, and each is a behaviour rather than a sentence

- **An unfinished capture is not a sample.** Excluded from every
  distribution *and counted* in `excluded.by_reason`. Verified by a
  fixture whose interrupted run is 900 s: it does not reach `max`.
- **A mix of machines is not a distribution.** Grouped by walking
  `hostinfo.COMPARED_FIELDS` rather than by three hardcoded names, so a
  field added there widens this grouping too — asserted by a guard that
  perturbs each compared field in turn. A capture with no manifest is
  its own class: "we do not know which machine" is not "the same
  machine as the others", and merging them would be the blend, silently.
- **Fewer than `MIN_BASELINE_RUNS` finished runs define nothing.** The
  class publishes a shortfall naming what is missing.

### What the item asked for and what it got

The viewer's trend gained the median–p95 band, drawn from published
figures only — and **drawn not at all over a mix**, where it prints the
refusal sentence instead. The mutation that matters is the one a
well-meaning implementation would make: fall back to
`host_classes[0].duration_us` when `blended` is null. That draws one
machine's band over two machines' points, and it reddens.

`store/v1`'s rows gained `host_class` — the label, not the manifest,
because that row is drawn for every snapshot on every `bga view`.

### Two budgets, and one of them moved

```text
bga snapshot --help    53 -> 44 lines (cap 45)
golden export         198,756 -> 209,867 B (backstop was 200,000)
  of which:  store-aggregate/v1 schema   9,137 B
             the aggregate document        ~700 B
```

The help came back under its cap by deleting design history from
argparse — five flags opened with a `UX-1xx:` prefix and spent four
lines on rationale, which is the exact shape `UX-158`'s guard exists to
stop, still live in the file the guard covers.

The **export backstop moved to 240,000**, and this is its fifth move.
Every move has been data, and the guard that establishes that is the
one added here: `test_the_data_is_the_documents_and_the_schemas` parses
every embedded block as JSON and asserts that nothing else is embedded.
A ceiling cannot tell 10 KB of new contract from 10 KB of vendored
font; that can, and it is why raising the number is a measurement here
rather than an argument. The `_DISTRIBUTION` subschema was collapsed to
one object-level description first — it appears eight times, and eight
copies of one paragraph is weight the export pays for nothing (10,961 →
9,137 B).

**Mutations verified red and reverted (9):** the percentile
interpolating; the sample floor dropped to 1; an incomplete capture
counted as a sample; the blend published without being asked for; the
host class ignoring one of `COMPARED_FIELDS`; a mixed store exiting 0;
the trend falling back to the first class's distribution; the band's
edges page-computed rather than published; the listing forgetting which
machine measured a snapshot.

**One mutation did not discriminate and was not counted.** Removing the
`mixes !== 1` check alone changes nothing, because `blended` is already
null on a refused store — the guard is real but that edit never reached
it. Redone as the fallback above, which is the mistake a real
implementation would actually make.

**Deviation from the Required Fix:** none in scope. Resource-profile
percentiles are computed where Plane 2 profiles exist (`cores_busy`
from the same `summarize_plane2_capacity` the capacity hint is
conditioned on, and peak RSS as a maximum over processes, never a sum)
but no fixture in this repo carries a `plane2.json` inside a snapshot,
so those two distributions are exercised by the code path and not by a
measured example. Said out loud rather than left as an implied claim.
The capacity model — builders, arrival rates, wait distributions —
remains the next task, as the Required Fix says.

Full suite: `3059 passed, 3 skipped in 310.54s`.
