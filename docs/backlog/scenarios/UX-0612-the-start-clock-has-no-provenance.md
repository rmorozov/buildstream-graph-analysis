# UX-612: the start clock has no provenance

**Priority:** High | **Status:** 🔴 Open | **Depends on:** UX-594 (which subtracts from it) | **Found by:** round 84, while building the queue seam | **Serves:** anyone computing a duration from a capture's start | **Topic:** capture

## Motivation

`wall_clock.start_us` is two different measurements wearing one name:

```text
--format wrapped   a real instant, read from the scheduler log
--format raw       the log file's mtime
```

Nothing published says which. `UX-594`'s queue wait subtracts a
request instant from it, so on the raw path the wait is silently
wrong — by however long the build ran before the file was last
written. Anything else subtracting from the start has the same defect
and cannot detect it either, because the converter exposes no
wrapped/raw signal to gate on.

This is the shape `UX-190` exists to prevent: an output that does not
say what it is.

## Required Fix

The run context publishes how `start_us` was obtained, and a consumer
that needs a real instant can refuse. `UX-594`'s wait is the first
such consumer and gates on it, with `queue_wait_absent_reason` saying
so rather than publishing a wrong number.

## Out of Scope

- Making the raw path produce a real start instant — declined: there
  is no instant in a raw log to read, which is why the mtime is there.

## Acceptance Test

A raw-path capture, and the queue wait absent with a reason naming the
clock rather than a figure.
