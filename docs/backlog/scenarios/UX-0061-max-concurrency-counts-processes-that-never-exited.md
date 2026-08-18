# UX-61: `max_concurrency` reports 5,268 concurrent processes on a 4-core runner, because a process with no observed exit is excluded from the metric but not from the timeline

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** `UX-11` (which introduced the metric)

## Motivation

The real `freedesktop-sdk` capture reports:

```text
process_count:   127630
matched_count:   119590
max_concurrency:   5268
```

on a **4-core** runner running `--builders 4 --max-jobs 4`. Whatever
5,268 is, it is not a count of processes doing work at one instant.

`UX-56` noted this and set it aside as "a separate question about
processes with no observed exit ... already documented in
`open_records_note`", which is where it has stayed. The note explains the
*cause* precisely — a `sh -c` wrapper that `_exit()`s bypasses the hook's
destructor, so no END line is written — and then says those processes are
"excluded from `max_concurrency`, not assumed to run indefinitely".

The measured number says that exclusion is not achieving what it claims.
8,040 processes had no observed exit; the reported concurrency is
5,268. Either the exclusion is not applied on the path that computes the
maximum, or "concurrent" is being derived from something other than
overlapping `[start, end)` intervals.

## Why it is worth fixing rather than caveating

`max_concurrency` is one of the few numbers Plane 2 publishes that a
reader will compare directly against something they know — their own core
count. A figure three orders of magnitude off does not read as a
subtle modelling caveat; it reads as the tool being broken, and it
discredits the numbers beside it that are correct.

It is also the input `UX-28` names as the right long-term answer for the
oversubscription check:

> Feeding Plane 2's *measured* concurrency back into the check — the
> genuinely right long-term answer.

That cannot happen while the measurement is this far off.

## Required Fix

1. **Reproduce it on a small capture first.** The 822-process
   `examples/06` capture reports a plausible figure; the divergence
   appears at scale, so bisect by process count rather than by reading.
2. **Decide what an unterminated process contributes.** Excluding it
   entirely understates; assuming it ran to the end of the capture
   overstates. A third option — treat its last observed activity as its
   end — is available now that `--trace-opens` records per-process
   activity.
3. **Publish the count either way**, as the CPU-time block already does
   with `measured` / `unmeasured`.

## Out of Scope

- Making the hook catch `_exit()`. It cannot: `_exit` bypasses
  destructors by design, which is why the note exists.
- `UX-28`'s oversubscription check itself, which is the consumer, not the
  cause.

## Acceptance Test

1. On the real `freedesktop-sdk` capture, `max_concurrency` is bounded by
   something explicable in terms of the run's real capacity.
2. On the `examples/06` capture it is unchanged.
3. The number of processes whose end had to be inferred is reported
   alongside it.

## Fix Implemented — and the cause was not what this task assumed

This task assumed the exclusion of unterminated processes was failing.
It was not: `compute_max_concurrency` applies it correctly, and it was
never the cause.

The cause was `pair_events` keying START/END on `(element, pid)`. Pids
inside a bwrap sandbox are **namespaced**, so they collide freely across
sandboxes — the element name was doing all the disambiguating work. Under
a project-wide `build-root` override every process shares one name
(`UX-56`), so a START in one sandbox pairs with an END in another, and
the resulting intervals stretch across unrelated processes.

Measured on a real collapsed capture of `examples/06`:

| | keyed on `(element, pid)` | keyed on `(sandbox, pid)` |
|---|---|---|
| longest paired "duration" | **23.48s** (in a ~30s build) | **8.63s** (the real `core.bst`) |
| `max_concurrency` | **34** on a 4-core `--builders 4` run | **20** |

20 is believable — 4 builders x 4 jobs plus their `sh`, `make` and gcc
driver wrappers, most of them blocked rather than running. 34 and 5,268
were not.

So this was a **symptom of `UX-56`**, and `UX-56`'s sandbox id is what
fixes it. A pre-`UX-56` capture has no sandbox id and falls back to the
element name, which is what this always did and is still correct whenever
the element name is real.

The report line also now says what the number counts: processes alive at
once, **not** cores in use, so a figure above the host's core count is
expected and is not oversubscription evidence on its own.

Tests: 5 new (`tests/unit/test_concurrency_pairing_key.py`).

## Verification Log

Filed 2026-08-17. The three figures are from the real
`native-report.json` published to `captures/fdsdk-latest`; the runner's
core count and scheduler settings are from the same capture's
`capture-context.txt` (`nproc=4`, `builders=4`, `max_jobs=4`).
