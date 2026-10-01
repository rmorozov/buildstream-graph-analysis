"""UX-1192 (styleguide §6e.9): every drawn mark carries its value as a
`<title>`, and a strip whose max exceeds 10x its p90 scales the rest to a
break and names the outlier at its edge.

Measured before the fix on the 1,202-element two-plane page: 16 svgs,
0 titles; the task-share strip ran 0 ms to 4.9 min with p95 at 0.6% of it.
"""

import base64
import gzip
import json
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

#: The 1,202-element two-plane page the review measured.
SCALE_SHAPE = ("--layers", "20", "--width", "60")

#: A drawing's ground, not a mark: the range bar and the axis rule.
GROUND = ".density-range, .interval-rule"

_READ = (
    pages.OPEN_EVERY_DOOR_JS
    + """
(async () => {
  for (const more of document.querySelectorAll("button.show-all-cards")) more.click();
  await new Promise((done) => setTimeout(done, 300));
  const shapes = ":scope > :is(circle, rect, line, polygon, path)";
  const drawings = [...document.querySelectorAll("svg")].map((svg) => {
    const marks = [...svg.querySelectorAll(shapes)].filter((m) => !m.matches(GROUND));
    return {
      where: svg.closest("[data-section]")?.dataset.section + " " + svg.getAttribute("class"),
      marks: marks.length,
      titles: svg.querySelectorAll("title").length,
      bare: marks.filter((m) => !m.querySelector(":scope > title")?.textContent.trim()).length,
      points: svg.dataset.values?.split(",").length ?? null,
      said: new Set([...svg.querySelectorAll("title")].map((t) => t.textContent)).size,
    };
  });
  const strip = (section) => {
    const svg = document.querySelector(`[data-section="${section}"] svg.density-strip`);
    if (!svg) return null;
    return {
      cut: svg.dataset.cut ? Number(svg.dataset.cut) : null,
      max: Number(svg.dataset.max),
      ticks: [...svg.querySelectorAll("line")].map((l) => ({
        mark: l.dataset.mark, x: Number(l.getAttribute("x1")),
        outlier: l.getAttribute("data-outlier"), title: l.querySelector("title")?.textContent,
      })),
    };
  };
  return { drawings, share: strip("wall_clock_share_us"), durations: strip("elements") };
})()
""".replace("GROUND", repr(GROUND))
)


@pytest.fixture(scope="module")
def reads(tmp_path_factory):
    import tools.bga_view as view

    into = tmp_path_factory.mktemp("u1192")
    run = pages.two_plane_run(into, SCALE_SHAPE)
    path = pathlib.Path(into) / "report.html"
    view.export(str(run), str(path))
    # `UX-1194`: the task table's first quantity is the task's own Duration; the share draws its strip without it.
    text = path.read_text(encoding="utf-8")
    packed = re.search(r'id="bga-report-gz">([^<]*)</script>', text)
    report = json.loads(gzip.decompress(base64.b64decode(packed.group(1))))
    del report["task_durations_us"]
    repacked = base64.b64encode(gzip.compress(json.dumps(report).encode())).decode()
    shares = pathlib.Path(into) / "shares.html"
    shares.write_text(text[: packed.start(1)] + repacked + text[packed.end(1) :], encoding="utf-8")
    uris = {"two_plane": path.as_uri(), "shares": shares.as_uri()}
    for label in ("golden", "macro_micro"):
        uris[label] = pages.export_uri(pages.FIXTURES[label], into / label)
    with Browser(chrome) as opened:
        return {label: opened.measure(uri, _READ) for label, uri in uris.items()}


@needs_browser
def test_every_mark_says_its_value(reads):
    for name, read in reads.items():
        drawings = read["drawings"]
        assert drawings, f"{name}: no svg drawn"
        wrong = [d for d in drawings if d["bare"] or d["titles"] != d["marks"]]
        assert not wrong, f"{name}: marks without their one <title>: {wrong}"
        # A series says every point, not only the ones it dots.
        series = [d for d in drawings if d["points"] is not None]
        assert series and all(d["said"] == d["points"] for d in series), f"{name}: {series}"


@needs_browser
def test_a_strip_names_its_outlier_and_scales_the_rest(reads):
    share = reads["shares"]["share"]
    assert share["cut"] is not None and share["cut"] < share["max"], share
    edge = [t for t in share["ticks"] if t["mark"] == "max"][0]
    assert edge["x"] == 100 and edge["outlier"].startswith("toolchain.bst"), edge
    assert edge["title"].startswith("toolchain.bst 4.9 min"), edge
    inside = [t for t in share["ticks"] if t["mark"] != "max"]
    assert all(t["x"] <= 90 for t in inside), inside
    assert max(t["x"] for t in inside) > 50, f"the rest still flattened: {inside}"
    # No outlier: no break, and the max sits at the edge on the one scale.
    durations = reads["two_plane"]["durations"]
    assert durations["cut"] is None, durations
    assert [t["x"] for t in durations["ticks"] if t["mark"] == "max"] == [100], durations
