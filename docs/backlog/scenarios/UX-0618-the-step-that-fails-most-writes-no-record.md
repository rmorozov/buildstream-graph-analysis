# UX-618: the step that fails most writes no record

**Priority:** High | **Status:** 🟢 Done Open | **Depends on:** UX-554 (the namer), UX-589 (its provenance), UX-418 (the backstop) | **Found by:** round 84, after four rounds of bisecting a log tail | **Serves:** every session reading a red CI job | **Topic:** guards

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

## Outcome

**Round 84**, 2026-09-03, closed in round 85 — the fix shipped without
its Outcome, which is the bookkeeping half of the same round's
`UX-617` shape.

### The gap, measured

```text
$ grep -n "junitxml" .github/workflows/ci.yml     # before
68:  run: make test PYTEST_ARGS="--junitxml=${{ runner.temp }}/junit.xml"
84:    --junitxml=${{ runner.temp }}/junit.xml"
88:  run: make test PYTEST_ARGS="--junitxml=${{ runner.temp }}/junit.xml"
```

Three writers, none of them the backstop — the step CI failed on five
times in round 84. So on the failure path that fires most, the namer
three steps later printed:

```text
the junit could not be read ([Errno 2] No such file or directory:
'/home/runner/work/_temp/junit.xml'); the suite's own output above is
all there is
```

`make test-small` did not accept `PYTEST_ARGS` either; only `test` did.

### The close, measured

```text
$ make test-small PYTEST_ARGS="--junitxml=/tmp/small.xml"
4028 passed, 22 skipped in 23.49s
$ python3 tools/dev_junit_tail.py /tmp/small.xml
the junit records no failure - the suite failed elsewhere …
  read from /tmp/small.xml: 4050 test(s) recorded, 0 failure(s), 0 error(s),
  written 0s before this read - match that against the suite's own summary above
```

`4050 test(s) recorded` is also what CI collects, which is how `UX-619`
established that its four failures were not a collection difference.

### Deviation from the Required Fix

**One.** The Required Fix named only the backstop; `PYTEST_ARGS` was
added to all four tier targets rather than to `test-small` alone. The
same one-token change, and it stops the next caller hitting the wall
this item is about.

### No mutation, and why

The change is a workflow argument and a make variable — there is no
clause to redden. `test_a_failed_suite_names_what_failed.py` already
holds the two claims that matter (the junit is uploaded whatever the
suite did; a step names the failures on the failure path) and both
stayed green. What this item bought is recorded in `UX-619` instead:
the next red backstop names its tests.

### Tier and suite

No new test file. Full suite at the round-84 gate: 6814 passed,
29 skipped.
