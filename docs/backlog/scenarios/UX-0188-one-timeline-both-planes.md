# UX-188: one timeline, both planes

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-51 (the correlate join this visualizes), UX-126 (the snapshot that should feed it) | **Topic:** capture

## Motivation

Field feedback: *"recheck that we can produce chrome:tracing
compatible output for plane2 capture — maybe we can make some kind of
merge tool that can merge timeline from plane 1 and plane 2."* Round
20 ground-truthed it: the pieces **exist and work** —
`bga log-to-chrome` renders a snapshot's `build.log` (verified live),
every extraction writes `run/chrome_trace.json`, and
`bga native-to-chrome combined <plane1_chrome> <raw_log> <out>
--anchor-element X` is exactly the plane-merge the user asked for.
Three gaps keep a user from reaching it:

1. **Snapshots do not retain the raw Plane 2 log** the combined mode
   needs — only the processed `plane2.json`. The merge exists for
   captures nobody makes by default (`capture run --raw-log` only).
2. **Wrong input succeeds silently**: `native-to-chrome standalone`
   fed a `plane2.json` writes `Wrote 0 trace events`, exit 0
   (reproduced live) — the wrong-input-silent-success shape.
3. **Nobody composes it**: reaching the merged timeline takes three
   commands with invented paths — the pre-UX-126 shape that snapshot
   exists to end. The converters also print their status lines to
   stdout (the one stderr-purity exception left in the tool).

## Required Fix

1. Snapshots retain the raw Plane 2 log (compressed — it is
   line-oriented text; gzip at copy-out, the readers already stream)
   behind a sticky `--keep-raw` first, default-on if the measured
   size cost on a big capture is acceptable (record the number).
2. **`bga timeline [RUN]`**: one command, `@last` grammar, that
   produces the combined chrome trace from a snapshot — Plane 1
   always, Plane 2 lanes when the raw log is present, one sentence
   naming what to open it with (Perfetto / chrome://tracing) and what
   was omitted when Plane 2 is absent.
3. `native-to-chrome` fed a file with zero parseable trace lines
   exits non-zero naming what it expected — "0 events" from a
   non-empty file is a refusal, not a success.
4. Converter status lines move to stderr (their payload is the file).

## Out of Scope

- A viewer (Perfetto exists).
- Changing either trace format.

## Acceptance Test

`bga snapshot` (with retention on) then `bga timeline @last` yields
one JSON that Perfetto's validator loads, containing both planes'
lanes with the anchor alignment `combined` mode already implements;
`bga timeline` on a raw-less snapshot renders Plane 1 and says what
is missing; `native-to-chrome standalone plane2.json out` exits
non-zero naming the expected format (mutation: restoring the silent
success reddens it); converters' stdout is empty when writing to a
file.

## What was built

Round 20's ground-truthing was right: the merge already existed and
worked. Nothing here reimplements it - all four items are about the
*route*.

**1. Snapshots keep the raw Plane 2 log**, gzipped, as `plane2.log.gz`.
The measurement the item asked for, on two real captures:

| capture | raw | gzipped | ratio |
|---|---|---|---|
| `examples/06` | 676,931 B | 53,828 B | **8.0%** |
| `examples/07` | 150,969 B | 12,915 B | **8.6%** |

53,828 B beside a 443,174 B processed report is **12% on top of what
the snapshot already held**, so this is default-on rather than sticky,
with `--no-keep-raw` to decline. Compression is the copy-out step, not
the write path: the tracer streams into a plain file for hours and it
is gzipped afterwards, and a failure to compress leaves the plain log
in place with a warning rather than losing a capture.

**2. `bga timeline [RUN]`**, `@last` by default, same alias grammar as
everything else. It *calls* `bga log-to-chrome` and `bga native-to-chrome
combined` rather than reimplementing them, so it cannot drift from the
three-command form it replaces. Verified on a real capture of
`examples/01` - 24 traced processes:

```text
$ bga timeline @last
Wrote both planes to .../timeline.json, aligned on work-a.bst.
  Open it with Perfetto (https://ui.perfetto.dev) or chrome://tracing.
```

77 events over 9 lane groups: `Build System Wrapper` plus `native:
work-a.bst` … `native: work-h.bst`, with 24 process spans under them.

The anchor, given none, is the **longest-running element Plane 2
traced**: the alignment is a single offset, so a fixed error in it is
the smallest share of the longest span - and that element is the one a
reader opening a timeline is most likely looking for.

With no raw log it renders Plane 1 and **says what is missing**, naming
`--no-keep-raw` as the likely cause, rather than quietly producing half
a timeline.

**3. Zero events from a non-empty file is a refusal.** Reproduced first
(`Wrote 0 trace events`, exit 0, from a `plane2.json` fed where a raw
log belongs); now exit 2 with a message that names that exact mistake.
An **empty** file still passes - a capture that traced nothing really
did produce no events, and refusing that would refuse a truth.

**4. Every converter's status line went to stderr.** The payload is the
file. This also fixed a bug `bga timeline` would otherwise have shipped
with: the Plane 1 converter told the user to open the *scratch* path it
had just rendered into, which is deleted a moment later.

Tests: 16 new (`tests/unit/test_one_timeline_both_planes.py`), and
`timeline` joined the help guard. Six mutations, each red - including
the over-refusal direction (refusing an empty file) and anchoring on
the shortest element.

**A defect the guards found in the new command:** `bga timeline
<path-to-snapshot>` failed, because it reached for `resolve_snapshot`
directly instead of the `is_alias` gate every other command uses - so an
explicit path was treated as an alias and refused. That is the store's
grammar, and this command was outside it.

**A false alarm worth recording**, because it cost time and will recur:
after a mutation was reverted, one guard kept failing with the *old*
behaviour while `inspect.getsource` showed the new code. A stale
`tools/__pycache__` entry, not a code defect - `find . -path "*/tools/*"
-name __pycache__ -exec rm -rf {} +` cleared it. When a revert does not
take, suspect the bytecode cache before the revert.

