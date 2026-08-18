# UX-68: the producer says "evidence, not a verdict"; the recommendation says "removing the edge is free" — and repeats it 8 times about a runtime stack

**Priority:** High | **Status:** 🟢 Done | **Depends on:** `UX-46` (which produces the evidence), `UX-66` (which unblocked the join that surfaces it)

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

```text
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

## Fix Implemented — and the user was right about the pattern

Investigated against the real capture's declared graph. The answer is
sharper than this task first stated: the stack findings are **false
positives by construction**, not probabilistically.

### Every stack stages exactly one file

| dependency | kind | staged | opened |
|---|---|---|---|
| `public-stacks/runtime-minimal.bst` (x8) | **stack** | **1** | 0 |
| `components/zstd.bst` | **stack** | **1** | 0 |
| `components/m4.bst` | autotools | **321** | 0 |

against the *used* dependencies, which stage 128 to 9,443 files. A
BuildStream `stack` has no artifact content of its own — it is pure
aggregation — so it stages a marker, and **every stack dependency scores
0-of-1 whatever the build does**.

Worse, `runtime-minimal.bst` aggregates `glibc`, `gcc-libs`,
`utf-locale` and `symlinks`. Declaring it `type: build` stages that
closure into the sandbox, and no compile can avoid touching libc. The
detector compared against the empty marker rather than the closure, and
concluded the dependency was free to delete — **eight times, attached to
the heaviest elements in the build**.

So: `components/m4.bst` was the *only* true finding of the ten.

### The user's hypothesis, tested

> generally it discovered pattern of usage for leaf stack elements — that
> are to optimize further export

Correct, and measurable. Across the real graph:

- **110 of 663 build edges (16.6%)** have a `stack` as their dependency.
- Recomputing the longest path with those edges narrowed to `runtime`:
  **3610.5s → 2241.9s, a 38% reduction.**

That number is an **upper bound on a hypothetical**, not a
recommendation, and the distinction matters: narrowing
`runtime-minimal` would break every compile in the project. But it does
establish that stack-mediated build ordering is a large, real lever on
this graph, and that the tool currently cannot say which instances of it
are safe — because it never attributes a stack's transitive content.

### What changed

- A dependency staging fewer than `_MIN_STAGED_FILES_FOR_EVIDENCE` files
  is classified as `aggregating_dependencies`, not `unused_candidates`,
  with a reason that names the kind when known. Kept rather than dropped,
  per the user's suggestion of a full report that retains them.
- `bga correlate` no longer says "removing the edge is free". It reports
  what was measured — *opened no file staged by N declared build
  dependencies* — and states that a runtime-only dependency looks
  identical from here.

**On the real capture: 10 candidates → 1, removing a 90% false-positive
rate from the tool's most prominent recommendation.**

### A correction to round 9

`docs/audits/round-9.md` suggested `components/zstd.bst` was "a concrete
library, read by nothing" and would make a better first recommendation.
It is `kind: stack` staging 1 file — the same false positive. Corrected
there.

## Verification Log

Filed 2026-08-17 (round 9). The recommendation text is verbatim from
`correlate.txt` in the capture published to `captures/fdsdk-latest` as
`5eda28a` (run `32064333551`, `bga_ref` `1143f2b`); the candidate
distribution is from the same capture's `native-report.json`, and the
producer's caveat is that report's own `declared_vs_used.note`. The
phrasing lives at `bga/correlate.py:192`.
