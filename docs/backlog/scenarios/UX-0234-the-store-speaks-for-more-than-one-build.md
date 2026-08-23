# UX-234: the store speaks for more than one build

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-203 (store/v1), UX-186 (the comparability grammar), Direction 9 | **Serves:** R5, R7 — first instrumentation for the unserved half of the role model

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
