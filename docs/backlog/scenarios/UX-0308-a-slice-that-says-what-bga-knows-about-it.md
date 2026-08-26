# UX-308: a slice that says what bga knows about it

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-298 (the emitter), UX-297 (the reductions beside it) | **Serves:** R1, R2 | **Topic:** capture

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
