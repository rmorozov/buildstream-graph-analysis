"""UX-1187: every element view carries duration and level, and the level filter composes with Top-N.

Measured before, on the 1,202-element run (`--layers 20 --width 60`):
"All elements" had duration and no depth, "What does my element wait on"
depth and no duration.
"""

import pytest

from bga import schemas
from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

SHAPE = ("--layers", "20", "--width", "60")


def test_every_element_view_carries_duration_and_level():
    presets = schemas.schema(schemas.ANALYZE)["properties"]["elements"][schemas.PRESETS]
    short = {
        preset["name"]: sorted({"element", "element_durations", "unweighted_depth"} - set(preset["columns"]))
        for preset in presets
    }
    assert {name: gap for name, gap in short.items() if gap} == {}, short


_TABLE = """(() => {
  const t = document.querySelector('table[data-table="elements"]');
  const shown = [...t.querySelectorAll('tbody tr')].filter((tr) => tr.checkVisibility());
  const raw = (tr, c) => tr.querySelector(`td[data-column="${c}"]`)?.dataset.raw;
  return shown.map((tr) => [raw(tr, 'element'), raw(tr, 'unweighted_depth')]);
})()"""


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
def test_a_level_filter_composes_with_top_n(tmp_path):
    run = pages.two_plane_run(tmp_path, shape=SHAPE, name="big")
    state = "v.elements=All%20elements&t.elements.unweighted_depth=%3D%2012&n.elements=10:element_durations"
    with Browser(find_chrome()) as browser:
        rows = browser.measure(f"{pages.export_uri(run, tmp_path / 'page')}#elements~{state}", _TABLE, 1440, 900)
    assert len(rows) == 10 and {depth for _, depth in rows} == {"12"}, rows
