"""UX-835 (styleguide §3d): a capped table filters what it sorts.

For every table whose badge reads `N of M`, every sortable column that
carries a declared quantity (`bga:quantity`, read off `data-quantity` -
`buildTable`'s own computed `spec.quantity`, not a guess this file
makes) must carry a filter (`input.th-filter`), or the column's
`bga:columns` entry must declare `filter: false` with a reason - no
column does today, so that clause is currently vacuous.

Round 115 measured `elements` "filters 3, sortable 6" and read that as
compliant; the actual defect was invisible until `data-quantity` (this
task) exposed it: `elementSignalTable`'s join defaulted every
undeclared column's quantity to `"count"` (`?? "count"`, the same
pattern `mapTable`'s record branch already had to unlearn), so
`is_leaf`/`element_kind`/`observed_critical` were flagged quantities
with no filter. `leaf_analysis` declares none and was never at fault.
"""
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: `dev_page_census.py`'s own badge-detection (UX-836): the nearest
#: `.badge` not inside the table itself. Mirrored rather than imported
#: so this reads `data-quantity`/`input.th-filter` per column in the
#: same pass, own-scoped the same way (`UX-532`'s shape).
CAPPED_TABLE_JS = r"""
(() => {
  const main = document.querySelector("main") || document.body;
  const ownThead = (t) => [...t.children].find((c) => c.tagName === "THEAD") || null;
  return [...main.querySelectorAll("table")].map((t) => {
    const wrapper = t.parentElement;
    const badgeEl = wrapper ? [...wrapper.querySelectorAll(".badge")]
      .find((b) => !t.contains(b)) : null;
    const thead = ownThead(t);
    const columns = thead ? [...thead.querySelectorAll("th")].map((th) => ({
      key: th.getAttribute("data-column"),
      quantity: th.getAttribute("data-quantity"),
      filtered: !!th.querySelector("input.th-filter"),
    })) : [];
    return {
      section: t.closest("[data-section]")?.getAttribute("data-section") || null,
      badge: badgeEl ? badgeEl.textContent.trim() : null,
      columns,
    };
  });
})()
"""

CAPPED_BADGE = re.compile(r"^[\d,]+ of [\d,]+$")


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def scale_tables(tmp_path_factory, browser):
    """The 1,202-element run - the one committed-or-built fixture whose
    tables cross the row cap (`UX-349`), reusing `test_a_new_control_
    class_lands_declared.py`'s `scale_census` construction: a
    deterministic `pages.scale_run`, exported and measured once."""
    import tools.bga_view as view

    into = tmp_path_factory.mktemp("filter-sort-scale")
    run = pages.scale_run(into)
    page = into / "scale.html"
    view.export(str(run), str(page))
    return browser.measure(page.as_uri(), CAPPED_TABLE_JS)


@needs_browser
@pytest.mark.medium
def test_a_capped_table_filters_every_declared_quantity_column(scale_tables):
    capped = [t for t in scale_tables if t["badge"] and CAPPED_BADGE.match(t["badge"])]
    assert capped, "no table crossed the row cap on the scale export"
    violations = [(t["section"], t["badge"], c["key"], c["quantity"])
                  for t in capped for c in t["columns"]
                  if c["quantity"] and not c["filtered"]]
    assert not violations, (
        f"a capped table sorts a declared-quantity column with no "
        f"filter (§3d): {violations}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
