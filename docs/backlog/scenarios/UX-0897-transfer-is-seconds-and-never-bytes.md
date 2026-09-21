# UX-897: transfer is measured in seconds and never in bytes, so "the network" is an adjective

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-92, UX-103 | **Found by:** the 2026-09-20 rollout brief ([`continuous-build-improvement.md`](../../design/continuous-build-improvement.md), section 1) — on a review build with the cache on, the question is whether the link is the bottleneck for sources and artifacts | **Serves:** R5 (whether more bandwidth is worth buying), R6 (why a cached build still waited) | **Topic:** capture | **Area:** tools | **Shape:** judgement

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

## Outcome (round 131, 2026-09-20) — 🟢 Done

**Premise:** held on the gap, **falsified on the source.** Transfer was
an adjective, and BuildStream is not where the bytes come from.

### The gap, measured

```text
$ git grep -lE "rx_bytes|tx_bytes|bytes_per_s" main -- bga tools
(no matches)
```

`transfer_share` is published in four modules on `main`; no byte count
is published anywhere. Three causes - the link, the remote, an object
count slow on any link - produce the same share and have different
fixes.

### The gap the Decomposition asked to measure, measured

"Whether BuildStream's log reports bytes per element or only per
session." Against BuildStream 2.8.0's own source: **neither.**

```text
src/buildstream/_artifactcache.py:135  element.info("Pushed artifact {} -> {}".format(display_key.brief, remote))
src/buildstream/_artifactcache.py:201  element.info("Pulled artifact {} <- {}".format(display_key, remote))
```

`_sourcecache.py` is the same shape, and `GetLocalDiskUsage` on
`buildbox-casd` reaches only the TTY status bar
(`_frontend/status.py:405`). So the Required Fix's "the same extraction
pass that reads the pipeline summary can read them" has nothing to
read; the counters come from `/proc/net/dev`, in the sampler that
already reads `/proc/meminfo` at 2s for 37µs a sample.

### After

```text
$ python3 -m bga.cli analyze tests/fixtures/a_build_that_pulls/run
  25% of wall-clock was artifact transfer (download 3.0s) - this build spent
  it moving artifacts rather than making them, and the host moved 125.0M over
  the 3.0s it was transferring - 41.7M/s, which is the whole host's traffic
  and so an upper bound on this build's
```

`transfer_window_us` is a **union** of the transfer spans, not the sum
`transfer_us` publishes: on the guard's two pulls overlapping by five
seconds, the sum is 20s and the window 15s, and dividing bytes by the
sum would have reported three quarters of the rate the link achieved.
`cache-trend` gains the `rate` column its own docstring's example
("40MB/s to 5MB/s") assumed.

### Mutations verified red and reverted (7)

| # | mutation | reddened |
|---|---|---|
| B1 | the window sums spans instead of uniting them | 3 clauses |
| B2 | absent counters read as zero bytes | 1 clause |
| B3 | loopback counted as the link | 1 clause |
| B4 | one sample accepted as a reading | 1 clause |
| B5 | a counter that went backwards read as negative traffic | 1 clause |
| B6 | the finding drops the host-scope caveat | 2 clauses |
| B7 | the trend prints `0B/s` for a rate nobody read | 1 clause |

B3 passed on its first writing: it sampled the live host, where
including `lo` changes a total that the clause never compared against.
`sum_net_dev` was split out so the guard feeds a constructed
`/proc/net/dev` - the same treatment `_busy_jiffies` already has, and
the fixing guide §5 shape.

### Deviation from the Required Fix

The bytes are the host's interface counters, not BuildStream's, because
BuildStream publishes none (above). On a shared machine they are an
upper bound on what the build moved, and that caveat rides in the
schema, in the `source` field and in the finding's own sentence rather
than being modelled away. Per-element granularity is therefore not
available at all; the row's own Decomposition allowed for that
("the finding's granularity follows what the log actually carries").
