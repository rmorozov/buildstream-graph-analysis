# UX-169: the report holds every process three times over

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-168 (which measured this and could not fix it from the reader)

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
