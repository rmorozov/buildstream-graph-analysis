# UX-618: the step that fails most writes no record

**Priority:** High | **Status:** 🔴 Open | **Depends on:** UX-554 (the namer), UX-589 (its provenance), UX-418 (the backstop) | **Found by:** round 84, after four rounds of bisecting a log tail | **Serves:** every session reading a red CI job | **Topic:** guards

## Motivation

`Test (small tier, with a backstop)` is the step CI fails on most —
five times in round 84 alone — and it is the one step that writes no
junit. So the namer three steps later has nothing to read:

```text
the junit could not be read ([Errno 2] No such file or directory:
'/home/runner/work/_temp/junit.xml'); the suite's own output above is
all there is
```

`UX-554` built the namer for exactly this reader and `UX-589` gave it
provenance, and both are useless on the failure path that fires most.
What is left is a log tail: with four failures each dumping a
1,300-line document, the names sit ~1,800 lines above the end and out
of reach of what an API returns.

Measured cost this round: a failure reproducible on **neither** a
working tree, a full clone, nor a shallow clone — 4 tests that fail in
CI and 4 more that skip there, against 4,050 collected in both — and
no way to learn which four without changing the workflow first.

## Required Fix

The backstop writes the junit too. The later `Test` step overwrites it
when it runs, which is what the drift gate wants; when the backstop
fails, `Test` is skipped and the backstop's junit is the record that
survives. The tier targets take `PYTEST_ARGS`, which only `test` did.

## Out of Scope

- The namer itself and its provenance line — both right, and this is
  what lets them run.
- Why those four tests fail in CI — unknown until this lands, and it
  gets its own row once the names are known.

## Acceptance Test

A red small tier in CI, and "The failing tests, named" naming them.
