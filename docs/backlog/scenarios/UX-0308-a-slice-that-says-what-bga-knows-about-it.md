# UX-308: a slice that says what bga knows about it

**Priority:** High | **Status:** 🟢 Done | **Depends on:** UX-298 (the emitter), UX-297 (the reductions beside it) | **Serves:** R1, R2 | **Topic:** capture

## Motivation

Round 43 inventoried the trace against what the run directory
carries. A slice today says one thing: its name — and for Plane 2
that name is the command **truncated to 120 characters**
(`tools/bga_timeline.py:262`), so the argv tail that distinguishes
two compiler invocations is simply gone. Meanwhile the record the
slice was built from carries `cpu_us`, `max_rss_kb`,
`children_cpu_us`, `exit_status`, `exec_chain`, `src` (hook or
spine) — and the Plane 1 task knows its element kind, its task
type (build/fetch/pull), and its cache outcome. None of it enters
the trace. Perfetto's details panel shows an empty pane where its
vocabulary — **debug annotations** — would show all of it, and
`trace_processor` cannot select on anything bga knows
(`extract_arg` has nothing to extract). The user's question
verbatim: are we using Perfetto's power? On slice metadata, no —
the field is unused.

## Required Fix

The emitter grows debug-annotation support (`TrackEvent`
annotation fields, numbers read from the proto files exactly as
`UX-298`'s were — never from memory); the timeline attaches, per
Plane 2 slice: full `cmd` (name stays short — the annotation is
where length belongs), `cpu_us`, `max_rss_kb`, `exit_status`,
`exec_chain`, `src`; per Plane 1 slice: `element`, `element_kind`,
`task_type`, cache outcome where the log states it. A non-zero
`exit_status` also gets a category (the one already-pinned
`EVENT_CATEGORY_IIDS` earns its constant), so failed work is
filterable. Annotation keys become a small named contract (the
trace dictionary, one place, `UX-312` documents it) — a stable key
set is what makes canned SQL against args possible.

## Out of Scope

- Flows, counters, run metadata (`UX-309`/`UX-310`/`UX-311`).
- Any new capture — every annotated fact is already in the raw log
  or the run directory.

## Acceptance Test

On the golden capture: the in-repo protobuf decoder (`UX-298`'s
guard reader — its CI `trace_processor` round-trip is a recorded,
still-open deviation) decodes each contract key, and
`trace_processor` resolves `extract_arg` for them where available on both
planes' slices, and the values equal the record/task fields they
came from (equality asserted, sampled rows); a >120-char command's
full argv is retrievable from the annotation while the slice name
stays short; the failed-process category exists exactly when
`exit_status != 0`; digest stability holds across two runs;
streaming holds (the big-run RSS ceiling unchanged — annotations
ride the same single pass).

## Progress (2026-08-26)

🟢 **Done.**

**The field numbers, read rather than remembered.**
`debug_annotation.proto` was fetched from the same tree `UX-298` read
and recorded with its sha256; `track_event.proto` and
`interned_data.proto` came back **byte-identical** to what `UX-298`
pinned, which is the evidence that the numbers already in the fixture
are still the numbers upstream means. The new ones:

```text
track_event.proto        TrackEvent.debug_annotations = 4
                         EventCategory.iid = 1, .name = 2
debug_annotation.proto   DebugAnnotation.name_iid = 1, int_value = 4,
                         string_value = 6
                         DebugAnnotationName.iid = 1, .name = 2
interned_data.proto      InternedData.event_categories = 1,
                         debug_annotation_names = 3
```

`UX-298`'s own non-vacuity clause - "the table above must cover what
the module pins" - caught all ten of them the moment they were added,
which is the guard doing exactly the job it was written for.

**What a slice carries now.** Per Plane 2 slice: `cmd` (whole), `src`,
`cpu_us`, `max_rss_kb`, `exit_status`, `exec_chain`. Per Plane 1 task:
`element`, `element_kind` (from the run's own graph), `task_type`,
`outcome`. A process that did not exit `0` also gets the `failed`
**category** - `EVENT_CATEGORY_IIDS`, the constant `UX-298` pinned as
"reserved rather than used", earning it.

**Three things the record turned out to say that a guess would not.**

1. *`exit_status` is a string with a vocabulary, not a number.*
   `spine.c` writes `exit=%d` for a normal exit and `exit=signal:%d`
   for a killed one, and the parser keeps it verbatim. The first draft
   of the failed-category test read `status not in (None, 0)`, which
   would have marked **every** process failed - `"0"` is not `0`.
   Success is exactly the string `"0"`; the constant is named
   `EXIT_STATUS_OK` and the guard asserts all three readings.
2. *An absent field is an absent key.* The hook cannot observe an exit
   status - its destructor runs before the process has one, and not at
   all when it is killed - so a hook-only record carries no
   `exit_status` rather than a zero, and gets no category either way.
   Missing evidence is not evidence of success.
3. *Annotations ride the begin, never the end.* Plane 1's outcome is
   only known when the task closes, so the writer pairs B to E first
   and puts the whole answer on one packet, rather than splitting a
   slice's facts across two for a reader to reassemble.

**What it costs**, measured on `examples/06`'s real capture, 825
slices, the same snapshot rendered by this tree and by the commit
before it:

```text
                    before      after
uncompressed      100,922 B   330,188 B     3.27x   (+278 B/slice)
gzipped            27,013 B    51,102 B     1.89x   (+29 B/slice)
```

The full command line is nearly all of it: 412 of 813 records run past
the 120-character name, and 127,167 of 199,389 command bytes are past
the cut. The duplication between the name and `cmd` is deliberate -
`debug.cmd` is *always* the whole command, so a query never has to know
the truncation rule - and gzip absorbs most of it. The annotation
**names** are interned, so ten keys over 825 slices cost ten strings.

**Streaming holds.** The annotations are built from the record that is
already in hand, so the writer's pass is unchanged; the guard re-asserts
`UX-297`'s property here, since this is the item that gave the writer a
reason to want more than the record.

**Deviation, recorded.** The acceptance test asks that
`trace_processor` resolve `extract_arg` for each key. There is still no
`trace_processor` in CI - `UX-298`'s own open deviation, which `UX-312`
absorbs as its first clause - so the decoding is done by the in-repo
protobuf reader, written from the wire rules rather than from the
emitter. That checks the bytes are what the schema says; it does not
check that Perfetto's own SQL reaches them, and this is written here so
the gap is not read as covered.

**Falsification.** Recorded in the Verification Log with the rest of
round 43.
