# UX-378: the host's memory is a number from before the build, and an OOM leaves no trace

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-104 (memory-aware capacity advice), UX-243 (the memory envelope reaches no reader) | **Serves:** anyone whose build died and does not know why | **Topic:** capture

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
