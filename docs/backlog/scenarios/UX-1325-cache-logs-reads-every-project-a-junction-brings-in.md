# UX-1325: `bga cache-logs PROJECT` reads only the top project's logs and says nothing about the junctioned projects beside them

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R1, R3 | **Topic:** analysis | **Area:** tools | **Shape:** judgement | **Reading:** container

**Guard:** none — open, no guard named yet

## Motivation

Reproduced on the walk's stand-in (`make-acme.sh` in that folder: three projects, local junctions two levels deep, 16 elements, `pkgs/zlib.bst` in all three) at `19f1fd73`, bst 2.8.1. BuildStream writes logs per project (`~/.cache/buildstream/logs/acme-os`, `acme-platform`, `acme-base`).

```text
$ bga cache-logs .
Read 11 log(s), 5 of them builds, from acme-os
  apps/browser.bst ... pkgs/zlib.bst ... apps/editor.bst ... apps/shell.bst
```

4 of 13 building elements; nothing names the two skipped projects. On carbonOS those would be
`carbonOS-bootstrap` and `freedesktop-sdk`.

## Decomposition

Input classes: a project with no junction (today); local junctions (project name in the checkout's
`project.conf`); nested junctions; a remote junction whose name is only known to `bst`; a junction
whose project has no logs yet. Surfaces: `bga cache-logs PROJECT_DIR`, `--list`, `--project`.

## Required Fix

Given a project directory, cache-logs resolves the project names of every junction it can read
(local checkouts' `project.conf`, recursively) and reads those log trees too, element names
carrying their junction prefix; a junction whose project name it cannot resolve is named in one
line with `--project` as the way to add it.

## Out of Scope

Resolving remote junctions' names without `bst`.

## Acceptance Test

On the stand-in, `bga cache-logs .` reads all three projects and reports 13 building elements
with junction-qualified names; a guard over a three-project log tree fixture asserts it. Reading
taken in this container.

## Outcome
