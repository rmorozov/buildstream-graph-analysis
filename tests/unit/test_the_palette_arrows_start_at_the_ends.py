"""UX-1227: from no active row, the palette's ArrowDown lands on row 0 and ArrowUp on the last row.

Measured before, golden's jump box typed "bst": one ArrowDown made row 1 active - row 0 was skipped.
"""

import pytest

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

# The box typed, then one arrow key from no active row: the active row's index and the row count.
_ARROW = """(() => {
  const jump = document.getElementById("jump");
  const press = (key) => {
    jump.value = "";
    jump.dispatchEvent(new Event("input", { bubbles: true }));
    jump.value = "bst";
    jump.dispatchEvent(new Event("input", { bubbles: true }));
    jump.dispatchEvent(new KeyboardEvent("keydown", { key, bubbles: true, cancelable: true }));
    const rows = [...document.querySelectorAll(".jump-hits li:not(.palette-group)")];
    return { active: rows.findIndex((li) => li.getAttribute("data-active") === "true"), rows: rows.length };
  };
  return { down: press("ArrowDown"), up: press("ArrowUp") };
})()"""


@pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)
def test_the_palette_arrows_start_at_the_ends(tmp_path):
    """One ArrowDown from rest is row 0; one ArrowUp from rest is the last row."""
    uri = pages.export_uri(pages.FIXTURES["golden"], tmp_path)
    with Browser(find_chrome()) as browser:
        got = browser.measure(uri, _ARROW, 1440, 900)
    assert got["down"]["rows"] > 2, got
    assert got["down"]["active"] == 0, got
    assert got["up"]["active"] == got["up"]["rows"] - 1, got
