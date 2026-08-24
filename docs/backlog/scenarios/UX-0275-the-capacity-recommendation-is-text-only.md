# UX-275: the capacity recommendation is text-only

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-116 | **Serves:** R5 and R7 — the two who consume `analyze/v1` rather than reading it | **Topic:** contracts

## Motivation

Found while documenting the block for `UX-242`, whose Required Fix
assumed `capacity_recommendation` is an `analyze/v1` key a consumer
could "meet in a payload and look up". It is not:

```text
$ bga analyze --schema | jq -r '.properties | keys[]'
attribution  attribution_hints  capacity_verdict  confidence  element_join
element_join_coverage  findings  floors  headline  next_steps  occupancy
pipeline_overhead  plane2_coverage  producer  resource_blast  run_id
run_instance  schema  section  signals  structural  timestamp_agreement
total_duration_us  utilisation  violations

$ bga analyze RUN --plane2 PLANE2.json -f json | jq .capacity_recommendation
null
```

The block is computed (`bga/cli.py:_capacity_recommendation`), rendered
in full by the text report, and dropped on the floor by the JSON
renderer. Its sibling `memory_envelope` — the other half of the same
`--builders` question, computed in the same twenty lines of
`_attach_plane2_capacity` — *is* published, as a key of `correlate/v1`.

So the tool's answer to its own founding question (`UX-09`, `UX-116`:
what should `--builders` and `--max-jobs` be, and which constraint is
the reason) is reachable only by a human reading a terminal. A CI job
that wants to assert "the graph binds below the configured builders" has
to parse the text report, which is the thing `UX-75` exists to make
unnecessary.

This is not a rendering oversight to fix quietly: it is a contract
decision. `analyze/v1`'s versioning rule says an addition does not bump
the version, so publishing it is additive and cheap — but *where* it
belongs is a real question, because `memory_envelope` chose
`correlate/v1` and the two are computed together.

## Required Fix

1. Decide and record which contract carries it — `analyze/v1` beside
   `capacity_verdict`, or `correlate/v1` beside `memory_envelope`. One
   answer, with the reason, not both.
2. Publish it there, with its `constraints` list, `binding_constraint`,
   `recommended_builders`, `change` and `caveat` intact. The caveat is
   load-bearing: a recommendation without it is a number a CI job would
   act on.
3. A guard that the text report and the payload cannot disagree about
   which constraint binds — the failure `UX-83` measured between two
   commands, one level down.

## Out of Scope

- Changing what the recommendation computes. `UX-116` settled that and
  `UX-242` documented it.
- Publishing every other text-only block in one sweep. If the audit
  finds more, they are their own rows; this one is filed because it is
  the answer to the question the tool was built to answer.

## Acceptance Test

`bga analyze RUN --plane2 P -f json | jq .<chosen_key>` returns the
recommendation, `--schema` declares it, and the guard reddens when the
renderer and the text report name different binding constraints.
