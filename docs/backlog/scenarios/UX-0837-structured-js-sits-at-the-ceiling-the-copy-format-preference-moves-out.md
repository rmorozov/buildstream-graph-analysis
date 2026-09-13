# UX-837: structured.js sits at the ceiling; the copy-format preference moves out

**Priority:** Medium | **Status:** 🟢 Done | **Depends on:** UX-337 (the 1,500-line ceiling), UX-829 (the sixth preset) | **Found by:** round 116, the batch gate | **Serves:** the next viewer change, which lands under the ceiling instead of on it | **Topic:** viewer | **Area:** bga-viewer | **Shape:** mechanical

## Motivation

`UX-829`'s sixth preset put `bga/viewer/structured.js` at 1,502 lines,
and `test_the_viewer_splits_along_its_seams.py` reddened at the round's
gate - `UX-337`'s ceiling, the condition that item was filed for: two
files holding half the viewer between them.

```text
$ wc -l bga/viewer/structured.js
1502
```

## Required Fix

The smallest self-contained group leaves along a derived seam: the
copy-format preference (`UX-280`'s `COPY_FORMAT_KEY`,
`COPY_FORMAT_MIRROR`, `readCopyFormat`, `writeCopyFormat`) moves to
`bga/viewer/viewstate.js`, whose own docstring names storage as the
home of what remembers for one browser. The seam is derived with
`tools/dev_js_deps.py --crossings` before the move and `--order` after
it; `docs/design/architecture.md`'s "Which file owns what" row follows.

## Decomposition

Input classes: an export opened from `file://` with no storage, a
served page with a remembered format, and a page whose 29 copy boxes
mirror one change (`UX-536`); the journey it extends is the reader
copying a table as Markdown into an issue (`UX-280`), unchanged in
behaviour - the guard is the module line count and the derived order.

## Out of Scope

The split of `structured.js` along its other seams (`renderStructured`,
`interrogable`, the preset tables) - declined this round: the ceiling
asks for one move under it, not a new module.

## Acceptance Test

`python3 -m pytest tests/unit/test_the_viewer_splits_along_its_seams.py`
green and `python3 tools/dev_js_deps.py --order bga/viewer` acyclic with
`viewstate.js` before `structured.js`; the export guards green;
mutation: the group back in `structured.js` - the ceiling guard red.

## Outcome

**Gap measured** at the gate (`make test`, 2026-09-13):

```text
E   AssertionError: viewer module(s) over UX-337's 1500-line ceiling: {'structured.js': 1502}
```

**Seam derived**, before the move:

```text
$ python3 tools/dev_js_deps.py --crossings bga/viewer/structured.js --groups '{"copy": [...], "text": [...], "rest": [...]}'
rest <- copy                 COPY_FORMAT_MIRROR readCopyFormat writeCopyFormat
rest <- text                 renderText renderText
```

The copy group needs nothing from the rest; the rest needs its three
names. `--order` after the move: `... viewstate.js questions.js
tables.js shapes.js structured.js ...`, acyclic.

**Close measured:**

```text
$ wc -l bga/viewer/structured.js bga/viewer/viewstate.js
1472  356
$ python3 -m pytest tests/unit/test_the_viewer_splits_along_its_seams.py tests/unit/test_the_report_is_read_not_decoded.py tests/unit/test_the_value_rule_has_a_home.py tests/unit/test_a_table_cell_obeys_the_value_rule.py tests/unit/test_the_graph_is_derived_not_guessed.py -q
117 passed
$ python3 -m pytest tests/unit/test_the_report_you_can_attach.py tests/unit/test_the_perfetto_handoff.py tests/unit/test_the_json_toggle_carries_the_key.py -q
120 passed, 1 skipped
```

eslint clean (`npx --yes --package eslint@9 --package globals@17 -- eslint bga/viewer`).

| mutation | result |
|---|---|
| the pre-move `structured.js` restored (`git show HEAD:bga/viewer/structured.js`, 1,502 lines) | `test_every_viewer_module_is_under_the_ceiling` red: `{'structured.js': 1502}` |

Restored from the moved copy, 49 passed.

Deviation: none. The architecture map's Verification Log entry is this
item's, so the log guard's anchor is the commit that re-grounds it.
