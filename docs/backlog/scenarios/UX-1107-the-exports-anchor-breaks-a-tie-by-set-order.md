# UX-1107: the export's anchor breaks a tie by set order

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** round 150, the export's anchor read under `PYTHONHASHSEED` 1-4 (2026-09-28) | **Serves:** R1 | **Topic:** viewer | **Area:** tools | **Shape:** mechanical | **Reading:** container

**Guard:** none — named test_the_export_anchor_is_seed_free.py, absent from tests/

## Motivation

`choose_anchor` (`tools/bga_timeline.py:1362`) takes `max` over
`spans.keys() & plane1_elements(...)`, a `set`, so among elements tied
on `longest` the winner is whichever the string hash puts first. On
`24507594`, `UX-530`'s two-plane snapshot over the golden fixture
(`tests/fixtures/golden/mixed_task_kinds`, four elements, six equal
processes each), `render()` in trackevent:

```text
PYTHONHASHSEED=1 anchor=base.bst decoded-sha256=dc8669da98b8
PYTHONHASHSEED=2 anchor=app.bst  decoded-sha256=dc8669da98b8
PYTHONHASHSEED=3 anchor=app.bst  decoded-sha256=dc8669da98b8
PYTHONHASHSEED=4 anchor=app.bst  decoded-sha256=dc8669da98b8
```

The export is equal there only because every element's Plane 1 build
starts the same distance before its processes. With element i's build
at 1.0 + 1.3·i s instead of 1.0 + i, the offset follows the anchor and
two exports of one run differ:

```text
PYTHONHASHSEED=1 anchor=base.bst decoded-sha256=928064ada637
PYTHONHASHSEED=2 anchor=app.bst  decoded-sha256=2d218c1ad77c
PYTHONHASHSEED=3 anchor=app.bst  decoded-sha256=2d218c1ad77c
PYTHONHASHSEED=4 anchor=app.bst  decoded-sha256=2d218c1ad77c
```

Digests are of the decoded export (`test_the_timeline_speaks_perfetto.py`'s
`decode`); the `.gz` bytes also carry an mtime.

## Decomposition

Input classes: elements tied on `longest` with equal and with skewed
Plane 1 starts; one longest element; no element shared by both planes.
Journey: `bga timeline` and `bga view --export`.

## Required Fix

In `tools/bga_timeline.py`: `choose_anchor` orders its candidates
before `max`, so a tie on `longest` goes to the first uid in sorted
order under every seed. Nothing else changes.

## Out of Scope

Choosing a better anchor than the longest span (`UX-298`'s rule).

## Acceptance Test

`tests/unit/test_the_export_anchor_is_seed_free.py`: the skewed
snapshot above, rendered in subprocesses under `PYTHONHASHSEED` 1-4,
names one anchor and decodes to one export. Mutation: restore `max`
over the unordered set, and seed 1's `base.bst` against 2-4's `app.bst`
reddens.
