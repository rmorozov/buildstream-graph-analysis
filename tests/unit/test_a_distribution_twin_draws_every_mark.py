"""UX-827: a distribution's twin is one row per published mark (§2f).

Round 115 measured the 1,202-element export: `blast_radius_distribution`
publishes n, min, max, nine deciles, p95 and p99 - sixteen marks - and
the twin drew five. The mean was not published at all. `twinRows` in
`bga/viewer/drawings.js` now lists min, the deciles, p95, p99, max,
mean, n in the population's order; this reads it through node, and the
booted export once, on the section the measurement named.
"""
import json
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

FULL = {"n": 1202, "min": 0, "max": 1201,
        "deciles": {f"p{s}": s for s in range(10, 100, 10)},
        "p95": 575, "p99": 900, "mean": 68, "is_flat": False}
ORDER = ["min", "p10", "p20", "p30", "p40", "median", "p60", "p70",
         "p80", "p90", "p95", "p99", "max", "mean", "n"]

_HARNESS = """
const { marksOf, twinRows } = await import("./bga/viewer/drawings.js");
const rows = twinRows(marksOf(%s), (v) => String(v));
console.log(JSON.stringify(rows.map(([name]) => name)));
"""


def _labels(distribution):
    result = subprocess.run(
        [node, "--input-type=module", "-e", _HARNESS % json.dumps(distribution)],
        capture_output=True, text=True, cwd=str(REPO), timeout=60)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@needs_node
class TestTheTwinListsEveryMark:
    def test_a_full_shape_is_fifteen_rows_in_order(self):
        assert _labels(FULL) == ORDER

    def test_an_unpublished_mark_is_no_row(self):
        thin = {"n": 12, "min": 1, "max": 9}
        assert _labels(thin) == ["min", "max", "n"]


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
class TestTheBootedExportAgrees:
    def test_the_blast_twin_has_one_row_per_mark(self, tmp_path):
        """The section round 115 measured, on the run it measured it on."""
        export = pages.export_uri(pages.scale_run(tmp_path), tmp_path)
        with Browser(find_chrome()) as browser:
            got = browser.measure(export, """
              (() => {
                const twin = document.querySelector(
                  '[data-section="blast_radius_distribution"] [data-role="drawing-twin"]');
                return twin ? [...twin.querySelectorAll('tbody tr')]
                  .map((r) => r.cells[0].textContent) : null;
              })()""")
        assert got == ORDER, got
