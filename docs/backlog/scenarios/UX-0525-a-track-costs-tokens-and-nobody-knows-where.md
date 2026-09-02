# UX-525: a track costs 81k-131k tokens, and nobody knows where

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-504 (the implementer whose runs these are), UX-500 (the measurement round it joins) | **Serves:** the maintainer's subscription | **Topic:** docs

## Motivation

Round 75 ran three implementer tracks and recorded, for the first
time, what one costs:

```text
track    wall      tokens
UX-490   943 s     81k
UX-492   996 s    123k
UX-493  1,174 s   131k
```

Three numbers and no split. The register (`UX-497`) cut what a
session *reads*; nothing says whether a track's tokens go to reading
the task file and its ranges, to pasted test output, to the Outcome,
or to retries — and the levers differ for each. Pytest output alone
is a suspect: a full `-q` run of a browser file prints hundreds of
lines the agent then quotes back.

## Required Fix

Instrument the next three tracks: the implementer's transcript
split into phases (orient/read, edit, test output, falsify, Outcome,
close) with tokens per phase, pasted in the round document beside
the wall clock. Then the one or two cheapest levers, named from the
split — the expected ones are a `make test-touching` that prints one
line unless red, and `-q --tb=short` as the agent's only pytest
shape — each landed with its before/after on a fourth track.

## Out of Scope

- Any model or context-window setting — the cost is what the agent
  reads and writes, and that is what is measured.
- The audit session's own tokens — a different shape of work; measure
  it separately if the track figures prove the method.

## Acceptance Test

Three tracks' phase splits pasted; one lever landed with its
before/after; the round-75 figures cited as the baseline.
