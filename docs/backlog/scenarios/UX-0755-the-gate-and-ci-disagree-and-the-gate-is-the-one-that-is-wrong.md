# UX-755: the gate and CI disagree, and the gate is the one that is wrong

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-336 (the loop), UX-418 (a slow file CI sees differently) | **Serves:** the session that runs `make test` and believes it | **Topic:** guards | **Area:** unassigned | **Shape:** judgement

## Motivation

`CLAUDE.md` says `make test` is **the gate**, and that running a tier
and committing is a thing this repository gets wrong. Round 103 found
a case where the gate itself reports a failure CI does not have, and
does it reproducibly.

`tests/unit/test_the_journey_has_an_answer_key.py` alone:

```console
$ PYTEST_XDIST= python3 -m pytest tests/unit/test_the_journey_has_an_answer_key.py -q
25 passed in 47.30s
```

The same file inside `make test`, on the same commit, twice — once on
a box sharing the machine with another agent's suite, once on a quiet
one:

```text
7630 passed, 83 skipped, 18 errors    (loaded)
7628 passed, 83 skipped, 18 errors    (quiet)
```

The error is a capture that traced nothing:

```text
AssertionError: Processes traced: 0 (0 matched, 0 no observed exit)
ELEMENT ATTRIBUTION UNRELIABLE: no process carried an element tag at all
```

CI on the same commit:

```text
read from junit.xml: 4698 test(s) recorded, 1 failure(s), 0 error(s)
```

Zero errors, and `bst-tests` and `bst-examples` both green. So the
file's LD_PRELOAD capture works in CI and in isolation here, and
fails only inside the full suite on this container.

The round first called this contention with a concurrent track. That
was wrong: the quiet-box run reproduced it identically. "Another
agent was running" is a plausible cause, not a measured one, and this
row exists partly because that reading was published before the
counter-test was run.

## Required Fix

1. Find what the full suite does to the capture that neither CI nor
   an isolated run does — a shared `TMPDIR`, a `casd` left running,
   an `LD_PRELOAD` the suite unsets, an ordering dependency. Name it.
2. Either make the file work under the suite, or make it **skip with
   a stated reason** on a host where its precondition does not hold —
   `test_every_skip_reason_is_declared` already governs that shape.
   Eighteen errors a session must learn to ignore is the worst of the
   three outcomes.
3. **The inverse check:** whatever the diagnosis, it must predict the
   isolated run passing *and* the in-suite run failing. A cause that
   explains only one of those is not the cause.

## Out of Scope

- `UX-741`, the wall-clock spine guard that reds on a loaded host.
  It is separately filed, it is a different mechanism, and it was the
  only other local-only failure this round.
- Making CI stricter. CI is the side that is right here; the defect
  is that the local gate reports failures a session cannot act on,
  which teaches the session to discount it.

## Acceptance Test

`make test` on this container, on a commit CI calls green, reports no
error this file's isolated run does not also report — or reports a
declared skip naming the precondition.

## Outcome

_Not started._
