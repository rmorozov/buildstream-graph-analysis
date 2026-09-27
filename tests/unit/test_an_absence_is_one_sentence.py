"""UX-1024 (styleguide §6e.12): no separator stands beside an empty value.

Measured on `golden`, reader "anyone" (the landed choice, `select
value=""`): the header's reader picker read `"I am anyone — "` - an
em dash with nothing after it, because `wireReaderControl` always
appended `" — "` between the select and the question span, and
"anyone" has no question. `renderDecision`'s empty-state sentences
(the finding fold, the reveal, the empty `dl`) were already checked
by hand and each already states what is missing and why; this guard
is the one measured defect, the separator that outlives its neighbour.
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

#: Every reader the picker offers, "anyone" first (the landed state) -
#: a separator beside an empty node must not appear under any of them.
_DRIVE = r"""
(() => {
  const select = document.querySelector("select[data-role=reader]");
  if (!select) return { picker: false };
  const orphan = (label) => {
    const question = document.querySelector('[data-role="reader-question"]');
    const text = (question?.textContent ?? "").trim();
    const wrap = question?.parentElement;
    // A plain text node has no `hidden` of its own to check; only an
    // element wrapping the dash can be told to disappear with it.
    const visibleSep = [...(wrap?.childNodes ?? [])]
      .some((n) => n.textContent.includes("—")
                   && !(n.nodeType === 1 && n.hidden));
    return { label, question: text, dashShown: visibleSep };
  };
  const seen = [];
  for (const option of select.options) {
    select.value = option.value;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    seen.push(orphan(option.value || "anyone"));
  }
  return { picker: true, seen };
})()
"""


@pytest.fixture(scope="module")
def driven(tmp_path_factory):
    uri = pages.export_uri(pages.FIXTURES["golden"], tmp_path_factory.mktemp("u1024"))
    with Browser(chrome) as opened:
        return opened.measure(uri, _DRIVE)


@needs_browser
class TestAnAbsenceIsOneSentence:
    def test_the_picker_exists(self, driven):
        assert driven["picker"] is True

    def test_no_separator_beside_an_empty_question(self, driven):
        bad = [row for row in driven["seen"]
              if not row["question"] and row["dashShown"]]
        assert bad == [], bad
