"""UX-1043 (styleguide §3l): the JSON toggle sits at one place.

Measured on `main` at `814a2db8`, both fixtures, every chapter open:
`button.json-toggle`'s x-centre spread 126-136 px (47-48 controls) -
it trailed the heading text, so its offset grew with the title. The
fold (`button.collapse`) and door (`button.describe`) held to 2-3 px.

`UX-1043` pins the toggle to the section head's right edge instead of
beside the fold and door: the head is the one node `rawjson.js` already
touches, and the right edge is the one side the fold (prepended) and
the door (`attachBlockDoor`, into the first block) do not claim, so
fixing it costs no move to either.

Offset here is `headRect.right - toggleRect.right` - zero and constant
if the button is truly pinned, not merely closer together than before.

The verifier held the first cut: `padding-right: 6.5rem` was a guessed
104px reservation against a 114.8px rendered button, so a wrapped
title's last line overlapped the toggle on 8/34 golden and 16/48
macro_micro sections at 390x844 while the offset clause above stayed
green (it reads `.right`, blind to what the padding leaves room for).
`rawjson.js`'s `syncToggleGutter` now reads the button's own box after
every text change; `test_no_title_line_overlaps_the_toggle` is the
clause that would have caught the miss.
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

#: styleguide §3l's own budget: one target (24px) of slack.
OFFSET_SPREAD_PX = 24

#: `UX-1043`'s Acceptance Test names both fixtures `UX-1042` files -
#: `golden` and `macro_micro`, every chapter opened.
LABELS = sorted(pages.FIXTURES)

_SCAN = r"""
(() => {
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
    for (const section of
         box.querySelectorAll(":scope > section[data-section]")) {
      section.removeAttribute("hidden");
    }
  }
  const out = [];
  document.querySelectorAll("section[data-section]").forEach((s) => {
    const heading = s.querySelector("h2, h3");
    const toggle = s.querySelector("button.json-toggle");
    if (!heading || !toggle) return;
    const hr = heading.getBoundingClientRect();
    const tr = toggle.getBoundingClientRect();
    out.push({key: s.getAttribute("data-section"), offset: hr.right - tr.right});
  });
  return out;
})()
"""


#: Every text-node client rect the head's wrapped title drew, tested
#: against the toggle's own rect - a rect that intersects it is a title
#: line the button sits on top of. The toggle's own text nodes are
#: excluded since it is inside the head. `__ZOOM__` is replaced (never
#: `.format()`, so the JS's own braces stay literal) with a root
#: font-size bump or nothing - the re-verification's own miss: a
#: reservation measured once (`getBoundingClientRect().width`, read on
#: append) is a frozen px that a later zoom leaves behind the button's
#: real, now-larger box. A CSS-only reservation has no "once" to freeze.
_OVERLAP_SCAN_TEMPLATE = r"""
(() => {
  for (const box of document.querySelectorAll("section.chapter")) {
    box.setAttribute("data-open", "true");
    for (const section of
         box.querySelectorAll(":scope > section[data-section]")) {
      section.removeAttribute("hidden");
    }
  }
  __ZOOM__
  const out = [];
  document.querySelectorAll("section[data-section]").forEach((s) => {
    const heading = s.querySelector("h2, h3");
    const toggle = s.querySelector("button.json-toggle");
    if (!heading || !toggle) return;
    const tr = toggle.getBoundingClientRect();
    const walker = document.createTreeWalker(heading, NodeFilter.SHOW_TEXT);
    let node;
    let hit = null;
    while (!hit && (node = walker.nextNode())) {
      if (toggle.contains(node)) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      for (const r of range.getClientRects()) {
        if (r.width === 0 || r.height === 0) continue;
        const overlap = !(r.right <= tr.left || r.left >= tr.right ||
                          r.bottom <= tr.top || r.top >= tr.bottom);
        if (overlap) {
          hit = {key: s.getAttribute("data-section"),
                 text: {left: r.left, right: r.right, top: r.top, bottom: r.bottom},
                 toggle: {left: tr.left, right: tr.right, top: tr.top, bottom: tr.bottom}};
          break;
        }
      }
    }
    if (hit) out.push(hit);
  });
  return out;
})()
"""

#: `document.documentElement.style.fontSize` at 40px - `--font-small`
#: and every `rem` token scale with it, including the button's own box.
_ZOOM_JS = "document.documentElement.style.fontSize = '40px';"


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def booted(tmp_path_factory):
    return pages.pages(tmp_path_factory, "sections-controls", labels=LABELS)


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", LABELS)
@pytest.mark.parametrize("width,height", [(1440, 900), (390, 844)])
def test_the_json_toggle_offset_is_stable(browser, booted, label, width,
                                          height):
    out = browser.measure(booted[label], _SCAN, width, height)
    assert out, f"{label} rendered no section with both a heading and a toggle"
    offsets = [row["offset"] for row in out]
    spread = max(offsets) - min(offsets)
    assert spread <= OFFSET_SPREAD_PX, (
        f"{label} at {width}x{height}: {len(offsets)} toggles, offset from "
        f"the head's right edge ranges {min(offsets):.1f}-{max(offsets):.1f}px "
        f"(spread {spread:.1f}px > {OFFSET_SPREAD_PX}px, styleguide §3l): "
        f"{sorted(out, key=lambda r: r['offset'])[:3]} .. "
        f"{sorted(out, key=lambda r: r['offset'])[-3:]}")


@needs_browser
@pytest.mark.medium
@pytest.mark.parametrize("label", LABELS)
@pytest.mark.parametrize("width,height", [(1440, 900), (390, 844)])
@pytest.mark.parametrize("zoom", [False, True], ids=["normal", "zoom40"])
def test_no_title_line_overlaps_the_toggle(browser, booted, label, width,
                                           height, zoom):
    script = _OVERLAP_SCAN_TEMPLATE.replace(
        "__ZOOM__", _ZOOM_JS if zoom else "")
    hits = browser.measure(booted[label], script, width, height)
    assert hits == [], (
        f"{label} at {width}x{height}{' zoomed to 40px root' if zoom else ''}"
        f": {len(hits)} section(s) whose wrapped title overlaps the toggle "
        f"(styleguide §3l): {hits[:3]}")
