"""UX-822 (styleguide §5b): what the header already says is not said
again.

Measured on the walk capture (round 115's design review, five readers)
and reproduced here on the committed fixtures: `section#readers` drew
a Reader/question/leads-with row per reader, repeating - label for
label - the five options `select[name=reader]` already offered 411px
above it. `readers` now reaches a reader through the picker alone
(`sections.js`'s `DRAWN_ELSEWHERE`): the option's own text is the
label, its `title` the question, and the chosen reader's lead still
lands in the decision panel.
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

#: No `#readers` section; every non-blank option carries a `title`;
#: choosing the last real option still lands a `.reader-lead`.
_CHECK = r"""
(() => {
  const section = document.getElementById("readers");
  const select = document.querySelector("select[name=reader]");
  const options = select
    ? [...select.options].filter((o) => o.value)
        .map((o) => ({ value: o.value, title: o.getAttribute("title") }))
    : [];
  let lead = null;
  let chosen = null;
  if (select && options.length) {
    chosen = options[options.length - 1].value;
    select.value = chosen;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    const n = document.querySelector("[data-role=reader-lead]");
    lead = n ? { reader: n.getAttribute("data-reader") } : null;
  }
  return { hasSection: Boolean(section), options, lead, chosen };
})()
"""


def _questions(label):
    from tools.bga_view import payloads

    payload = payloads(str(pages.FIXTURES[label]))["report.json"]
    return {e["id"]: e["question"] for e in payload.get("readers") or []}


@pytest.fixture(scope="module", params=sorted(pages.FIXTURES))
def measured(request, tmp_path_factory):
    label = request.param
    uri = pages.export_uri(pages.FIXTURES[label],
                           tmp_path_factory.mktemp(f"readers-once-{label}"))
    with Browser(chrome) as opened:
        return label, opened.measure(uri, _CHECK, 1440, 900)


@needs_browser
class TestTheReadersSectionIsGone:
    def test_no_readers_section(self, measured):
        label, out = measured
        assert out["hasSection"] is False, f"{label}: {out}"


@needs_browser
class TestThePickerCarriesTheQuestion:
    def test_every_option_titles_its_question(self, measured):
        label, out = measured
        questions = _questions(label)
        assert len(out["options"]) >= 2, (
            f"{label}: fewer than two readers - the picker should not "
            f"be offered at all")
        missing = [o for o in out["options"]
                  if not o["title"] or o["title"] != questions.get(o["value"])]
        assert missing == [], f"{label}: {missing}"


@needs_browser
class TestTheLeadStillLands:
    def test_choosing_a_reader_still_draws_the_lead(self, measured):
        label, out = measured
        assert out["lead"] is not None, f"{label}: {out}"
        assert out["lead"]["reader"] == out["chosen"], f"{label}: {out}"
