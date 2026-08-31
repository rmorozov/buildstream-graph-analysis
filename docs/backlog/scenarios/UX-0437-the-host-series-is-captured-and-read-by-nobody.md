# UX-437: the host memory series is captured every run and read by nobody

**Priority:** High | **Status:** 🟢 Done | **Found by:** round 69, strand (a) of the outside walk — is every captured thing reachable? | **Serves:** anyone whose build was slow because the host ran out of memory | **Topic:** viewer

## Motivation

`bga snapshot` samples the host every two seconds for the whole build
and writes `host-samples.jsonl` beside the run. On a real capture of
`examples/06`:

```text
host-samples.jsonl   2,230 B   15 samples
keys: available, cached_kb, clock, interval_s, mem_available_kb,
      mem_free_kb, mem_total_kb, monotonic_at_start, pgmajfault,
      pswpin, pswpout, schema, swap_free_kb, swap_total_kb, t,
      wall_at_start
```

**Nothing reads it.** Checked four ways on that capture:

| destination | result |
|---|---|
| the published page payload | 0 of 14 data keys present |
| `plane2.json` | no `host`, `mem` or `swap` key at all |
| the terminal report | no line mentions host memory or swap |
| the Perfetto trace | one counter track, `traced processes running` |

The two apparent payload hits — `schema` and `available` — are generic
names colliding with unrelated keys elsewhere, so the real reach is
zero. And the reader function exists:

```text
$ grep -rn "read_host_samples" --include=*.py .
tests/unit/test_the_host_was_asked.py:64
tests/unit/test_the_host_was_asked.py:100
tests/unit/test_the_host_was_asked.py:149
tools/bst_native_build_tracer.py:807      <- the definition
```

**`read_host_samples()` is called by its own test and by nothing else.**

`UX-378` built the capture side in round 61 and was right to stop
there — its Out of Scope says so plainly:

> Acting on the series. Naming a capture as memory-starved is a finding
> and a later item; this one is about there being something to read.

**The later item was never filed.** Fixing guide §3.11 asks for the row
before the commit lands, and this is what its absence costs: eight
rounds of every capture writing a series that no reader, no page and no
query has ever seen. This is that row.

The data is not marginal. `pswpin`/`pswpout` and `pgmajfault` are the
difference between "the build was slow" and "the build was swapping",
and `mem_available_kb` against `mem_total_kb` is what says whether the
capacity recommendation `UX-116` prints was reachable on this host at
all.

## Required Fix

- **Decide the destination first**, because there are three and they
  are not equivalent: a counter track in the trace (the series drawn
  against the build, which is what a time series wants), a section on
  the page, or a finding when the series says the host was starved.
  The trace is the cheapest and the most natural shape; the finding is
  what `UX-378` had in mind.
- **Publish it wherever that lands**, with the schema and the sentence
  the visual contract requires — `mem_available_kb` is bytes and must
  say so.
- **A guard that a captured file has a consumer.** This one was found
  by a sweep written for the round; nothing standing asks the question,
  which is why eight rounds passed. The census `UX-401` runs over
  published keys — the gap is one level earlier, between what the
  capture writes and what gets published at all.

## Out of Scope

- **Changing what is sampled**: `UX-378` chose the fields against a
  measurement and this item consumes them rather than revisiting them.
- **The other low-reach files the same sweep flagged** —
  `run/graph.json` at 17% and `plane2.json` at 49% — which are screening
  numbers from a name-matching instrument that over-counts, and each
  needs its own reading before anything is claimed.
- **Naming a host as under-provisioned**: a verdict is a separate
  decision from making the series visible, and the same split `UX-378`
  made still applies.

## Acceptance Test

```bash
cd examples/06-macro-micro-optimization
bga snapshot -- bst build all.bst
```

The series reaches a named destination and a reader can see it. A
mutation deleting `host-samples.jsonl` before the render must redden
the guard; a guard that passes on a capture with no consumer for the
file is the defect this item is.

## Outcome

**Round 70, 2026-08-31.** The destination is the trace; the census that
would have found this eight rounds ago now exists and found a second
instance on its first run.

### The destination, and why not the other two

The trace, as counter tracks on the Plane 1 lane. A sample every two
seconds is a **time series**, and the trace is the only surface in this
tool with the build's own time axis to draw one against - the page has
sections, not seconds. `UX-310` had already built the counter machinery
for exactly this shape, so the cost is five track descriptors and one
packet per sample. Naming a host as starved stays a finding and stays
out, which is the split `UX-378` made.

Placed **before** the `if not raw_log` return rather than beside the
concurrency counter below it, because the host was sampled whether or
not the build was traced: gating it on Plane 2's records would make the
one series that says "the machine ran out of memory" visible only on
captures that already had Plane 2.

### The clock, which was wrong before it was right

The first cut placed the samples with `offset_us` - the Plane 1 ↔ Plane
2 alignment offset. That is the wrong number twice over: it is 0 on a
capture with no Plane 2, which is exactly the capture this series is
most worth having, and it is an *offset* rather than an origin, so the
samples landed at the epoch. Measured, on the fixture:

```text
sample stamps, ns:  1874318860000  1876318860000  1878318860000
the build:          1787331688483000000 .. 1787331734616000000
```

Fifty-six years early. The sampler writes the **pair** it read at one
instant - `monotonic_at_start` and `wall_at_start` - so the walk from
one clock to the other needs no anchor element at all, and
`host_series` now returns wall-clock microseconds. The clause that
caught it is the one this item's own falsification table calls M4: the
first version of that clause checked only the *spacing* between
samples, which is identical on any epoch, and it passed the bug. It
reads the build's `wall_clock` window out of `run-context.json` now.

### The series, on the capture the item was filed against

```console
$ PYTHONPATH=. python3 -m tools.bga_timeline \
    examples/06-macro-micro-optimization/.bga/runs/20260830T171837Z \
    -o /tmp/t437.pftrace
Wrote Plane 1 to /tmp/t437.pftrace.
  Plane 2 is not in it: the Plane 2 capture attributes no span to an element, ...
  2 slices, 0 flows, 0 counters on 8 tracks. Open it with Perfetto ...
  10 host counters on 5 tracks: host major faults, host memory available,
  host pages swapped in, host pages swapped out, host swap free.
```

Decoded off the wire, with the units the descriptors carry:

```text
host major faults            faults   [39076, 39076]
host memory available        bytes    [15907303424, 15884218368]
host pages swapped in        pages    [0, 0]
host pages swapped out       pages    [0, 0]
host swap free               bytes    [0, 0]
```

`mem_available_kb` is multiplied by 1,024 once, here, so the counter a
reader sees is in the unit its label claims - the item's second bullet.
The three `/proc/vmstat` totals are cumulative since boot and are drawn
as sampled; `docs/spec/trace-dictionary.md` says which three, because a
reader differencing a level or levelling a difference gets a wrong
answer either way.

### `counters` is still the concurrency series

`trace.counters` is the writer's total and three guards read the
reported `counters` as `UX-310`'s series - `UX-430`'s narrowing guard
compares `one["counters"] < whole["counters"]`, which folding a second
population into would leave measuring something else. So the result
gained `host_counters` and `host_series` of its own, and `counters`
became `len(series)` - the same number it was, said in terms of the
population it names. The Plane-1-only return hardcoded `"counters": 0`
and would otherwise have reported zero on a trace with fifty samples in
it.

### The census, which is the third bullet

`tests/unit/test_every_captured_file_has_a_consumer.py`. The
instrument is deliberately **not** a text scan for the file name -
fixing guide §5, and "the string `host-samples.jsonl` appears in a
module" is its own example: it cannot tell a reader from a writer, from
a constant, from a comment. `builtins.open` is wrapped while eight
readers run over a complete capture, and the question is answered by
what was actually opened. `gzip.open`, `json.load` off a path and
`pathlib.read_text` all bottom out there.

```text
readers asked  bga analyze, bga blast, bga correlate, bga timeline,
               bga view --export, bga view (payloads), the store
               listing, the store's settings
before         host-samples.jsonl    written every capture, opened by nobody
               run/chrome_trace.json written every capture, opened by nobody
after          host-samples.jsonl    opened by bga timeline
               run/chrome_trace.json declared against `UX-452`
```

Two clauses keep the census from passing by having nothing to check:
every reader must have run clean (a non-zero exit counts as a failure,
because a command that stopped early opens nothing after it stopped),
and the fixture must carry every file row the capture layout names.
A third asserts each declared exemption is *still* unread, so a
declaration cannot outlive the defect it describes.

One correction inside the instrument, found by mutation: the first
version recorded the path *before* calling through to `open`, so an
attempted read of a missing file counted as a consumer -
`read_host_samples` opens the path whether or not it is there, and the
census would have passed on the very absence this item is about. It
records after the open returns.

### Falsification

| # | mutation | result |
|---|---|---|
| M1 | delete the whole emission block | **red** — 8 clauses |
| M2 | the fixture stops writing `host-samples.jsonl` (the item's own acceptance mutation) | **red** — 9 clauses, including the fixture-coverage one |
| M3 | drop the kB → bytes scale | **red** — `test_the_kilobyte_fields_are_published_in_bytes` only |
| M4 | place the samples with `offset_us` — the bug above | **red** — `test_the_samples_sit_inside_the_build_they_were_taken_during` |
| M5 | add a file to the capture that nothing reads | **red** — `test_nothing_in_the_capture_is_written_and_never_read` |
| M6 | report `trace.counters` as `counters` again | **red** — `test_the_result_counts_the_two_populations_apart` |
| M7 | drop the store listing from the readers | **red** — the census, on `.size` and `element-slice.json` |
| M8 | delete the "No host series" branch of the summary | **red** — `test_it_says_so_when_there_are_none` |
| M9 | give a declared exemption a reader | **red** — `test_every_declared_exemption_is_still_unread` |
| M10 | the fixture stops writing `plane2-resource.json` | **red** — `test_the_fixture_carries_every_file_the_layout_names` |
| M11 | a reader that exits non-zero | **red** — `test_every_reader_ran_clean` |

M4 and M11 are the two worth reading. M4 passed the first version of
its own clause, which is §5 in miniature: "the samples are two seconds
apart" is a proxy for "the samples are on the build's axis", and an
interval is the same on any epoch. M11 passed too, until the clause
stopped believing that a reader which returned `1` had read anything.

### The import that only CI could see

The first push of this item used `from tools.bst_native_build_tracer
import read_host_samples`. Every import beside it in the module is
relative, and installed there is no top-level `tools` package at all -
this file is `bga._tools.bga_timeline`. The whole suite passed, because
a checkout has a `tools/` directory; `UX-77`'s packaging job did not:

```text
File ".../bga/_tools/bga_timeline.py", line 496, in host_series
    from tools.bst_native_build_tracer import read_host_samples
ModuleNotFoundError: No module named 'tools'
```

Fixed to the relative form and re-checked the way that job does it - a
built wheel in a clean venv, run from an empty directory:

```console
$ python3 -m build --wheel --outdir dist/ && python3 -m venv /tmp/pkgvenv
$ /tmp/pkgvenv/bin/pip install dist/*.whl
$ cd /tmp/empty && BGA_EXPECT_DEV=1 python3 tests/installed_command_sweep.py \
      --bga /tmp/pkgvenv/bin/bga
  ok      bga timeline /tmp/tmpsh_7jh0e/20260101T000000Z ... -> 0
```

Worth recording because it is the census's own blind spot in miniature:
the census asks whether a file has a reader **in this checkout**, and
`bga timeline` was that reader here and a traceback in the shape a user
installs. The packaging sweep is the guard that covers it, and it did.

### Filed rather than fixed

- **`UX-452`** (contracts, Low): `run/chrome_trace.json`, the second
  file the census found unread. The capture layout's own row already
  says nothing on a read path requires it. Deleting a path from the
  layout is a contract change with its own blast radius, so it is a row
  rather than a line in this commit (§3.11).

### Deviation from the Required Fix

None on the three bullets. Two notes on scope:

- The item's Motivation says the series reaches "no payload, no page,
  no query". It still reaches no payload and no page — the destination
  chosen is the trace, which the first bullet asks to be *decided*
  rather than to be all three. The canned question library gains no
  entry here; a query over these tracks is `trace_processor` work and
  the dictionary rows are what a query needs first.
- The census covers the whole `.bga/` tree of a fixture project, which
  is one capture. A store with several snapshots in different states is
  not exercised, and does not need to be for the question asked: a file
  that no reader opens on a complete capture opens on no capture.

### The suite

```console
$ make lint
All checks passed!

$ make test
5442 passed, 28 skipped, 1 warning in 270.50s (0:04:30)
```
