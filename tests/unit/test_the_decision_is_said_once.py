"""UX-1146: the decision is said once on the landed page.

`#headline` keeps its evidence and leaves the sentence to the decision
panel; `next_steps` is the rail's sub-entry into the panel's list, not a
section; a finding several Why folds name is said once, under the list.
Read on the landed page with the Why folds open; the rail is left out,
because it repeats each heading on purpose (`UX-640`). Styleguide §1e, §5a.
`UX-1262`: the two-plane page is exported with its store, so it carries a comparison.
"""

import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

_MEASURE = (
    pages.FULL_LAYOUT_JS
    + r"""
(() => {
  for (const fold of document.querySelectorAll("#decision details.why-ranked, #decision details.why-shared")) fold.open = true;
  const nav = document.querySelector("nav.toc");
  const saved = nav ? nav.style.display : null;
  if (nav) nav.style.display = "none";
  const text = document.body.innerText;
  if (nav) nav.style.display = saved;
  const sentences = text.split(/(?<=[.?!])\s+|\n+/)
    .map((s) => s.replace(/\s+/g, " ").trim())
    .filter((s) => s.split(" ").length >= 8);
  const sub = document.querySelector('nav.toc [data-toc-sub="next_steps"]');
  return {
    sentences,
    whyFolds: document.querySelectorAll("#decision details.why-ranked").length,
    headlineShown: !!document.querySelector('[data-section="headline"]'),
    nextStepsSection: !!document.querySelector('[data-section="next_steps"]'),
    panelSteps: document.querySelectorAll("#decision li[data-step]").length,
    compareChapter: !!document.getElementById("chapter-compare"),
    railSub: sub && { href: sub.getAttribute("href"), text: sub.textContent,
                      target: !!document.getElementById(sub.getAttribute("href").slice(1)) },
  };
})()
"""
)


def _run(label, into):
    if label == "two_plane":
        return pages.two_plane_run(into, ("--layers", "8", "--width", "14"))
    return pages.FIXTURES[label]


@pytest.fixture(scope="module", params=["two_plane", "golden", "macro_micro"])
def landed(request, tmp_path_factory):
    into = tmp_path_factory.mktemp(f"u1146-{request.param}")
    uri = pages.export_uri(_run(request.param, into), into, store=request.param == "two_plane")
    with Browser(chrome) as opened:
        return request.param, opened.measure(uri, _MEASURE)


@needs_browser
class TestTheDecisionIsSaidOnce:
    def test_the_page_has_a_decision_to_repeat(self, landed):
        label, page = landed
        assert page["headlineShown"] and page["panelSteps"] and len(page["sentences"]) > 10, (label, page)

    def test_the_store_page_draws_its_comparison(self, landed):
        label, page = landed
        assert page["compareChapter"] == (label == "two_plane"), label

    def test_no_long_sentence_appears_twice(self, landed):
        label, page = landed
        seen = page["sentences"]
        assert sorted({s[:90] for s in seen if seen.count(s) > 1}) == [], label

    def test_next_steps_is_the_rails_link_into_the_panel(self, landed):
        label, page = landed
        assert not page["nextStepsSection"], label
        assert page["railSub"] == {"href": "#decision-next", "text": "What should I run next?", "target": True}, label


@needs_browser
def test_the_two_plane_page_shares_a_finding_between_why_folds(tmp_path_factory):
    """The population the shared-paragraph rule is about: two Why folds
    naming one finding, which only the two-plane page has."""
    into = tmp_path_factory.mktemp("u1146-shared")
    uri = pages.export_uri(_run("two_plane", into), into)
    with Browser(chrome) as opened:
        shared = opened.measure(
            uri, r"""[...document.querySelectorAll("#decision .why-shared [data-ranks]")].map((p) => p.dataset.ranks)"""
        )
    assert any(" " in ranks for ranks in shared), shared
