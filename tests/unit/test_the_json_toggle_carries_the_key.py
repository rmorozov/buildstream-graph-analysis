"""UX-825 (styleguide §4g.2): a payload key is contract vocabulary, not
heading text.

`format.js:353` used to append `span.section-key.muted` beside every
section's `h2`. Measured on the golden export before the fix,
`span.section-key` computed `display != none` on 33 of 47 sections; the
fix moves the key onto the JSON toggle's `title`/`aria-label` and out
of the heading, `data-section` still carrying it for the guards.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: Every `span.section-key` still in the DOM, and every JSON toggle
#: paired with whether its `title`/`aria-label` carries its own key.
_KEYS = """
(() => {
  const spans = [...document.querySelectorAll("span.section-key")];
  const toggles = [...document.querySelectorAll("button.json-toggle")].map((b) => {
    const key = b.getAttribute("data-json-toggle");
    return { key, title: b.title, ariaLabel: b.getAttribute("aria-label") };
  });
  return { spans: spans.length, toggles };
})()
"""


@pytest.fixture(scope="module")
def measured(tmp_path_factory):
    uri = pages.export_uri(pages.FIXTURES["golden"],
                           tmp_path_factory.mktemp("json-toggle-key"))
    with Browser(chrome) as opened:
        return opened.measure(uri, _KEYS, 1440, 900)


@needs_browser
class TestTheKeyStaysOffTheHeading:
    def test_no_section_key_span_is_in_the_dom(self, measured):
        assert measured["spans"] == 0, measured["spans"]

    def test_every_toggle_carries_its_key(self, measured):
        toggles = measured["toggles"]
        assert len(toggles) >= 30, len(toggles)
        missing = [t for t in toggles
                  if t["key"] not in t["title"]
                  or t["key"] not in (t["ariaLabel"] or "")]
        assert not missing, missing
