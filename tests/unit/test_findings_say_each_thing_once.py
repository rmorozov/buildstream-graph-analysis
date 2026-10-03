"""UX-1249: the findings say each thing once, and what is at rest is an action.

On `macro_micro` and a 1,202-element two-plane synthetic run: no finding
lists the elements a more severe one listed (the analysis makes them
one; two claims at one severity, or about one element, are two), no
element name is drawn twice in one card outside its step, and a card a
reader lands on carries a step or a priority above Info - an Info card
with no step is folded under "Also noted · N", a note riding its card.

Styleguide §5a.
"""

import base64
import gzip
import json
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

#: The shape whose `blast-radius-ranking` and `foundation-candidates` named one set before.
SHAPE = ("--layers", "20", "--width", "60")

_CARDS = r"""
(() => {
  const section = document.querySelector('section[data-section="findings"]');
  const also = section.querySelector("details.also-noted");
  return {
    also: also ? { open: also.open, summary: also.querySelector("summary").textContent,
                   cards: also.querySelectorAll("article.finding").length } : null,
    cards: [...section.querySelectorAll("article.finding")].map((card) => {
      const fold = card.parentElement.closest("details");
      const said = card.cloneNode(true);
      said.querySelectorAll(".step, details, button, .investigate").forEach((n) => n.remove());
      return {
        id: card.dataset.findingId,
        severity: card.dataset.severity,
        noteOf: card.dataset.noteOf ?? null,
        atRest: !fold || fold.open,
        step: Boolean(card.querySelector(".step:not(.muted)")?.textContent.trim()),
        text: said.textContent,
      };
    }),
  };
})()
"""


def _report_in(page):
    text = pathlib.Path(page).read_text(encoding="utf-8")
    packed = re.search(r'id="bga-report-gz">([^<]*)</script>', text)
    if packed:
        return json.loads(gzip.decompress(base64.b64decode(packed.group(1))))
    body = re.search(r'id="bga-report">(.*?)</script>', text, re.S).group(1)
    return json.loads(body.replace("<\\/", "</"))


@pytest.fixture(scope="module", params=["macro_micro", "synthetic"])
def drawn(request, tmp_path_factory):
    into = tmp_path_factory.mktemp(f"u1249-{request.param}")
    run = pages.two_plane_run(into, SHAPE) if request.param == "synthetic" else pages.FIXTURES[request.param]
    page = pages.export_page(run, into)
    with Browser(chrome) as opened:
        measured = opened.measure(page.as_uri(), _CARDS)
    return request.param, _report_in(page)["findings"], measured


@needs_browser
@pytest.mark.medium
class TestFindingsSayEachThingOnce:
    def test_no_element_set_is_named_again_below_its_finding(self, drawn):
        label, findings, _ = drawn
        severity = {f["id"]: f["severity"] for f in findings}
        named = {}
        for f in findings:
            if len(set(f["elements"])) > 1:
                named.setdefault(frozenset(f["elements"]), []).append(f["id"])
        again = [ids for ids in named.values() if len({severity[i] for i in ids}) > 1]
        assert again == [], (label, again)

    def test_no_element_is_named_twice_in_one_card(self, drawn):
        label, findings, measured = drawn
        elements = {f["id"]: f["elements"] for f in findings}
        twice = {}
        for card in measured["cards"]:
            for uid in elements.get(card["id"], [])[:40]:
                count = len(re.findall(rf"(?<![\w./-]){re.escape(uid)}(?![\w/-])", card["text"]))
                if count > 1:
                    twice.setdefault(card["id"], []).append((uid, count))
        assert len(measured["cards"]) == len(findings), label
        assert twice == {}, (label, twice)

    def test_a_card_at_rest_has_a_step_or_ranks_above_info(self, drawn):
        label, _, measured = drawn
        cards = measured["cards"]
        heads = {c["id"]: c for c in cards if not c["noteOf"]}
        idle = [
            c["id"]
            for c in cards
            if c["atRest"] and not c["step"] and (heads.get(c["noteOf"]) or c)["severity"] == "info"
        ]
        assert measured["also"] and not measured["also"]["open"], (label, measured["also"])
        assert idle == [], (label, idle)

    def test_the_fold_counts_what_it_holds(self, drawn):
        label, _, measured = drawn
        also = measured["also"]
        assert also["summary"] == f"Also noted · {also['cards']}" and also["cards"], (label, also)
