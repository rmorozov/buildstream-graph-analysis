"""UX-1192 (styleguide §6e.9): every drawn mark carries its value as a
`<title>`, and a strip whose max exceeds 10x its p90 scales the rest to a
break and names the outlier at its edge. UX-1204: the band, the store
trend and an element's history title every mark, through the node
harness (no built page draws them); at 390 the uid box holds its
placeholder and every opened SQL paste fits its `.investigate`.

Measured before the fix on the 1,202-element two-plane page: 16 svgs,
0 titles; the task-share strip ran 0 ms to 4.9 min with p95 at 0.6% of it.
"""

import base64
import gzip
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

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


#: UX-1204: the uid box's placeholder against its content box; every SQL paste, opened, against its block.
_NARROW = r"""
(async () => {
  for (const pre of document.querySelectorAll(".investigate pre.query")) pre.removeAttribute("hidden");
  await new Promise((done) => setTimeout(done, 100));
  const box = document.querySelector("[data-role=query-element]");
  const cs = box && getComputedStyle(box);
  const ctx = document.createElement("canvas").getContext("2d");
  if (box) ctx.font = cs.font;
  return {
    box: box && { need: Math.ceil(ctx.measureText(box.placeholder).width),
                  have: box.clientWidth - parseFloat(cs.paddingLeft) - parseFloat(cs.paddingRight) },
    pastes: [...document.querySelectorAll(".investigate pre.query")].map((pre) => ({
      // The block's column too: an unwrapped paste widens its `.investigate` with it.
      wide: pre.scrollWidth, room: Math.min(pre.closest(".investigate").clientWidth,
                                            pre.closest(".investigate").parentElement.clientWidth) })),
  };
})()
"""


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
    # The outlier is planted: the analyzer's 4.9 min share for a 0 ms task was a defect (`UX-1194` follow-up).
    report["wall_clock_share_us"]["toolchain.bst|BUILD|BUILD|0"] = 291_775_000
    repacked = base64.b64encode(gzip.compress(json.dumps(report).encode())).decode()
    shares = pathlib.Path(into) / "shares.html"
    shares.write_text(text[: packed.start(1)] + repacked + text[packed.end(1) :], encoding="utf-8")
    uris = {"two_plane": path.as_uri(), "shares": shares.as_uri()}
    for label in ("golden", "macro_micro"):
        uris[label] = pages.export_uri(pages.FIXTURES[label], into / label)
    with Browser(chrome) as opened:
        out = {label: opened.measure(uri, _READ) for label, uri in uris.items()}
        out["narrow"] = opened.measure(uris["two_plane"], _NARROW, 390, 844)
        return out


@needs_browser
def test_every_mark_says_its_value(reads):
    for name, read in reads.items():
        if name == "narrow":
            continue
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
    # Scaled to the cut, the rest spreads 10x wider than on the outlier's one scale (where the cut sits at 100*cut/max).
    assert max(t["x"] for t in inside) > 10 * 100 * share["cut"] / share["max"], f"the rest still flattened: {inside}"
    # No outlier: no break, and the max sits at the edge on the one scale.
    durations = reads["two_plane"]["durations"]
    assert durations["cut"] is None, durations
    assert [t["x"] for t in durations["ticks"] if t["mark"] == "max"] == [100], durations


@needs_browser
def test_the_uid_box_and_an_opened_sql_paste_fit_390(reads):
    narrow = reads["narrow"]
    assert narrow["box"]["need"] <= narrow["box"]["have"], narrow["box"]
    assert narrow["pastes"], "no .investigate paste on the two-plane page"
    over = [p for p in narrow["pastes"] if p["wide"] > p["room"]]
    assert over == [], (len(narrow["pastes"]), over[:3])


_HARNESS = r"""
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;
_installDocument();
globalThis.document.createElementNS = (ns, tag) => globalThis.document.createElement(tag);
const all = (n, pred, out = []) => {
  if (pred(n)) out.push(n);
  for (const c of n.children ?? []) all(c, pred, out);
  return out;
};
const text = (n) => !n ? "" : ((n.children ?? []).length
  ? (n._text ?? "") + n.children.map(text).join("") : (n._text ?? ""));
const mod = await import("./tests/viewer.mjs");
const shapes = new Set(["circle", "rect", "line", "polygon", "path"]);
const read = (block) => {
  const svg = all(block, (n) => n.attrs?.role === "img")[0];
  const marks = (svg.children ?? []).filter((n) => shapes.has(String(n.tagName).toLowerCase()));
  return { marks: marks.length, bare: marks.filter((m) => !(m.children ?? []).some(
    (c) => String(c.tagName).toLowerCase() === "title" && text(c).trim())).map((m) => m.attrs.class) };
};
"""

_BAND = {
    "baseline_band": {
        "band_low_us": 100,
        "band_high_us": 200,
        "observed_low_us": 80,
        "observed_high_us": 260,
        "runs": [90, 150, 250],
    },
    "candidate": {"total_duration_us": 230},
}
_STORE = {
    "schema": "store/v1",
    "count": 3,
    "snapshots": [
        {
            "stamp": s,
            "bytes": 1,
            "incomplete_reason": None,
            "total_duration_us": d,
            "verdict_kind": v,
            "elements": [{"element_uid": "elt", "duration_us": d, "on_critical_path": True}],
        }
        for s, d, v in (("a", 1_000_000, None), ("b", 5_000_000, "regressed"), ("c", 2_000_000, None))
    ],
}
_AGGREGATE = {"blended": {"mixes": 1, "duration_us": {"samples": 3, "median": 2_000_000, "p95": 5_000_000}}}


@needs_node
def test_the_band_the_trend_and_the_history_title_every_mark():
    source = (
        _HARNESS
        + f"""
console.log(JSON.stringify({{
  band: read(mod.renderBand({json.dumps(_BAND)})),
  trend: read(mod.renderTrend({json.dumps(_STORE)}, undefined, {json.dumps(_AGGREGATE)})),
  history: read(mod.renderElementHistory({json.dumps(_STORE)}, "elt", null)),
}}));
"""
    )
    result = subprocess.run(
        [node, "--input-type=module", "-e", source],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=90,
        env=dict(os.environ, BGA_DOM_SHIM=str(REPO / "tests" / "dom_shim.mjs")),
    )
    assert result.returncode == 0, result.stderr[-3000:]
    out = json.loads(result.stdout)
    assert out["band"]["marks"] == 6 and out["trend"]["marks"] == 5 and out["history"]["marks"] == 3, out
    assert {k: v["bare"] for k, v in out.items() if v["bare"]} == {}, out
