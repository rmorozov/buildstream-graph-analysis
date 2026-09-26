"""UX-1020: every rendered label reads sentence case, and a plural
follows its count.

Booted on `golden` and `macro_micro`: every heading, button, `summary`,
rail entry, `th` and `option` is normalised (`tools.dev_rendered_strings`)
and held against `docs/design/rendered-strings.json` - present, and
either sentence case or a listed exception (`product name`, `code`,
`acronym`, `command name`, `sentence continuation`). `no (s) in
innerText` is checked over the whole document, not just these six
roles - a plural is chosen by its count everywhere on the page.
"""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome
from tools import dev_rendered_strings as strings

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

INVENTORY = json.loads(strings.INVENTORY.read_text())
_KNOWN = {(row["role"], row["text"]) for row in INVENTORY}
_EXCEPTION = {(row["role"], row["text"]): row["exception"] for row in INVENTORY}


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@needs_browser
class TestEveryLabelIsSentenceCase:

    @pytest.mark.parametrize("label", ["golden", "macro_micro"])
    def test_every_rendered_label_is_listed_and_cased(
            self, tmp_path_factory, browser, label):
        uri = pages.export_uri(pages.FIXTURES[label],
                                tmp_path_factory.mktemp(f"labels-{label}"))
        rows = strings.rows_for(browser, label, uri)
        missing = [r for r in rows if (r["role"], r["text"]) not in _KNOWN]
        assert not missing, (
            f"{label} renders a label the inventory does not carry: "
            f"{missing[:5]} - add it to docs/design/rendered-strings.json "
            f"(python3 tools/dev_rendered_strings.py --write)")
        uncased = [r for r in rows
                   if _EXCEPTION[(r["role"], r["text"])] is None
                   and not strings.is_sentence_case(r["text"])]
        assert not uncased, f"{label} renders not-sentence-case: {uncased}"

    @pytest.mark.parametrize("label", ["golden", "macro_micro"])
    def test_no_parenthesised_plural_reaches_the_page(
            self, tmp_path_factory, browser, label):
        uri = pages.export_uri(pages.FIXTURES[label],
                                tmp_path_factory.mktemp(f"plural-{label}"))
        body = browser.measure(uri, '(() => document.body.innerText)()')
        assert "(s)" not in body, (
            f"{label} still spells a plural `(s)` rather than choosing it "
            f"by count")

    def test_no_text_transform_on_words(self):
        css = (REPO / "bga/viewer/style.css").read_text()
        assert "text-transform" not in css, (
            "a case rule belongs to the string that is rendered, not to "
            "the stylesheet (UX-1020)")
