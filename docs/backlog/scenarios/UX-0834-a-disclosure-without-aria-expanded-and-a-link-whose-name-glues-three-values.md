# UX-834: a disclosure without aria-expanded, and a link whose name glues three values

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-716 (every control has a resting appearance), UX-532 (the twin) | **Found by:** round 115, the design review | **Serves:** a keyboard or screen-reader user | **Topic:** viewer | **Area:** bga-viewer | **Shape:** mechanical

## Motivation

Two controls differ from every other of their class:

```text
button.twin-toggle "as table"   drawings.js:274   aria-expanded absent (collapse, json-toggle, chapter-open all carry it)
a.path-box                      views.js:1033     three display:block spans, no separator → accessible name "toolchain.bst0.0 simport"
```

## Required Fix

In `bga/viewer/drawings.js` `twin-toggle` carries `aria-expanded`, flipped on the same click
path; in `bga/viewer/views.js` `a.path-box` gets `aria-label` "<element>, <duration>, <kind>".

## Decomposition

Input classes: a drawing with a twin, a critical path with one and
with fifteen boxes; the journey is the timeline handoff's keyboard path.

## Out of Scope

- The twin's default state — closed is right (§2a).

## Acceptance Test

`test_every_control_has_a_resting_appearance.py` extended: every
`button` that toggles a sibling's `hidden` carries `aria-expanded`;
`a.path-box` accessible name contains a separator; mutation: drop
either — red.

## Outcome

**Gap measured**, golden export (`bga view tests/fixtures/golden/mixed_task_kinds
--export`), driven with `tests/browser.py`, before the fix:

```text
twin_before: null  twin_after: null   (aria-expanded absent, click is a no-op on it)
path_box_name:        "base.bst0.0 sunknown"   (textContent, no separator)
path_box_aria_label:  null
```

**Close measured**, same page, same driver, after the fix:

```text
twin_before: "false"  twin_after: "true"   (flips on click, both directions)
path_box_aria_label:  "base.bst, 0.0 s, unknown"
```

**Mutation table** (`tests/unit/test_every_control_has_a_resting_appearance.py`,
class `TestDisclosuresAndLinksAreLegible`, `PYTHONDONTWRITEBYTECODE=1`):

| mutation | reddened | count |
|---|---|---|
| drop `"aria-expanded": "false"` from `twin-toggle` | `test_every_named_disclosure_flips_aria_expanded` | 1 failed, 8 passed |
| drop `box.setAttribute("aria-label", ...)` on `a.path-box` | `test_path_box_name_separates_its_three_values` | 1 failed, 8 passed |

Both reverted from the pre-mutation copy; full file green again (9 passed) after each.
