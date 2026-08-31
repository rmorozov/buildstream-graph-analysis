"""UX-435: the handoff box was bounded in the mode it is smallest in.

`#actions-group` holds the Perfetto hand-off in the sticky rail.
`test_apparatus_in_its_place.py` guards it — `position === "static"`,
`group_px > 0` — with **no upper bound on its height**, against a
fixture that is the *export*. The export hides both fallbacks; they are
unhidden only when a server is behind the trace, which is the mode
`bga view` opens by default. Measured on `with_timeline`, before:

```text
                 group      share of rail
exported  1440x900   208x39px      4.9%
exported   390x844   327x39px     38.6%
served    1440x900  208x157px     19.5%
served     390x844  327x113px     64.2%
```

Four times the height served, and **64.2% of the rail on a phone** —
a number the item did not have, because nothing had measured the served
page at that width either.

The two fallbacks were blocks of prose under the control: `actions`
45px against `actions-download` 92px, twice the affordance it is a
fallback for. They are inline routes on the control's own line now,
each still its own hideable element with its own id, so
`wireTheHandoff` unhides exactly what it unhid before. `UX-198` and
`UX-314` added them for measured failures and both are still here.

```text
                 group      share of rail
served    1440x900  208x106px     13.2%
served     390x844   327x62px     50.0%
```

**This is §3f's rule in a second dimension.** That section says a bound
is enforced at the largest size the tool tells people to use. This says:
in the mode people use it in. A page has modes as well as sizes, and a
measurement taken where a control is smallest has not met the control.
"""
import json
import pathlib
import shutil
import sys
import threading
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402
from pages import snapshot_copy    # noqa: E402

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
needs_node = pytest.mark.skipif(shutil.which("node") is None,
                                reason="node is not installed")

FIXTURE = REPO / "tests/fixtures/with_timeline/run"

#: What the group may cost, **served**, per viewport. Measured at 106px
#: and 62px; the headroom is one wrapped line, so a word added to a
#: link is absorbed and a paragraph is not.
BOUND_PX = {(1440, 900): 130, (390, 844): 86}

#: And what it may cost as a share of the rail it sits in - the number
#: the field report was actually about. 13.2% and 50.0% measured.
BOUND_SHARE = {(1440, 900): 16.0, (390, 844): 56.0}

MEASURE = """
(() => {
  const box = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { w: Math.round(r.width), h: Math.round(r.height) };
  };
  const group = box("#actions-group"), rail = box("nav.toc");
  const blocks = [...document.querySelectorAll("#actions-group *")]
    .filter((el) => !el.hidden
      && getComputedStyle(el).display.startsWith("block"))
    .map((el) => el.id || el.tagName);
  // Each fallback's own state, read from the element rather than
  // inferred from the block list - the fix empties that list of them
  // by design, so inferring visibility from it asserts the opposite
  // of what it means. This file's first cut did exactly that.
  const route = (id) => {
    const el = document.getElementById(id);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { hidden: el.hidden, w: Math.round(r.width),
             h: Math.round(r.height) };
  };
  return JSON.stringify({ group, rail, blocks,
    routes: { "actions-fallback": route("actions-fallback"),
              "actions-download": route("actions-download") } });
})()
"""


@pytest.fixture(scope="module")
def served(tmp_path_factory):
    """The page as `bga view` opens it: a server behind the trace."""
    if chrome is None or shutil.which("node") is None:    # pragma: no cover
        pytest.skip(NO_BROWSER)
    from tools.bga_view import serve

    run = snapshot_copy(FIXTURE, tmp_path_factory.mktemp("served"))
    httpd, url = serve(str(run), port=0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)
    try:
        with Browser(chrome) as opened:
            yield lambda w, h: json.loads(
                opened.observe(url, MEASURE, width=w, height=h)["value"])
    finally:
        httpd.shutdown()


@needs_browser
@needs_node
@pytest.mark.parametrize("width,height", sorted(BOUND_PX))
class TestTheGroupIsBoundedWhereItIsLargest:

    def test_the_served_page_really_unhides_a_fallback(
            self, served, width, height):
        """The whole point. A run where neither fallback showed would
        make every bound below a measurement of the export, which is
        the defect this item is."""
        seen = served(width, height)
        shown = [name for name, box in seen["routes"].items()
                 if box and not box["hidden"] and box["h"] > 0]
        assert shown, (
            f"neither fallback is visible served - this guard would then "
            f"be measuring the export, which is what it exists to stop: "
            f"{seen['routes']}")

    def test_the_group_is_under_its_height_bound(self, served, width, height):
        seen = served(width, height)
        assert seen["group"]["h"] <= BOUND_PX[(width, height)], (
            f"{width}x{height}: the hand-off group is "
            f"{seen['group']['h']}px, over the {BOUND_PX[(width, height)]}px "
            f"this item bounds it at")

    def test_the_group_is_under_its_share_of_the_rail(
            self, served, width, height):
        """The field report's own unit: how much of the rail it takes."""
        seen = served(width, height)
        share = 100.0 * seen["group"]["h"] / seen["rail"]["h"]
        assert share <= BOUND_SHARE[(width, height)], (
            f"{width}x{height}: {share:.1f}% of the rail, over "
            f"{BOUND_SHARE[(width, height)]}%")

    def test_no_fallback_is_a_block_of_prose(self, served, width, height):
        """What the height is spent on, not just how much.

        A bound alone can be met by shrinking a font. The rule is that
        a fallback is a route on the control's line, not a paragraph
        under it - so neither may render as a block.
        """
        seen = served(width, height)
        blocks = set(seen["blocks"])
        assert not blocks & {"actions-fallback", "actions-download"}, (
            f"{width}x{height}: a fallback renders as a block: {blocks}")
