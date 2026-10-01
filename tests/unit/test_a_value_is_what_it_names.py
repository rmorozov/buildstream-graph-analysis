"""UX-1180: a value on the page is the thing its label names.

Four readings that were not: a "Cores busy 983564.29x" over a 0 ms span
(toolchain.bst: 938 ms of CPU over a 1 us wall span), an epoch start
printed as "496481.0 h", and a gate message with a spaced hyphen and a
glued "1.5s". Read on the two-plane page (`gen-synthetic --seed 1
--store --layers 8 --width 14`, 114 elements) and `macro_micro`.
"""

import json
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome
from tests.unit.test_marginal_efficiency_gate import _run_bga, _trio

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

SHAPE = ("--layers", "8", "--width", "14")

_CARDS = r"""
(async () => {
  const out = {};
  for (const uid of %s) {
    location.hash = "#element-" + uid.replace(/[^\w-]+/g, "-");
    await new Promise((done) => setTimeout(done, 200));
    const section = document.getElementById("element-" + uid.replace(/[^\w-]+/g, "-"));
    const text = (section?.textContent ?? "").replace(/\s+/g, " ");
    out[uid] = { built: Boolean(section), cores: /Cores busy/.test(text),
                 duration: text.match(/Duration(\d+ ms|[\d.]+ s)/)?.[1] ?? null };
  }
  return out;
})()
"""

_TEXT = r"""
(() => {
  document.querySelectorAll("details").forEach((d) => { d.open = true; });
  const found = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let node = walker.nextNode(); node; node = walker.nextNode()) {
    const t = node.data.trim();
    if (/(?<![\w.])\d{4,}(\.\d)? h\b/.test(t) || /(?<![\w.])\d{4,}\.\d+×/.test(t)) found.push(t.slice(0, 60));
  }
  const started = [...document.querySelectorAll("dt, th, label")]
    .find((n) => /Started at/.test(n.textContent));
  return { found, started: started?.parentElement?.textContent.replace(/\s+/g, " ") ?? null };
})()
"""


@pytest.fixture(scope="module")
def two_plane(tmp_path_factory):
    into = tmp_path_factory.mktemp("two-plane")
    run = pages.two_plane_run(into, SHAPE)
    import tools.bga_view as view

    page = into / "report.html"
    view.export(str(run), str(page))
    plane2 = json.loads((run.parent / "plane2.json").read_text())
    return page.as_uri(), plane2["cpu_time"]["per_element"]


@needs_browser
class TestNoRatioOverNoSpan:
    def test_no_card_reads_cores_busy_over_a_zero_length_span(self, two_plane):
        uri, per_element = two_plane
        empty = sorted(u for u, e in per_element.items() if e["wall_span_s"] < 0.001 and e["cpu_us"])
        assert empty, "the fixture has no element with CPU over a sub-millisecond span"
        with Browser(chrome) as browser:
            seen = browser.measure(uri, _CARDS % json.dumps(empty))
        assert all(v["built"] for v in seen.values()), seen
        assert [u for u, v in seen.items() if v["cores"]] == [], seen

    def test_a_card_with_a_real_span_still_reads_it(self, two_plane):
        """The instrument sees a ratio when there is one."""
        uri, per_element = two_plane
        real = sorted(
            (u for u, e in per_element.items() if e["wall_span_s"] >= 1 and e["cpu_per_wall_second"]), key=str
        )
        with Browser(chrome) as browser:
            seen = browser.measure(uri, _CARDS % json.dumps(real[:40]))
        assert any(v["cores"] for v in seen.values()), seen


@needs_browser
class TestAnInstantIsNotADuration:
    def test_no_value_reads_an_epoch_as_hours_or_a_ratio_as_thousands(self, tmp_path_factory):
        uri = pages.export_uri(pages.FIXTURES["macro_micro"], tmp_path_factory.mktemp("instant"))
        with Browser(chrome) as browser:
            seen = browser.measure(uri, _TEXT)
        assert seen["found"] == []
        assert re.search(r"Started at, since the epoch\s*\d{4}-\d\d-\d\d \d\d:\d\d:\d\d UTC", seen["started"] or ""), (
            seen
        )


class TestTheGateMessageIsSpaced:
    def test_the_marginal_gate_reads_1_5_s_and_holds_no_spaced_hyphen(self, tmp_path):
        base, _good, bad = _trio(tmp_path, 10)
        failed = _run_bga(["compare", str(base), str(bad), "--fail-on-inefficient-additions"])
        assert "Marginal efficiency gate FAILED" in failed.stderr
        line = " ".join(failed.stderr.split())
        assert re.search(r"\d\.\d s of the \d+\.\d s this change added", line), line
        assert " - " not in line, line
        assert not re.search(r"\d(?:ms|s)\b", line), line
