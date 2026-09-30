# UX-1168: the rail's mark goes stale when no section enters or leaves

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** round 156's full suite, `test_three_backs_restore_rail_and_chapters` once red (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_the_rail_mark_follows_the_reading_line.py`

## Motivation

In the full suite under load, `test_filter_and_back_state_is_kept_and_told.py::test_three_backs_restore_rail_and_chapters` failed once at `('two_plane', 390)`, `back_twice`: the rail's mark read `change` where it had read `decide`, while `y`, `open` and the hash matched. Alone it passed 3 of 3.

`scrollspy` (`bga/viewer/nav.js`) recomputes the mark only in its `IntersectionObserver` callback, rooted on the whole viewport at `threshold: 0`. A section's top crossing the 15% reading line while no section enters or leaves the screen fires no callback, so the mark keeps the section above it. After Back, an intermediate layout can fire the last callback and the settled position fire none.

## Decomposition

Input classes: `macro_micro` and `golden`, every chapter open, at 1440x900 and 390x844.

## Required Fix

The mark is recomputed whenever a section edge crosses the reading line, by scroll or by layout, with no per-frame layout read.

## Decision

- **A second observer on the line:** `scrollspy` observes the same sections with a zero-height root, `rootMargin: -15% 0px -85% 0px` (derived from `READING_LINE`), and its callback is `mark`. A section starting or stopping straddling the line is exactly what can change "here".
- **Not `scrollend`:** it fires only for a scroll; a fold or a restored layout that moves a section across the line without scrolling would still leave the mark stale. The line observer covers both and reads no layout of its own.
- **Guard:** `tests/unit/test_the_rail_mark_follows_the_reading_line.py`: each section is placed 30px under the line, scrolled 60px, kept only when the set on screen is the same before and after; the mark must name that section.

## Out of Scope

The reading line's position and the `UX-1046` ended-above rule; the Back journey's own guard.

## Acceptance Test

On `macro_micro` at 1440 and 390, a 60px scroll that carries a section's top past the reading line with no section entering or leaving moves the mark to it. Mutation: drop the line observer, and the guard reds.

## Outcome

**Gap measured** - `golden` and `macro_micro` (`pages.export_uri`), every chapter open, Chromium; a scratch `gap.py` running the guard's script, base `b58ffeb4`:

```text
golden 1440       evidence: decision -> decision   findings: overview -> overview   (top 105, line 135)
golden 390        evidence: decision -> decision   overview: evidence -> evidence   findings: overview -> overview   (top 96-97, line 127)
macro_micro 1440  evidence: decision -> decision   findings: overview -> overview   headline: findings -> findings
macro_micro 390   evidence: decision -> decision   overview: evidence -> evidence   findings: overview -> overview
```

11 of 11 crossings with an unchanged on-screen set left the mark on the section above (a 12th started already marked, by `UX-1046`).

**Close measured** - same script, the line observer in:

```text
golden 1440       evidence: decision -> evidence   findings: overview -> findings
golden 390        evidence: decision -> evidence   overview: evidence -> overview   findings: overview -> findings
macro_micro 1440  evidence: decision -> evidence   findings: overview -> findings   headline: findings -> headline
macro_micro 390   evidence: decision -> evidence   overview: evidence -> overview   findings: overview -> findings
page              golden 322,505 -> 322,577 B (+72); with_timeline 342,797 -> 342,869 B (+72)
flaky guard alone test_three_backs_restore_rail_and_chapters x5: 1 passed each (17.2-17.4s)
```

**Mutation table** - `tests/unit/test_the_rail_mark_follows_the_reading_line.py` (1 test), each mutation alone, `nav.js` restored from its copy:

| mutation | reddened | run |
|---|---|---|
| `line.observe(section)` commented out | `test_a_crossing_with_no_section_entering_moves_the_mark` (`'decision' == 'evidence'`) | 1 failed |
| line observer's `rootMargin` `"0px"` (the viewport again) | same (`evidence` / `decision`) | 1 failed |
| both reverted | - | 1 passed |
