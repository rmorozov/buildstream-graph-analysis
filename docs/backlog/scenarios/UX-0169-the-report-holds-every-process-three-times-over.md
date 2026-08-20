# UX-169: the report holds every process three times over

**Priority:** Medium | **Status:** 🟢 Done — 413 MB → 204 MB, report byte-identical | **Depends on:** UX-168 (which measured this and could not fix it from the reader)

## Motivation

`UX-168` was filed against the trace *reader* — "analysis slurps the
whole trace into RAM" — and streaming it was correct and did not move
the number the item cared about. Measured on a 56 MB / 400k-event
synthetic trace, `bga analyze` peaked at **635 MB resident / 545 MB allocated either
way**; the whole-file string is freed long before the peak arrives.

Where the peak actually is, measured cumulatively in one interpreter:

```text
baseline              19 MB
after parse          246 MB   400k event dicts
after pair+merge     517 MB   400k record dicts
after full report    917 MB   400k entries in report["processes"]
```

Every traced process is materialised three times in three shapes —
parsed event, paired/merged record, report row — and all three are
alive at once because each stage takes the previous stage's list as an
argument and the caller keeps a name bound to it. The multiplier is
~2.3 kB of Python object per traced process, against ~140 bytes of
trace text: a **16x amplification**, and it is the amplification, not
the file, that decides whether a multi-hour build can be analyzed on
the machine that just built it.

This is the phase right after the build, when the machine is at its
least able to spare a gigabyte.

## Required Fix

Pick one and measure it, rather than doing all three:

- **Drop the intermediates.** `pair_events` and `merge_record_streams`
  consume their input; nothing needs the event list afterwards. Freeing
  each stage as the next consumes it should cost one line and remove
  ~250 MB of the 917.
- **Slot the row.** `report["processes"]` entries are uniform dicts; a
  `__slots__` class or a tuple-of-columns costs a serialisation shim
  and roughly halves per-row size.
- **Cap what the report carries.** The renderer shows a bounded number
  of processes; the JSON report carries all of them because it always
  has. Whether every row must survive into the report at all is a
  product question, not a memory one, and should be answered before
  either optimisation above.

## Out of Scope

- The trace format and the reader (`UX-168`, done).
- Analysis time. 17.9s for 400k processes is not the complaint.

## Acceptance Test

`bga analyze` on the same synthetic 400k-event trace peaks
measurably below 545 MB allocated — measured with `tracemalloc`, not
`ru_maxrss`, which Linux does not reset across `exec` and which a
subprocess therefore inherits from its parent — with the number quoted and reproduced by the
test that quotes it, and the report's own content unchanged
(byte-identical JSON against the current output on a small fixture).

## What was built

Three changes, none of them to what the report says.

**The events are released as the records are built.** `pair_events`
grew `consume=True`: it sorts in place and empties the list as it
reads it, so an event dies as soon as its record exists. Opt-in,
because it is destructive and only one caller — `load_and_summarize`,
which drops its reference on the next line — has no use for the events
afterwards. Every other caller keeps the copying default, and there is
a test that the default leaves its input alone.

**The events are dropped at all.** `load_and_summarize` bound `events`
through `summarize` and the opens pass. `count_unmatched_ends` moved
above the pairing so the name can go with a `del` immediately after.

**The opens pass streams.** `parse_open_records` was called as
`parse_open_records(handle.read(), ...)` directly beneath a UX-168
comment claiming it streamed — it built exactly the whole-file string
that comment was about. It is now `parse_open_lines(handle, ...)`, a
one-pass reader whose only state is the current block's own `unique`
count; `parse_open_records(text)` stays as the string-taking wrapper
for callers that have one.

### Measured

52 MB trace, 200,000 processes, all matched, 16 concurrent — a real
build's shape rather than a generator's:

| | peak allocated | report |
|---|---|---|
| before | 413 MB | `f2dd541bf93b5243` |
| events freed + opens streamed | 331 MB | `f2dd541bf93b5243` |
| **+ consuming pairer** | **204 MB** | `f2dd541bf93b5243` |

A 51% cut, and the report digest is identical at every step — which is
the half that makes the number mean anything. 204 MB is barely above
the 198 MB the event list costs on its own, so what is left is the
parse, not the analysis holding it twice.

### A correction to UX-168's figures

`UX-168`'s measurements were taken on a synthetic trace whose `END`
lines carried no `ppid`. The parser requires it, so every `END` was
dropped and its "400k-event / 400k-process" trace was really 400,000
`START`s with no observed exit — the one shape where nothing can be
freed during pairing, because every `START` stays pending forever.

The direction of UX-168's findings is unaffected (streaming the reader
beats slurping it at the call site; the end-to-end peak did not move).
The absolute figures are not representative, and UX-168's file now
says so and carries these:

```text
parse only, streaming   198 MB      (UX-168 recorded 215 MB)
parse only, slurped     318 MB      (UX-168 recorded 365 MB)
```

Recorded here as well as there because the mistake is instructive: a
memory fixture that does not exercise the release path cannot measure a
release.

### Guards

`tests/unit/test_analysis_memory_shape.py`, seven of them. Four
mutations, each red:

- pairing copies again (`consume=False`) → the peak ratio guard fails.
- the opens pass reads the whole file again → the "never builds a
  string" guard fails.
- the short-block guard removed → a stray path after an unrelated
  `START` is attributed to the dead block.
- the header check moved after the path branch → a header arriving
  mid-block is eaten as a path.

The remaining three are contract and parity assertions, not mutation
targets: the consuming and copying pairers return equal records, the
default leaves its input intact, and the streaming and string opens
readers agree on the same input.
