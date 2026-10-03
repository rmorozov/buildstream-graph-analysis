# UX-1326: `bga blast --no-cost` refuses without a snapshot, though `bst show` holds everything it needs

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R1, R3 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_blast_answers_before_the_first_capture.py`

## Motivation

On carbonOS build-meta (316 elements in `groups/core.bst`, 140 junctioned), no snapshot yet:

```text
$ bga blast pkgs/gcc.bst --no-cost
Error: @last names a snapshot and /root/walk/carbon has none yet. `bga snapshot -- bst build TARGET` takes one.
$ bga graph-from-show . groups/core.bst /tmp/carbon-graph.json
Wrote graph.json with 316 elements, 1163 dependencies   (6.6 s)
$ bga rebuild-set /tmp/carbon-graph.json --cut junctions/bootstrap.bst:pkgs/glibc.bst --count-only
216
```

The help says `--no-cost` answers "from the graph and the source inventory alone". A first capture
of such a project takes hours; this is the answer available in seconds.

## Decomposition

Input classes: no snapshot and a loadable project; no snapshot and a project that fails to load
(the `bst show` error, not the alias error); a snapshot present (today). Surfaces: `bga blast
--no-cost`; the alias error in `bga/run_store.py:398`.

## Required Fix

`bga blast --no-cost` with no snapshot builds the graph and source inventory from `bst show` on
the requested target (or the project's default target, named in the output) and answers; the
output says it read the project, not a run.

## Out of Scope

`graph`, `floors` and the other run-reading sections without a snapshot.

## Acceptance Test

On carbonOS, `bga blast junctions/bootstrap.bst:pkgs/glibc.bst --no-cost` with no snapshot answers
with element counts; a guard with a fake `bst show` asserts it. Reading taken in this container.

## Outcome

### The gap, measured

The Motivation's reading at `19f1fd73`; the measured path still refuses the same way, as intended:

```text
$ cd /root/walk/carbon; bga blast junctions/bootstrap.bst:pkgs/glibc.bst
Error: @last names a snapshot and /root/walk/carbon has none yet. `bga snapshot -- bst build TARGET` takes one.
```

### The close, measured

bst 2.8.1 from `/root/walk/venv`, no `.bga` in either project:

```text
$ cd /root/walk/carbon; bga blast junctions/bootstrap.bst:pkgs/glibc.bst --no-cost --target groups/core.bst
  Read from the project, not a run - no snapshot here yet; `bst show` on groups/core.bst
  Resolved as an element (it also reads as a path; resolution order is url, path, element)
  Sourced directly by 1 element: junctions/bootstrap.bst:pkgs/glibc.bst
  Rebuilds 216 elements (202 that build, 14 that assemble) of 316 in the project
  Cost: not measured - no run yet; `bga snapshot -- bst build TARGET` takes one
real 0m7.014s
$ cd /root/walk/carbon; bga blast junctions/bootstrap.bst:pkgs/glibc.bst --no-cost
Error: no snapshot here, and `bst show` could not read the project: bst show failed (exit 255) for targets []: …
pkgs/mozjs.bst: Malformed YAML:
Duplicate key variables at line 35 column 0
Pass --target ELEMENT to read the graph from one element instead.
$ cd <copy of jproj without .bga>; bga blast junctions/platform.bst --no-cost
  Read from the project, not a run - no snapshot here yet; `bst show` on every element in the project (BuildStream's default: project.conf declares no `defaults: targets`)
  Resolved as a junction (…)
$ python3 -m pytest -q tests/unit/test_blast_answers_before_the_first_capture.py
7 passed
```

216 is the walk's `rebuild-set --cut` figure. carbonOS declares no `defaults: targets`, so its
default is BuildStream's own, every element, and `bst show` with no target fails on
`pkgs/mozjs.bst` by itself; the Acceptance Test's no-target reading needs `--target groups/core.bst`.

### Mutations verified red and reverted (7)

| # | mutation | reddened |
|---|---|---|
| N1 | `cmd_blast` never takes the project branch | 5 failed, 1 passed |
| N2 | the project branch taken without `--no-cost` | 1 failed, 5 passed |
| N3 | `--target` ignored | 1 failed, 5 passed |
| N4 | `defaults: targets` not read | 1 failed, 5 passed |
| N5 | the answer does not say it read the project | 3 failed, 3 passed |
| N6 | bst's error not printed | 1 failed, 5 passed |
| E | `no_snapshot` ignores `list_runs`, against a snapshot present (verifier) | 1 failed, 6 passed |

Restored: 7 passed.

### Deviation from the Required Fix

carbon without `--target` does not answer: no `defaults: targets`, and bare `bst show` fails on pkgs/mozjs.bst, so bga prints bst's error and "Pass --target" rather than invent a target. `--target ELEMENT` is a new, undeclared option. The UX-1321 wording and the C901 split landed in this commit. (`cb6c7f71`)
