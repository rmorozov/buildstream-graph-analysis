"""UX-1147: one question per heading, and a heading's name is its question.

No two headings share text; no chapter or section heading holds its fold,
its reader chip or its JSON toggle; no finding title ends in a colon,
shouts a word, or capitalises one mid-sentence (styleguide §6e.1, §6e.3).
"""

import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome
from tools.dev_rendered_strings import _ACRONYMS

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: Names, not words: a proper noun keeps its capital mid-sentence.
_PROPER = {"Plane", "BuildStream", "Perfetto", "Linux"}

#: Units and symbols are spelled in capitals; a word is not.
_SYMBOLS = {"GB", "MB", "KB", "TB", "LB"}

_MEASURE = r"""
(() => {
  const headings = [...document.querySelectorAll("h1, h2, h3, h4, h5, h6")];
  const text = (node) => node.textContent.replace(/\s+/g, " ").trim();
  return {
    headings: headings.map(text),
    holding: headings
      .filter((h) => h.querySelector("button, .reader-tag, [data-reader-tag]"))
      .map((h) => `${h.tagName} ${text(h).slice(0, 60)}`),
    sectionHeads: document.querySelectorAll("section[data-section] h2, section[data-section] h3").length,
    titles: [...document.querySelectorAll("article.finding .title")].map((t) => {
      const copy = t.cloneNode(true);
      copy.querySelector(".badge")?.remove();
      return text(copy);
    }),
  };
})()
"""


def _run(label, into):
    if label == "two_plane":
        return pages.two_plane_run(into, ("--layers", "8", "--width", "14"))
    return pages.FIXTURES[label]


@pytest.fixture(scope="module", params=["two_plane", "golden", "macro_micro"])
def drawn(request, tmp_path_factory):
    into = tmp_path_factory.mktemp(f"u1147-{request.param}")
    uri = pages.export_uri(_run(request.param, into), into)
    with Browser(chrome) as opened:
        return request.param, opened.measure(uri, _MEASURE)


def _shouted(title):
    words = re.findall(r"[A-Za-z][A-Za-z_]+", re.sub(r"`[^`]*`", "", title))
    return [w for w in words if w.isupper() and w not in _ACRONYMS | _SYMBOLS]


def _mid_capitals(title):
    """Capitalised words that neither open the title nor follow a colon."""
    prose = re.sub(r"`[^`]*`|\([^)]*\)", "", title)
    found = []
    for clause in prose.split(": "):
        words = clause.split()
        found += [
            w for w in words[1:] if re.fullmatch(r"[A-Z][a-z]+", w.strip(",.;-")) and w.strip(",.;-") not in _PROPER
        ]
    return found


@needs_browser
class TestAHeadingIsItsQuestionAlone:
    def test_the_page_has_headings_and_findings(self, drawn):
        label, measured = drawn
        assert measured["sectionHeads"] > 10 and measured["titles"], (label, measured["sectionHeads"])

    def test_no_two_headings_share_text(self, drawn):
        label, measured = drawn
        seen = [h for h in measured["headings"] if h]
        twice = sorted({h for h in seen if seen.count(h) > 1})
        assert twice == [], (label, twice)

    def test_no_heading_holds_its_controls(self, drawn):
        label, measured = drawn
        assert measured["holding"] == [], (label, measured["holding"][:5])

    def test_no_finding_title_ends_in_a_colon(self, drawn):
        label, measured = drawn
        assert [t for t in measured["titles"] if t.endswith(":")] == [], label

    def test_no_finding_title_shouts(self, drawn):
        label, measured = drawn
        assert {t[:50]: _shouted(t) for t in measured["titles"] if _shouted(t)} == {}, label

    def test_no_finding_title_is_title_case(self, drawn):
        label, measured = drawn
        assert {t[:50]: _mid_capitals(t) for t in measured["titles"] if _mid_capitals(t)} == {}, label
