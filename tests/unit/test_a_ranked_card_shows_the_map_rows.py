"""UX-1267: a ranked element card shows the map rows ("On the path") in a closed fold.

Read on `macro_micro`, exported: the first ranked card (not on demand) holds
`details[data-fold="element-maps"]`, closed, whose `dt` "On the path" sits
beside a `dd` walking back to `elements.criticality_probability[<uid>].probability`.

Styleguide §2e.
"""

import pytest

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

_READ = r"""
(() => {
  const card = document.querySelector('section[data-section^="element-"][data-element]:not([data-on-demand])');
  const fold = card?.querySelector(':scope > details[data-fold="element-maps"]');
  const dt = [...(fold?.querySelectorAll("dl.pairs > dt") ?? [])].find((n) => n.textContent.trim() === "On the path");
  return { uid: card?.getAttribute("data-element"), open: fold?.open ?? null,
           path: dt?.nextElementSibling?.getAttribute("data-path") ?? null };
})()
"""


@needs_browser
def test_the_first_ranked_card_folds_on_the_path(tmp_path):
    uri = pages.export_uri(pages.FIXTURES["macro_micro"], tmp_path)
    with Browser(chrome) as browser:
        got = browser.measure(uri, _READ, 1440, 900)
    assert got["uid"], got
    assert got["open"] is False, got
    assert got["path"] == f"elements.criticality_probability[{got['uid']}].probability", got
