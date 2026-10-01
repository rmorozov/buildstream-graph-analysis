"""UX-1254: one card answers what this build wants from this host, each value read off the section it links."""

import json
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
        "observed": rec["builders"],
        "source": "capacity_recommendation",
    }
    assert (card["cores"]["average"], card["cores"]["host"]) == (rec["cores_busy"], rec["host_cpu_count"])
    peak = max(row["peak_rss_bytes"] for row in two_plane["element_join"] if row.get("peak_rss_bytes"))
    memory = card["memory"]
    assert memory["per_element_bytes"] == peak, (memory, peak)
    assert memory["bytes"] == peak * rec["recommended_builders"], memory
    for field in ("builders", "cores", "memory"):
        assert card[field]["source"] in two_plane, (field, card[field]["source"])
    assert card["absence"] is None and card["caveat"] == rec["caveat"]


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
    rows = {row["field"]: row for row in got["rows"]}
    assert sorted(rows) == ["builders", "cores", "memory"], rows
    for field, row in rows.items():
        assert row["links"] == [f"#{two_plane['agent_sizing'][field]['source']}"] and row["lands"], row
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
