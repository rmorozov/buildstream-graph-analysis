# UX-138: one concept, one name

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — (mechanical; the worklist is written)

Docs polish round (round 14); the full variants table with locations is
in [`round-14`](../../audits/round-14.md).

## Motivation

The fresh-eyes read swept the user-facing docs for competing names of
one concept. The worst offenders, each verified with locations:

- **"sandbox tax" vs "toll"** — alternating *mid-paragraph* in the
  Plane 3 docs, because the CLI output itself prints "toll" under a
  "Sandbox tax" heading;
- **two unrelated meanings of "cold"** in one reference doc — the
  capture mode (vs incremental) and the `--cold` structural floor —
  never disambiguated;
- **"task" where user docs mean "element"** (cli.md's critical-path
  definition among them);
- "baseline set" vs "band" used interchangeably when one is the runs
  and the other the statistic; "run directory" spelled three ways with
  `run-directory` as a path placeholder; the plane *names* introduced
  in README before the numbers every other doc uses; "capture" vs
  "snapshot" for the stored artifact, unpinned.

None of these confuses the author; all of them cost a reader a
double-take, and the corpus is otherwise disciplined enough that the
inconsistencies read as meaningful when they are not.

## Required Fix

1. Adopt the canonical column of the round-14 table: **element**;
   **sandbox tax** (and align the CLI's own output labels — if the tool
   prints "toll", fix the tool, not just the docs); **cold /
   incremental** for capture modes with "caches off/on" as gloss only,
   and the structural floor referred to as **the cold floor
   (`--cold`)** with a one-line disambiguation where both appear;
   **baseline set** (runs) defines the **noise band** (statistic),
   stated once; **run directory** in prose, `RUN/` as the placeholder;
   **Plane N (short name)** on first use per doc; **capture** = act
   and published artifact, **snapshot** = a capture in `.bga/runs/`,
   pinned in a five-line glossary in docs/README.
2. Apply corpus-wide (guides + README + the CLI's rendered labels
   where they are the source of a variant), with the docs tests green.

## Out of Scope

- The spec's own vocabulary (Parts 0-40 use "task" with a definition;
  spec-internal usage stands).

## Acceptance Test

The glossary exists; a grep per canonical term (pasted in the log)
shows no competing variant remaining in guides/README outside quoted
historical output; the CLI prints the same label the docs teach for
the sandbox tax; both "cold"s are disambiguated at every co-occurrence.


---

## What was built

The glossary is five rows in `docs/README.md`, and the corpus was swept
to match it.

**The tool was the source of one variant, so the tool changed.**
`bga cache-logs` printed `Sandbox tax:` as its heading and `toll` in
every row beneath it — which is where the docs' alternating usage came
from. Now: *"Who paid it (by tax seconds, not by share)"*, `4.0s tax of
49.0s`, and `bga correlate`'s granularity finding says "sandbox tax" too.
A test asserts the report contains no `toll` at all, so the two cannot
drift apart again.

The rest: **element** in user prose; **cold floor (`--cold`)**
disambiguated from **cold capture mode** at the one place both appear;
**run directory** in prose with `RUN/` as the placeholder (six variants
of `/path/to/run-directory` and `/path/to/run` collapsed);
**baseline set → noise band** stated once with the distinction made.

Out of scope held: the spec's own "task" vocabulary is untouched, and so
are quoted historical outputs in the audits and case studies.


> **Reopened and closed by `UX-154`.** The sweep stopped one file short:
> `bga correlate` went on alternating "sandbox tax" and "toll" inside a
> single sentence, and the no-`toll` guard this log claimed was scoped to
> the cache-logs report alone. Both fixed. The guard now parses every
> module in `bga/` and `tools/` and checks string *literals the code can
> print* — docstrings and comments recording `UX-99`'s history are where
> the word belongs, and the `toll_*` JSON keys stay, because they are a
> published contract (`UX-75`) rather than prose.
