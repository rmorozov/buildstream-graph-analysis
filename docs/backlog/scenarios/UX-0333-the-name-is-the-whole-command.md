# UX-333: the name is the whole command

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-308 (which split name from annotation), UX-298 (the interning that prices this) | **Serves:** R1, R2 | **Topic:** capture

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

## Outcome (round 50, 2026-08-27) — 🟢 Done

### The gap, measured

The filing's central claim, re-derived on a workload built for it -
3,000 processes, realistic 466-character compiler argvs with the shared
flags prefix at the front and the distinguishing file at the end:

```text
argv length              466
shared prefix, any two   282 characters
unique full commands   3,000
unique cmd[:120]           1
```

**One name for three thousand distinct compiles.** The filing said two;
its argvs were longer and shared less. Either way the conclusion is the
same and stronger than "invisible detail": the trim did not hide the
tail, it destroyed identity, and a reader scanning that lane sees one
label repeated 3,000 times.

### After

Every slice name is the record's whole `cmd`, walked per record through
the in-repo decoder (`test_each_annotation_equals_the_field_it_came_from`),
and `debug.cmd` is gone.

### What it costs, and why the annotation went with it

```text
                                gzipped                raw
trim + debug.cmd  (UX-308)      127,960             1,914,053
full name + debug.cmd           166,566  +30.2%     3,350,676  +75.1%
full name, no debug.cmd         146,042  +14.1%     1,925,667   +0.6%
```

Keeping both pays for one string twice - that is the +75.1%. Dropping
the annotation with the trim moves the bytes from the annotation table
to the name table and costs **+0.6% raw**. The gzipped column still
rises, and that is the same fact from the other side: near-unique names
are exactly what interning cannot compress, so the saving interning used
to make is the saving that goes away.

On the committed 826-slice capture it moves the other way:

```text
uncompressed   348,014 -> 316,559 B   -9.0%
gzipped         58,150 ->  52,642 B   -9.5%
```

because 412 of those 813 records ran past 120 characters and the rest
were already short - untrimming lengthens 412 names and dropping the
annotation shortens all 826. **What the name costs is a property of the
workload, not a constant**, which is why the guard is a ceiling with
room rather than an equality, and both figures are on the record.

### The declared break

`debug.cmd` is removed from `PLANE2_ANNOTATIONS`, and its absence is
written into the contract rather than left as a gap - in the emitter,
in `docs/spec/trace-dictionary.md`, and in the architecture. A saved
query reading it gets NULL and must read `slice.name`.

Two consumers in this tree were reading it and the guards found both:
the `failed-processes` canned question (`extract_arg` would have
returned null into a column headed `command`, silently), and
`test_the_real_reader_agrees.py`'s `trace_processor` clause, which now
asks for both halves - the tail findable by name, and the annotation
really absent.

### Mutations verified red and reverted (2, plus what the suite caught)

| # | mutation | reddened |
|---|---|---|
| M1 | reintroduce `cmd[:120]` - the filing's own | 3 failed, 25 passed: the equality walk, the hook-record clause, and `test_a_long_command_is_whole_in_the_name` |
| M2 | restore `debug.cmd` beside the full name - the opposite direction | 3 failed, 25 passed, including the real-capture size ceiling at **522,500 B against 420,000**, which is the byte guard catching the double payment on its own |

M1 first failed with a bare `KeyError` from a dict lookup. The lookup
asks with a message now, listing the names the trace does carry - the
re-run is what the table records.

The full suite then reddened **three more clauses nobody mutated**: the
canned question above and the golden snapshot (`UX-331`'s sentence).
Those are guards doing their job on a declared break, and they are the
reason the break is small.

### Deviation from the Required Fix

- **"the 120 constant survives only if some UI ceiling demonstrably
  demands it, with the ceiling cited"** - no such ceiling was found and
  the constant is gone rather than kept unargued. Perfetto renders the
  name into a slice box and elides it at the box's width, which is a
  display decision at the reader's zoom, not a data one.
- `trace_processor` is still not in CI, so the two clauses that ask
  Perfetto's own reader skip here. That is `UX-298`'s standing
  deviation, restated rather than newly incurred.
