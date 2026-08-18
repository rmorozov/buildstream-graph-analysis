# UX-91: BuildStream's own cached logs are an uningested third data plane

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — (new capability direction)

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
