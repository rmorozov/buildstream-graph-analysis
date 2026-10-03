"""UX-1254: one card answers what this build wants from this host, each value read off the section it links.

Styleguide §3a."""

import json
import os
import pathlib
import shutil
import subprocess
import sys
from types import SimpleNamespace

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga.correlate import compute_agent_sizing
from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
MACRO = REPO / "tests/fixtures/macro_micro"
ABSENT = "Cores and memory need Plane 2, which this run did not capture."
VIEWPORTS = [(1440, 900), (390, 844)]

_READ = r"""
(() => {
  const card = document.querySelector('[data-section="agent_sizing"]');
  const chapter = document.querySelector('section.chapter[data-chapter="machine"]');
  const rows = card ? [...card.querySelectorAll("[data-field]")].map((p) => ({
    field: p.dataset.field, text: p.textContent,
    links: [...p.querySelectorAll("a")].map((a) => a.getAttribute("href")),
    lands: [...p.querySelectorAll("a")].every((a) => document.getElementById(a.getAttribute("href").slice(1))) })) : [];
  return {
    first: chapter?.querySelector(":scope > section[data-section]")?.dataset.section ?? null,
    rows,
    absence: card?.querySelector("p.empty-population")?.textContent ?? null,
  };
})()
"""


def _analyze(run, *extra):
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(run), *extra, "--format", "json"],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=300,
    )
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


@pytest.fixture(scope="module")
def two_plane():
    return _analyze(MACRO / "run", "--plane2", str(MACRO / "plane2.json"))


@pytest.fixture(scope="module")
def plane1():
    return _analyze(pages.FIXTURES["golden"])


def test_each_value_equals_its_source_section(two_plane):
    card, rec = two_plane["agent_sizing"], two_plane["capacity_recommendation"]
    graph = next(c["allows"] for c in rec["constraints"] if c["name"] == "graph")
    assert card["builders"] == {
        "recommended": rec["recommended_builders"],
        "graph_ceiling": graph,
        "swept_to": len(rec["sweep"]),
        "observed": rec["builders"],
        "source": "capacity_recommendation",
    }
    assert (card["cores"]["average"], card["cores"]["host"]) == (rec["cores_busy"], rec["host_cpu_count"])
    peak = max(row["peak_rss_bytes"] for row in two_plane["element_join"] if row.get("peak_rss_bytes"))
    memory = card["memory"]
    assert memory["per_element_bytes"] == peak, (memory, peak)
    assert memory["bytes"] == peak * rec["recommended_builders"], memory
    assert (memory["basis"], memory["bound"]) == ("envelope", "upper"), memory
    for field in ("builders", "cores", "memory"):
        assert card[field]["source"] in two_plane, (field, card[field]["source"])
    assert card["absence"] is None and "caveat" not in card, card


def test_plane1_only_says_cores_and_memory_are_absent(plane1):
    card = plane1["agent_sizing"]
    assert (card["cores"], card["memory"], card["absence"]) == (None, None, ABSENT), card


@pytest.fixture(scope="module")
def read(tmp_path_factory):
    root = tmp_path_factory.mktemp("agent-sizing")
    uris = {label: pages.export_uri(pages.FIXTURES[label], root / label, f"{label}.html") for label in pages.FIXTURES}
    with Browser(chrome) as browser:
        got = {(label, w): browser.measure(uri, _READ, w, h) for label, uri in uris.items() for w, h in VIEWPORTS}
    shutil.rmtree(root, ignore_errors=True)
    return got


@needs_browser
@pytest.mark.parametrize("width", [w for w, _ in VIEWPORTS])
def test_the_card_leads_the_machine_chapter_with_one_link_a_row(read, two_plane, width):
    got = read[("macro_micro", width)]
    assert got["first"] == "agent_sizing", got["first"]
    card = two_plane["agent_sizing"]
    rows = {row["field"]: row for row in got["rows"]}
    peak = ["cores_peak"] if card["cores"]["peak_source"] else []
    assert sorted(rows) == sorted(["builders", "cores", "memory", *peak]), rows
    for field, row in rows.items():
        src = card["cores"]["peak_source"] if field == "cores_peak" else card[field]["source"]
        assert row["links"] == [f"#{src}"] and row["lands"], row
    assert "at most" in rows["memory"]["text"] and "memory envelope" in rows["memory"]["text"], rows["memory"]
    assert f"{two_plane['capacity_recommendation']['cores_busy']:.2f} of 4" in rows["cores"]["text"], rows["cores"]
    assert "2 recommended" in rows["builders"]["text"] and "graph allows 2" in rows["builders"]["text"]
    assert got["absence"] is None


@needs_browser
@pytest.mark.parametrize("width", [w for w, _ in VIEWPORTS])
def test_the_plane1_card_reads_one_absence_sentence(read, width):
    got = read[("golden", width)]
    assert got["first"] == "agent_sizing", got["first"]
    assert [row["field"] for row in got["rows"]] == ["builders"], got["rows"]
    assert got["absence"] == ABSENT, got["absence"]


#: UX-1272: the 2,402-element page's sizing inputs: 4 builders, no host RAM, a 64.0 MiB largest process.
_HOST = SimpleNamespace(
    capacity_recommendation={"builders": 4, "recommended_builders": 4, "constraints": [], "caveat": "c"},
    plane2_capacity={"cores_busy": 0.86, "host_cpu_count": 4},
    memory_envelope={},
    utilization_envelope={"available": True, "busy_cores_p95": 3.25},
    plane2_report={"peak_memory": {"per_element": {"a.bst": {"peak_rss_kb": 65536}, "b.bst": {"peak_rss_kb": 1024}}}},
)


def test_no_host_ram_still_sizes_memory_from_the_process_peaks():
    memory = compute_agent_sizing(_HOST)["memory"]
    assert memory == {
        "per_element_bytes": 65536 * 1024,
        "builders": 4,
        "bytes": 4 * 65536 * 1024,
        "basis": "process_peak",
        "bound": "none",
        "source": "peak_memory",
    }, memory


def test_a_host_cpu_series_gives_the_peak_its_own_link():
    cores = compute_agent_sizing(_HOST)["cores"]
    assert (cores["peak"], cores["peak_source"]) == (3.25, "utilization_envelope"), cores


_PROBE = """
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;
_installDocument();
const app = await import("./tests/viewer.mjs");
const text = (n) => !n ? "" : (n._text ?? "") + (n.children ?? []).map(text).join("");
const all = (n, pred, out = []) => {
  if (n && pred(n)) out.push(n);
  for (const c of n?.children ?? []) all(c, pred, out);
  return out;
};
const card = app.renderSection("agent_sizing", JSON.parse(process.env.CARD), {}, undefined, null, {}, {});
console.log(JSON.stringify(all(card, (n) => n.attrs?.["data-field"]).map((row) => ({
  field: row.attrs["data-field"], text: text(row),
  links: all(row, (n) => n.tagName === "a").map((a) => a.attrs.href) }))));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_the_peak_row_says_it_is_no_bound():
    card = compute_agent_sizing(_HOST)
    done = subprocess.run(
        [shutil.which("node"), "--input-type=module", "-e", _PROBE],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=60,
        env=dict(os.environ, BGA_DOM_SHIM=str(REPO / "tests" / "dom_shim.mjs"), CARD=json.dumps(card)),
    )
    assert done.returncode == 0, done.stderr[-3000:]
    rows = {row["field"]: row for row in json.loads(done.stdout)}
    assert [rows[f]["links"] for f in ("builders", "cores", "cores_peak", "memory")] == [
        ["#capacity_recommendation"],
        ["#capacity_recommendation"],
        ["#utilization_envelope"],
        ["#peak_memory"],
    ], rows
    assert "3.25 busy at p95" in rows["cores_peak"]["text"], rows["cores_peak"]
    memory = rows["memory"]["text"]
    # UX-1272: one process's peak per builder bounds nothing, in either direction.
    assert "at most" not in memory and "at least" not in memory, memory
    assert "4 builders \u00d7 the largest single process (64.0 MiB) = 256.0 MiB; not a bound" in memory, memory
