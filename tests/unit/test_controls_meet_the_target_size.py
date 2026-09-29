"""UX-1022 (styleguide §6e.7): 73 of 77 rendered buttons under 24px in a
dimension on `macro_micro`, 54 of 58 on `golden` - the door at 14x14px,
control heights at 14/23/40/58px, before this item.

`--hit-min` (24px, 44px under `@media (pointer: coarse)`) as a
`min-width`/`min-height` floor on `button`, `summary`, `input`,
`select`, `textarea` and every `a` outside running prose - a floor, so
a class rule's own smaller `width`/`height` (the door's `1.1em`) still
clamps up rather than fighting this one. WCAG 2.2 2.5.8's own
exception, a link inline in a sentence (`p a`), is the one control this
file does not require it of. Boots the golden export, once with a fine
pointer and once under touch emulation (`UX-1022`'s `Browser.measure
coarse=True`).
"""

import pathlib
import shutil
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from browser import NO_BROWSER, Browser, find_chrome

REPO = pathlib.Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

FINE_MIN = 24
COARSE_MIN = 44

#: Every rendered control, its box, and whether it is a link inline in
#: running prose - the one exception this project keeps (WCAG 2.5.8).
_SCAN = """
(() => {
  const sel = "button, a, summary, input, select, textarea";
  const inSentence = (n) => n.tagName === "A" && !!n.closest("p");
  const out = [];
  document.querySelectorAll(sel).forEach((n) => {
    const r = n.getBoundingClientRect();
    if (r.width > 0 && r.height > 0) {
      out.push({tag: n.tagName, cls: n.className,
                 w: r.width, h: r.height, sentence: inSentence(n)});
    }
  });
  return out;
})()
"""


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def golden(tmp_path_factory):
    from tools.bga_view import export

    run = tmp_path_factory.mktemp("target-golden") / "run"
    shutil.copytree(GOLDEN, run)
    (run / "expected_output.json").unlink(missing_ok=True)
    page = tmp_path_factory.mktemp("target-golden-page") / "report.html"
    export(str(run), str(page))
    return page.as_uri()


def _under(controls, bound):
    return [c for c in controls if not c["sentence"] and min(c["w"], c["h"]) < bound - 0.01]


@needs_browser
def test_every_control_is_24x24_with_a_fine_pointer(browser, golden):
    controls = browser.measure(golden, _SCAN)
    under = _under(controls, FINE_MIN)
    assert under == [], (
        f"{len(under)} control(s) under {FINE_MIN}x{FINE_MIN}px with a fine pointer: {under[:5]} (styleguide §6e.7)"
    )


@needs_browser
def test_every_control_is_44x44_under_a_coarse_pointer(browser, golden):
    controls = browser.measure(golden, _SCAN, coarse=True)
    under = _under(controls, COARSE_MIN)
    assert under == [], (
        f"{len(under)} control(s) under {COARSE_MIN}x{COARSE_MIN}px "
        f"under a coarse pointer: {under[:5]} (styleguide §6e.7)"
    )
