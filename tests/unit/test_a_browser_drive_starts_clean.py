"""UX-1215: every browser drive starts on a fresh session history.

Chrome caps a tab's history at 50 entries and the worker's shared tab
carries every earlier drive's pushes, so a guard's own entries were pruned
and Back landed elsewhere. `cdp.mjs` resets the history before each load.
"""

import pytest

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: Past the 50-entry cap, so a surviving history reads 50.
_PUSH = "(() => { for (let i = 0; i < 60; i++) history.pushState({ i }, '', '#drive-' + i); return history.length; })()"
_READ = "history.length"


@pytest.fixture(scope="module")
def uris(tmp_path_factory):
    return pages.pages(tmp_path_factory, "clean", labels=["golden", "macro_micro"])


@needs_browser
@pytest.mark.parametrize("label", ["golden", "macro_micro"])
def test_a_drive_after_sixty_pushes_reads_a_history_of_its_own(uris, label):
    with Browser(chrome) as browser:
        assert browser.measure(uris[label], _PUSH) >= 50
        assert browser.measure(uris[label], _READ) <= 2
