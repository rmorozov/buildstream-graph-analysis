"""UX-337: the viewer is modules a person can hold, in an order that holds.

Two files carried half the viewer between them - `app.js` at 2,752
lines and `views.js` at 2,531, 5,283 of 9,603 - so every edit to either
paid a long read first. Splitting them is a pure move, and the reason
it was worth a guard rather than a commit message is the machinery
underneath:

`tools/bga_view.py::_module_order` walks `import` lines from `app.js`
and concatenates the modules in the order it derives, because an export
opens over `file://` where a relative `import` is refused.
`_inline_module` then strips `export ` and blanks the imports, and the
whole premise is *what a module imported is now declared above it*.

`UX-199` is on file because that premise broke: the export defined none
of `renderBand`, `renderTrend` or `renderBlastSearch` while calling all
three, threw a `ReferenceError` in `boot()`, and rendered an **empty**
report for several rounds.

Two ways this split could reintroduce it, neither of which the existing
guards see:

- **a cycle.** `walk()` adds a module to `seen` *before* recursing, so a
  cycle does not hang - it silently emits an order in which a module
  precedes something it imports. The concatenated blob then references
  a `const` in its temporal dead zone, and the page is empty again.
- **a re-export.** `export * from "./x.js"` and a bare
  `export { a, b };` are invisible to `_IMPORT_RE` and survive
  `_inline_module` verbatim. The tidy shape - keep `views.js` as an
  index and re-export the chapters through it - produces an export that
  never inlines the new modules at all.

So the clauses below assert the order is a real topological order of
the import graph, that the graph has no re-export form the walker
cannot see, and that no module has grown back past the size that
started this.
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
VIEWER = REPO / "bga/viewer"

# `UX-337`'s acceptance line. Not a style preference: `app.js` and
# `views.js` were 2,752 and 2,531 when the item was filed, and the whole
# point of the split is that no module goes back there.
LINE_CEILING = 1_500


def _modules():
    return sorted(path.name for path in VIEWER.iterdir()
                  if path.suffix == ".js")


def _imports(name):
    """The modules `name` imports, read the way the export reads them."""
    import tools.bga_view as view

    text = (VIEWER / name).read_text(encoding="utf-8")
    return [match.group(1) for match in re.finditer(view._IMPORT_RE, text)]


class TestNoModuleIsTooLongToRead:

    def test_every_viewer_module_is_under_the_ceiling(self):
        over = {name: len((VIEWER / name).read_text(
                    encoding="utf-8").splitlines())
                for name in _modules()}
        over = {name: n for name, n in over.items() if n > LINE_CEILING}
        assert over == {}, (
            f"viewer module(s) over UX-337's {LINE_CEILING}-line ceiling: "
            f"{over}. This is the condition the item was filed for - two "
            f"files holding half the viewer between them")


class TestTheOrderTheExportInlinesIn:

    def test_every_module_comes_after_everything_it_imports(self):
        """The premise `_inline_module` rests on, asserted directly.

        `walk()` guards recursion with `seen`, so a cycle emits an
        order rather than hanging. What it emits puts one of the two
        modules before something it imports, and the export then reads
        a `const` before its declaration - `UX-199`'s empty page.
        """
        import tools.bga_view as view

        order = view._module_order()
        at = {name: index for index, name in enumerate(order)}
        wrong = []
        for name in order:
            for needed in _imports(name):
                if at.get(needed, len(order)) >= at[name]:
                    wrong.append(f"{name} is inlined before {needed}")
        assert wrong == [], (
            f"the export's module order is not a dependency order: {wrong}. "
            f"Every one of these is a `ReferenceError` in the concatenated "
            f"blob, which is UX-199 exactly")

    def test_the_order_reaches_every_module_app_js_depends_on(self):
        import tools.bga_view as view

        order = view._module_order()
        reachable, frontier = set(), ["app.js"]
        while frontier:
            name = frontier.pop()
            if name in reachable:
                continue
            reachable.add(name)
            frontier.extend(_imports(name))
        missing = sorted(reachable - set(order))
        assert missing == [], (
            f"module(s) the viewer imports that the export never inlines: "
            f"{missing}")

    def test_the_order_names_each_module_once(self):
        import tools.bga_view as view

        order = view._module_order()
        repeated = sorted({name for name in order if order.count(name) > 1})
        assert repeated == [], (
            f"module(s) inlined twice: {repeated}. Every top-level "
            f"declaration in them would be redeclared in one scope")

    def test_everything_inlined_is_also_served(self):
        """The export is not the only consumer of these files.

        `bga view` serves real ES modules and answers 404 for a path
        not in `ASSETS`, so a module that only the inliner knows about
        works in an attached report and breaks the served page.
        """
        import tools.bga_view as view

        unserved = [name for name in view._module_order()
                    if name not in view.ASSETS]
        assert unserved == [], (
            f"module(s) the export inlines that `bga view` will not serve: "
            f"{unserved}")


class TestNoImportFormTheWalkerCannotSee:

    @pytest.mark.parametrize("name", _modules())
    def test_the_module_re_exports_nothing(self, name):
        """`export * from` / `export { a };` are invisible to the walk.

        Both are the natural way to keep `views.js` as an index over the
        chapters that moved out of it, and both produce an export whose
        `_module_order` never mentions the new modules - so the symbols
        are called and never declared.
        """
        text = (VIEWER / name).read_text(encoding="utf-8")
        found = re.findall(r"(?m)^\s*export\s*(?:\*|\{)[^\n]*", text)
        assert found == [], (
            f"{name} re-exports: {found}. `_module_order` walks `import` "
            f"lines and cannot see this, and `_inline_module` leaves it in "
            f"the concatenated blob verbatim")

    @pytest.mark.parametrize("name", _modules())
    def test_every_import_names_a_module_that_exists(self, name):
        missing = [needed for needed in _imports(name)
                   if not (VIEWER / needed).exists()]
        assert missing == [], (
            f"{name} imports module(s) that are not there: {missing}")
