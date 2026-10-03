"""UX-1168: the rail's mark moves when a section crosses the reading line.

A scroll that carries a section's top past `scrollspy`'s reading line
while no section enters or leaves the screen still moves the mark to
that section. Chromium (`tests/browser.py`) on `macro_micro`, every
chapter open, at 1440x900 and 390x844.

Styleguide §3h.
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

# Each section is placed 30px under the line, then scrolled 60px: its top
# crosses the line, and a crossing counts only if the set on screen is the same after.
_CROSS = r"""
(async () => {
  const frame = () => new Promise((done) => requestAnimationFrame(done));
  const frames = async (n) => { for (let i = 0; i < n; i += 1) await frame(); };
  for (const open of document.querySelectorAll('section.chapter[data-open="false"] [data-chapter-open]')) open.click();
  await frames(10);
  const linked = new Set([...document.querySelectorAll("[data-toc]")].map((a) => a.getAttribute("data-toc")));
  const secs = [...document.querySelectorAll("section[data-section]")]
    .filter((s) => linked.has(s.getAttribute("data-section")));
  const line = innerHeight * 0.15, under = 30, move = 60;
  const onScreen = (shift) => secs.filter((s) => {
    const r = s.getBoundingClientRect();
    return r.bottom - shift > 0 && r.top - shift < innerHeight;
  }).map((s) => s.dataset.section).join(",");
  const mark = () => document.querySelector("[data-toc][data-current]")?.getAttribute("data-toc") ?? null;
  const out = [];
  for (const s of secs.slice(1)) {
    scrollTo(0, s.getBoundingClientRect().top + scrollY - line - under);
    await frames(8);
    if (Math.abs(s.getBoundingClientRect().top - line - under) > 2) continue;
    if (onScreen(-5) !== onScreen(move + 5)) continue;
    const on = onScreen(0), before = mark();
    if (before === s.dataset.section) continue;
    scrollBy(0, move);
    await frames(12);
    out.push({ section: s.dataset.section, before, after: mark(), same: onScreen(0) === on,
               top: Math.round(s.getBoundingClientRect().top), line: Math.round(line) });
    if (out.length >= 3) break;
  }
  return out;
})()
"""


@pytest.fixture(scope="module")
def crossed(tmp_path_factory):
    uri = pages.pages(tmp_path_factory, prefix="ux1168", labels=["macro_micro"])["macro_micro"]
    with Browser(find_chrome()) as browser:
        return {width: browser.measure(uri, _CROSS, width, height) for width, height in ((1440, 900), (390, 844))}


@needs_browser
class TestTheMarkFollowsTheReadingLine:
    def test_a_crossing_with_no_section_entering_moves_the_mark(self, crossed):
        for width, out in crossed.items():
            assert len(out) >= 2, (width, out)
            for step in out:
                assert step["same"] and step["top"] <= step["line"], (width, step)
                assert step["after"] == step["section"], (width, step)
