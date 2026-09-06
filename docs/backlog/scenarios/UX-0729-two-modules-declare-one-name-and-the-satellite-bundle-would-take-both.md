# UX-729: two modules declare one name, and the satellite bundle would take both

**Priority:** Low | **Status:** 🔴 Not Started | **Depends on:** UX-721 (the same flattening, its other edge), UX-199 (which derived the order) | **Serves:** anyone who inlines a second entry point | **Topic:** viewer | **Shape:** judgement | **Area:** tools

## Motivation

`UX-721` refused the aliased import because the export concatenates the
modules into one scope. That scope has a second way to break, and it is
already true of the tree — measured over the 22 viewer modules' own
top-level declarations:

```console
$ # every `export`ed / top-level function|const|let|class, by owner
modules 22   top-level names 393
collisions {'make': ['drawings.js', 'perfetto_page.js']}

$ python3 -c "from tools.bga_view import _module_order; print(_module_order('perfetto_page.js'))"
['perfetto.js', 'primitives.js', 'format.js', 'controls.js', 'questions.js',
 'drawings.js', 'views.js', 'element.js', 'perfetto_page.js']
```

Both declare `function make`, with **different signatures** —
`drawings.js:108` takes `(doc, tag, attrs, ...children)` and
`perfetto_page.js:57` takes `(tag, attrs, ...children)`.

Nothing is broken today: the export inlines `app.js`'s bundle only (21
modules, no `perfetto_page.js`), and `perfetto.html` is *served*, where
`<script type="module" src="perfetto_page.js">` gives each module its
own scope and the two `make`s never meet. The finding is that
`_module_order("perfetto_page.js")` is a callable that returns a
bundle which cannot be flattened, and nothing says so.

## Required Fix

Either the export refuses a bundle whose modules declare one name twice
— the same shape as `UX-721`'s refusal, and it would name both modules
— or `perfetto_page.js`'s `make` is renamed and a guard holds the
whole-tree property (no two viewer modules share a top-level name),
which is stronger and costs one rename today. Pick one and say which
in the Outcome; the second is cheaper now and the first survives a
tree that grows a legitimate duplicate.

**The decision, taken here: rename, and guard the whole tree.** One
rename today (`perfetto_page.js`'s `make`, local to that file and
shadowed by `drawings.js`'s four-argument one) buys the stronger
property: **no two viewer modules share a top-level name**, guarded
over all 22 rather than over the bundles the export happens to build.
A refusal at export time would only catch a bundle someone assembles,
and `_module_order("perfetto_page.js")` is callable today without any
export asking for it. The refusal is the right answer for a tree that
grows a legitimate duplicate; this tree has exactly one, and it is not
legitimate — two functions named `make` with different signatures.
Say in the Outcome what the guard costs to run.

## Out of Scope

- Aliased imports. `UX-721` closed that edge and its refusal is the
  model this one follows.
- Making the export inline `perfetto_page.js`. **Declined**: `UX-373`
  settled that the satellite pages are served, and inlining a second
  entry point is a different item with its own byte budget.

## Acceptance Test

A bundle whose modules declare one name twice is refused, naming both
modules — or the property holds tree-wide and a guard reads it.
Mutation: give a second module a name the first declares — red,
naming both.

## Outcome

**The gap, measured.** Re-derived with `tools/dev_js_deps.declarations`
over `bga/viewer/*.js` (the character scanner `derive` already uses,
not a fresh regex):

```console
modules 22   top-level names 394
collisions {'make': ['drawings.js', 'perfetto_page.js']}
```

394, not the file's 393 — a naive line regex over the raw text gives
the same 394, so the one-off is in the earlier measurement, not in the
method; the collision itself matches exactly. `_module_order`, re-run:

```console
$ python3 -c "from tools.bga_view import _module_order; print(_module_order('perfetto_page.js'))"
['perfetto.js', 'primitives.js', 'format.js', 'controls.js', 'questions.js',
 'drawings.js', 'views.js', 'element.js', 'perfetto_page.js']
```

**The close, measured.** `perfetto_page.js`'s `function make(tag, attrs,
...children)` renamed `makeNode`, its only two occurrences (the
declaration and the `renderQuestions(make, options)` call). Re-derived:

```console
modules 22   top-level names 394
collisions {}
```

`perfetto.html` still boots for real: `tests/unit/test_one_page_behind_the_button.py`
(18 tests, real Chrome, `renderQuestions` exercised through `makeNode`)
and `tests/unit/test_the_browser_waits_for_a_condition.py` (10 tests)
both pass unmodified. No other module referenced `make` by name.

**The guard's cost.** `tests/unit/test_no_two_viewer_modules_share_a_top_level_name.py`,
4 tests: **0.08-0.35s** alone, no fixture, no subprocess, no browser —
it reads the 22 files on disk.

**The mutation table.**

| mutation | clause that reds |
|---|---|
| `element.js` gains a top-level `function makeNode` (a name `perfetto_page.js` already declares) — the Acceptance Test's own | `test_no_name_has_two_owners` (names `element.js` and `perfetto_page.js`) + `test_the_known_collision_is_closed` |
| the walk skips `drawings.js` (vacuity: an empty read of one module would pass the no-collision clause for having nothing to collide) | `test_the_walk_reaches_every_module` |

Both applied to a scratch copy and reverted from it, not `git checkout
--`; `__pycache__` cleared before the re-run confirmed green.
