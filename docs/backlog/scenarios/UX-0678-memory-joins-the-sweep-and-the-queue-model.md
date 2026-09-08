# UX-678: memory joins the sweep and the queue model

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-613 (capacity-model/v1), UX-30 (the sweep), UX-116 (memory envelope) | **Serves:** R5 sizing a builder, R4 reading the sweep | **Topic:** analysis | **Shape:** judgement

## Motivation

```text
bga/ingest/models.py:38-43     Resource = PROCESS / DOWNLOAD / UPLOAD / CACHE — no MEMORY
bga/replay/scheduler.py        the sweep varies PROCESS capacity only
bga/capacity_model.py:1-75     inputs: builder count, arrival rate, service-time distribution — memory absent
bga/findings.py:810-989        memory_envelope / capacity_recommendation: static peak arithmetic, separate from both
```

The sweep will happily say "eight builders buy 40 %" on a machine
whose RAM fits four of these elements at once; the envelope knows
that and the sweep does not read it.

## Required Fix

Memory as a replay resource: each element's measured peak RSS is its
demand, host RAM (from `host-samples`) the capacity; the sweep's knee
and the queue model's utilization are reported under both
constraints, and the recommendation names which one bound first.

## Out of Scope

- Storage as a resource — the same shape, filed when a capture
  measures per-element disk (it does not yet).

## Acceptance Test

A synthetic run whose elements' peaks sum past host RAM at six
builders: the sweep's knee moves to the memory-bound builder count
and says so; mutation: remove the constraint — the knee guard reds.

## Outcome

**Gap measured.** Per-element peak RSS is captured (`peak_rss_kb` -
`bga/correlate.py:834,939,1070`, `bga/cli.py:290`) and host RAM is
recorded per capture (`mem_total_kb`, `HostSampler.__enter__`,
`tools/bst_native_build_tracer.py:826`), but `capacity_sweep`
(`bga/replay/scheduler.py`) swept only `PROCESS` and never read either.

**Close measured.** `capacity_sweep` gained `peak_rss_bytes`/
`host_memory_bytes`: each swept capacity's own replayed schedule is
read for its peak concurrent RSS (sweep-line over
`ScheduledTask.start_us/finish_us`), and `memory_knee_points`/
`binding_constraints` publish the memory-feasible ceiling and which
constraint bound first. Wired into `bga sweep` (JSON + text) and into
`analyze --plane2`'s `capacity_recommendation` (`sweep_memory_builders`/
`sweep_binding`, additive). Through the real CLI, a synthetic run (8
independent 1s tasks, each measured at a 2 GiB peak, 6.5 GiB host RAM,
builder cap 8):

```text
$ bga sweep <run> --plane2 <plane2.json> --min-capacity 1 --max-capacity 8
...
Knee point (PROCESS): capacity 8 (diminishing returns beyond this)
  MEMORY BINDS BEFORE THE KNEE: capacity 8 needs ~16.0 GB against 6.5 GB
  of RAM. ...
  Recommendation: memory-bound at 3 builder(s)
```

`--format json` on the same run: `"memory_knee_points": {"PROCESS": 3}`,
`"binding_constraints": {"PROCESS": {"name": "memory", "builders": 3}}`.
At 32 GiB host RAM (memory never binds): `Recommendation: builder-bound
at 8 builder(s)`.

**Verifier HOLD, fixed.** `bga sweep --plane2 <report>` crashed in both
formats: `_finish_capacity_recommendation` read `result.floors` on
`_produce_sweep_output`'s ad-hoc holder, which never sets that
attribute - pre-existing on the text branch, reached in JSON too once
`_attach_plane2_capacity` moved ahead of the format check. Fixed with
`getattr(result, 'floors', None)`.

### Mutations

| # | mutation | reddened | count |
|---|---|---|---|
| 1 | `binding_constraints` comparison forced to always name `builders` | 3 of 9 tests | `pytest -q`: 3 failed |
| 2 | `_peak_concurrent_rss_bytes`'s running sum (`+=` -> `=`) | 2 of 9 | `pytest -q`: 2 failed |
| 3 | `_peak_rss_and_host_memory`'s both-halves gate forced off | 1 of 9 | `pytest -q`: 1 failed |
| 4 | `floors = getattr(...)` reverted to `result.floors` | both CLI-path tests (text + json) | `pytest -q`: 2 failed |

All reverted from copies (never `git checkout --`); each confirmed
green again after restore.

**Deviation (flagged for the session).** `bga/capacity_model.py`'s
queue model (`store/v1` listing, Erlang-C/Allen-Cunneen) carries no
per-element peak RSS and no host RAM at all - only an aggregate
`peak_rss_bytes` distribution per finished run and no memory total to
check it against. Joining memory there needs either a new CLI input
(a third `--capacity N,RATE,MEM` field or a separate flag) or reading a
representative snapshot's host-samples, neither named by the brief;
implementing it un-briefed risked exactly the kind of decision this
track was told to report rather than take. Not implemented; the sweep
side (which the Acceptance Test and guard are both scoped to) is.
