# The tools area

Moved from [`docs/design/architecture.md`](../architecture.md)'s
Plane 3 chapter (`UX-810`), joined by its ingestion-path chapter
(`UX-815`); no line inside either is read by a guard, so nothing else
stays behind. Later chapters on `tools/` join this page as they are
filed.

## Plane 3: BuildStream's own persisted logs (`UX-91`)

BuildStream writes a per-element log for every task it runs, and keeps
them: `$XDG_CACHE_HOME/buildstream/logs/<project>/<element>/<key>-<action>.<timestamp>.log`.
They were sitting on every developer's machine, unread by anything.

`bga cache-logs PROJECT_DIR` reads them. It is the only
part of this tool that needs **no capture, no flags and no foresight** —
the evidence is a by-product of builds that already happened, including
builds nobody thought to instrument.

What that buys, and what it costs:

- **Per-element phase breakdown.** Each log carries BuildStream's own
  timed activities — `Staging dependencies`, `Integrating sandbox`,
  `Running commands`, `Caching artifact` — at one-second resolution.
- **The sandbox tax** (`UX-99`): how much of each element's time went to
  staging, integrating and caching rather than to the build itself. On
  freedesktop-sdk it is **13.0s of 4409.0s (0.3%)** — and the answer
  being *small* is the point: the toll is what the merge half of the
  granularity advice is computed from (`UX-100`), and a project where it
  is 0.3% has no elements that are too small to be worth their own
  sandbox.
- **The configure tax** (`UX-102`): what the build tools themselves say
  they spent answering configure questions. Counted only where the build
  tool reports it — cmake does, autotools' `configure` and meson do not
  — so on an autotools project this is a floor of zero rather than a
  measurement, and the report says so and points at Plane 2's traced
  view instead. With `--native-report`, both figures are shown per
  element, side by side and **never summed**: one is wall-clock the tool
  self-reported, the other is CPU seconds traced, and adding them would
  invent a quantity.
- **The developer tax** (`UX-101`): which elements this project has spent
  the most time rebuilding, across every build in the tree. With
  `--graph` it can separate a rebuild caused by an upstream key change
  from one whose own definition changed — the logs alone carry no
  dependency edges.

The costs are stated in the report itself, every time: one-second
resolution, no `--builders`, no `--max-jobs`, no scheduler context, no
timestamps inside `Running commands`, and **no session id** — a log's
header is its own task's start, not its build's, so the number of builds
is a lower bound taken from the most-rebuilt element, never a count.
Nothing in Plane 3 may feed a certified floor, and the report says that
too.

## The ingestion path now measures itself (`UX-105`–`UX-110`)

Every plane above rests on an ingestion mechanism, and each mechanism
used to be trusted rather than measured. A capture said what it found;
nothing said what it could not have found. The most recent round closed
that, and the pattern is the same in all four cases: **the same quantity,
obtained twice, is a free test** (`UX-53`) — so wherever a second source
existed, it was wired up.

### Plane 2 knows the size of its own blind spot

`LD_PRELOAD` structurally cannot see a statically-linked process: no
dynamic linker runs, so nothing loads the hook. Every Plane 2 report used
to carry one fixed footnote about that, which fired identically on a
capture that missed nothing and on one whose entire process list was
empty.

- **`bga capture census PROJECT`** (`UX-105`) classifies every executable
  the project's own sources stage — ELF header arithmetic, no build, no
  BuildStream. `examples/01-resource-contention` reports **5 static
  executables reaching 10 of 10 elements**; `examples/06`'s glibc
  toolchain reports zero and gets silence instead of a warning.
  Classification reads `e_type` as well as `PT_INTERP`, because
  `PT_INTERP` alone calls every shared object on the system a static
  binary — measured, on a real sysroot, before it was believed.
- **`bga capture run --trace-spine`** (`UX-106`) adds a static ptrace
  process-event tracer inside the sandbox that records every process
  whatever its linkage. On `examples/01` that is the difference between
  **0 processes and 24**. It attaches with `PTRACE_SEIZE` behind a pipe
  handshake — the child blocks until the parent has seized it — rather
  than inferring the attach stop from the first `SIGSTOP` it happens to
  see (`UX-130`); every restart site degrades by name instead of failing
  silently (`UX-128`); and the final drain is bounded rather than
  unbounded, which took a build with a backgrounded daemon in it from
  **30.01s to 0.01s** of teardown (`UX-133`).
- **The two record streams are one process list** (`UX-107`). A
  dynamically-linked process is now recorded twice, and consumed naively
  that double-counts every one: on `examples/06`, 1644 records read as
  1644 processes and **112.61 CPU seconds for a build that used 58.47**.
  They are joined on `(invocation, pid)` and a START inside a tolerance,
  every entry carries `spine+hook` / `spine-only` / `hook-only`, and
  coverage stops being a footnote and becomes a count. Verified at scale:
  **127,632 processes on freedesktop-sdk, all one class**. `UX-487`
  made the two streams carry the same *counters* as well as the same
  identities: the spine records `minflt`/`majflt` from the `/proc`
  read it already did, and `inblock`/`oublock` from the task's own
  `/proc/<pid>/task/<pid>/io` — the hook's key names and units, so a
  spine-only process reaches every reader a hook-recorded one does.
  On one workload traced by both at once the two agree exactly.
- **One counter, and two refusals** (`UX-310`). `UX-298` pinned
  `TYPE_COUNTER` as "reserved rather than used" under the rule that an
  event stream may carry only what a capture measured; this is its
  caller, and the same rule decides what is *not* drawn. There is no
  memory curve: `max_rss_kb` is a per-process **lifetime** peak, not a
  sample, so a curve from it would sum peaks that never coexisted -
  exactly what `compute_peak_memory` refuses - and a guard asserts no
  memory counter exists rather than leaving the absence to be read as
  an oversight. "Cores busy" and "open process count" are one question,
  answered by `compute_max_concurrency` over matched records only,
  because an open record's end is unknown and a curve that included it
  would be inventing one. So one series - *traced processes running* -
  whose peak **equals** the published `max_concurrency`, with the tie
  rule taken from the scalar rather than re-decided. The stride is a
  decision with a number: 1,000 windows, each contributing its maximum
  and its closing value, so the cost is independent of build size and
  the peak survives exactly - 1,626 raw endpoints become 538 samples on
  `examples/06` with the peak still 20. Cost: one packet a sample plus
  one for the track, 25.1 B uncompressed and 6.3 B compressed.
- **The trace knows whose build it was** (`UX-311`). A trace file
  leaves the machine that made it - attached, shared, opened weeks later
  beside five others - and carried no identity at all. One `bga: run`
  process track, ranked first, holds one annotated instant: the run
  stamp, project, targets, manifest hash, git commit, `bga` and `bst`
  versions, the host manifest, the builders, and the plane anchor and
  offset. Portable vocabulary on purpose - `trace_processor` selects it
  like any other slice. An unfinished run says so in the **track name**
  (`bga: run (interrupted)`), not only in an annotation, because an
  annotation is something a reader has to open a slice to see and the
  honesty `UX-156` enforces in the report belongs where the first scroll
  lands; all three ways of being unfinished are covered because it calls
  `bga`'s own one accessor rather than re-deriving the rule. Lane order
  is explicit: `sibling_order_rank` per track, and - the rule that had
  to be read rather than remembered - the root descriptor (`uuid = 0`)
  setting `process_ordering` to `PROCESS_ORDERING_EXPLICIT`, without
  which every rank is a hint no UI reads. Identity first, Plane 1
  second, element lanes after, **heaviest traced first** and labelled
  with their kind. That last is a recorded deviation: the item asks for
  the critical path, the timeline reads two logs and a graph rather than
  an analysis, and the trace states which rule it used in `lane_order`
  instead of letting a reader assume the other one.
- **The arrows say why something started now** (`UX-309`). An element
  ends, another begins, and whether that adjacency is *causation* is
  what `graph.json` knows and the trace never said. Perfetto's
  vocabulary is **flows**, drawn as arrows: the timeline emits one per
  dependency edge whose two endpoints both produced a task, and one per
  `ppid` link inside a sandbox - the exec chain, which makes a build
  system's process tree followable instead of inferred from lane
  adjacency. Nothing else: there is no captured relation between one
  element's process and another's, and a flow that invented one would be
  a lie the UI draws in bold. A flow is *one id on two slices* and
  upstream infers the direction from their timestamps, so an edge whose
  source does not begin strictly before its sink is **dropped and
  counted** rather than guessed at - on `examples/06` that is two edges,
  because `toolchain.bst` is instantaneous and both its dependents begin
  in the microsecond it does. The bound is no bound, and the measurement
  is the argument: a flow id rides the slice packet that already exists,
  so **packets are unchanged** at both scales measured (2,335 on
  `examples/06`, 62,804 on a 20,000-process synthetic) and a flow costs
  20.0 B uncompressed, 8.6 B gzipped. The ids are `fixed64`, a different
  wire type from every other number the emitter writes, and a varint in
  that field is a packet a reader drops without complaining - so the
  guard asserts the wire type, not only the value.
- **A slice says what `bga` knows about it** (`UX-308`). A slice used
  to carry its name alone. Perfetto's
  vocabulary for the rest is **debug annotations**, and the timeline now
  writes them: per Plane 2 slice `src`, `cpu_us`,
  `max_rss_kb`, `exit_status`, `exec_chain`; per Plane 1 task
  `element`, `element_kind`, `task_type`, `outcome`. A process that did
  not exit `0` also gets the `failed` **category**, which is what makes
  a class of slice filterable in the UI and selectable in SQL - and
  which is the constant `UX-298` pinned as "reserved rather than used".
  The keys are a contract (`PLANE1_ANNOTATIONS` / `PLANE2_ANNOTATIONS`
  in `tools/bga_timeline.py`, rendered by `UX-312`'s trace dictionary),
  because renaming one silently breaks a saved query; the guard holds
  the emitted set and the documented set equal in both directions. An
  absent field is an absent key rather than a zero: the hook cannot
  observe an exit status, and `0` there would state that the process
  succeeded. Measured on `examples/06`, 825 slices: 100,922 to 330,188 B
  uncompressed and 27,013 to 51,102 B gzipped - the whole command line
  was nearly all of it, and on that capture 412 of 813 records ran past
  the 120-character name.
- **And the name is the whole command** (`UX-333`, which reverses the
  half of `UX-308` above that trimmed it). The 120-character cut fell
  where a compiler argv is least distinguishing: the flags prefix is
  shared and the file is at the end, so **3,000 distinct compiles
  interned to one slice name** - the trim did not hide detail, it
  destroyed identity. The name is untrimmed and the `cmd` annotation
  that carried the tail is dropped with it, because the two together
  would pay for one string twice. Measured on those 3,000 processes at
  466 characters of argv: full name with `cmd` kept costs +75.1% raw,
  full name without it +0.6%. A saved query reading `debug.cmd` gets
  NULL now and reads `slice.name` instead - a declared break.
- **Extraction is one pass over the log, holding no events**
  (`UX-297`). Parsing and pairing were two phases with the whole event
  list between them, because `pair_events` sorted globally before
  pairing. Pairing needs a weaker property than that: one key's own
  events in order, a key being one process seen through one mechanism,
  whose START and END are written by one writer. `examples/06` carries
  **2 global inversions and 0 per-key inversions**, which is the
  measurement that decides it. `stream_records` yields a record when
  its END arrives and holds only the processes currently open;
  `pair_events` is that generator with its input and output sorted, so
  the list every existing caller wants is still a list and still says
  the same thing. On a 200,000-process trace: **288.3 MB peak to 259.5
  MB, 8.2 s to 7.1 s, identical report digest**. The remaining floor is
  the record list itself - `O(processes)`, not `O(elements)`, and named
  as such rather than implied (`UX-313`).
- **Opens-dependent findings state their scope.** Declared-vs-used
  (`UX-46`) now computes over the hook-covered processes and says what
  share that is — `examples/01`'s eight static elements are reported
  `UNCOVERED - 0 of 3 process(es) … were reachable by the LD_PRELOAD
  hook` instead of being skipped in a silence that reads as "no unused
  dependencies".

The spine is **opt-in**, and that decision was a measurement (`UX-108`):
the rule was stated before the numbers — under 2% wall it defaults on,
over it stays a flag — and **+2.7%** on `examples/06` against **+13.5%**
on `examples/08-process-storm` chose. Those two percentages are kept as
the figures that decided it, but they are not the claim any more.

`UX-112` re-measured the same question as a full {spine} × {opens}
factorial and found the ratio unstable and the *unit* wrong: it is a
fact about the fixture's baseline, not about the tool. `UX-129` then
found the replacement headline overshot too. What five independent
measurements support is **0.3 to 1.1 ms per process** — below the
run-to-run spread on `examples/06`, clearly visible on `examples/08`.
The spread is machine state rather than uncertainty within a run: the
tightest measurement, five interleaved `off`/`on` pairs, gives +0.79s on
2003 processes (0.39 ms), with the raw figures in
[`docs/audits/data/spine-cost-storm.md`](../../audits/data/spine-cost-storm.md).
The predicted spine × opens interaction is not there — on the
process-dense fixture the spine is *cheaper* alongside opens, because
opens raises the baseline.

`UX-113`'s `--trace-spine=auto` follows directly: pay that cost only
where the census says the hook is blind, which is also why the exact
size of it matters less than it looks. It is what `bga snapshot` uses by
default.

### Plane 1 knows the resolution of its own timestamps

A wrapped log line is stamped when the wrapper *reads* it, and
BuildStream flushes in bursts, so both ends of every span carry a
read-lag. The same log already contained the check: BuildStream's own
`[HH:MM:SS]` elapsed prefix is an independent measurement of the same
task. Nothing was comparing them (`UX-110`).

Compared across three real builds from 12s to 3261s, the envelope is
**-0.56s to +1.50s and does not grow with the task** — 0.03% of a
1415-second element and 11% of a three-second one, which is why it went
unseen. `bga analyze` now states the resolution where it is a material
share of some task, and names any task reported as *shorter* than
BuildStream timed it, which is a duration that did not happen rather than
one measured imprecisely.

It is **compared, never substituted**: the elapsed prefix is a
second-resolution lower bound, and moving a span's endpoint to satisfy it
would manufacture overlap the capacity model reports as a violation.

### What this is worth

The tool's whole posture is that a number nobody can check is not a
measurement. These four changes apply that to the layer underneath every
number the tool prints — so a report can now distinguish, in its own
output, between *"we looked and found nothing"* and *"nothing could have
looked"*.

