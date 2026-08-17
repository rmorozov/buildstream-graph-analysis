# UX-68: the producer says "evidence, not a verdict"; the recommendation says "removing the edge is free" — and repeats it 8 times about a runtime stack

**Priority:** High | **Status:** 🔴 Open | **Depends on:** `UX-46` (which produces the evidence), `UX-66` (which unblocked the join that surfaces it)

## Motivation

Round 9 closed the macro→micro loop on a real project, and the first
thing it produced end to end was a recommendation that is probably wrong.

`declared_vs_used`'s own note is careful, and correct:

> A candidate is an element/dependency pair where none of the
> dependency's staged files were opened. **This is evidence, not a
> verdict:** runtime-only dependencies, cached configure probes, and
> dependencies needed only for a directory's existence all look the same
> from here.

`bga correlate` renders it as:

```
components/_private/cmake-stage1.bst:
  - declares 1 build dependency it never read (public-stacks/runtime-minimal.bst)
    - removing the edge is free and widens the graph
```

**"Free" is a verdict.** The producer explicitly refused to give one.

## The distribution makes it worse, not better

Across the real capture's 10 unused candidates:

| dependency | candidates |
|---|---|
| `public-stacks/runtime-minimal.bst` | **8** |
| `components/m4.bst` | 1 |
| `components/zstd.bst` | 1 |

A **stack** element with `runtime` in its name, declared by nearly every
component in the project, is precisely the runtime-only case the
producer's note names as indistinguishable from this evidence. So the
tool's most-repeated piece of advice — 8 of 10 findings, attached to the
elements it correctly identified as the most important in the build — is
most likely a false positive, stated as free.

A first user who acts on it edits eight elements and discovers whether
their runtime environment was load-bearing. That is the single worst
first impression this tool could make, and it now sits at the top of its
most polished output.

## Why this is a consumer bug, not an analysis one

Worth being precise, because the fix should not touch the measurement:

- `UX-46`'s detection is correct and its caveat is well-drafted.
- `UX-52` already taught the graph plane that runtime edges are not
  build-gating; the knowledge that `runtime-minimal` is a runtime stack
  exists in the project's own graph.
- The join simply drops the caveat when it turns a measurement into a
  sentence.

## Required Fix

1. **Never state a verdict the producer refused.** The recommendation
   should read as evidence — "no file from X was opened during this
   element's build" — with the removal framed as a hypothesis to check.
2. **Use what the graph already knows.** An element whose kind is
   `stack` (or which the graph reaches only by runtime edges, `UX-52`)
   should be labelled as a likely runtime-only dependency rather than
   ranked as a free win.
3. **Say when a finding is systemic.** One dependency accounting for 8 of
   10 candidates is a project-wide pattern, not eight independent
   discoveries, and presenting it as eight separate recommendations
   inflates the apparent yield eightfold.
4. **Rank the confident findings first.** `components/zstd.bst` under
   `python3.bst` — a concrete library, read by nothing — is a far better
   first recommendation than the stack that everything declares.

## Out of Scope

- Changing `declared_vs_used` itself. It is right, including its note.
- Deciding whether `runtime-minimal.bst` is genuinely removable from
  `freedesktop-sdk`. That is the project's call; the tool's job is to
  present evidence at the confidence it actually has.

## Acceptance Test

1. On round 9's capture, no recommendation contains the word "free" for a
   dependency the evidence cannot distinguish from runtime-only.
2. A `stack`-kind dependency is labelled as a likely runtime-only edge.
3. A dependency appearing in most candidates is reported once as a
   project-wide pattern, not once per element.
4. A concrete, non-stack unused dependency (`components/zstd.bst` here)
   still surfaces, and ranks above the systemic one.

## Verification Log

Filed 2026-08-17 (round 9). The recommendation text is verbatim from
`correlate.txt` in the capture published to `captures/fdsdk-latest` as
`5eda28a` (run `32064333551`, `bga_ref` `1143f2b`); the candidate
distribution is from the same capture's `native-report.json`, and the
producer's caveat is that report's own `declared_vs_used.note`. The
phrasing lives at `bga/correlate.py:192`.
