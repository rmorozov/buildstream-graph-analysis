# UX-589: the failure namer reads a junit the run did not write

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-554 (the namer), UX-558 (its position), UX-588 (which met it) | **Found by:** round 83, chasing two tests that had not failed | **Serves:** every session reading a red CI job | **Topic:** guards

## Motivation

`tools/dev_junit_tail.py` names the failing tests so a log-tail reader
does not have to scroll. When the suite dies at **collection**, no
junit is written at all — and the namer then reads whatever junit is
on disk from an earlier step of the same job, naming *its* failures as
this run's.

Measured on run 33751159258, `test (3.9)`, where the real failure was
four collection errors from `UX-588`:

```text
the junit could not be read ([Errno 2] No such file or directory:
'/home/runner/work/_temp/junit.xml'); the suite's own output above is
all there is
```

That run said so correctly. The run before it, 33750369347, did not —
it printed:

```text
2 test(s) failed, named here because the log tail above may be truncated (UX-554):
  FAILURE tests.unit.test_the_rail_takes_a_step...test_next_walks_the_order_the_page_declares
  FAILURE tests.unit.test_the_rail_takes_a_step...test_previous_walks_back
```

Those two tests pass on that tree — locally, and on 3.10/3.11/3.12 in
the same CI run. The names came from a junit an earlier step left
behind. A reader who trusts them investigates a regression that is not
there; this round did, for four measurements.

## Required Fix

The namer compares the junit's mtime against the run's start (or the
workflow writes a fresh path per step, or deletes the file before the
suite runs) and says *"this junit predates the run"* rather than
naming its contents. The one-line summary a log-tail reader sees must
never be a previous step's failures presented as this step's.

## Out of Scope

`UX-588`'s floor guard, which is what exposed this. The naming step's
position in the workflow (`UX-558`) is right and is not touched.

## Acceptance Test

A junit written before a run, and the namer refusing to name it.
