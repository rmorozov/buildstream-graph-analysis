"""UX-1056: `back()` after a fragment link restores the pre-click folds and scroll.

The click snapshots the open chapters and `scrollY` into the entry it
leaves (`history.replaceState`); `popstate` applies that snapshot. On
`macro_micro` at 1440x900, in a real browser (`tests/browser.py`).
Each link click follows a real `Enter` (`Browser.journey`): Chrome prunes
an entry added without user activation first once the shared tab's
history is at its cap of 50, and a bare scripted `click()` carries none.
"""

import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import NO_BROWSER, Browser, find_chrome

needs_browser = pytest.mark.skipif(find_chrome() is None, reason=NO_BROWSER)

_HELPERS = r"""
window.__j = (() => {
  const read = () => ({
    y: Math.round(scrollY),
    chapters: document.querySelectorAll('section.chapter[data-open="true"]').length,
    sections: [...document.querySelectorAll("[data-section]")]
      .filter((node) => !node.closest("[hidden]")).length,
  });
  const frame = () => new Promise((done) => requestAnimationFrame(done));
  // The same reading on 8 consecutive frames, capped at 240.
  const settled = async () => {
    let last = "", same = 0;
    for (let i = 0; i < 240 && same < 8; i += 1) {
      await frame();
      const now = JSON.stringify(read());
      same = now === last ? same + 1 : 0;
      last = now;
    }
    return read();
  };
  const on = (name) => new Promise((done, fail) => {
    window.addEventListener(name, done, { once: true });
    setTimeout(() => fail(new Error(`no ${name} in 10s`)), 10000);
  });
  const page = (url) => String(url).split("#")[0];
  const traverse = async (go) => {
    const step = navigation.currentEntry.index + (go === "back" ? -1 : 1);
    if (page(navigation.entries()[step]?.url) !== page(location.href)) {
      throw new Error(`${go}() would leave the document`);
    }
    const moved = on("popstate");
    history[go]();
    await moved;
    return settled();
  };
  return { read, settled, on, traverse, moved: null };
})();
null
"""


def _follow(href):
    """A real `Enter` on the page for user activation, then the link's click."""
    click = f'(() => {{ const moved = __j.on("hashchange"); document.querySelector(\'a[href="{href}"]\').click(); return moved.then(__j.settled); }})()'
    return [{"key": "Enter"}, {"read": click}]


_BACK = {"read": '__j.traverse("back")'}
_STEPS = [
    {"read": _HELPERS},
    {"read": "__j.settled()"},  # initial
    *_follow("#graph_summary"),  # first
    *_follow("#confidence"),  # second
    _BACK,  # back_once
    _BACK,  # back_twice
    # A click on the restored entry: wireViewState rewrites its hash.
    {"read": 'document.body.click(); new Promise((done) => setTimeout(done, 100)).then(() => __j.traverse("forward"))'},
    _BACK,  # after_a_rewrite
    # A rail view link reveals in its own listener, before the document's.
    *_follow("#elements~v.elements=Critical%20path"),
    _BACK,  # rail_back
    # The reader shuts the revealed chapter, then leaves by another link.
    *_follow("#graph_summary"),
    {"read": 'document.querySelector("[data-chapter-open=elements]").click(); __j.settled()'},
    *_follow("#confidence"),
    _BACK,  # shut_back
    {
        "read": '[...document.querySelectorAll("button")].find((n) => n.textContent.trim() === "Expand all").click(); __j.settled()'
    },
    *_follow("#graph_summary"),
    _BACK,  # expanded_back
]
_NAMES = [
    "initial",
    "first",
    "second",
    "back_once",
    "back_twice",
    "forward",
    "after_a_rewrite",
    "rail_link",
    "rail_back",
    "shut_link",
    "shut",
    "shut_leave",
    "shut_back",
    "expanded",
    "expanded_link",
    "expanded_back",
]


@pytest.fixture(scope="module")
def journey(tmp_path_factory):
    uri = pages.export_uri(pages.FIXTURES["macro_micro"], tmp_path_factory.mktemp("back"))
    with Browser(find_chrome()) as browser:
        seen = [value for value in browser.journey(uri, _STEPS, 1440, 900) if value is not None]
    assert len(seen) == len(_NAMES), seen
    return dict(zip(_NAMES, seen))


@needs_browser
class TestBackUnwindsAReveal:
    def test_the_click_opens_a_folded_chapter(self, journey):
        """Non-vacuity: the reveal back() must undo happened."""
        # `UX-1146`: five - `next_steps` is the decision's rail sub-entry now.
        assert journey["initial"] == {"y": 0, "chapters": 1, "sections": 5}, journey
        assert journey["first"]["chapters"] == 2 and journey["first"]["y"] > 0, journey

    def test_one_back_after_one_click_restores_the_resting_page(self, journey):
        assert journey["back_twice"] == journey["initial"], journey

    def test_one_back_after_two_clicks_restores_the_first_click(self, journey):
        assert journey["back_once"] == journey["first"], journey

    def test_a_view_state_rewrite_keeps_the_snapshot(self, journey):
        """A click on the restored entry rewrites its hash; the snapshot survives."""
        assert journey["after_a_rewrite"] == journey["initial"], journey

    def test_back_after_a_rail_view_link_re_folds(self, journey):
        """`nav.js` reveals on the link itself; the snapshot must precede it."""
        assert journey["rail_link"]["chapters"] == 2, journey
        assert journey["rail_back"] == journey["initial"], journey

    def test_back_does_not_re_reveal_the_entry_anchor(self, journey):
        """The entry's own `#graph_summary` must not reopen what the reader shut."""
        assert journey["shut"]["chapters"] == 1, journey
        assert journey["shut_back"]["chapters"] == 1, journey

    def test_back_keeps_folds_the_reader_opened(self, journey):
        """`Expand all` then a click: back() re-folds nothing."""
        assert journey["expanded"]["chapters"] == 7, journey
        assert journey["expanded_back"]["chapters"] == 7, journey
