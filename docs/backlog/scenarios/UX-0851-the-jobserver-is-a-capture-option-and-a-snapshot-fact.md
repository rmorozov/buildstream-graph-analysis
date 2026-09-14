# UX-851: the jobserver is a capture option and a snapshot fact

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** UX-841 | **Found by:** round 117, Direction 20 | **Serves:** R4 (the mode travels with the run) | **Topic:** contracts | **Area:** tools | **Shape:** judgement

## Motivation

`--jobserver N` is a tracer flag and `jobserver: N|null` a report
field; `bga capture`, the snapshot and `bga compare` do not know it,
so two captures of one project cannot be told apart by mode on the
page or in the store.

## Required Fix

`bga capture --jobserver auto|N|off` (default off; `auto` sizes the
ceiling to the host's cores minus the builders); the snapshot's
`run_context` records `jobserver` (mode, ceiling, auth style, the
policy table from `UX-846`, the project's `max-jobs`); `bga analyze`
publishes it under `run_context` (additive, `analyze/v6`); `bga
compare` names the mode of each side in its header; the custom-kind
variable names a project needs (`UX-843`'s unknown kind) come from
`variables: {bga-jobserver-env: "MYJOBS=-j"}` beside `bga-foundation`,
validated at extraction like `UX-833`'s map.

## Out of Scope

A `bst` configuration key for the mode - declined: bga runs the
jobserver, BuildStream does not know it exists.

## Acceptance Test

`tests/unit/test_the_snapshot_records_the_jobserver.py`: a capture
with `--jobserver 4` records the block and `compare` prints the mode;
mutation: drop the field from `run_context` - red; the help guard's cap
holds or moves with its reason.
