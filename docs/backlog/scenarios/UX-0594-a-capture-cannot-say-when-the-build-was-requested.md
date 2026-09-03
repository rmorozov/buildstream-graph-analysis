# UX-594: a capture cannot say when the build was requested

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-234 (the store as a distribution), UX-581 | **Serves:** R6, the contributor waiting on a verdict | **Topic:** capture

## Motivation

Direction 9's first argued step, and the reason R6 is the one role
the roles table still calls unserved (`UX-580`). `bga`'s clock starts
when the build does:

```text
git grep -li "queue seam" -- docs/backlog/scenarios   1 (UX-581's own file)
```

The waiting a contributor actually experiences happens before the
first scheduler line, so turnaround is not measurable end to end — only
the half that begins after the queue let go.

## Required Fix

The capture records a requested-at instant alongside the started-at
it already has, from whatever the CI system makes available, and
refuses to invent one when it does not. The gap between them is
published as its own quantity.

## Out of Scope

- Modelling the queue (`UX-595`) — this is the measurement it would stand on.

## Acceptance Test

A capture with a requested-at publishes the wait; one without
publishes an absence, not a zero. Mutation: default the missing
instant to the start — red.

## Outcome (round 84)

`queue_seam` in run-context, from `_run_context_common.add_queue_seam`,
written by both producer paths and read into the `store/v1` row.

### The gap, re-measured first

```text
$ python -c "from tools.bst_run_context import build_run_context as b; \
    print(sorted(b('tests/fixtures/synthetic_multi_subproject/wrapper_log.txt')))"
['host_cpu_count', 'host_manifest', 'host_memory_mb', 'max_jobs',
 'producer', 'resource_capacities', 'trace_epsilon_us', 'wall_clock']
$ git grep -l "GITHUB_RUN_ID\|GITLAB_CI\|CI_JOB\|JENKINS_URL\|BUILD_URL"
(no output)
```

A started-at and nothing else about time; no CI variable was read
anywhere. The Motivation's own grep now returns 2 — the second hit is
this file, matching the command printed inside it.

### The close

```text
$ CI_PIPELINE_CREATED_AT=2026-08-13T08:40:00Z  … build_run_context(…)
{"requested_at_us": 1786610400000000,
 "requested_at_source": "gitlab_ci:CI_PIPELINE_CREATED_AT",
 "started_at_us": 1786611600000000, "queue_wait_us": 1200000000}
$ (nothing set)                                … build_run_context(…)
{"requested_at_us": null, "requested_at_source": null, "started_at_us":
 1786611600000000, "queue_wait_us": null, "absent_reason": "no_request_instant"}
$ CI_PIPELINE_CREATED_AT=2026-08-13T09:20:00Z  … build_run_context(…)
{… "queue_wait_us": null, "absent_reason": "request_after_start"}
```

Three absences, named rather than blended: nobody published an instant,
this capture has no start instant either, or the two disagree about
their order — a clock problem, not a queue of negative length. Zero
stays a real answer: a request *at* the start publishes `0` and no
reason, and that is what separates it from an invented zero.

### Mutations verified red and reverted (11)

| mutation | reddened |
|---|---|
| missing instant defaults to the start | `…an_absence_not_a_zero` |
| a request after the start publishes a negative wait | `…refused_rather_than_signed` |
| no start instant drops the request instant too | `…no_wait_either` |
| the source names the system, not the variable | `…not_only_the_system` (+1) |
| the CI variable is tried before the generic one | `…generic_variable_is_tried_first` |
| an unreadable instant raises | `…falls_through_rather_than_raising` |
| the trailing `Z` rewrite removed | `…reads_as_the_offset_it_means` |
| a naive instant read as local time | `…reads_as_utc` |
| the second producer never records the seam | `…beside_the_host_manifest` |
| the store row forgets the wait | `…the_wait_the_capture_recorded` |
| the store row forgets why there is no wait | `…never_looked_differ` |

`tests/unit/test_a_capture_says_when_it_was_requested.py`: 16 tests, 0.93 s.

**Two guards did not discriminate as first written.** The `Z` one and
the naive-instant one compared `parse_instant` against itself, and on
3.11 under `TZ=UTC` those two mutations changed nothing. Rewritten
against a `fromisoformat` narrowed to what 3.9 accepts, and under
`TZ=Asia/Tokyo` — the environments the claims are actually about.

### Deviation from the Required Fix

**No CLI flag.** `bga extract --help` is 45 lines against a cap of 45
(`test_help_is_short.py`), and the capture reaches its producer through
four layers. The instant arrives by environment variable — how a CI
system publishes everything else it knows.

**Two sources, not a survey.** `BGA_REQUESTED_AT` and GitLab's
`CI_PIPELINE_CREATED_AT`, exercised through a synthesized environment —
so the *mechanism* is measured here and the *names* are not. GitHub
Actions publishes no request instant and takes the generic route.

**The start clock's quality is unchecked.** Under `--format raw`,
`wall_clock.start_us` is anchored on the log's mtime, so a wait against
it is wrong and nothing detects that; the converter exposes no
wrapped/raw signal to gate on. Filed, not guessed at.
