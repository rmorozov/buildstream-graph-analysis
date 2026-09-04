# UX-630: two environment variables no inventory sees

**Priority:** Medium | **Status:** 🔴 Open | **Depends on:** UX-326 (the tool's sentences are contracts) | **Found by:** architecture review 15 | **Serves:** anyone trying to find out what changes bga's output | **Topic:** docs

## Motivation

Two environment variables landed this window, both input surfaces:

```text
BGA_RATE            bga/report/rate.py:30           changes what whatif prints
BGA_REQUESTED_AT    tools/_run_context_common.py:258  changes what a capture publishes
```

Of the eight `BGA_*` names in `bga/` and `tools/`, **six** appear in
no document outside `docs/backlog/` and `docs/audits/`. Only
`BGA_NO_PROGRESS` and `BGA_INTERRUPT_GRACE_SECONDS` do.

`rate.py:22` chose an environment variable on the grounds that it
*"costs no help line"* — which is the same reason `bga --help`, the
inventory the architecture review's own checklist item 4 uses, cannot
report it. The choice and the blind spot are one decision.

## Required Fix

An environment-variable surface a reader can find, and an inventory
that reads the tree rather than `--help`, so a variable added without
a flag still appears.

## Out of Scope

- Whether these two should be flags instead — a separate argument.

## Acceptance Test

A new `BGA_*` name in `bga/` or `tools/` with no documented home,
reddening a guard.
