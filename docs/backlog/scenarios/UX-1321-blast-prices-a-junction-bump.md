# UX-1321: `bga blast` on a junction, or a path inside a junctioned project, says it rebuilds nothing

**Priority:** High | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the junction-heavy onboarding walk, 2026-10-03 (`/mnt/project-files/onboarding-walk-2026-10-03/onboarding-walk.md`) | **Serves:** R2, R3 | **Topic:** analysis | **Area:** bga | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_blast_prices_a_junction_bump.py`

## Motivation

Reproduced on the walk's stand-in (`make-acme.sh` in that folder: three projects, local junctions two levels deep, 16 elements, `pkgs/zlib.bst` in all three) at `19f1fd73`, bst 2.8.1.

```text
$ bga blast junctions/platform.bst
  Resolved as a path (it also reads as an element; resolution order is url, path, element)
  Nothing in this run sources it. Touching it rebuilds nothing here.
$ bga blast subprojects/platform/subprojects/base/files/gen/cmake
  Nothing in this run sources it. Touching it rebuilds nothing here.
$ bga blast files/gen/cmake            # the same thing in the top project
  Sourced directly by 4 elements ... Rebuilds 5 elements ... Cost: 17.1 s
```

The truth for the junction is 13 of 16 elements. `sources.json` stores the junctioned source as
`junctions/platform.bst:junctions/base.bst:files/gen/cmake`; the path form never maps to it, and
junction elements have no entry (`bga/blast.py:429` prints the sentence).
`docs/guides/real-project.md` says "a junction bump rebuilds its whole subproject" and that blast
prices a change before you make it.

## Decomposition

Input classes: a junction element named by its element path; the same named by its file path
(`elements/junctions/x.bst`); a nested junction (`a.bst:b.bst`); a path inside a local junction's
checkout; a path inside a nested one; a path under no junction and sourced by nothing (today's
answer stays); a remote (git) junction named by its url.

## Required Fix

A junction is a source of every element behind its prefix: blasting it answers that closure plus
everything downstream, and says it read the name as a junction. A path under a local junction's
checkout maps to its junction-prefixed identity before the lookup. "Rebuilds nothing" is never
printed for a path inside a junction checkout; an unresolvable one says so.

## Out of Scope

A cost for a remote junction's ref bump beyond the elements it rebuilds.

## Acceptance Test

On the stand-in, `bga blast junctions/platform.bst` reports 13 elements rebuilt and the base
subproject path reports the four base elements it sources; a guard holds both on a fixture run
with a junction. Reading taken in this container.

## Outcome

### The gap, measured

At `44afd957`, cwd `/root/walk/jproj`, run `20261003T135337Z`:

```text
$ bga blast junctions/platform.bst --no-cost
  Resolved as a path (it also reads as an element; resolution order is url, path, element)
  Nothing in this run sources it. Touching it rebuilds nothing here.
```

The base path read the same (Motivation). Truth, from `bst show --format '%{name} %{full-key}'`
on a copy before and after appending a line (`keys.sh`, bst 2.8.1): a file in
`subprojects/platform/subprojects/base/files/gen/cmake` moves **13 of 16** keys; a
`subprojects/platform/README` nothing stages moves **0 of 16**.

### The close, measured

```text
$ bga blast junctions/platform.bst
  Resolved as a junction (it also reads as a path, an element; resolution order is junction, url, path, element)
  Read as a junction: every element behind `junctions/platform.bst:` is its source (11 here), so a bump rebuilds at most the closure below
  Rebuilds 16 elements (12 that build, 4 that assemble) of 16 in this build
$ bga blast subprojects/platform/subprojects/base/files/gen/cmake
  Inside the checkout of junction junctions/platform.bst:junctions/base.bst (subprojects/platform/subprojects/base), read as junctions/platform.bst:junctions/base.bst:files/gen/cmake
  Sourced directly by 4 elements: …:pkgs/gcc-libs.bst, …:pkgs/glib.bst, …:pkgs/openssl.bst, …:pkgs/zlib.bst
  Rebuilds 13 elements (10 that build, 3 that assemble) of 16 in this build
$ bga blast subprojects/platform/README
  It is inside the checkout of junction junctions/platform.bst, read as junctions/platform.bst:README, and no source stages it. If it is that project's configuration, `bga blast junctions/platform.bst` prices it.
$ python3 -m pytest -q tests/unit/test_blast_prices_a_junction_bump.py
8 passed
```

The junction answers **16**, not the Acceptance Test's 13: the graph of all four snapshots has
every top-level element downstream of something behind the junction (`pkgs/zlib.bst`
build-depends on base's `toolchain.bst`), so the stated rule (behind the prefix plus downstream)
gives 16 of 16. The 13 is the base path's figure, which the key diff confirms.

### Mutations verified red and reverted (6)

| # | mutation (`bga/blast.py`) | reddened |
|---|---|---|
| M1 | `_as_junction` returns `None` | 3 failed, 5 passed |
| M2 | `_junction_path` never maps into a checkout | 4 failed, 4 passed |
| M3 | the miss falls through to "rebuilds nothing" | 2 failed, 6 passed |
| M4 | `_staging` drops the owning-prefix check | 2 failed, 6 passed |
| M5 | `elements/junctions/x.bst` not read as its element | 1 failed, 7 passed |
| A | `startswith(name + ":")` → `startswith(name)`, against the sibling `junctions/platform.bst-extra.bst` (verifier) | 2 failed, 6 passed |

Restored: 8 passed.
