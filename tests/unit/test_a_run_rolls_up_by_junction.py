"""UX-1327: `bga analyze` rolls a junctioned run up by junction prefix, and `variant-cost` names `junction-cost`."""

import contextlib
import io
import json
import pathlib

import pytest

from bga.cli import create_parser, main
from tests import pages
from tests.fixtures.topologies import nested_junctions, write_run_dir

REPO = pathlib.Path(__file__).resolve().parents[2]

PLAT = "junctions/platform.bst"
BASE = f"{PLAT}:junctions/base.bst"
BUILD_US = 1_000_000
# The committed capture `nested_junctions` writes, read where the census reads it.
RUN = REPO / "tests/fixtures/nested_junctions/run"

# prefix -> (elements, building, assembling, built, cached, build_us, bump blast)
EXPECTED = {
    "": (5, 4, 1, 1, 4, 1 * BUILD_US, None),
    PLAT: (5, 4, 1, 5, 0, 5 * BUILD_US, 11 + 2),
    BASE: (6, 4, 2, 2, 4, 2 * BUILD_US, 6 + 3 + 2),
}


def _analyze(run, fmt):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(io.StringIO()):
        main(["analyze", str(run), "--format", fmt])
    return buffer.getvalue()


@pytest.fixture(scope="module")
def nested():
    return json.loads(_analyze(RUN, "json")), _analyze(RUN, "text")


def test_the_committed_capture_is_what_the_factory_writes():
    run_context, graph, trace = nested_junctions()
    for name, value in (("run-context.json", run_context), ("graph.json", graph), ("trace.json", trace)):
        assert json.loads((RUN / name).read_text()) == value, name


def test_each_element_counts_under_its_deepest_prefix_and_every_level_is_a_row(nested):
    document, _text = nested
    rows = {row["prefix"]: row for row in document["by_junction"]["rows"]}
    assert list(rows) == ["", PLAT, BASE]
    for prefix, (elements, building, assembling, built, cached, build_us, blast) in EXPECTED.items():
        row = rows[prefix]
        got = (
            row["elements"],
            row["building"],
            row["assembling"],
            row["built"],
            row["cached"],
            row["build_us"],
            row["bump_blast_elements"],
        )
        assert got == (elements, building, assembling, built, cached, build_us, blast), prefix
    assert rows[""]["name"] != ""
    assert sum(row["elements"] for row in rows.values()) == document["by_junction"]["graph_elements"] == 16


def test_the_critical_path_seconds_split_by_junction_sum_to_the_path(nested):
    document, _text = nested
    block = document["by_junction"]
    path = sum(row["duration_us"] for row in document["critical_path_detail"])
    assert block["critical_path_us"] == path > 0
    assert sum(row["critical_path_us"] for row in block["rows"]) == path
    assert sum(row["critical_path_share"] for row in block["rows"]) == pytest.approx(1.0)


def test_the_text_report_prints_one_line_per_row(nested):
    _document, text = nested
    section = text.split("By Junction:", 1)[1].split("\n\n", 2)[1]
    lines = section.splitlines()
    assert len(lines) == 4, section
    assert lines[2].split()[:2] == [PLAT, "5"]
    assert lines[3].split()[:3] == [BASE, "6", "4+2"]
    assert lines[3].split()[-1] == "11/16"


def test_a_junction_reused_far_less_than_the_top_project_is_one_finding(nested):
    document, _text = nested
    gaps = [f for f in document["findings"] if f["id"] == "junction-cache-gap"]
    assert len(gaps) == 1
    assert gaps[0]["evidence"]["prefix"] == PLAT
    assert gaps[0]["title"].startswith(f"0.0% cache hits behind {PLAT} against 80.0%")
    assert len(gaps[0]["title"]) <= 100
    # base is 66.7% against 80.0%: inside the 50-point gap, so no line names it.
    assert not any(BASE in line for line in gaps[0]["detail"])


def test_a_caches_off_run_publishes_the_rows_and_no_finding(tmp_path):
    run_context, graph, trace = nested_junctions()
    run_context["queue_summary"]["build"]["skipped"] = 0
    document = json.loads(_analyze(write_run_dir(tmp_path, (run_context, graph, trace)), "json"))
    assert document["confidence"]["run_mode"] == "full"
    assert [row["prefix"] for row in document["by_junction"]["rows"]] == ["", PLAT, BASE]
    assert "junction-cache-gap" not in {f["id"] for f in document["findings"]}


def test_an_unjunctioned_run_has_no_section(tmp_path):
    run = pages.FIXTURES["golden"]
    assert "by_junction" not in json.loads(_analyze(run, "json"))
    assert "By Junction:" not in _analyze(run, "text")


def test_variant_cost_is_the_name_and_junction_cost_its_alias():
    parser = create_parser()
    for name in ("variant-cost", "junction-cost"):
        assert parser.parse_args([name, "a", "b"]).run_dirs == ["a", "b"]
    row = next(line for line in parser.format_help().splitlines() if line.strip().startswith("variant-cost"))
    assert "junction-cost" in row, row
