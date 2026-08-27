# UX-325: --aggregate crashes on every user install

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** UX-234 (the feature), UX-203 (the CI installed-mode lesson this extends) | **Serves:** R1, R5, R7 | **Topic:** store

## Motivation

Round 45's stranger walk, friction 2: `bga snapshot --aggregate` —
named in `docs/README.md` as one of the commands to know — dies
with `ModuleNotFoundError: No module named 'tools.bga_snapshot'`
on a plain `pip install` (bga/store_aggregate.py:506 imports
`from tools.bga_snapshot import store_listing`). The import only
resolves in a contributor checkout, so the feature has never run
once in user mode — the exact class 47a3f83/UX-203 was about (the
wheel ships differently than the checkout), recurring because
CI's installed-mode exercise never grew past the commands it was
written for.

## Required Fix

The import moves inside the package (or `store_listing` does);
and the guard that keeps the class dead: CI's installed-mode job
runs **every documented command** at least to a successful parse
plus one real invocation for those that read fixtures —
mechanically derived from the docs' command inventory (the UX-322
table), not a hand-list that ages.

## Out of Scope

- Restructuring tools/ vs bga/ beyond this import (UX-313's
  boundary questions live elsewhere).

## Acceptance Test

In a scratch venv with plain `pip install .`: `bga snapshot
--aggregate` on a fixture store emits `store-aggregate/v1`
(exit 0); the CI job's command sweep is derived from the
documented inventory and fails if any documented command errors
at parse or on its fixture invocation (mutation: reintroduce the
tools. import → the sweep reds in installed mode).
