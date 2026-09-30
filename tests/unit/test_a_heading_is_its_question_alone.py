"""UX-1147: one question per heading, and a heading's name is its question.

No two headings share text; no chapter or section heading holds its fold,
its reader chip or its JSON toggle; no finding title ends in a colon,
shouts a word, or capitalises one mid-sentence (styleguide §6e.1, §6e.3).
At 390 px a section heading's controls take their own row: every drawn h3
spans at least 80% of its section's content width and is no taller than
its text laid out at that full width.
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


#: A heading's share of its section's content box at 390 px; the fold beside it is the rest.
_SHARE = 0.8

_SQUEEZE = r"""
(() => {
  const out = [];
  for (const h of document.querySelectorAll("section[data-section] h3")) {
    if (!h.getClientRects().length) continue;
    const sec = h.closest("section[data-section]");
    const cs = getComputedStyle(sec);
    const content = sec.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight);
    const probe = document.createElement("div");
    const hs = getComputedStyle(h);
    for (const p of ["font", "letterSpacing", "wordSpacing", "lineHeight", "textTransform"]) probe.style[p] = hs[p];
    Object.assign(probe.style, {position: "absolute", visibility: "hidden", width: `${content}px`, overflowWrap: "normal"});
    probe.textContent = h.textContent;
    document.body.append(probe);
    const needs = probe.getBoundingClientRect().height;
    probe.remove();
    const r = h.getBoundingClientRect();
    out.push({id: sec.id, width: r.width, height: r.height, content, needs});
  }
  return out;
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
        measured = opened.measure(uri, _MEASURE)
        measured["compact"] = opened.measure(uri, _SQUEEZE, width=390, height=844)
        return request.param, measured


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

    def test_at_390_a_heading_has_its_sections_width(self, drawn):
        label, measured = drawn
        heads = measured["compact"]
        narrow = {h["id"]: f"{h['width']:.0f}/{h['content']:.0f}" for h in heads if h["width"] < _SHARE * h["content"]}
        assert len(heads) > 10 and narrow == {}, (label, len(heads), narrow)

    def test_at_390_a_heading_is_no_taller_than_its_text(self, drawn):
        label, measured = drawn
        tall = {
            h["id"]: f"{h['height']:.0f}>{h['needs']:.0f}" for h in measured["compact"] if h["height"] > h["needs"] + 1
        }
        assert tall == {}, (label, tall)
