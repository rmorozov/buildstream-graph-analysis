# UX-1329: The README's real-project install line installs the user's project, and `bga --help` buries doctor, snapshot and view

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R1 | **Topic:** docs | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

README "Use it on your real project" opens with `pip install -e ".[bst]"` under "run from inside
the project", which in the user's project tries to install their project. `bga --help` lists 35
commands; `doctor`, `snapshot` and `view` sit in the bottom "thin aliases" block
(`bga/tools_dispatch.py:146`) beside `release-notes`, a maintainer tool:

```text
capture, analysis and conversion (thin aliases for the programs in
tools/, which remain runnable directly as `python3 -m <module>`):
  ...
  release-notes     Generate a release body from the closed backlog rows  (tools.bga_release_notes)
  gen-synthetic     ...
  snapshot          Capture, analyze and compare - the whole local loop  (tools.bga_snapshot)
  doctor            Check this machine can capture at all  (tools.bga_doctor)
```

Measured on a fresh venv at `19f1fd73`.

## Decomposition

Surfaces: README's real-project block; `bga --help` and bare `bga`. Readers: a newcomer with a
clone of bga beside their project.

## Required Fix

The README install line installs bga's checkout with the `bst` extra from beside the user's
project. `bga --help` opens with a three-line "Start here" naming `doctor`, `snapshot` and `view`
in order; `release-notes` is not listed among user commands.

## Out of Scope

A PyPI wheel; reordering the remaining commands.

## Acceptance Test

`bga --help | head` shows the three first commands; the README install line resolves from a
directory beside the clone; guards hold both. Reading taken in this container.

## Outcome
