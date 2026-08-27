# UX-330: the stranger needs a seed

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-213 (the committed-capture precedent), UX-188 (the timeline this makes reachable) | **Serves:** R1 — the evaluating newcomer | **Topic:** docs

## Motivation

Three walk frictions with one root: a no-bst newcomer has no
committed path into half the tool. The example `.bga` stores are
empty scaffolds (a `.gitignore` and `tmp/`), so every store
command dead-ends in "take a snapshot" — with the command that
crashes without bst (UX-324); the only real run data hides in a
fixtures directory named only by real-project.md's *appendix*; no
committed artifact anywhere can feed `bga timeline` ("one trace,
both planes" is untestable by a stranger, and its error on the
seeded snapshot mis-advises "try its parent" — the real cause, no
build.log kept, is never named); and `bga capture report` refuses
the committed plane2/v2 fixture with a message claiming the file
is not what it demonstrably is (`correlate` reads it happily).

## Required Fix

One documented no-bst seed path from the README: a command
(`gen-synthetic` extended, or a documented fixture copy) that
plants a store with at least two runs, a plane2 report **and a
timeline-capable raw log**, so list/aliases/analyze/compare/view/
timeline/whatif/blast all exercise end to end; `timeline`'s
missing-input error names the actual missing file; `capture
report` reads plane2/v2 (or names the version split honestly
instead of "neither").

## Out of Scope

- Committing large captures (the seed is generated or tiny — the
  UX-213 size argument stands).

## Acceptance Test

On a bst-less machine, following the README's no-bst paragraph
verbatim reaches a served `bga view` and a rendered `bga
timeline` with zero errors (walked in CI's installed-mode job);
`timeline`'s error on a log-less snapshot names build.log;
`capture report` on the committed plane2/v2 fixture renders
(mutation: re-refuse → red).
