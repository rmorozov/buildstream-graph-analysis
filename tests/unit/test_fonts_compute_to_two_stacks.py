"""UX-1035 (styleguide §4.5): four computed `font-family` values before
this item - `system-ui` and `ui-monospace` (the two declared stacks),
plus `html`'s unstyled UA serif default and an unstyled `input`'s UA
"Arial" - neither a token, both leaking a third and fourth stack onto
the page.

`--font-sans`/`--font-mono` in `style.css`, set on `html` and inherited
onto form controls, close both. This file boots the golden export and
walks every rendered element's computed `font-family`.
"""
import pathlib
import shutil
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from browser import NO_BROWSER, Browser, find_chrome

REPO = pathlib.Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: The two stacks (styleguide §4.5). A third computed value anywhere fails.
STACKS = 2

_WALK = """
(() => {
  const seen = new Set();
  document.querySelectorAll('*').forEach(el => {
    const r = el.getBoundingClientRect();
    if (r.width > 0 && r.height > 0) {
      seen.add(getComputedStyle(el).fontFamily);
    }
  });
  return [...seen];
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def golden(tmp_path_factory):
    from tools.bga_view import export

    run = tmp_path_factory.mktemp("fonts-golden") / "run"
    shutil.copytree(GOLDEN, run)
    (run / "expected_output.json").unlink(missing_ok=True)
    page = tmp_path_factory.mktemp("fonts-golden-page") / "report.html"
    export(str(run), str(page))
    return page.as_uri()


@needs_browser
def test_every_rendered_element_computes_to_one_of_two_stacks(browser, golden):
    families = browser.measure(golden, _WALK)
    assert len(families) == STACKS, families
