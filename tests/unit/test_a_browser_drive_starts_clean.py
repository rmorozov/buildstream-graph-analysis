"""UX-1215, UX-1217: every browser drive starts on a fresh history, history-write budget and localStorage.

Chrome caps a tab's history at 50 entries and the worker's shared tab
carries every earlier drive's pushes, so a guard's own entries were pruned
and Back landed elsewhere; one Chrome per worker also shares localStorage,
so a stored `bga.copy-format` was read by the next file's drive.
`cdp.mjs` resets both before each load. Chrome also drops a frame's history writes past 200 in 10s,
so a drive after a flood read an empty fragment: each drive opens its own tab.
"""

import pytest

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: Past the 50-entry cap, so a surviving history reads 50.
_PUSH = "(() => { for (let i = 0; i < 60; i++) history.pushState({ i }, '', '#drive-' + i); return history.length; })()"
_READ = "history.length"
_STORE = "(() => { localStorage.setItem('bga.copy-format', 'markdown'); return localStorage.length; })()"
_KEYS = "Object.keys(localStorage)"
_FLOOD = "(() => { for (let i = 0; i < 200; i++) history.replaceState(null, '', '#w' + i); return location.hash; })()"
_WRITE = "(() => { history.replaceState(null, '', '#after'); return location.hash; })()"


@pytest.fixture(scope="module")
def uris(tmp_path_factory):
    return pages.pages(tmp_path_factory, "clean", labels=["golden", "macro_micro"])


@needs_browser
@pytest.mark.parametrize("label", ["golden", "macro_micro"])
def test_a_drive_after_sixty_pushes_reads_a_history_of_its_own(uris, label):
    with Browser(chrome) as browser:
        assert browser.measure(uris[label], _PUSH) >= 50
        assert browser.measure(uris[label], _READ) <= 2


@needs_browser
@pytest.mark.parametrize("label", ["golden", "macro_micro"])
def test_a_drive_after_a_stored_preference_reads_an_empty_storage(uris, label):
    with Browser(chrome) as browser:
        assert browser.measure(uris[label], _STORE) >= 1
        assert browser.measure(uris[label], _KEYS) == []


@needs_browser
@pytest.mark.parametrize("label", ["golden", "macro_micro"])
def test_a_drive_after_a_flood_of_history_writes_can_still_write_one(uris, label):
    with Browser(chrome) as browser:
        assert browser.measure(uris[label], _FLOOD) == "#w199"
        assert browser.measure(uris[label], _WRITE) == "#after"
