"""UX-1078: a snapshot writes `tail.json` - one row per phase UX-1077
announces - and the listing, the aggregate and the page carry its sum.

Harness: `test_the_tail_says_what_it_is_doing.project` (the tracer's
`main` for real on the golden run; the build and `bst show` replaced).
"""

import json
import os
import pathlib
import re
import shutil
import stat
import subprocess

import jsonschema
import pytest

from tests.unit.test_the_tail_says_what_it_is_doing import (
    ELAPSED,
    TAIL_PHASES,
    TOTAL,
    tailed_project,
)

REPO = pathlib.Path(__file__).resolve().parents[2]
node = shutil.which("node")


@pytest.fixture
def project(tmp_path, monkeypatch):
    return tailed_project(tmp_path, monkeypatch)


def _snapshot(capsys, *flags):
    from tools.bga_snapshot import main

    assert main(list(flags) + ["--", "bst", "build", "all.bst"]) == 0
    return capsys.readouterr()


def _tails(project_dir):
    from bga import run_store

    return [run_store.read_tail(path) for path in run_store.list_snapshots(str(project_dir))]


def test_the_file_holds_the_phases_the_tail_announced(project, capsys, monkeypatch):
    from bga import schemas

    monkeypatch.setenv("BGA_FORCE_PROGRESS", "1")
    _snapshot(capsys)
    err = _snapshot(capsys).err.splitlines()
    announced = [m.group(1) for m in map(ELAPSED.match, err) if m]
    tail = _tails(project)[-1]
    assert [row["name"] for row in tail["phases"]] == announced == TAIL_PHASES
    assert tail["complete"] is True
    jsonschema.validate(tail, schemas.schema(schemas.TAIL))
    assert all(isinstance(row["wall_us"], int) for row in tail["phases"])


def test_the_listing_carries_the_sum(project, capsys):
    from tools.bga_snapshot import main

    _snapshot(capsys)
    _snapshot(capsys)
    assert main(["--list", "--format", "json"]) == 0
    listing = json.loads(capsys.readouterr().out)
    for row, tail in zip(listing["snapshots"], _tails(project)):
        assert row["bga_tail_us"] == sum(p["wall_us"] for p in tail["phases"] if p.get("stage") != "before")
    assert main(["--list"]) == 0
    text = capsys.readouterr().out
    assert text.count("  bga ") == 2, text


def test_a_nonzero_pre_build_duration_stays_out_of_the_post_build_sum(tmp_path, capsys, monkeypatch):
    """review, pull request 300: `before the build` is measured and kept in
    `tail.json`, but a nonzero readiness check must not land in
    `bga_tail_us` (the store's aggregate) or the total line."""
    root = tailed_project(tmp_path, monkeypatch)
    stub = tmp_path / "path" / "bst"  # tailed_project's stub
    stub.write_text("#!/bin/sh\nsleep 0.2\necho 'BuildStream 2.0.0+stub'\n")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)

    err = _snapshot(capsys).err.splitlines()
    total_line = next(line for line in err if TOTAL.match(line))
    tail = _tails(root)[-1]
    before = next(p for p in tail["phases"] if p["name"] == "before the build")
    assert before["wall_us"] >= 150_000, "the sleep did not land in the phase"
    after_sum = sum(p["wall_us"] for p in tail["phases"] if p["name"] != "before the build")
    full_sum = sum(p["wall_us"] for p in tail["phases"])
    printed_s = float(re.match(r"^bga's own time after the build: (\d+\.\d)s", total_line).group(1))
    assert abs(printed_s - after_sum / 1e6) < 0.1, total_line
    assert printed_s < full_sum / 1e6, "the before-phase leaked into the total"

    from tools.bga_snapshot import main

    assert main(["--list", "--format", "json"]) == 0
    listing = json.loads(capsys.readouterr().out)
    assert listing["snapshots"][-1]["bga_tail_us"] == after_sum


def test_no_compare_has_no_compare_row(project, capsys):
    _snapshot(capsys)
    _snapshot(capsys, "--no-compare")
    names = [row["name"] for row in _tails(project)[-1]["phases"]]
    assert "compare" not in names and "store size" in names


def test_an_interrupted_tail_keeps_its_rows(project, capsys, monkeypatch):
    from tools import bga_snapshot

    _snapshot(capsys)

    def interrupted(*_):
        raise KeyboardInterrupt

    monkeypatch.setattr(bga_snapshot, "_compare", interrupted)
    with pytest.raises(KeyboardInterrupt):
        _snapshot(capsys)
    tail = _tails(project)[-1]
    assert tail["complete"] is False
    assert [row["name"] for row in tail["phases"]] == TAIL_PHASES[:-1]


def _rows(n):
    return [
        {
            "stamp": f"2026010{i}T000000Z",
            "total_duration_us": 10_000_000,
            "bga_tail_us": 1_000_000 * (i + 1),
            "build_wall_us": 9_000_000,
            "incomplete_reason": None,
            "bytes": 1,
        }
        for i in range(n)
    ]


def test_the_aggregate_carries_the_tail():
    from bga.store_aggregate import aggregate, render

    document = aggregate({"project": "p", "snapshots": _rows(5)})
    assert document["host_classes"][0]["bga_tail_us"]["median"] == 3_000_000
    assert document["blended"]["bga_tail_us"]["samples"] == 5
    assert any(line.startswith("    bga after the build:") for line in render(document))


_TREND = r"""
const shim = await import(process.env.BGA_DOM_SHIM);
globalThis._makeNode ??= shim.makeNode;
shim.installDocument();
const views = await import("%(views)s");
const text = (n) => (n.textContent ?? "") + (n.children ?? []).map(text).join("");
console.log(JSON.stringify(text(views.renderTrend(%(store)s, null, null))));
"""


@pytest.mark.skipif(node is None, reason="node is not installed")
def test_the_page_shows_the_tail_beside_the_build():
    script = _TREND % {
        "views": (REPO / "tests/viewer.mjs").as_uri(),
        "store": json.dumps({"snapshots": _rows(3), "count": 3}),
    }
    done = subprocess.run(
        [node, "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        cwd=REPO,
        timeout=120,
        env={**os.environ, "BGA_DOM_SHIM": (REPO / "tests/dom_shim.mjs").as_uri()},
    )
    assert done.returncode == 0, done.stderr[-3000:]
    drawn = json.loads(done.stdout)
    assert "bga after the build" in drawn
    assert "1.0 s beside a 9.0 s build" in drawn, drawn
