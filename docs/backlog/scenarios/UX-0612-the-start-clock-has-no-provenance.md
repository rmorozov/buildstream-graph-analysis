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

## Outcome

### The gap, re-measured on `5343bd6`

```text
$ build_run_context(raw.log, log_format="raw")     # mtime forced to
{'start_us': 1786665600000000, 'end_us': 1786665605000000}   2026-08-14T00:00:00Z
  mtime_us 1786665600000000 · start == mtime: True
$ build_run_context(wrapper_log.txt, "wrapped")
{'start_us': 1786611600000000, 'end_us': 1786611743000000}
  mtime_us 1788497049826867                       # 62 days later
$ set(raw_keys) ^ set(wrapped_keys)               -> set()
$ wall_clock keys, either path                    -> ['end_us', 'start_us']
$ BGA_REQUESTED_AT=2026-08-13T23:40:00Z, raw path
{… "started_at_us": 1786665600000000, "queue_wait_us": 1200000000}
```

Every clause of the Motivation held. That 1200000000 is the gap to a
file's last-write time; no build waited it.

### The close

```text
$ raw path      wall_clock {… 'start_us_source': 'file_mtime'}
                queue_seam {"started_at_source": "file_mtime",
                            "queue_wait_us": null,
                            "absent_reason": "start_not_an_instant"}
$ wrapped path  wall_clock {… 'start_us_source': 'log_timestamp'}
                queue_seam {… "queue_wait_us": 1200000000}   # unchanged
$ --start-time  wall_clock {… 'start_us_source': 'operator_declared'}
                queue_seam {… "queue_wait_us": 1200000000}
```

Three sources, and the gate is membership of the two that are instants,
not a deny-list — a fourth source added without a decision is refused.
Keyed on the *earliest* bst-invocation event, the one
`invocation_wall_clock` reports, rather than on the `--format` flag,
because `auto` decides per line.

### Mutations verified red and reverted (7)

| mutation | reddened |
|---|---|
| the gate branch never fires | `…refuses_the_wait_and_names_the_clock` (+4) |
| the raw anchor claims `log_timestamp` | `…the_mtime_and_says_so` (+4) |
| `--start-time` loses its own tier | `…the_wait_a_raw_capture_refuses` (+1) |
| the source is the last invocation, not the first | `…earliest_invocation_is_the_one_sourced` |
| `bst_extract_run` never records the source | `…goes_in_beside_the_seam` |
| the row enum drops the fourth reason | `…permits_the_reason_the_capture_writes` (+1) |
| `file_mtime` admitted to the instant set | `…refuses_the_wait_and_names_the_clock` (+1) |

`tests/unit/test_the_start_clock_says_where_it_came_from.py`: 17 tests,
1.99 s single-process. **None failed to discriminate.**

### Deviation from the Required Fix

**One surface beyond the two declared.** `UX-594`'s own guard file
constructed `{"wall_clock": {"start_us": …}}` with no source and
asserted a wait from it — the defect this item is about, in a test.
Two of its cases now declare `log_timestamp`; nothing else there moved,
and all 16 pass.

**The raw path still anchors on the mtime.** Declined in the file and
not attempted: there is no instant in a raw log to read.

**`started_at_source` is in the seam, not in the store row.** The row
carries the refusal through `queue_wait_absent_reason`, whose enum
gained the fourth value; a second row column for the clock would be a
key nothing yet reads.
