"""UX-294: every viewer module is named in the map a reader opens.

Found by review 3's checklist item 4 - *what shipped since the last
review that no document names*. The viewer is fifteen ES modules and
the architecture named a handful; `views.js` at 2,400 lines, `nav.js`,
and `viewstate.js` - the fragment contract `UX-211` and `UX-225`
publish links against - appeared in it **zero** times. The reader who
opens `bga/viewer/` was told what the *page* does and had to derive
which file did it.

**Why this guards the map and not "somewhere in docs".** The item's own
acceptance says *named in at least one document under `docs/`*, and by
the time it was implemented that was already true of all fifteen - the
backlog task files and the Verification Log name them in passing. A
guard on it would have been green the day it was written and green
forever after, which is the non-discriminating shape this repository
keeps catching in its own work (`UX-297`'s M2, `UX-312`'s dead
queries). So the rule is the one the item's *Required Fix* asks for:
the architecture carries a map from module to what it owns, and the
map and the directory agree in both directions.

The Python side has had this for many rounds; this is the viewer half
of the same discipline.
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
VIEWER = REPO / "bga/viewer"
ARCHITECTURE = REPO / "docs/design/architecture.md"
HEADING = "### Which file owns what"


def _map():
    """The module -> owns table, as the architecture writes it."""
    text = ARCHITECTURE.read_text(encoding="utf-8")
    assert HEADING in text, (
        f"{ARCHITECTURE.name} has no {HEADING!r} section; the map a reader "
        f"opens `bga/viewer/` with is gone")
    section = text.split(HEADING, 1)[1].split("\n## ", 1)[0]
    rows = {}
    for line in section.splitlines():
        found = re.match(r"^\| .*?`([\w.]+\.(?:js|css))` \| (.+?) \|$", line)
        if found:
            rows[found.group(1)] = found.group(2).strip()
    return rows


def _shipped():
    return {path.name for path in VIEWER.iterdir()
            if path.suffix in (".js", ".css")}


class TestTheMapAndTheDirectoryAgree:

    def test_every_module_has_an_entry(self):
        missing = sorted(_shipped() - set(_map()))
        assert missing == [], (
            f"viewer module(s) the architecture's map does not name: "
            f"{missing}. A reader opening `bga/viewer/` has to derive what "
            f"they own, which is what UX-294 was filed for")

    def test_the_map_names_nothing_that_shipped_out(self):
        extra = sorted(set(_map()) - _shipped())
        assert extra == [], (
            f"the map names module(s) that no longer exist: {extra}. A map "
            f"pointing at a deleted file is worse than none")

    def test_every_entry_says_something(self):
        """A row is a sentence, not a filename repeated.

        The cheapest way to satisfy the two clauses above is a table of
        names with empty cells, which would pass them and help nobody.
        """
        thin = {name: owns for name, owns in _map().items()
                if len(owns) < 25 or owns.strip("`") == name}
        assert thin == {}, (
            f"map entr(ies) that do not say what the module owns: {thin}")

    def test_the_html_is_not_in_the_map(self):
        """`index.html` and the satellite pages are the page's *shell*,
        and the map is about where behaviour lives. Asserted so that
        adding them later is a decision rather than a drift."""
        assert not any(name.endswith(".html") for name in _map())

    @pytest.mark.parametrize("module", sorted(_shipped()))
    def test_each_module_is_named_somewhere_in_the_docs_tree(self, module):
        """The item's own acceptance, kept as the weaker companion.

        It passes today for every module and is expected to - it is
        here so that a module which leaves the map *and* every other
        document at once is caught twice rather than once.
        """
        hits = [path for path in (REPO / "docs").rglob("*.md")
                if module in path.read_text(encoding="utf-8")]
        assert hits, f"{module} is named in no document under docs/"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
