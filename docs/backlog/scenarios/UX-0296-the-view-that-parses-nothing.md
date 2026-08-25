# UX-296: the view that parses nothing

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-226 (the decision this promotes), UX-203 (the store rows it leans on) | **Serves:** R1, R2 | **Topic:** viewer

## Motivation

The field showstopper, reproduced and measured this round: a real
dual-plane snapshot's run directory reached ~2 GB (`plane2.json`
1.5 GB; raw log 400 MB gzipped), and `bga view` on it froze in
parsing and then died of memory near server start.

Measured mechanism: `serve()` builds every payload before the
socket exists, serially running every whole-file load path in the
codebase. (1) The analyze payload `json.load`s the entire
plane2.json (`bga/cli.py:145`) — measured 2.9× bytes-to-RAM, ~4.3 GB
projected at field size, ~30 s a pass. (2) The store-aggregate walk
(`bga/store_aggregate.py:155`) re-parses **every snapshot's**
plane2.json on every view of **any** run, to extract two scalars —
measured 1.17 GB of RSS to view a 2 MB neighbour, and with fewer
than three runs it publishes null distributions after paying it.
The element-slice precedent (capture-time writing, `UX-226`) was
never extended to these scalars. (3) The band re-analyzes every
historical run in-process per page load (`tools/bga_view.py:214`,
`bga/compare.py:1070`) — though store rows already carry the
durations a band needs. (4) The trace step decompresses the 400 MB
raw log to ~4.7 GB on disk and reads it as **one string** at a
measured 6.3× amplification (`tools/native_trace_to_chrome_trace.py:258`)
— ~30 GB projected, immediately before `ThreadingHTTPServer` is
constructed at `tools/bga_view.py:760`: the observed OOM "near the
http server run", with (1)+(2) as the observed freeze before it.

Direction 15's first rule is the fix's shape: **capture computes;
view serves.** Nothing on the `bga view` path may do O(events)
work; large artifacts are opened only to stream bytes to a socket.

## Required Fix

The measured load sites leave the view path: the resource scalars
join the capture-time store row (the `UX-226` precedent, extended);
the band builds from the durations the store rows already carry
rather than re-analyzing the store; the analyze payload is read
from the run's published report where one exists; the trace step
leaves startup entirely — built on demand at first request, spilled
to disk rather than RAM until `UX-297`/`UX-298` retire it. A run
predating an artifact gets the sentence naming the command that
produces it, not an in-process analysis. Serving large files streams (fixed-size
chunks), never `read()`-whole. The guard is a generated big-run
fixture (order 10^6 events, built by the test, never committed)
with a **peak-RSS ceiling** on the view startup path and a startup
**time ceiling** — both with argued numbers in the guard's
docstring, the page-size lesson applied to RAM.

## Out of Scope

- The storage format itself (`UX-297`/`UX-298`) — this item makes
  view honest about what already exists on disk.
- The capture-side footprint (`UX-300`).

## Acceptance Test

On the generated big-run fixture: `bga view` reaches "serving on
127.0.0.1" under the RSS ceiling and the time ceiling with the
big artifacts untouched (open-count asserted via an audit hook —
the trace file may be opened only by the byte-serving handler);
mutation: reintroducing a whole-file parse on the startup path
reddens both. A store containing one big run pays nothing for it
when a different run is viewed (measured in the guard).

## Outcome

🟢 **Done.** All four measured load sites left the `bga view` startup
path, and the guard is a generated fixture rather than an argument.

**Measured, before and after, on one fixture shared by both trees** —
a store holding a big snapshot (`plane2.json` 247 MB, 1,000,000 process
records, streamed out by the test) and a 2 MB neighbour beside it.
Startup measured in a subprocess so peak RSS is that process's own
high-water mark, `serve()` timed from call to bound socket, and every
`open()` recorded by an audit hook:

```text
                        before (a260301)              after
view the big run     17.04 s  1232.9 MB          0.04 s   39.5 MB
  plane2.json opened at startup:  3                        0
view the neighbour    8.79 s  1233.5 MB          0.06 s   39.8 MB
  plane2.json opened at startup:  2                        0
```

The neighbour is the row that shows the defect's shape: viewing a 2 MB
run cost 1.2 GB because the store aggregate walked into the *other*
snapshot's monolith for two floats. It now costs what a 2 MB run
should.

**The four sites.**

1. *The analyze payload.* `bga snapshot` already runs the analysis it
   prints; it now publishes it as `analyze.json` beside the run from
   the same in-memory result (one analysis rendered twice, text and
   JSON, rather than a second run of the analyzer), and `payloads()`
   serves that. Direction 15's first rule, end to end.
2. *The store aggregate.* The resource scalars join the capture-time
   store row — the `UX-226` precedent, extended. The native tracer
   writes `plane2-resource.json` beside the report it has just written,
   from the object still in memory, and `_resource_profile(row)` is now `dict(row["resource"])`
   where it was a `json.load` of every snapshot's monolith. The
   aggregates-only helper never touches `processes`, and publishes the
   same numbers: on `macro_micro`,
   `{'cores_busy': 1.603977885512677, 'peak_rss_mb': 153.515625}` by
   both routes. A run captured before this gets `resource_shortfall`
   naming the command that writes the sidecar, not a silent blank.
3. *The band.* `_band_sample` loads `run-context.json` for the two
   scalars the band needs, where a whole `BuildEfficiencyAnalyzer` per
   baseline used to run. Equal on both fixtures: `full 46133000` and
   `unknown 16000` µs.
4. *The trace.* Startup now asks only whether a timeline *could* exist
   — a `build.log` file test — and the first request for the bytes
   renders them, under a lock, into a file the handler streams with
   `shutil.copyfileobj` at 256 KB. This is the read that was
   immediately before `ThreadingHTTPServer`, so it is also the one that
   turned a freeze into an OOM.

**The guard.** `tests/unit/test_the_view_parses_nothing.py`, five
clauses, medium tier at 8.0 s: both ceilings on the big run; the
monolith is never opened at all (a ceiling can be met by a faster
machine, this cannot be met by anything but not reading the file); the
neighbour pays nothing; the published analysis is what gets served
(marked with a value no analysis would produce, so a payload sourced
elsewhere fails rather than looking plausible); and the timeline is
offered without being built. Both ceilings are argued from measurement
in the docstring rather than picked: 250 MB sits between what the
process uses (39 MB) and what one parse of the fixture would cost
(~700 MB at the measured 2.9x bytes-to-RAM), so the bound discriminates
in the only direction that matters.

**Two defects found while measuring, and fixed here.**

*The instrument was measuring the wrong process.* Startup runs in a
subprocess precisely so that peak RSS is its own, and the first version
read `getrusage(RUSAGE_SELF).ru_maxrss` there - which is wrong, because
`signal->maxrss` survives `execve`. Measured directly: a parent holding
411 MB spawns a child that allocates 10 MB, and the child reports
`ru_maxrss` **411.4 MB** against a `VmHWM` of 10.5 MB. It inflates and
never deflates, so no regression could hide behind it, but it made the
guard's verdict depend on the size of whatever spawned it: green run
alone, red inside the full suite at 317.9 MB of "peak" for 13 ms of
work. The child now reads `VmHWM` from `/proc/self/status`, which
`execve` resets, and every figure above was re-measured with it.

*The band's cheap path had no fallback.* `total_duration_us` is the
wall clock **when the run recorded one**; where it did not, the
analysis falls back to the task horizon, which is computed from the
trace and has no cheap source. Reading only `RunContext.wall_clock_us`
therefore contributed `None` to the band for such runs, and
`compute_band` sorted a list of them: `TypeError`, caught by
`test_which_elements_caused_the_regression.py` in the full suite. A run
with no recorded wall clock is now analysed the old way; a captured
one - the case the item is about - takes the cheap path.

**Falsification.** Four mutations against the committed tree, each
confirmed to have landed before the suite ran:

```text
V1  the aggregate parses the monolith again          3 red (RSS 1233 MB)
V2  the timeline is built at startup                 the open-count clause red
V3  the analyze payload is re-derived per load       2 red
V4  `payloads` ignores the published analysis        1 red
```

**Deviation from the Required Fix, recorded.** The fix asks that a run
predating the artifact get "the sentence naming the command that
produces it, not an in-process analysis". Two thirds of that shipped:
an unpublished run's **Plane 2** report is refused above
`PLANE2_VIEW_MAX_BYTES` (64 MB) with exactly that sentence, naming
`bga snapshot -- bst build TARGET` and the memory a parse would cost.
The Plane 1 analysis still runs in process, because refusing it would
leave `bga view` unable to open any run captured before this round —
and it is not the cost the item is about: it reads a wrapped log, does
no O(events) work, and measures 0.04 s on this fixture. The bound is
where the refusal lives, so the guard's big run exercises the degraded
path and still lands inside both ceilings.

**Out of scope, unchanged.** The 95% of the monolith nobody reads is
still written (`UX-297`), the trace is still rendered from a
Chrome-trace conversion rather than emitted natively (`UX-298`), and
the capture-side footprint is still unmeasured (`UX-300`).
