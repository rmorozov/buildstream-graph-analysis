# UX-1169: accessible names after UX-1162 still miss the drawings' values and three labels

**Priority:** Low | **Status:** 🟢 Done | **Depends on:** — | **Found by:** the round-156 walk (2026-09-30) | **Serves:** R1 | **Topic:** viewer | **Area:** bga/viewer | **Shape:** judgement | **Reading:** container

**Guard:** `tests/unit/test_every_control_and_drawing_names_what_it_shows.py`, `tests/unit/test_the_store_section_takes_a_window.py`

## Motivation

Page: the round-156 walk of the two-plane page (`bga gen-synthetic <d> --store --seed 1 --layers 8 --width 14`, 114 elements) and golden/macro_micro at `b58ffeb4`, Chromium 1440x900 and 390x844.

Chromium `Accessibility.getFullAXTree`, every fold open: 17 drawings, 6 carry a details relation (the six with a visible table twin), 11 carry none: their `aria-details` points at a `display:none` span that holds the values only in its `aria-label`. 46 "View as JSON" names on the two-plane page (33 on golden) end in a raw section key ("View as JSON - critical_path_detail", "- binary_cost") while the heading reads a question. The store-trend "As table" toggle loses its name after "Show all" (`views.js:482`). The chapter button reads "Sections · 4" and its name "4 sections: What if I change this?" lacks the visible label. The filter badge has no `role=status` or `aria-live`, so a typist hears no count.

## Decomposition

Input classes: the two-plane synthetic page, `golden` and `macro_micro`, at 1440 and 390.

## Required Fix

Each drawing's `aria-details` reaches a node the AX tree exposes; "View as JSON" is named by the section's question; the "As table" toggle keeps its name after "Show all"; the chapter button's name contains its visible label; the count is a live region.

## Decision

- **Drawings**: `valueRoute` (`drawings.js`) drops `hidden` and takes `role="note"`; `style.css` clips `[data-role="drawing-values"]` to 1px, so the node is in the tree and off screen, and its values stay in `aria-label` (off `main.textContent`'s word count).
- **"View as JSON"** (`rawjson.js`): the name is `View as JSON: <heading>` / `Hide JSON: <heading>`; the key stays on `title` (`UX-825`).
- **"As table" after "Show all"** (`views.js`): the handler calls `nameDrawing` on the replacement twin, so `aria-details` and the toggle's `aria-labelledby` resolve again.
- **Chapter fold** (`chapters.js` `labelFold`): the name is `Sections · N: <title>`, the visible label first.
- **Filter badge** (`structured.js`): `role="status"`. Naming only; the badge's text and visibility are `UX-1170`'s.
- **Guard**: `UX-1162`'s file extended rather than a parallel `test_the_ax_tree_carries_each_relation.py` (same `Browser.ax` fixture, three pages): `cdp.mjs --ax` now reports each node's `details` relation count; four tests read the tree. The Show-all case needs the served store, so it is one clause in `test_the_store_section_takes_a_window.py` (DOM: the route and both ids resolve).
- **Mutation**: hide one drawing's route; restore the key `aria-label`; the old chapter name; drop `role`; drop the re-route.

## Out of Scope

The visible labels; the names `UX-1162` fixed; the Copy command names (150 characters).

## Acceptance Test

On the two-plane page `getFullAXTree` shows a details relation on all 17 drawings, no "View as JSON" name carries a key, and the badge is a live region. Guard: a new `test_the_ax_tree_carries_each_relation.py` reading the AX tree, not the DOM label. Mutation: point one `aria-details` back at the hidden span, and the guard reds.

## Outcome

**The gap, measured.** Chromium's tree (`Browser.ax`) over the guard's own `_TAG` (chapters open, `#utilisation` and the first question fold, one badged filter typed `zzzz`), the two-plane page (`gen-synthetic --store --seed 1 --layers 8 --width 14`), `83f10ca8`; `probe4.py` in the track's scratch dir.

```text
before.html 1440: drawings 16 with details relation 6; json toggles 46 named by key 46; chapter folds 7 name holds label 0; status badges 0
   e.g. View as JSON — findings | 4 sections: What if I change this?
before.html 390: drawings 16 with details relation 6; json toggles 46 named by key 46; chapter folds 7 name holds label 0; status badges 0
```

**The close, measured.** Same probe, this commit; export `page_bytes` 151,230 -> 151,401 (+171 B).

```text
after.html 1440: drawings 16 with details relation 16; json toggles 46 named by key 0; chapter folds 7 name holds label 7; status badges 3
   e.g. View as JSON: Findings (14) | Sections · 4: What if I change this?
after.html 390: drawings 16 with details relation 16; json toggles 46 named by key 0; chapter folds 7 name holds label 7; status badges 3
```

The walk's 17th drawing reads 17 on one probe run and 16 on the next under the same `_TAG` (a render-timing difference, not a route); both runs read every drawing present with a relation.

**Mutation table.** `PYTEST_XDIST= python3 -m pytest <guard> -q`, one mutation at a time, restored from a saved copy.

| Mutation | Reddened | Run printed |
|---|---|---|
| first column strip's route `hidden = true` (one drawing) | `test_every_drawing_s_details_reach_a_node_the_tree_exposes` x3 pages | 3 failed, 25 passed, 2 skipped |
| `valueRoute` `hidden = true` (every drawing) | same x3 | 3 failed, 25 passed, 2 skipped |
| JSON toggle `aria-label` back to `View as JSON — <key>` | `test_a_json_toggle_is_named_by_its_question_not_its_key` x3 | 3 failed, 25 passed, 2 skipped |
| chapter name back to `N sections: <title>` | `test_a_chapter_fold_s_name_holds_its_visible_label` x3 | 3 failed, 25 passed, 2 skipped |
| badge `role="status"` dropped | `test_a_filtered_table_s_count_is_a_live_region` two_plane, macro_micro | 2 failed, 26 passed, 2 skipped |
| Show-all's `nameDrawing` re-route dropped | `test_after_show_all_..._keeps_its_name` | 1 failed, 11 passed |

A `hidden` route in `element.js`'s history sparkline stayed green (28 passed): no page in the fixture draws it; `test_every_drawing_has_a_name_and_a_data_route.py` holds that site.

**Deviation:** the Acceptance named a new test file; the guard extended `test_every_control_and_drawing_names_what_it_shows.py` instead.
