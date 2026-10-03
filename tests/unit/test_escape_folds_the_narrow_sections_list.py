"""UX-998 (round 169, walk seed 4): Escape folds the open narrow Sections list.

Styleguide §4c: Escape leaves what the keyboard opened, and focus
returns to the control that opened it. Measured before, at 390x844 on
`macro_micro`: Toggle open, Escape -> `data-folded="false"`, focus kept.
"""

import pytest

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: Open the rail with a real press on its toggle, and put focus on START.
_OPEN = r"""
(() => {
  const title = document.querySelector("nav.toc .toc-title");
  if (!title.disabled) title.click();
  const start = START === "title" ? title : document.querySelector("nav.toc ul a[href^='#']");
  start.focus();
  return null;
})()
"""

_READ = r"""
(() => {
  const nav = document.querySelector("nav.toc");
  const a = document.activeElement;
  return { folded: nav.getAttribute("data-folded"), focus: a && a.className,
           expanded: nav.querySelector(".toc-title").getAttribute("aria-expanded") };
})()
"""


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    return pages.export_uri(pages.FIXTURES["macro_micro"], tmp_path_factory.mktemp("escape-rail"))


@pytest.fixture(scope="module")
def browser():
    if chrome is None:
        pytest.skip(NO_BROWSER)
    with Browser(chrome) as opened:
        yield opened


def _journey(browser, page, start, width, height):
    steps = [
        {"wait": 100},
        {"read": _OPEN.replace("START", f'"{start}"')},
        {"read": _READ},
        {"key": "Escape"},
        {"read": _READ},
    ]
    return browser.journey(page, steps, width, height)[-2:]


@needs_browser
@pytest.mark.parametrize("start", ["title", "link"])
def test_escape_folds_the_open_list_and_focuses_its_toggle(browser, page, start):
    opened, after = _journey(browser, page, start, 390, 844)
    assert opened["folded"] == "false", opened
    assert (after["folded"], after["expanded"]) == ("true", "false"), after
    assert after["focus"] == "toc-title", after


@needs_browser
def test_escape_leaves_the_wide_rail_open(browser, page):
    opened, after = _journey(browser, page, "link", 1440, 900)
    assert opened["folded"] == after["folded"] == "false", (opened, after)
    assert after["focus"] != "toc-title", after
