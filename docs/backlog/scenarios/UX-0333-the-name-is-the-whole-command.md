# UX-333: the name is the whole command

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-308 (which split name from annotation), UX-298 (the interning that prices this) | **Serves:** R1, R2 | **Topic:** capture

## Motivation

The user's field report: slice names are still trimmed in the
Perfetto output. Confirmed — `tools/bga_timeline.py:1019` keeps
`name = cmd[:120]`, with the full command one click away in
`debug.cmd` (UX-308's split). The field says the click is the
wrong trade: the reader scanning a lane wants the distinguishing
argv tail *on the slice*, not in the details pane — two compiler
invocations differing at character 200 are identical on screen.

Measured this round, on 3,000 processes with realistic 560-char
compiler argvs through the real writer: **the trim is worse than
invisible detail — it destroys identity.** Compiler argvs share
their first 120 characters (the flags prefix) and differ at the
*end* (the file), so the whole workload interned to **2 unique
names** — thousands of different compiles render as
identically-named slices, which is precisely the field complaint.
The fix is nearly free done right: full command as the interned
name **with the `debug.cmd` duplicate dropped** costs **+8.4 %
gzipped, +0.4 % raw** (keeping both would cost +22.8 % gz /
+75.2 % raw — the string paid twice). Near-unique names mean
interning saves little, and that is fine: the bytes moved from
the annotation to the name table.

## Required Fix

The full command becomes the slice name (interned, as all names
are); the `debug.cmd` duplication is dropped or reduced per the
measurement, so the trace does not pay twice for one string; the
trace dictionary updated (a rename in the annotation contract is
a break — declared, not slipped); the 120 constant survives only
if some UI ceiling demonstrably demands it, with the ceiling
cited.

## Out of Scope

- Truncation heuristics (smart middle-elision etc.) — the fix is
  the whole name; Perfetto's own rendering handles display.

## Acceptance Test

On the fixture trace: every slice name equals the record's full
`cmd` (equality walk via the in-repo decoder, plus
`trace_processor` where available); the size deltas measured and
recorded here; the dictionary and per-scope guards green after
the annotation change (mutation: trim reintroduced → equality
walk reds).
