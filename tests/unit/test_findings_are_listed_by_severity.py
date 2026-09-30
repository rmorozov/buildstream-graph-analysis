"""UX-1148: findings are published, and drawn, in severity order.

Severity first, then `compute_findings`' argued order; an indented note
stays directly under the table it qualifies.
"""

import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga.analyzer import BuildEfficiencyAnalyzer
from bga.findings import compute_findings
from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

_RANK = {"critical": 0, "high": 1, "medium": 2, "info": 3}

_MEASURE = r"""
(() => [...document.querySelectorAll("#findings article.finding")].map(a => ({
  id: a.dataset.findingId, severity: a.dataset.severity, noteOf: a.dataset.noteOf ?? null,
})))()
"""


def _run(label, into):
    if label == "two_plane":
        return pages.two_plane_run(into, ("--layers", "8", "--width", "14"))
    return pages.FIXTURES[label]


@pytest.fixture(scope="module", params=["two_plane", "golden", "macro_micro"])
def drawn(request, tmp_path_factory):
    into = tmp_path_factory.mktemp(f"u1148-{request.param}")
    uri = pages.export_uri(_run(request.param, into), into)
    with Browser(chrome) as opened:
        return request.param, opened.measure(uri, _MEASURE)


@needs_browser
class TestTheCardsAreInSeverityOrder:
    def test_there_are_findings_of_two_severities(self, drawn):
        label, cards = drawn
        assert len({card["severity"] for card in cards}) >= 2, (label, cards)

    def test_no_card_outranks_the_one_above_it(self, drawn):
        label, cards = drawn
        severities = [card["severity"] for card in cards if not card["noteOf"]]
        ranks = [_RANK[s] for s in severities]
        assert ranks == sorted(ranks), (label, severities)

    def test_a_note_sits_under_the_card_it_qualifies(self, drawn):
        label, cards = drawn
        assert label == "two_plane" or any(card["noteOf"] for card in cards), (label, cards)
        for above, card in zip(cards, cards[1:]):
            if card["noteOf"]:
                assert card["noteOf"] in (above["id"], above["noteOf"]), (label, above, card)


def test_an_indented_note_stays_under_its_table():
    analyzer = BuildEfficiencyAnalyzer()
    analyzer.load(REPO / "tests/fixtures/with_timeline/run")
    ids = [f["id"] for f in compute_findings(analyzer.analyze())]
    assert ids[ids.index("chain-graph") - 1] == "time-concentration", ids
