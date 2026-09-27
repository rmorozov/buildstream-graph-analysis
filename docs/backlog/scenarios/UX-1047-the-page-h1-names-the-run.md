# UX-1047: the page's one `h1` is the run, or §6e.1 says it is the wordmark

**Priority:** Medium | **Status:** 🔴 Not Started | **Depends on:** — | **Found by:** the second styleguide audit (2026-09-27), styleguide §6e.1, §3i, §4f | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement

## Motivation

Measured on `main` at `814a2db8` on three pages with **both planes**: `macro_micro` (11 elements), and `bga gen-synthetic <d> --store --seed 1` (`--layers 6 --width 12`, 74 elements; `--layers 20 --width 60`, 1,202) with `bga capture report --json <snapshot>/plane2.log --project-dir <d> > <snapshot>/plane2.json`, each exported by `python3 -m tools.bga_view <snapshot>/run --export` and booted through `tests/browser.py` at 1440x900:

```text
h1#wordmark      "bga"                       21px  (--font-h1)
h2.chapter       "Where did the time go?"    21px  (--font-h1, since UX-1018)
header alias     the run's alias and instant  not a heading
```

§6e.1 (binding): "one outline: one `h1` (the run), `h2` a chapter at
`--font-h1`", and its guard's stated clause is "sizes strictly
decreasing by level". §3i: the header holds "a wordmark on the left,
the run's alias and start instant". The page's `h1` is the product's
name, and it is the same size as every chapter title, so the outline's
top is neither the run nor larger than what it heads. §4f has four
sizes, so an `h1` above `--font-h1` needs a fifth or the chapter
drops a step. The guard does not see it:
`test_the_heading_outline_has_three_levels.py` holds `min(h2) >
max(h3)` and never compares `h1` with `h2` - measured equal on all four
pages at both widths - so it is narrower than the rule it cites.

## Decomposition

Input classes: an aliased run, an unaliased run, the served page's run
switcher, the compact header.

## Required Fix

Decide: (a) the header's run alias is the `h1` and the wordmark is not
a heading — §3i's 72 px holds, and `h1` shares `--font-h1` with the
chapter as the one allowed tie; or (b) §6e.1 names the wordmark and
drops "the run". Default, if no decision: (a). Amend §6e.1, §3i and
§4f to one outline.

## Out of Scope

The header's budget (§3i) and the picker.

## Acceptance Test

`test_the_heading_outline_has_three_levels.py` reads the `h1`'s text
against the run's alias, and the size clause the rule states.
Mutation: put `h1` back on the wordmark, and the guard reds.

## Outcome

Not started.
