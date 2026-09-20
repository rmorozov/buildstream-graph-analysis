# UX-897: transfer is measured in seconds and never in bytes, so "the network" is an adjective

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-92, UX-103 | **Found by:** the 2026-09-20 rollout brief ([`continuous-build-improvement.md`](../../design/continuous-build-improvement.md), section 1) — on a review build with the cache on, the question is whether the link is the bottleneck for sources and artifacts | **Serves:** R5 (whether more bandwidth is worth buying), R6 (why a cached build still waited) | **Topic:** capture | **Area:** tools | **Shape:** judgement

## Motivation

`bga/cache_effectiveness.py` names pull and push time as a share of wall
clock (`TRANSFER_SHARE_NOTABLE = 0.1`) and `bga/cache_trend.py` reads
that share as a series — its own docstring opens on "a remote that slows
from 40MB/s to 5MB/s", a throughput the tool cannot compute, because no
byte count is captured anywhere. So the report can say *40% of this
build was transfer* and cannot say whether the cause is the link, the
remote, or an object count that would be slow on any link. Those have
three different fixes and one of them is hardware the infrastructure
team would be asked to buy.

Bytes are not a new measurement: BuildStream reports what it pulled and
pushed, and the same extraction pass that reads the pipeline summary can
read them.

## Required Fix

Capture pulled and pushed bytes at extraction, publish them beside the
existing transfer seconds, and derive a throughput with its own
absence rule (no bytes, no throughput — never a zero). The finding that
already names a notable transfer share gains one clause: the observed
rate, and whether the session's byte count over its transfer seconds is
near the link's capability or far below it. `bga cache-trend` gains the
series the docstring's example assumes.

## Decomposition

surfaces: `tools/bst_extract_run.py` (bytes at extraction), `bga/cache_effectiveness.py` (throughput beside the share), the `trace/v9` or run-context contract that carries them, and the transfer line in the report
guards: a fixture with bytes and one without — the second must print the share exactly as today and no throughput at all
gap: whether BuildStream's log reports bytes per element or only per session; the finding's granularity follows what the log actually carries
track: `implementer`, once the log's own shape is read
gate: with `UX-896`

## Out of Scope

Measuring the network independently of the build (no synthetic probes).
Any recommendation to buy bandwidth: the row publishes the rate and the
share; what that is worth is `whatif`'s axis and R8's argument.

## Acceptance Test

On a fixture carrying byte counts, the report prints both the transfer
share and the achieved rate, and `cache-trend` prints the rate per run.
On the golden fixture, which has no bytes, output is byte-identical to
today. Mutations: halve the bytes (the rate halves, the share does not
move), zero the transfer seconds (no rate, no division), remove the byte
key (the clause disappears rather than printing zero).

## Outcome
