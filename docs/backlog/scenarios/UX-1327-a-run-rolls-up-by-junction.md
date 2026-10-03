# UX-1327: No report section answers which junction's elements cost the most, and `junction-cost` is about variants

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R3, R5 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_a_run_rolls_up_by_junction.py` over the committed capture `tests/fixtures/nested_junctions/run`

## Motivation

Reproduced on the walk's stand-in (`make-acme.sh` in that folder: three projects, local junctions two levels deep, 16 elements, `pkgs/zlib.bst` in all three) at `19f1fd73`, bst 2.8.1. The report has no grouping by junction prefix. A junction-heavy owner asks which project's
elements dominate the critical path, which junction's elements were built locally rather than
pulled from that project's cache, and what each junction's bump costs. `bga junction-cost @last`
answers a different question:

```text
N separate invocations against one junctioned build: 1 run
  Refused: One run is nothing to join ...
```

## Decomposition

Input classes: no junction (section absent); one junction; nested junctions (each prefix level
its own row, the deepest owning the element); a junction whose elements were all cached. Surfaces:
`analyze` text and json (a new optional key, schema version bump if required), `junction-cost`'s name.

## Required Fix

`bga analyze` prints a "By junction" section when the run has junctioned elements: per junction
prefix, elements, built vs cached, build seconds, share of the critical path, and the blast of a
bump; and one finding when a junction's cache-hit ratio is far below the top project's.
`variant-cost` is added as the command's name, `junction-cost` kept as an alias.

## Out of Scope

The page's rendering of the section.

## Acceptance Test

On the stand-in, `bga analyze @last` prints the three-row section (top project, platform, base)
with element counts 4, 5, 6 building and cached; a guard over a fixture run asserts the rows.
Reading taken in this container.

## Outcome

**Gap measured** at `44afd957`, on the stand-in's cold run
(`/root/walk/jproj/.bga/runs/20261003T135009Z/run`), in this container:

```text
$ python3 -m bga.cli analyze <run> | grep -ci "by junction"        -> 0
$ python3 -m bga.cli analyze <run> --format json | ... 'by_junction' in doc   -> False
$ python3 -m bga.cli variant-cost a b
bga: error: argument COMMAND: invalid choice: 'variant-cost' (choose from ... 'junction-cost' ...)
```

**Close measured**, same run, same container:

```text
$ python3 -m bga.cli analyze /root/walk/jproj/.bga/runs/20261003T135009Z/run
By Junction:

  project / junction                            elements build+asm  built cached    build  on path of path    bump
  acme-os                                              5       4+1      5      0   17.1 s    8.2 s   40.4%       -
    junctions/platform.bst                             5       4+1      5      0   12.0 s     0 ms    0.0%   16/16
      junctions/platform.bst:junctions/base.bst        6       4+2      6      0   21.0 s   12.0 s   59.6%   16/16
```

Truth, from `graph.json` and `trace.json` with no `bga` import: 5/5/6 elements, 4+1/4+1/4+2, all built
(cold), BUILD seconds 17.138/12.020/21.031 (bga's 17.15 s is the same spans on the run's 50 ms
epsilon grid), bump blast 16 and 16. JSON: `by_junction` under `analyze/v7` (an optional addition,
no bump). No `junction-cache-gap` finding: the run is cold. The finding fires at 50 points or more
below the top project's hit share, over 5 elements or more, on an incremental run only;
`nested_junctions` publishes it for `junctions/platform.bst` (0.0% against 80.0%) and not for its
nested base (66.7%). `variant-cost` is the name; `junction-cost` dispatches and is listed in
`variant-cost`'s help line as its old name.

**Mutation table** (`tests/unit/test_a_run_rolls_up_by_junction.py`, 8 tests; reverted: 8 passed):

| mutation | result | reddened |
|---|---|---|
| prefix = before the first `:` | 5 failed, 3 passed | rows, path split, text, finding, caches-off |
| an element counts in every ancestor's row | 4 failed, 4 passed | rows, path split, text, finding |
| bump blast drops nested elements | 1 failed, 7 passed | rows |
| gap 50 -> 10 points | 1 failed, 7 passed | finding (base fires) |
| min elements 5 -> 6 | 1 failed, 7 passed | finding |
| no run-mode gate | 1 failed, 7 passed | caches-off |
| json key dropped | 3 failed, 5 passed | rows, path split, caches-off |
| text section dropped | 1 failed, 7 passed | text |
| built = any task, not BUILD | 2 failed, 6 passed | rows, finding |
| `junction-cost` alias dropped | 1 failed, 7 passed | alias |
| section on an unjunctioned run | 1 failed, 7 passed | unjunctioned |

### Deviation from the Required Fix

`variant-cost` is the command and `junction-cost` its alias. Totals read 5/5/6, not 4/5/6. The verifier held on 3 doc/schema reds and the fixup found 5 more (key-path prose, Part 32.4, reader map R3, CHANGELOG Unreleased, Verification Log); squashed into one commit. The contracts surface is 635 keys with UX-1330's `did_you_mean`. (`7ac2d5b6`)
