# UX-142: doctor fails every project not named all.bst

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-125 (done — this is its flagship check's blind spot)

## Motivation

`bga doctor`'s `project-loads` check runs
`bst show --deps none --format %{name} all.bst` — **hardcoding the
target**. Any project without a top-level `all.bst` (which is
essentially every real project, freedesktop-sdk included) gets
`[FAIL] project-loads: the project does not load` and exit 1, on a
perfectly healthy project, from the exact command the walkthrough
tells a new user to run first. It passes in CI and in its own
verification log only because all nine `examples/*` ship an `all.bst`
— a fixture convention read back as a world fact. No test covers a
project without one.

The irony is the point: the tool built to front-load environment
failures ships a false failure of its own on first contact with
reality.

## Required Fix

Make the load probe target-agnostic: enumerate `elements/*.bst` (or
the project's declared element-path) and `bst show --deps none` a
discovered element, falling back through the list on per-element
errors so one broken element does not condemn the project; if nothing
can be probed, WARN with "no element found to probe" rather than FAIL.
The plugin two-cause diagnosis stays attached to whatever error the
probe surfaces. Add the missing test: a healthy fixture project whose
only element is not `all.bst` must exit 0.

## Out of Scope

- Any other check (verified real this round).

## Acceptance Test

`bga doctor` on a copy of `examples/06` with `all.bst` renamed exits 0
with `project-loads` ok; on the fdsdk checkout the capture workflow
already has, doctor exits 0 (wire it as a workflow step so the check
meets a real project every capture); the plugin-diagnosis cases still
produce their two distinct remedies.
