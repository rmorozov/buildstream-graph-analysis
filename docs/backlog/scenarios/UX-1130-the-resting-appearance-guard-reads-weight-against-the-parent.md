# UX-1130: the resting-appearance guard reads a weight equal to the parent's as inherited

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** UX-1051 | **Found by:** round 149's bookkeeping ledger, promoted at round 152's sweep | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** mechanical | **Reading:** container

**Guard:** `tests/unit/test_every_control_has_a_resting_appearance.py::test_an_explicit_weight_equal_to_the_ancestors_is_declared`

## Motivation

`tests/unit/test_every_control_has_a_resting_appearance.py`'s weight
half compares a control's computed `font-weight` with its parent's, so
an explicit `font-weight: 600` grade under a 600 ancestor passes as
inherited. The quiet grade also draws at 400 in body text and at 700
where it sits in an `h2`/`h3` (collapse, json-toggle, chapter-open),
and no rule says which is meant.

## Decomposition

Input classes: a quiet-grade control under a 400 ancestor, under a 700 heading, and one with an explicit weight equal to its ancestor's.
Journey: the resting look of every control (styleguide §6d), at 1440x900.

## Required Fix

The guard reads the declared weight (the stylesheet rule that matches
the control) rather than the computed-against-parent comparison. The
styleguide says the quiet grade inherits its context's weight, which is
what the page draws today: no control changes its look.

## Decision

- **Route:** default. No control changes its look; the guard's weight read becomes the declared weight (inline style or any matched stylesheet rule, media-aware); styleguide §6d states the quiet grade inherits its context's weight.
- **Rejected:** giving the quiet grade an explicit weight (changes looks); reading computed-vs-parent (blind to an explicit equal weight).
- **Files:** `tests/unit/test_every_control_has_a_resting_appearance.py`, `docs/design/styleguide.md`. Not `style.css`.
- **Guard:** planted inline `font-weight` equal to each button's parent's; no control may read `inherited`.
- **Mutation:** restore the computed-vs-parent expression in `LOOKS`.
- **Class:** guard-blind-spot (a proxy read).

## Out of Scope

Changing any control's weight.

## Acceptance Test

An explicit `font-weight` on a quiet-grade control under an ancestor of
the same weight reddens the guard. Mutation: compare against the
parent's computed weight again; the planted case passes and the test
reddens.

## Outcome

Gap measured: before, the planted case (explicit weight equal to parent's on every button, macro_micro) read `inherited` for all controls.
Close measured: `python3 -m pytest -n 2 -q tests/unit/test_every_control_has_a_resting_appearance.py` -> 17 passed; no existing control declares a weight.

| mutation | red | count |
|---|---|---|
| `LOOKS` weight back to computed-vs-parent | `test_an_explicit_weight_equal_to_the_ancestors_is_declared` | 1 failed, 16 passed |
