# UX-370: Plane 2's frequency and time do not reach the page

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-356 (every field of the element join reaches a reader), UX-102 (configure tax, both planes side by side) | **Serves:** anyone asking what the build spends its time running | **Topic:** viewer

## Motivation

The round's question was concrete: can a reader tell what cmake
configure costs, or what generating a test image costs, in calls and in
seconds? Plane 2 measures both. `tests/fixtures/macro_micro/plane2.json`
publishes:

```text
binary_cost[app.bst].by_count   cmake x26, sh x16, make x11, c++ x10, ld x7
binary_cost[app.bst].by_cpu     cc1plus  5 calls, 70.6% of this element's CPU
by_binary                       ar as c++ cc1plus cmake collect2 ld make
configure_phase                 configure_cpu_us 4,481,317 (6.42% of CPU),
                                with a note on how parentage classifies it
```

Booted, the exported page contains the *names* — `cmake`, `make`,
`cc1plus` all appear — and **none of the numbers**:

```text
6.42% / 4.48s configure figure on the page   no
a by_binary or binary_cost section           no
sections matching binar|configure            none (only plane2_coverage)
```

This is `UX-356`'s shape one document over: published, and not rendered.
A reader who wants "what does configure cost me" has the answer in the
JSON beside the run and no way to reach it from the report.

**Test image generation is a real gap, not a rendering one.**
`configure_phase` classifies by parentage from a named set of configure
entry points; nothing classifies image or artifact assembly. That is a
second, smaller item's worth of work and is named here so the two are
not confused.

## Required Fix

Render what Plane 2 already measures, in the two axes the question asks
for:

- **Frequency and time per binary**, for the run and per element —
  `binary_cost.by_count` and `.by_cpu` are already shaped for a table
  with a share column.
- **The configure phase as a number**, beside the sandbox tax it belongs
  with (`UX-102` put toll and work side by side; this is the same
  drawer). Its note already says what it counts, which is `UX-346`'s
  door.

Both are populations with a share, so `UX-303`'s strip and `UX-289`'s
preset table apply unchanged.

## Falsification

The `UX-356` clause, pointed at Plane 2: every scalar under
`binary_cost`, `by_binary` and `configure_phase` reaches a rendered node
or is named in a redirect sentence that says why not. It fails today on
all of them.

## Out of Scope

- Classifying test-image or artifact-assembly work. Named above,
  belongs in its own item, and needs a capture that does it.
- `plane2_coverage`, which already renders and is a different question
  (how much of the run Plane 2 saw, not what it saw).
