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
