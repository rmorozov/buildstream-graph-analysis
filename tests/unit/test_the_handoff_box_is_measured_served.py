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

`UX-451` is the third dimension, and `UX-435` named it as the thing it
could not do: a page has **states** as well as modes and sizes, and the
bound above was measured with the status line **empty**. Two of the
states `#handoff` can carry are refusals of ~300 characters, and the
item could not measure them because they need Perfetto to refuse a real
trace.

They can be driven. `wireTheHandoff` reads the size threshold from
`run.trace_inline_max_bytes`, which the server publishes, so a server
started with that threshold at zero puts every trace over it; the other
half of the condition - that `ui.perfetto.dev` may not fetch this
origin - is already true of the ephemeral port `bga view` binds by
default, and is not forced at all. Measured that way, before this item:

```text
             group, resting     group, refused    share of rail
1440x900          106px             408px          13.2% -> 50.7%
 390x844           62px             248px          50.0% -> 80.0%
```

The refusal is drawn in `#handoff-refusal` now - a sibling of the
group, so it stays in the content column when `app.js` moves the group
into the rail - and the group returns to **exactly** its resting
height in the refused state, which is why the bounds below are
unchanged rather than raised.
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

#: What the refusal banner must be given, per viewport: a width that is
#: not the rail's. Measured at 649px and 327px - the desktop figure is
#: `max-width: 68ch` inside a 1024px content band, and the phone figure
#: is the whole viewport, because at 390px there is no second column to
#: be wider than. Both are the point: the sentence is out of the 208px
#: sticky column either way.
REFUSAL_MIN_W = {(1440, 900): 600, (390, 844): 320}

#: The shortest the refusal can be and still be the sentence this item
#: is about. Measured at 294 characters; a clause that only checked the
#: banner was *visible* would pass on an empty one.
REFUSAL_MIN_CHARS = 250

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
def can_drive_a_page():
    """The precondition both served fixtures share, asked once.

    `UX-451` added a second fixture that needs exactly this, and a
    second `pytest.skip(NO_BROWSER)` beside the first is a second skip
    site coining the same reason - which `tests/skip_reasons.py` counts
    as one more thing no guard can read before it fires. One gate,
    asked in one place, is `UX-321`'s rule and it applies to the
    fixtures as much as to the clauses.
    """
    if chrome is None or shutil.which("node") is None:    # pragma: no cover
        pytest.skip(NO_BROWSER)


@pytest.fixture(scope="module")
def served(tmp_path_factory, can_drive_a_page):
    """The page as `bga view` opens it: a server behind the trace."""
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


REFUSED = """
(async () => {
  // The tab the click opens, stubbed: headless returns null from
  // `window.open`, and a null tab skips the size branch entirely -
  // which is the branch that produces the sentence. Stubbing it is
  // driving the failure, not faking it: everything after this point
  // is the page's own code on the page's own numbers.
  window.open = () => ({ location: "", close() {} });
  const banner = document.getElementById("handoff-refusal");
  document.getElementById("perfetto").click();
  for (let i = 0; i < 100 && banner.hidden; i++) {
    await new Promise((r) => setTimeout(r, 50));
  }
  const box = (sel) => {
    const el = document.querySelector(sel);
    if (!el) return null;
    const r = el.getBoundingClientRect();
    return { w: Math.round(r.width), h: Math.round(r.height) };
  };
  const rail = document.querySelector("nav.toc");
  return JSON.stringify({
    chars: banner.textContent.length,
    hidden: banner.hidden,
    line: document.getElementById("handoff").textContent,
    inTheRail: Boolean(rail && rail.contains(banner)),
    banner: box("#handoff-refusal"), group: box("#actions-group"),
    rail: box("nav.toc"),
  });
})()
"""


@pytest.fixture(scope="module")
def refused(tmp_path_factory, can_drive_a_page):
    """The served page **after a hand-off it refused**.

    `UX-451`. `TRACE_BUDGET_B` is the threshold the server publishes as
    `run.trace_inline_max_bytes`; at zero every trace is over it, which
    is one half of the refusing condition. The other half - that
    `ui.perfetto.dev`'s own `connect-src` does not allow this origin -
    is already true of the ephemeral port `serve(port=0)` binds, and is
    left alone. So this drives the state rather than simulating it.
    """
    import tools.bga_view as view

    run = snapshot_copy(FIXTURE, tmp_path_factory.mktemp("refused"))
    budget = view.TRACE_BUDGET_B
    view.TRACE_BUDGET_B = 0
    try:
        httpd, url = view.serve(str(run), port=0)
    finally:
        view.TRACE_BUDGET_B = budget
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.3)
    try:
        with Browser(chrome) as opened:
            yield lambda w, h: json.loads(
                opened.observe(url, REFUSED, width=w, height=h)["value"])
    finally:
        httpd.shutdown()
        httpd.server_close()


@needs_browser
@needs_node
@pytest.mark.parametrize("width,height", sorted(BOUND_PX))
class TestTheRefusalIsBoundedToo:
    """`UX-451`: the state `UX-435` bounded the group without."""

    def test_the_refusal_really_rendered(self, refused, width, height):
        """The clause every other one here rests on. A run that did not
        refuse would make the three below a second measurement of the
        resting state - which is the defect this item is, one level in.
        """
        seen = refused(width, height)
        assert not seen["hidden"], (
            f"{width}x{height}: the hand-off did not refuse, so nothing "
            f"below measures the refused state: {seen}")
        assert seen["chars"] >= REFUSAL_MIN_CHARS, (
            f"{width}x{height}: the banner holds {seen['chars']} "
            f"characters, under the {REFUSAL_MIN_CHARS} this item measured "
            f"- it is showing something shorter than the refusal")

    def test_the_group_holds_its_resting_bound_while_refused(
            self, refused, width, height):
        """The third bullet of the item, and the reason the numbers in
        `BOUND_PX` did not move: the group is bounded in the mode *and*
        the state where it was largest, by the sentence leaving it
        rather than by the bound being raised."""
        seen = refused(width, height)
        assert seen["group"]["h"] <= BOUND_PX[(width, height)], (
            f"{width}x{height}: refused, the hand-off group is "
            f"{seen['group']['h']}px, over the {BOUND_PX[(width, height)]}px "
            f"the resting state is bounded at - the refusal is being drawn "
            f"in the rail again")
        share = 100.0 * seen["group"]["h"] / seen["rail"]["h"]
        assert share <= BOUND_SHARE[(width, height)], (
            f"{width}x{height}: refused, {share:.1f}% of the rail, over "
            f"{BOUND_SHARE[(width, height)]}%")

    def test_the_sentence_is_not_written_into_the_rail(
            self, refused, width, height):
        """Where it went, asserted structurally rather than by width.

        A width alone could be met by a banner inside the rail that
        overflowed it; containment is the property the fix actually
        has, and it is what keeps the sentence out of the sticky column
        when `app.js` moves the group.
        """
        seen = refused(width, height)
        assert not seen["inTheRail"], (
            f"{width}x{height}: the refusal banner is inside nav.toc, so "
            f"it is back in the rail's column whatever it measures")
        assert seen["banner"]["w"] >= REFUSAL_MIN_W[(width, height)], (
            f"{width}x{height}: the banner is {seen['banner']['w']}px, "
            f"under the {REFUSAL_MIN_W[(width, height)]}px measured - it is "
            f"in a narrower track than the content band")

    def test_the_rail_says_nothing_it_has_no_room_for(
            self, refused, width, height):
        """Exactly one of the two holds the state. Both would be the
        same sentence twice - `UX-371`, the page's repeated text - and
        the rail's copy is the one that does not fit."""
        seen = refused(width, height)
        assert seen["line"] == "", (
            f"{width}x{height}: the rail's status line still carries "
            f"{seen['line']!r} while the banner has the refusal")


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
