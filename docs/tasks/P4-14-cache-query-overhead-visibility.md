# P4-14: Surface BuildStream's cache-query overhead as a reportable signal

**Priority:** P4 | **Status:** 🔴 Not Started (needs a real large-project measurement before committing to a direction) | **Depends on:** `P4-10` (real ingestion pipeline this would extend)

## Spec Reference
Not spec-mandated - `docs/specification.md` has zero matches for "CAS", "sandbox", "Query cache", or "cache-query" (confirmed via grep). This is `bga`'s own added heuristic, same non-spec territory as `P4-12`/`P4-13`.

## Background
User's observation: even a build where every element is already cached still has to do *something* to determine that - compute/look up each element's cache key and check the local (and possibly remote) artifact cache - and suspected BuildStream's log hides this time entirely, reporting it as if it took zero seconds, potentially summing to real time on a project with thousands of elements.

Empirically confirmed against a real, installed BuildStream 2.7.0 (`pip install buildstream`, a from-scratch one-element local-source project, `bst build` at **default verbosity - no `--verbose` needed**):
```
[--:--:--][        ][    main:core activity                 ] START   Build
[--:--:--][        ][    main:core activity                 ] START   Loading elements
[00:00:00][        ][    main:core activity                 ] SUCCESS Loading elements
[--:--:--][        ][    main:core activity                 ] START   Resolving elements
[00:00:00][        ][    main:core activity                 ] SUCCESS Resolving elements
[--:--:--][        ][    main:core activity                 ] START   Initializing remote caches
[00:00:00][        ][    main:core activity                 ] SUCCESS Initializing remote caches
[--:--:--][        ][    main:core activity                 ] START   Query cache
[00:00:00][        ][    main:core activity                 ] SUCCESS Query cache
```
This is BuildStream's own `Stream.query_cache()` (`_stream.py`), which runs over *every* planned element before any FETCH/BUILD/PULL/PUSH queue work begins - loading artifact metadata and checking cache-hit status for each - wrapped in one `messenger.simple_task("Query cache", ...)` (`_messenger.py`). The user's intuition was right that this is real work with a real elapsed cost. But it's logged as one aggregate, non-element-scoped line, not distributed across the elements it actually checked - and `tools/chrome_trace_to_bga_trace.py` already, deliberately, drops it: `action="main"` is not in `ACTION_TO_KIND`, per its own docstring ("BuildStream's own top-level pseudo-activity bracket ... not a real element task and has no `TaskKind` equivalent"). So today `bga` has zero visibility into this cost - not "measured as negligible," but genuinely never measured at all.

A second, more granular case exists for projects with a remote artifact cache configured: `Stream.query_cache()` switches from the single synchronous loop above to a real, parallel scheduler queue, `CacheQueryQueue` (`_scheduler/queues/cachequeryqueue.py`), with its own `action_name = "Cache-query"` and its own resource types (`[ResourceType.PROCESS, ResourceType.CACHE]`) - a genuine per-element job going through the same `ElementJob` START/SUCCESS-with-`elapsed` machinery as FETCH/BUILD/PULL/PUSH (confirmed via `_scheduler/jobs/job.py`: the START/SUCCESS messages fire unconditionally, not gated by `CacheQueryQueue.log_to_file = False` - that flag only suppresses a per-element captured-output logfile, not the terminal status line). **Not yet directly observed in a real log** - this repo's test environment has no remote cache to configure against, so the exact line format for this case (does it produce a normal `[hash][cache-query:element] START/SUCCESS` bracket `bga`'s regex would already syntactically match, just currently unrecognized by `ACTION_TO_KIND`? or something else entirely?) needs direct verification with a real remote-cache fixture before any implementation, not assumed from source reading alone.

Whether either case sums to a *material* fraction of wall-clock time on a large (thousands-of-elements) project is an open, unverified question - this task's job is to make the cost visible and measurable first, not to assert significance up front.

## Candidate Directions
1. **Recognize the per-element `Cache-query` action** (remote-cache case) as a new `TaskKind` (e.g. `CACHE_QUERY`), extending `ACTION_TO_KIND`/`bga/ingest/models.py::TaskKind` the same way other real action words are already recognized. Report it as its own category (or fold into `DOWNLOAD`-adjacent resource accounting, matching `KIND_TO_RESOURCE`'s existing FETCH/PULL grouping) rather than silently absorbing it into `BUILD` or dropping it. Requires the real-log verification above first.
2. **Surface the aggregate "Query cache" pipeline-level cost** (no-remote-cache case) as a single, clearly-labeled report line (e.g. "Query cache: 0.4s, not attributable to individual elements - BuildStream reports this as one pipeline-level operation") rather than forcing it into a per-element task - honest about the real precision limit (one number, not N).
3. **Do nothing beyond documenting the gap**, if a real large-project measurement shows this cost is consistently negligible relative to total build time - this task should include actually measuring it against a real, large (or as large as practically constructible) project before committing to either direction above, not assume significance from first principles alone.

## Required Fix (once a direction is chosen after real measurement)
- At minimum: extract and surface the "Query cache" line's elapsed duration somewhere in the produced run directory/report (even as a single caveat-labeled number) instead of silently discarding it as today.
- If the remote-cache per-element case is confirmed real and log-visible: recognize it as a distinct `TaskKind`, following the existing action-word-recognition pattern.
- Document the real precision limit prominently in both cases: this is a coarse, at-best-single-number signal for the no-remote-cache case, not a per-element breakdown - do not imply more precision than BuildStream's own log actually provides.

## Out of Scope
- Don't invent per-element cache-query durations by estimation/interpolation when the log only provides one aggregate number - that would misrepresent measured data as more precise than it is, against this codebase's "no silent correction" discipline.
- Don't change any existing invariant-bearing computation (attribution identity I4, critical path, LB) - this is purely an additive, presentational signal unless real large-project data shows otherwise and the user decides to escalate it.

## Acceptance Test
- The no-remote-cache "Query cache" log excerpt above, reproduced by a checked-in test fixture (real or realistic).
- A real, large (thousands-of-elements-scale, or as large as practically constructible) project's actual "Query cache" elapsed value measured and reported, to settle whether Candidate Direction 3 (do nothing further) applies.
- If the remote-cache per-element case is pursued: a real log excerpt from an actual remote-cache-configured build showing the `Cache-query` action's real line format, captured before writing any parsing code for it.

## Verification Log
_(append real command + output here once run, before marking 🟢)_
