# UX-378: the host's memory is a number from before the build, and an OOM leaves no trace

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-104 (memory-aware capacity advice), UX-243 (the memory envelope reaches no reader) | **Serves:** anyone whose build died and does not know why | **Topic:** capture | **Area:** tools

## Motivation

bga talks about swap more than almost anything else. Its own sentences,
in `findings.py`, `analyzer.py` and `report/text.py`:

```text
"one more builder would swap. Swapping is the worst build slowdown there
 is and no CPU-side gain compensates for it"
"above the memory-feasible capacity is a recommendation to swap"
"pushing the build host into swap is a qualitatively worse failure mode"
```

None of it is measured. What a capture records about host memory is two
numbers taken once, before the build:

```text
run-context.json    host_memory_mb   16075
host_manifest       memory_bytes     16855859200
```

Everything else is modelled: the memory envelope is a sum over Plane 2's
per-process `maxrss`, and the swap verdict is that sum against total
RAM. Nothing samples what the host was actually doing. There is no
series of `MemAvailable`, no `SwapFree`, no `pgmajfault`, no page-cache
figure — `grep -rn swap` over `bga/` and `tools/` returns advice and
never a reading.

**So an OOM is not diagnosable from a capture, and worse, it is not
distinguishable from a normal exit.** The evidence exists in one of the
two record streams and stops there:

- The spine writes `exit=signal:9` — `spine.c:385` reads the wait status
  from `PTRACE_GETEVENTMSG` and a kill is distinguishable from an exit
  code. The parser keeps it as `record["exit_status"]`.
- It reaches `bga timeline`, and the trace dictionary documents it and
  the `failed` category built on it.
- It reaches **nothing else**. `plane2.json` has no key for it —
  `process_count`, `matched_count`, `open_count` and
  `open_records_note` are the whole vocabulary — so the terminal report
  and `bga view` cannot say a process was killed.
- Under the default spine policy there are no spine records at all
  (`UX-376`), so the field is usually absent anyway, and a killed
  process arrives as `open_reason: no-observed-exit` — the same record a
  `sh -c` wrapper that `_exit()`ed normally produces. That collision is
  named in `_open_record`'s own docstring: "killed by a signal, or still
  running when the trace ended".

A reader whose build was OOM-killed gets a capture that says some
processes had no observed exit, which is also what a healthy capture
says.

## Required Fix

Two halves, both cheap.

**Sample the host while the build runs**, into its own file beside the
run — the capture directory already holds several such (`UX-381`). A
low-frequency series (a second or two) of `MemTotal`, `MemAvailable`,
`SwapTotal`, `SwapFree`, `Cached` from `/proc/meminfo` and `pgmajfault`,
`pswpin`, `pswpout` from `/proc/vmstat` is a few bytes a sample and
answers the question the advice has been guessing at. bga already knows
the process count over time, so the two series draw on one timeline —
which is the reader's actual question: *how many processes were alive
when the memory ran out*.

**Publish how processes ended.** `exit_status` is already parsed and
already documented; `plane2/v2` gains a count of processes that exited
non-zero and of processes the kernel killed, with the signal, so the
report and the page can say it. Where the spine did not run, that count
is unavailable rather than zero — the distinction this repository makes
everywhere else.

## Falsification

Capture a build with an element that allocates until the kernel kills
it. Assert the capture publishes a killed-process count naming the
signal, and that the host series shows `MemAvailable` falling across
that interval. Today the first is absent from `plane2/v2` and the second
does not exist.

The other direction: an ordinary capture publishes a killed count of
zero (with the spine on) or "unavailable" (with it off), and its host
series is flat — so the signal is evidence, not decoration.

## Out of Scope

- Per-process memory, which `UX-63`'s `maxrss` and `UX-243`'s envelope
  already cover. This is the host, which they cannot see.
- Acting on the series. Naming a capture as memory-starved is a finding
  and a later item; this one is about there being something to read.

## Outcome

Round 61. Both halves, and each one falsified against a capture built
for it.

**The host is sampled while the build runs.** `HostSampler` writes
`host-samples.jsonl` beside the run — one JSON object per sample, every
two seconds, from `/proc/meminfo` (`MemFree`, `MemAvailable`, `Cached`,
`SwapFree`) and `/proc/vmstat` (`pgmajfault`, `pswpin`, `pswpout`). A
header line carries `mem_total_kb`, `swap_total_kb` and the
wall/monotonic pair that puts the series on a wall clock, the way
`UX-185`'s `bga-clocks` line does for the build.

`bga snapshot` passes `--host-samples` **always, not behind a flag**.
One sample costs 37 microseconds — 1,000 reads of both files in 0.037 s
— and the question it answers has no other source in a capture.

**The clock is the trace's own**, which is the point rather than a
detail. `hook.c` stamps every record with
`clock_gettime(CLOCK_MONOTONIC)` and `time.monotonic()` is that same
clock on Linux, so a sample and a process record join with no offset —
which is what makes *how many processes were alive when the memory ran
out* answerable. On a real capture:

```text
trace records span   1317.6 .. 1319.1  (monotonic)
host samples span    1316.4 .. 1318.4  (monotonic)
```

The series starts before the first traced process and ends with the
build, because the sampler wraps the build and nothing else — bga's own
census, hook compile and shim probe run outside it, or the series would
describe this tool's startup as build memory pressure.

**And how processes ended is published.** `spine.c` has written
`exit=signal:9` since `UX-106`, the parser has kept it, `bga timeline`
has rendered it — and `plane2/v2` had no key for it, so the terminal
and `bga view` could not say a process had been killed. Measured on a
fixture that kills a traced child, captured twice:

```text
                       spine on            spine off
killed_by_signal       {"9": 1}            —
available              true                false
unknown                0                   23
per_element            consumer.bst: 9 x1  —
```

The right-hand column is the clause that matters most. **"Nothing was
killed" is a claim a capture without a spine cannot make**, and
publishing zero there is how a reader whose build was OOM-killed would
be told their build was healthy. Killed processes are counted by signal
because 9 and 15 mean different things, and only elements with
something to say appear — a clean element in the list makes the block
`O(elements)` and buries the one that matters.

### Falsification run

Ten mutations against the committed tree. All ten caught:

| # | Mutation | Caught by |
| --- | --- | --- |
| M1 | no status at all reports zero kills | `test_no_status_at_all_is_unavailable_and_not_zero_kills` |
| M2 | a signal counts as a non-zero exit | 3 clauses |
| M3 | every element is listed, clean ones included | `test_the_element_that_lost_a_process_is_named` |
| M4 | the sampler stamps the wall clock | `test_it_stamps_the_traces_own_clock` |
| M5 | the snapshot stops asking for samples | `test_the_snapshot_always_passes_the_flag` |
| M6′ | the hook compile moves inside the sampled window | `test_the_sampler_wraps_the_build_and_only_the_build` |
| M6″ | the sampler wraps nothing | the same clause |
| M7 | a truncated last line kills the whole read | `test_a_truncated_last_line_is_tolerated` |
| M8 | the header drops the wall/monotonic pair | `test_the_header_carries_the_pair...` |
| M9 | `run_store` loses the name | `test_the_store_names_the_file` |

**M6 was rewritten rather than counted.** The first version of the
sampled-window clause compared `source.index` of three literals — where
text sits in the file, not what runs — which is exactly the shape the
fixing guide's item 9 warns about, and its second assertion was
near-vacuous. It now reads the parse tree: the single `with sampler:`
in `run_traced_build`, the calls inside it, and the six pieces of bga's
own startup that must not be among them. Both replacement mutations
redden it.

### Verification Log

```text
$ python3 -m pytest tests/unit/test_the_host_was_asked.py -q
15 passed in 0.91s

$ cd <fixture that kills a traced child>
$ bga snapshot --trace-spine=on -- bst build all.bst
$ ls .bga/runs/<stamp>/
analyze.json  build.log  capture-context.txt  element-slice.json
host-samples.jsonl  plane2-resource.json  plane2.json  plane2.log.gz  run

$ head -2 .bga/runs/<stamp>/host-samples.jsonl
{"schema":"host-samples/v1","interval_s":2.0,"clock":"CLOCK_MONOTONIC",
 "wall_at_start":1787997494.28,"monotonic_at_start":1267.316862912,
 "mem_total_kb":16461068,"swap_total_kb":0,"available":true}
{"mem_free_kb":13830152,"mem_available_kb":15666824,"cached_kb":1746792,
 "swap_free_kb":0,"pswpin":0,"pswpout":0,"pgmajfault":8245,"t":1267.318}

$ python3 -c "...plane2.json...['process_outcomes']"
{"available": true, "exited_zero": 21, "exited_nonzero": 2,
 "killed_by_signal": {"9": 1}, "killed": 1, "unknown": 0,
 "per_element": {"consumer.bst": {"killed": 1, "exited_nonzero": 1,
                                  "statuses": {"9": 1, "1": 1}}, ...}}

$ # the same build, --trace-spine=off
{"available": false, "unknown": 23, "note": "no process reported how it
 ended. Only the ptrace spine can ..."}
```

Tiered small on landing at 0.91s.
