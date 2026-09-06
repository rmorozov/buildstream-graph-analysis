"""UX-729: the export concatenates every viewer module into one scope,
where two top-level declarations of the same name are one declaration
and a caller. `bga/viewer/perfetto_page.js` and `bga/viewer/drawings.js`
both declared `function make`, with different signatures - harmless
only because `_module_order("app.js")` never inlines
`perfetto_page.js`, and `_module_order("perfetto_page.js")` is callable
without any export asking for it (`UX-721`'s Outcome first measured the
collision).

**The decision taken in the task file:** rename, and guard the whole
tree - stronger than a refusal scoped to the bundles the export happens
to build, because that bundle is not the only one `_module_order` can
return.
"""
import collections
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tools.dev_js_deps import declarations

VIEWER = REPO / "bga/viewer"


def _modules():
    return sorted(VIEWER.glob("*.js"))


def _owners(modules=None):
    """`{name: [modules that declare it]}` over every top-level
    declaration - the property the task guards is tree-wide, not just
    over what `app.js`'s own bundle happens to inline."""
    owners = collections.defaultdict(list)
    for path in modules if modules is not None else _modules():
        for decl in declarations(path):
            owners[decl["name"]].append(path.name)
    return owners


class TestNoTwoModulesShareATopLevelName:
    """The property: `_module_order` can return any module as an entry
    point, and every bundle it can build must be flattenable."""

    def test_the_tree_is_twenty_two_modules(self):
        """The population, asserted where the collision count is read -
        an empty walk would pass the clause below for the wrong reason."""
        assert len(_modules()) == 22

    def test_no_name_has_two_owners(self):
        owners = _owners()
        collisions = {name: sorted(set(mods)) for name, mods in owners.items()
                      if len(set(mods)) > 1}
        assert collisions == {}, (
            f"top-level name(s) declared by more than one viewer module, "
            f"which the export would concatenate into one: {collisions}")

    def test_the_known_collision_is_closed(self):
        """`drawings.js:108` and `perfetto_page.js:57` both declared
        `make`, with different signatures - `_module_order`'s
        `perfetto_page.js` bundle would have kept only the second.
        `perfetto_page.js`'s is renamed `makeNode`."""
        owners = _owners()
        assert owners["make"] == ["drawings.js"]
        assert "makeNode" not in owners or owners["makeNode"] == ["perfetto_page.js"]

    def test_the_walk_reaches_every_module(self):
        """Vacuity: a walk that silently skipped a file would pass the
        clause above for having read nothing to collide."""
        owners = _owners()
        seen = {module for mods in owners.values() for module in mods}
        assert seen == {path.name for path in _modules()}
