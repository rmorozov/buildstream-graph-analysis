"""UX-665: a control class or a folding table lands declared.

Round 79's control walk cost 336k tokens re-deriving the page's
census by hand; round 90 asked for the class registry so the next
walk reads it instead. `REGISTRY` is `dev_page_census.py`'s own
output on `golden` and `macro_micro`, by selector - a class either
page grows that is not here is exactly what round 77 had to
re-discover, and this reds naming it.

`golden` and `macro_micro` publish no shared resource and fold no
table (`UX-532`'s own defect: it stayed green through the row-
migration bug because no fixture had one), so the nested-table clause
runs `pages.shared_resource_run` too - the fixture that shape needs,
not a fixture that merely could have one.
"""
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

import tools.dev_page_census as census_tool
from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: `selector -> (label pattern, the styleguide section or item that
#: owns it)`. Measured with
#: `python3 tools/dev_page_census.py <export.html>` on `golden` and
#: `macro_micro` - 26 classes, one union, document-wide (the rail's
#: stepper and jump box are not inside `main`, and the first draft's
#: `main`-scoped census missed both - the falsify mutation below is
#: what found it). A pattern rather than a literal label:
#: `button.copy-rows` says "Copy 5 rows" on one page and "Copy 3 rows"
#: on the other, and the row count is not the claim.
REGISTRY = {
    "a": (r".+", "UX-216"),                    # a plain citation link
    "a.element": (r".+", "UX-216"),            # a generic element-name link
    "a.inspect": (r"^⌕$", "§1a"),               # bga:role's generic Inspect link
    "a.path-box": (r".+", "§3c"),              # the critical chain, folded
    "a.why": (r"^why$", "UX-207"),             # links a top action to its finding
    "button": (r".+", "§4d"),                  # the Perfetto handoff button
    "button.chapter-open": (r"^Show \d+ sections?$", "§3c"),
    "button.collapse": (r"^[▾▸]$", "§3c"),
    "button.copy-rows": (r"^Copy \d+ rows?$", "§3d"),
    "button.copy-sql": (r"^Copy ", "§4c"),
    "button.copy-step": (r"^Copy command$", "§4c"),
    "button.copy-view": (r"^Copy ", "§4c"),
    "button.describe": (r"^\?$", "§2b"),       # the described-value affordance
    "button.focus-this": (r"^Focus", "§4c"),
    "button.json-toggle": (r"view as JSON", "§1"),
    "button.mark-this": (r".+", "§4c"),
    "button.twin-toggle": (r"^as (table|drawing)$", "§2a"),
    "button[data-all]": (r".+", "§3c"),        # Collapse all / Expand all
    "button[data-step]": (r".+", "§3c"),       # the Top/Prev/Next stepper
    "input.copy-markdown": (r".*", "§4c"),
    "input.table-filter": (r".+", "§3d"),
    "input.th-filter": (r"^threshold for ", "§3d"),
    "input[type=checkbox]": (r".*", "UX-219"),  # the what-if boxes
    "input[type=search]": (r".+", "UX-223"),    # the jump box
    "select.preset-view": (r".+", "§3d"),
    "select.top-n": (r".+", "§3d"),
}


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def censuses(tmp_path_factory, browser):
    """`{label: census}` for the two committed fixtures plus the fixture
    `UX-532`'s shape needs - one browser, one boot per page."""
    booted = pages.pages(tmp_path_factory, "control-registry")
    shared = pages.shared_resource_uri(
        tmp_path_factory.mktemp("control-registry-shared"))
    out = {label: census_tool.census(uri, browser)
           for label, uri in booted.items()}
    out["shared_resource"] = census_tool.census(shared, browser)
    return out


@needs_browser
@pytest.mark.medium
class TestEveryControlClassIsDeclared:
    def test_every_measured_class_is_in_the_registry(self, censuses):
        undeclared = sorted({
            control["selector"]
            for label in pages.FIXTURES
            for control in censuses[label]["controls"]
            if control["selector"] not in REGISTRY})
        assert not undeclared, (
            f"undeclared control class(es), add a REGISTRY row naming "
            f"the owning section: {undeclared}")

    def test_a_declared_label_still_matches_what_is_measured(self, censuses):
        mismatched = []
        for label in pages.FIXTURES:
            for control in censuses[label]["controls"]:
                pattern = REGISTRY.get(control["selector"], (None, None))[0]
                if pattern and not re.search(pattern, control["label"]):
                    mismatched.append(
                        (label, control["selector"], control["label"]))
        assert not mismatched, (
            f"a declared class's label no longer matches its pattern: "
            f"{mismatched}")

    def test_the_registry_is_not_wider_than_what_is_measured(self, censuses):
        """A row for a class neither page grows any more is drift the
        other way - undetectable, because nothing reds on it."""
        measured = {control["selector"]
                   for label in pages.FIXTURES
                   for control in censuses[label]["controls"]}
        stale = sorted(set(REGISTRY) - measured)
        assert not stale, f"registry row(s) for no measured class: {stale}"

    def test_a_table_whose_cells_fold_is_enumerated(self, censuses):
        """`UX-532`'s shape. `golden` folds nothing; `macro_micro` folds
        two sections already; the built fixture is the one whose whole
        reason to exist is `resource_blast`'s sixty rotating rows."""
        assert censuses["golden"]["tables_with_nested"] == []
        assert censuses["macro_micro"]["tables_with_nested"], (
            "macro_micro should already enumerate a folded nested table")
        sections = {row["section"]
                   for row in censuses["shared_resource"]["tables_with_nested"]}
        assert "resource_blast" in sections, (
            f"the fixture built for UX-532's shape enumerated no nested "
            f"table where it should: "
            f"{censuses['shared_resource']['tables_with_nested']}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
