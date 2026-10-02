"""UX-1252: a run of zero or absent values in one block is one sentence.

Styleguide §6e.12: no `dl.pairs` draws two consecutive absent (none,
empty) rows or two consecutive zero rows; UX-1270: the two groups are
"Not recorded" and "Zero", a boolean keeps its row, no dt reads "None";
the rail's "· save trace" never puts its separator on a line alone; an
absence names the series its question reads. The JSON view keeps every
field.
"""

import contextlib
import json
import os
import pathlib
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

_MEASURE = r"""
(async () => {
  document.querySelectorAll("details").forEach((d) => { d.open = true; });
  await new Promise((done) => setTimeout(done, 50));
  const clear = (dd) => {
    const value = dd.firstElementChild;
    // A bucket's advice keeps its row (`UX-390`, `test_one_bucket_one_row.py`).
    if (dd.querySelector("p.run-advice")) return false;
    const text = (value?.textContent ?? "").trim();
    // A share answers or checks its block and keeps its row, zero or not.
    if (text.endsWith("%")) return false;
    const raw = value?.getAttribute("data-raw");
    if (raw === "0" || /^(0|0 ms)$/.test(text)) return "zero";
    return raw === "" || text === "none" ? "absent" : false;
  };
  const runs = [];
  for (const list of document.querySelectorAll("dl.pairs")) {
    const dds = [...list.children].filter((n) => n.tagName === "DD");
    for (let i = 1; i < dds.length; i += 1) {
      if (clear(dds[i - 1]) && clear(dds[i - 1]) === clear(dds[i])) {
        runs.push(`${list.closest("[id]")?.id}: ${dds[i - 1].previousElementSibling?.textContent} + ${dds[i].previousElementSibling?.textContent}`);
      }
    }
  }
  const lines = (node) => {
    const range = document.createRange();
    range.selectNodeContents(node);
    // A line is a band of rects that overlap vertically; a separator alone is a second band.
    let bottom = -Infinity, count = 0;
    for (const r of [...range.getClientRects()].filter((r) => r.width > 0).sort((a, b) => a.top - b.top)) {
      if (r.top >= bottom - 1) count += 1;
      bottom = Math.max(bottom, r.bottom);
    }
    return count;
  };
  const rail = [...document.querySelectorAll("#actions-fallback, #actions-download")]
    .filter((node) => !node.hidden && node.getClientRects().length)
    .map((node) => ({ id: node.id, lines: lines(node) }));
  // The answer to `#cache`'s question is a share; it keeps its row.
  const answer = document.querySelector('section[data-section="cache"] dl.pairs > dt[data-key="hit_share"]');
  for (const door of document.querySelectorAll("button.describe")) door.click();
  const opened = [...document.querySelectorAll("dl.pairs > dt[data-none] + dd > .description")]
    .filter((n) => !n.hidden).map((n) => ({
      text: n.textContent.slice(0, 60),
      labelled: [...n.parentElement.querySelectorAll(":scope > span[data-key]")]
        .some((name) => getComputedStyle(n, "::before").content === `"${name.textContent.replace(/[,.]\s*$/, "")}: "`),
      block: getComputedStyle(n).display === "block" }));
  const none = [...document.querySelectorAll("dl.pairs > dt")].filter((dt) => dt.textContent.trim() === "None").length;
  return { runs, none, folded: document.querySelectorAll("dl.pairs > dt[data-none]").length, rail,
           answer: answer !== null, opened };
})()
"""


@pytest.fixture(scope="module", params=["macro_micro", "two_plane"])
def measured(request, tmp_path_factory):
    into = tmp_path_factory.mktemp(f"u1252-{request.param}")
    with contextlib.ExitStack() as stack:
        if request.param == "two_plane":
            # Served: the save-trace link is drawn only with a server behind the trace.
            uri = stack.enter_context(pages.served_store_page(into, runs=2))
        else:
            uri = pages.export_uri(pages.FIXTURES[request.param], into)
        with Browser(chrome) as opened:
            result = {width: opened.measure(uri, _MEASURE, width=width, height=844) for width in (1440, 390)}
    return request.param, result


@needs_browser
class TestAllClear:
    def test_no_block_draws_two_clear_rows_running(self, measured):
        label, result = measured
        for width, got in result.items():
            assert got["runs"] == [], (label, width, got["runs"][:5])
            assert got["folded"] > 0, (label, width)
            assert got["none"] == 0, (label, width)

    def test_the_row_that_answers_the_block_is_not_folded(self, measured):
        label, result = measured
        if label != "macro_micro":
            pytest.skip("`#cache` reads a zero hit share on macro_micro")
        for width, got in result.items():
            assert got["answer"], (label, width)

    def test_an_opened_folded_sentence_is_its_own_labelled_line(self, measured):
        label, result = measured
        for width, got in result.items():
            assert got["opened"], (label, width)
            assert all(o["labelled"] and o["block"] for o in got["opened"]), (label, width, got["opened"][:3])

    def test_the_rail_separator_keeps_its_link(self, measured):
        label, result = measured
        if label != "two_plane":
            pytest.skip("only a served page draws the save-trace link")
        for width, got in result.items():
            assert got["rail"], (label, width)
            assert all(entry["lines"] == 1 for entry in got["rail"]), (label, width, got["rail"])


_PLANTED = """
const { renderPairs } = await import("./tests/viewer.mjs");
(await import(process.env.BGA_DOM_SHIM)).installDocument();
const out = renderPairs("planted", { a: null, b: 0, c: false, d: 0, e: null });
console.log(JSON.stringify(out.querySelectorAll("dl.pairs > dt").map((dt) =>
  [dt.textContent, dt.getAttribute("data-none") ?? dt.getAttribute("data-key")])));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_a_planted_block_groups_absent_and_zero_apart_and_keeps_its_boolean():
    """UX-1270: {a: null, b: 0, c: false, d: 0, e: null}."""
    run = subprocess.run(
        [shutil.which("node"), "--input-type=module", "-e", _PLANTED],
        capture_output=True,
        text=True,
        cwd=REPO,
        env=os.environ,
        timeout=60,
    )
    assert run.returncode == 0, run.stderr
    terms = dict(json.loads(run.stdout))
    assert terms == {"Not recorded": "a e", "Zero": "b d", "C": "c"}, terms


def test_the_cores_absence_names_the_cpu_series():
    from bga import schemas
    from bga.analyzer import analyze_run

    envelope = analyze_run(REPO / "tests/fixtures/golden/mixed_task_kinds").utilization_envelope
    question = schemas.schema("analyze/v7")["properties"]["utilization_envelope"]["bga:question"]
    assert "cores" in question
    assert "CPU" in envelope["absence"] and "memory" not in envelope["absence"], envelope
