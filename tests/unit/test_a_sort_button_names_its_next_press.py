"""UX-1279: a sort button's name is "Sort by <column>, <order a press applies>: <table>".

On macro_micro's by_binary and elements tables, each label names the order its press gives, which is the
th's aria-sort after one press; a second press flips both.
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

TABLES = ("by_binary", "elements")

_PRESS = (
    r"""
(async () => {
  for (const b of document.querySelectorAll("section.chapter")) b.setAttribute("data-open", "true");
  const turn = () => new Promise((done) => setTimeout(done, 80));
  const out = {};
  for (const key of KEYS) {
    const table = document.querySelector(`table[data-table="${key}"]`);
    const heads = () => [...table.querySelectorAll("thead tr:first-child > th")]
      .filter((th) => th.querySelector("button.th-sort"));
    const read = (th) => ({ text: th.querySelector("button").textContent.trim(), quantity: th.hasAttribute("data-quantity"),
      label: th.querySelector("button").getAttribute("aria-label"), sort: th.getAttribute("aria-sort") });
    const rows = [];
    await turn();
    for (let i = 0; i < heads().length; i += 1) {
      const rest = read(heads()[i]);
      heads()[i].click();
      await turn();
      const once = read(heads()[i]);
      heads()[i].click();
      await turn();
      rows.push({ rest, once, twice: read(heads()[i]) });
    }
    out[key] = rows;
  }
  return out;
})()
"""
).replace("KEYS", str(list(TABLES)))

_LABEL = re.compile(r"^Sort by (?P<column>.+), (?P<order>ascending|descending): (?P<table>.+)$")


@pytest.fixture(scope="module")
def pressed(tmp_path_factory):
    uri = pages.pages(tmp_path_factory, "ux1279", ("macro_micro",))["macro_micro"]
    with Browser(chrome) as browser:
        return browser.measure(uri, _PRESS, 1440, 900)


def _order(state):
    found = _LABEL.match(state["label"])
    assert found, state
    return found["order"]


@needs_browser
@pytest.mark.parametrize("key", TABLES)
def test_a_label_names_its_column_and_its_table(pressed, key):
    rows = pressed[key]
    assert len(rows) >= 2, rows
    for row in rows:
        found = _LABEL.match(row["rest"]["label"])
        assert found and found["column"] == row["rest"]["text"], row
        assert found["table"] == key.replace("_", " ").capitalize(), row


@needs_browser
@pytest.mark.parametrize("key", TABLES)
def test_the_named_order_is_the_one_a_press_applies(pressed, key):
    for row in pressed[key]:
        assert row["once"]["sort"] == _order(row["rest"]), row
        assert _order(row["rest"]) == ("descending" if row["rest"]["quantity"] else "ascending"), row
    assert any(row["rest"]["quantity"] for row in pressed[key]) or key == "by_binary", pressed[key]


@needs_browser
@pytest.mark.parametrize("key", TABLES)
def test_a_second_press_flips_the_label_and_the_sort(pressed, key):
    for row in pressed[key]:
        assert row["twice"]["sort"] == _order(row["once"]), row
        assert row["twice"]["sort"] != row["once"]["sort"], row
        assert row["twice"]["label"] != row["once"]["label"], row
