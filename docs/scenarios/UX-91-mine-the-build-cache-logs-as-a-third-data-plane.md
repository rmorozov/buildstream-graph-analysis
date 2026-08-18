# UX-91: BuildStream's own cached logs are an uningested third data plane

**Priority:** Medium | **Status:** 🟡 In Progress — (1) and (2) done | **Depends on:** — (new capability direction)

## Motivation

Everything `bga` ingests today requires deciding to capture *before*
building: Plane 1 needs the wrapped log, Plane 2 needs the tracer. But
BuildStream itself already persists a per-element build log for every
artifact it creates (`~/.cache/buildstream/logs/<project>/<element>/…`,
and the same logs inside the artifact cache via `bst artifact log`),
timestamped line-by-line, surviving across builds, accumulated for free
on every developer machine and CI runner. Nothing reads them. That is
the only data source that can answer *retrospective* questions — "what
did last night's build do?" — for builds nobody wrapped, and
*longitudinal* ones — "what does this element's configure step cost
across the last 30 builds?" — that no single capture can.

Concretely minable, in increasing order of ambition:

1. **Per-phase breakdown inside an element** from its log's own
   timestamps and command echoes: staging vs `configure` vs compile vs
   install. On this round's fdsdk capture, `cmake-stage1.bst` is 43% of
   the build; whether its 1570s is compile or configure is currently a
   Plane 2 question — the cached log already knows, with zero capture
   overhead.
2. **Frequency analysis across elements and builds**: operations whose
   text recurs across many element logs (the `cmake -B_builddir`
   configure probes this round's Plane 2 found repeated 9× are visible
   as log lines too) — a cheap, no-tracer approximation of the UX-23
   redundancy detector, available retroactively.
3. **Timestamp correlation across a build's logs**: reconstructing an
   approximate Plane 1 timeline (element start/end, overlap, gaps) for
   *unwrapped historical builds*, clearly labeled lower-confidence, so
   `bga compare` gains a baseline even where no one captured one.

## Required Fix

A `bga cache-logs` ingestion tool (or `bga extract --format cache-logs`)
that walks the local log directory (and/or `bst artifact log` output)
for a project, and emits: per-element phase timings (1), a cross-log
repeated-operation report (2), and optionally a degraded run directory
(3) flagged with its provenance so compare/analyze confidence treats it
honestly. Start with (1)+(2); (3) only if the timestamp quality proves
sufficient (measure first — UX-06 showed BuildStream's elapsed prefixes
are per-activity, so this needs the absolute timestamps in the persisted
logs, not the console format).

## Out of Scope

- Replacing the wrapper for the certified floors (cached logs cannot
  carry `--max-jobs` or scheduler context; the floors keep requiring a
  real capture).
- The artifact/CAS statistics direction (UX-92).

## Acceptance Test

Against a real fdsdk capture's populated log directory (the workflow
already leaves one behind — publish it with UX-81): the tool reports
`cmake-stage1.bst`'s configure/compile split, and its repeated-operation
report finds the known cross-element cmake probes without any Plane 2
artifact present. Determinism: two runs over the same log tree produce
identical output.

---

## Fix Implemented — (1) and (2)

**Status:** 🟡 In Progress — (1) and (2) done and verified against real
logs; (3) deliberately not attempted, on measured grounds

`tools/bst_cache_logs.py`, reachable as **`bga cache-logs`**. Points at
`$XDG_CACHE_HOME/buildstream/logs` by default, so on any machine that
has ever run a build it works with no arguments and no prior capture.

### What the logs actually contain — measured first

The Required Fix says "measure first". Measured against real bst 2.7.0
logs, and the measurement changed the design:

- **Phase timings are real and per-activity.** Each `SUCCESS` line's
  `[HH:MM:SS]` is that activity's own duration, not time since session
  start. That is the same per-activity behaviour `UX-06` found in the
  console format — which corrupts a *timeline* and is exactly right for
  a *duration*. A build log yields `Staging dependencies`, `Integrating
  sandbox`, `Staging sources`, `Running commands`, `Caching artifact`,
  and the enclosing `Build` total.

- **There are no timestamps inside `Running commands`.** Counted on a
  real 136-line log: 14 timestamped lines, every one of them a phase
  START/SUCCESS/STATUS, none between the first echoed command and the
  phase's own SUCCESS.

  **This contradicts the acceptance test.** It asks for
  "`cmake-stage1.bst`'s configure/compile split", and these logs cannot
  produce one: nothing times the individual commands. What is available
  is the command *boundaries* (`+ sh -c -e …`) and whatever a tool
  reports about itself — cmake prints `-- Configuring done (0.8s)`, and
  that is kept as `self_timed`, labelled, never mixed into the phases,
  because cmake measured it and the log did not. A configure-vs-compile
  *time* split remains a Plane 2 question. Recorded rather than
  finessed.

- **Absolute start is available at one-second resolution**, from the
  header and redundantly from the filename stamp — confirmed to agree
  (`115357` ↔ `11:53:57`). BuildStream writes it in the runner's local
  time with no offset, so it is only comparable against logs from the
  same machine. Kept as both the literal string and a parsed value.

### (1) Per-element phase breakdown

```
  core.bst [84331b67] 18-08-2026 11:53:22 (14.0s)
    Running commands                    14.0s (100%)
    Configuring (self-reported)          0.8s
    Generating (self-reported)           0.0s
```

The key and timestamp are not decoration: these logs accumulate across
builds — that is the whole reason they can answer a longitudinal
question — so one element appears once per build it took part in, and
without them two real builds of `core.bst` read as one row printed
twice.

### (2) Repeated operations, with no tracer

Against this machine's real log tree, with **no Plane 2 artifact
present**:

```
Operations repeated across 3+ elements (a pointer, not a measurement -
these logs carry no per-command timing):
  9x  cmake --build _builddir -- ${JOBS}
        in app.bst, codegen.bst, core.bst, lib-a.bst (+5 more)
  9x  cmake -B_builddir -H"." -G"Unix Makefiles" ...
        in app.bst, codegen.bst, core.bst, lib-a.bst (+5 more)
```

Those are the same cross-element cmake probes `UX-23`'s Plane 2
detector found — recovered retroactively from logs BuildStream had
already written. It is weaker than Plane 2 and says so in the output:
Plane 2 can say a shared operation *cost* 20 seconds; this can only say
it recurs, and in how many elements.

Deliberately not normalizing paths or arguments away. Two elements
running `cmake` in their own build directories are doing the same kind
of work, but calling that "the same operation" is a claim this data
cannot support — exact text, whitespace-normalized, keeps every match
verifiable by eye.

### A real bug the real-log test caught immediately

The first run of the parser over logs a real `bst build` had just
written failed on the fixture project's junction:
`subproj-junction.bst:libfoo.bst`. The element pattern split at the
first colon, found no whitespace after it, and matched *nothing* — so
every junction-qualified element parsed as nameless.
`junction-name:element-name` is the qualified naming this project's own
ingestion docs call the contract between planes, so Plane 3 would have
been unjoinable to the other two. Fixed (split at the first colon
*followed by whitespace*) with two regression tests, one of which pins
that `Staging dependencies at: /` still splits at the element.

### (3) Not attempted, and why

Timeline reconstruction for unwrapped historical builds. The clock is
one-second resolution and carries no offset; there is no `--builders`,
no `--max-jobs` and no scheduler context anywhere in these logs. The
Required Fix gates (3) on the timestamp quality proving sufficient, and
one second across a build whose elements start within the same second
of each other is not sufficient to reconstruct overlap honestly. The
report says so in its own payload rather than only in this document:

```
"caveat": "Phase durations are BuildStream's own per-activity elapsed values
at one-second resolution. These logs carry no --builders, no --max-jobs and
no scheduler context, and no timestamps inside 'Running commands' - so there
is no configure-vs-compile time split here, and nothing in this report may
feed a certified floor."
```

### The fdsdk half of the acceptance test

Not met yet, and now reachable: the capture workflow discarded its log
directory at job teardown. It now publishes `bst-element-logs.tar.gz`
alongside the run directory (`_casd/` excluded — different format,
hundreds of files). The next capture will carry a real, large log tree
to check this against.

### Verification

- Determinism (the task's own requirement): two scans of one tree
  produce byte-identical JSON. Sorted explicitly rather than relying on
  directory order.
- 16 tests, one of them bst-gated and running a **real `bst build`**
  rather than reading whatever the machine happens to have — ambient
  state would make it non-deterministic, and a test that *skipped* on a
  clean machine would trip the `bst-tests` job's own "nothing was
  skipped" assertion. The gated tier is now 15 and CI's pinned count
  moved with it.
- Suite 1231; `make lint`, `make check-clean` green.
