"""UX-671: the rail acts on the view, and the URL does not follow.

A rail preset sub-entry applied its view (the badge changed) and a jump
box hit scrolled to its target, but neither wrote the anchor - so
"Copy link to this view" named wherever the reader used to be, not
where either control just put them. Measured served, `macro_micro`,
Chromium: `scrollY 0 -> 0` after a preset click with its section 7,137
px below; the jump box scrolled but `location.hash`'s anchor stayed
whatever it was before.

Both controls now write the section they land on before the
view-state writer's own capture runs, the same anchor a plain rail
`<a href="#key">` already gets from the browser for free.
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

#: Polls for the state the click is supposed to produce, rather than a
#: fixed sleep or a frame count (`UX-795`) - so a dropped anchor write
#: reports "never happened" instead of "did not happen inside 50ms".
_WAIT = """
const waitFor = async (check, tries = 60, ms = 50) => {
  for (let i = 0; i < tries; i++) {
    if (check()) return true;
    await new Promise((go) => setTimeout(go, ms));
  }
  return false;
};
"""

#: A preset sub-entry belonging to the `elements` section, on a run
#: whose `elements` section sits thousands of pixels below the top -
#: the exact shape the motivation measured.
_PRESET = _WAIT + """(async () => {
  const link = document.querySelector(
    'a[data-toc-view][href^="#elements~"][data-toc-view="Critical path"]');
  const section = document.getElementById("elements");
  const before = { hash: location.hash, scrollY: window.scrollY };
  link.click();
  await waitFor(() => location.hash.startsWith("#elements~"));
  // `UX-670`: `revealAndLand` lands three times as a folded chapter's
  // `content-visibility` estimate corrects, so the settled rect is
  // what the guard waits for - not the first, approximate, landing.
  await waitFor(() => Math.abs(section.getBoundingClientRect().top - 105) < 40);
  const after = { hash: location.hash, scrollY: window.scrollY,
                   rectTop: section.getBoundingClientRect().top };
  const link1 = location.href;
  return { before, after, link1 };
})()"""

#: The jump box, landed by the hit and by Enter - the two ways in the
#: Required Fix names. `readers` is not the run's first section, so a
#: write that only ever preserved whatever anchor was already there
#: would still show `""`.
_JUMP = _WAIT + """(async () => {
  const box = document.getElementById("jump");
  const setter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype, "value").set;
  const search = async (mode) => {
    location.hash = "";
    window.scrollTo(0, 0);
    setter.call(box, "e");
    box.dispatchEvent(new Event("input", { bubbles: true }));
    await waitFor(() => document.querySelector(
      '.jump-hits button[data-jump="readers"]'));
    const hit = document.querySelector(
      '.jump-hits button[data-jump="readers"]');
    const section = document.getElementById("readers");
    const before = { hash: location.hash, scrollY: window.scrollY };
    if (mode === "enter") {
      box.dispatchEvent(new KeyboardEvent("keydown",
        { key: "Enter", bubbles: true }));
    } else {
      hit.click();
    }
    await waitFor(() => location.hash.startsWith("#readers~"));
    await waitFor(() => Math.abs(section.getBoundingClientRect().top - 105) < 40);
    return { before, after: { hash: location.hash, scrollY: window.scrollY,
                              rectTop: section.getBoundingClientRect().top },
             link: location.href };
  };
  return { hit: await search("click"), enter: await search("enter") };
})()"""

#: Reopening the copied link on a fresh load: the anchor the writer put
#: in it must be what the second load scrolls to, unaided by anything
#: this session remembered.
_REOPEN = _WAIT + """(async (target) => {
  const before = window.scrollY;
  await waitFor(() => window.scrollY !== before || true, 1, 200);
  const key = location.hash.replace(/^#/, "").split("~")[0];
  const node = key ? document.getElementById(key) : null;
  await waitFor(() => node && Math.abs(
    window.scrollY + node.getBoundingClientRect().top - 105) < 40);
  return { key, rectTop: node ? node.getBoundingClientRect().top : null };
})()"""


@pytest.fixture(scope="module")
def preset(tmp_path_factory):
    # `cdp.mjs` drives the one page target the shared browser already
    # has open, so each fixture exports to its own directory - a URL
    # the target has already seen (even a bare path a `replaceState`
    # moved on from) does not reliably force a reload.
    if chrome is None:
        pytest.skip(NO_BROWSER)
    at = pages.export_uri(pages.FIXTURES["macro_micro"],
                          tmp_path_factory.mktemp("rail-jump-preset"))
    with Browser(chrome) as browser:
        return browser.measure(at, _PRESET, 1440, 900)


@pytest.fixture(scope="module")
def jumped(tmp_path_factory):
    if chrome is None:
        pytest.skip(NO_BROWSER)
    at = pages.export_uri(pages.FIXTURES["macro_micro"],
                          tmp_path_factory.mktemp("rail-jump-jumped"))
    with Browser(chrome) as browser:
        return browser.measure(at, _JUMP, 1440, 900)


def _reopened(link, tag):
    # `cdp.mjs` drives the one page target the shared browser already
    # has open - a same-document `#hash`-only navigate would not
    # reload it, so a query tag forces the real, separate load
    # "pasted into an issue" means.
    base, _, fragment = link.partition("#")
    forced = f"{base}?reopen={tag}#{fragment}"
    with Browser(chrome) as browser:
        return browser.measure(forced, _REOPEN, 1440, 900)


@needs_browser
class TestAPresetSubEntryGoesToItsSection:
    def test_the_view_moved_the_reader_not_just_the_table(self, preset):
        """The motivation's own measurement: `scrollY 0 -> 0` is the
        defect, so a real move off zero is the fix."""
        assert preset["before"]["scrollY"] == 0, preset["before"]
        assert preset["after"]["scrollY"] > 1000, preset["after"]

    def test_the_anchor_names_the_section_now_in_view(self, preset):
        assert preset["after"]["hash"].startswith("#elements~"), preset

    def test_the_landing_is_at_the_section_not_past_it(self, preset):
        assert abs(preset["after"]["rectTop"] - 105) < 40, preset["after"]

    def test_the_copied_link_reopens_on_the_same_section(self, preset):
        out = _reopened(preset["link1"], "preset")
        assert out["key"] == "elements", out


@needs_browser
class TestTheJumpBoxWritesWhatItScrolledTo:
    def test_the_hit_writes_the_anchor(self, jumped):
        out = jumped["hit"]
        assert out["before"]["hash"] == "", out["before"]
        assert out["after"]["hash"].startswith("#readers~"), out["after"]
        assert abs(out["after"]["rectTop"] - 105) < 40, out["after"]

    def test_enter_writes_the_anchor_too(self, jumped):
        out = jumped["enter"]
        assert out["after"]["hash"].startswith("#readers~"), out["after"]
        assert abs(out["after"]["rectTop"] - 105) < 40, out["after"]

    def test_the_copied_link_reopens_where_the_jump_landed(self, jumped):
        out = _reopened(jumped["hit"]["link"], "jump")
        assert out["key"] == "readers", out


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
