"""UX-1042 (styleguide §3l): pointer travel is a budget, per journey.

(a) Placement: each control class's offset within the block it acts on
spreads by at most one target (24 px) across the page, per viewport; dx
passes from either edge. (b) Travel: four journeys' Fitts bits
(`log2(D/W + 1)` per hop, `W` the target's smaller side) and wheel
pixels (the scroll a hop needed) stay under a bound measured on
`macro_micro` and the two-plane 1,202-element page, both size classes.
"""
import functools
import json
import os
import pathlib
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: One target, px (§3l); never widened.
SPREAD = 24
VIEWPORTS = [(1440, 900), (390, 844)]
LABELS = ["macro_micro", "both_scale"]
_BUILD = {
    "both_scale": functools.partial(
        pages.two_plane_run, shape=("--layers", "20", "--width", "60"),
        name="both_scale"),
}

#: The classes held to one place; each block is `blockOf`'s, below.
PLACEMENT = ("button.collapse", "button.describe", "button.json-toggle",
             "button.chapter-open")
#: Measured past 24 px on a2a7dded (dx 204-874) - a placement row to
#: file, never a wider bound; read, not held.
UNPLACED = ("button.copy-rows", "select.top-n")

#: `(label, width): {journey: (bits, wheel px)}`, the median of 3 runs
#: on a2a7dded (spread 0 on every value); J2 is its worst chapter.
MEASURED = {
    ("macro_micro", 1440): {"J1": (4.52, 0), "J2": (18.39, 0),
                            "J3": (15.66, 38444), "J4": (12.77, 11760)},
    ("macro_micro", 390): {"J1": (2.09, 424), "J2": (17.58, 0),
                           "J3": (18.54, 50754), "J4": (9.99, 17694)},
    ("both_scale", 1440): {"J1": (4.48, 0), "J2": (19.60, 0),
                           "J3": (12.48, 45892), "J4": (12.77, 12536)},
    ("both_scale", 390): {"J1": (1.68, 771), "J2": (18.94, 0),
                          "J3": (20.37, 57357), "J4": (10.02, 22213)},
}
HEADROOM_BITS = 0.5
HEADROOM_WHEEL = 1.10
#: Chapters no section of which offers ?, JSON and fold together.
UNOFFERED = {"macro_micro": ["change"], "both_scale": ["compare"]}

_PRELUDE = r"""
const frames = (n) => new Promise((r) => {
  let i = 0;
  const step = () => (++i >= n ? r() : requestAnimationFrame(step));
  requestAnimationFrame(step);
});
// Double rAF, repeated until the scroll position holds.
async function settle() {
  let y = -1;
  for (let i = 0; i < 30 && y !== scrollY; i++) { y = scrollY; await frames(2); }
}
const vis = (n) => { const r = n.getBoundingClientRect(); return r.width > 0 && r.height > 0; };
const $ = (s, root = document) => [...root.querySelectorAll(s)].filter(vis);
let pos = null;
const steps = [];
async function hop(label, n, click = true) {
  if (!n || !vis(n)) { steps.push({label, missing: true}); return; }
  let r = n.getBoundingClientRect();
  let wheel = 0;
  if (r.top < 0 || r.bottom > innerHeight) {
    const y0 = scrollY;
    n.scrollIntoView({block: "center"});
    await settle();
    wheel = Math.abs(scrollY - y0);
    r = n.getBoundingClientRect();
  }
  const c = {x: r.left + r.width / 2, y: r.top + r.height / 2};
  const d = pos ? Math.hypot(c.x - pos.x, c.y - pos.y) : 0;
  const w = Math.min(r.width, r.height);
  steps.push({label, d: Math.round(d), w: Math.round(w), wheel: Math.round(wheel),
              bits: pos ? Math.log2(d / w + 1) : 0});
  pos = c;
  if (click) { n.click(); await settle(); }
}
async function journey(fn) {
  pos = null; steps.length = 0;
  scrollTo(0, 0); await settle();
  await fn();
  return {steps: [...steps]};
}
"""

#: J1, J3, then placement with every chapter open, then J4 - one load.
_DOCUMENT = "(async () => {" + _PRELUDE + r"""
  const out = {};
  out.J1 = await journey(async () => {
    await hop("verdict", $(".diagnosis")[0], false);
    await hop("first next step's Copy", $("button.primary")[0]);
  });
  out.J3 = await journey(async () => {
    for (const b of $("section.chapter button.chapter-open")) {
      await hop("chapter " + b.getAttribute("data-chapter-open"), b);
    }
  });
  const shut = [...document.querySelectorAll("button.chapter-open")]
    .filter((b) => b.getAttribute("aria-expanded") !== "true").length;
  const head = (n) => {
    const s = n.closest("section[data-section]");
    const h = s && s.querySelector("h2, h3");
    return h && h.contains(n) ? h : null;
  };
  const blockOf = {
    "button.collapse": head,
    "button.json-toggle": head,
    // `attachBlockDoor` prepends the door to the block it describes.
    "button.describe": (n) => head(n) || n.closest("h2, h3, h4") || n.parentNode,
    "button.chapter-open": (n) => n.closest("h2.chapter-title"),
    "button.copy-rows": (n) => n.closest(".table-tools")?.parentNode,
    "select.top-n": (n) => n.closest(".table-tools")?.parentNode,
  };
  const placement = {};
  for (const [cls, find] of Object.entries(blockOf)) {
    placement[cls] = [];
    for (const n of $(cls)) {
      const b = find(n);
      if (!b) continue;
      const r = n.getBoundingClientRect(), br = b.getBoundingClientRect();
      placement[cls].push({left: r.left - br.left, right: br.right - r.right,
                           top: r.top - br.top});
    }
  }
  out.placement = {shut, classes: placement};
  let table = null;
  out.J4 = await journey(async () => {
    // The longest table offering the full tool row (`viewstate.js`'s lookup).
    const tools = (t) => t.parentNode?.querySelector(":scope > .table-tools");
    const t = $("table[data-table]")
      .filter((t) => tools(t)?.querySelector("input.table-filter") && t.querySelector("input.th-filter"))
      .sort((a, b) => b.rows.length - a.rows.length)[0];
    const row = t && tools(t);
    await hop("table filter", row && $("input.table-filter", row)[0], false);
    await hop("top-n", row && $("select.top-n", row)[0], false);
    await hop("first column filter", t && $("input.th-filter", t)[0], false);
    await hop("sort first header", t && $("th", t)[0]);
    await hop("copy rows", row && $("button.copy-rows", row)[0], false);
    table = t && t.getAttribute("data-table");
  });
  out.J4.table = table;
  out.chapters = [...document.querySelectorAll("nav.toc button.toc-chapter-open")]
    .map((b) => b.getAttribute("data-toc-chapter"));
  return out;
})()"""

#: J2 for one chapter: rail row, its first section, ?, JSON twice, fold.
_RAIL = "(async () => {" + _PRELUDE + r"""
  const nav = document.querySelector("nav.toc");
  let folded = nav.getAttribute("data-folded");
  if (folded === "true") {
    nav.querySelector(".toc-title").click(); await settle();
    folded = nav.getAttribute("data-folded");
  }
  const cid = __CHAPTER__;
  const DOORS = ["button.describe", "button.json-toggle", "button.collapse"];
  let walked = true;
  const j = await journey(async () => {
    await hop("rail row", nav.querySelector(`button.toc-chapter-open[data-toc-chapter="${cid}"]`));
    // The chapter's first section offering all three; none walks no further.
    const target = (a) => document.getElementById(a.getAttribute("href").slice(1));
    const owned = (sec, s) => [...sec.querySelectorAll(s)]
      .filter((n) => n.closest("section[data-section]") === sec)[0];
    const offers = (a) => { const s = target(a); return s && DOORS.every((d) => owned(s, d)); };
    const link = $(`li[data-chapter="${cid}"] a[data-toc]`, nav).find(offers);
    if (!link) { walked = false; return; }
    await hop("rail section link", link);
    const sec = target(link);
    const own = (s) => owned(sec, s);
    await hop("?", own("button.describe"));
    await hop("JSON", own("button.json-toggle"));
    await hop("JSON (close)", own("button.json-toggle"));
    await hop("fold", own("button.collapse"));
  });
  j.folded = folded;
  j.walked = walked;
  return j;
})()"""


def totals(journey):
    """`(bits, wheel px, missing labels)` over one journey's hops."""
    hops = journey["steps"]
    return (sum(h.get("bits", 0) for h in hops),
            sum(h.get("wheel", 0) for h in hops),
            [h["label"] for h in hops if h.get("missing")])


def spread(values):
    return max(values) - min(values)


def walk(browser, uri, width, height):
    """Every journey on one page at one viewport, J2 per chapter."""
    out = browser.measure(uri, _DOCUMENT, width, height)
    out["J2"] = {cid: browser.measure(
        uri, _RAIL.replace("__CHAPTER__", json.dumps(cid)), width, height)
        for cid in out["chapters"]}
    return out


def build(root):
    """`{label: file uri}` under `root`, a fixed-length path: the page
    prints the run's path, and a longer one wraps differently."""
    made = {}
    into = root / "macro_micro"
    made["macro_micro"] = pages.export_uri(pages.FIXTURES["macro_micro"],
                                           into, "macro_micro.html")
    for label, make in _BUILD.items():
        into = root / label
        made[label] = pages.in_place_uri(make(into), into, f"{label}.html")
    return made


@pytest.fixture(scope="module")
def browser():
    with Browser(chrome) as opened:
        yield opened


@pytest.fixture(scope="module")
def walked(browser):
    root = pathlib.Path(f"/tmp/bga-travel-{os.getpid():010d}")
    shutil.rmtree(root, ignore_errors=True)
    try:
        uris = build(root)
        yield {(label, size): walk(browser, uris[label], *size)
               for label in LABELS for size in VIEWPORTS}
    finally:
        shutil.rmtree(root, ignore_errors=True)


def _page(size):
    return f"{size[0]}x{size[1]}"


@needs_browser
@pytest.mark.parametrize("label", LABELS)
@pytest.mark.parametrize("size", VIEWPORTS, ids=_page)
@pytest.mark.parametrize("cls", PLACEMENT)
def test_a_control_class_sits_at_one_place(walked, label, size, cls):
    placement = walked[label, size]["placement"]
    assert placement["shut"] == 0, f"{label}: J3 left chapters shut"
    rows = placement["classes"][cls]
    assert rows, f"{label} at {_page(size)}: no visible {cls} in its block"
    dx = min(spread([r["left"] for r in rows]),
             spread([r["right"] for r in rows]))
    dy = spread([r["top"] for r in rows])
    assert dx <= SPREAD and dy <= SPREAD, (
        f"{label} at {_page(size)}: {len(rows)} {cls}, offset in its block "
        f"spreads dx {dx:.1f}px (the nearer edge), dy {dy:.1f}px > {SPREAD}px "
        f"(styleguide §3l)")


@needs_browser
@pytest.mark.parametrize("label", LABELS)
@pytest.mark.parametrize("size", VIEWPORTS, ids=_page)
@pytest.mark.parametrize("name", ["J1", "J2", "J3", "J4"])
def test_a_journey_stays_under_its_budget(walked, label, size, name):
    out = walked[label, size]
    if name == "J2":
        runs = out["J2"]
        assert all(j["folded"] == "false" for j in runs.values()), (
            f"{label} at {_page(size)}: the rail did not open")
        unwalked = sorted(c for c, j in runs.items() if not j["walked"])
        assert unwalked == UNOFFERED[label], (
            f"{label}: chapters with no section offering ?, JSON and fold "
            f"are {unwalked}, not {UNOFFERED[label]}")
        walks = [totals(j) for j in runs.values() if j["walked"]]
    else:
        walks = [totals(out[name])]
    missing = [m for w in walks for m in w[2]]
    assert not missing, f"{label} at {_page(size)}: {name} lost hops {missing}"
    bits = max(w[0] for w in walks)
    wheel = max(w[1] for w in walks)
    base_bits, base_wheel = MEASURED[label, size[0]][name]
    assert bits <= base_bits + HEADROOM_BITS, (
        f"{label} at {_page(size)}: {name} is {bits:.2f} Fitts bits, measured "
        f"{base_bits} + {HEADROOM_BITS} (styleguide §3l)")
    assert wheel <= base_wheel * HEADROOM_WHEEL, (
        f"{label} at {_page(size)}: {name} needs {wheel}px of wheel, measured "
        f"{base_wheel} x {HEADROOM_WHEEL} (styleguide §3l)")
