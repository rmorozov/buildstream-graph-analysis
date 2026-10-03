"""UX-1250: a next-step command names a store run `@<stamp>`, not by its absolute path.

A two-run store, the older run analysed: every argv stays short and
path-free, and each run-taking step resolves, from the project
directory, to the run it was printed for.

Styleguide §1d.
"""

import os
import pathlib
import shutil

import pytest

from bga import cli, findings

REPO = pathlib.Path(__file__).resolve().parents[2]
FIXTURE_RUN = REPO / "tests/fixtures/macro_micro/run"
STAMPS = ("20260101T000000Z", "20260102T000000Z")


class _Result:
    def __init__(self, run_dir):
        self.run_instance = {"run_dir": str(run_dir), "targets": ["app.bst"]}
        self.plane2_coverage = {"covered": 1}


@pytest.fixture
def store(tmp_path):
    project = tmp_path / ("a-deliberately-long-project-directory-name" * 2)
    for stamp in STAMPS:
        shutil.copytree(FIXTURE_RUN, project / ".bga" / "runs" / stamp / "run")
    (project / "project.conf").write_text("name: ux1250\n", encoding="utf-8")
    return project


def _steps(run_dir):
    headline = {
        "top_actions": [{"element_uid": "app.bst", "finding_id": "x"}],
        "diagnosis": findings.DIAGNOSIS_SCHEDULER_BOUND,
    }
    return findings.compute_next_steps(_Result(run_dir), headline)


def test_every_argv_is_short_and_path_free(store):
    steps = _steps(store / ".bga" / "runs" / STAMPS[0] / "run")
    assert {s["id"] for s in steps} >= {"blast-the-top-element", "sweep-the-capacity", "look-inside-the-element"}
    for step in steps:
        line = " ".join(step["argv"])
        assert len(line) <= 60, f"{step['id']}: {len(line)} chars: {line}"
        assert "/.bga/runs/" not in line, f"{step['id']}: {line}"


def test_each_step_resolves_the_run_it_was_printed_for(store, monkeypatch):
    run_dir = store / ".bga" / "runs" / STAMPS[0] / "run"
    monkeypatch.chdir(store)
    parser = cli.create_parser()
    checked = 0
    for step in _steps(run_dir):
        if step["argv"][1] not in ("blast", "sweep", "correlate"):
            continue
        args = parser.parse_args(step["argv"][1:])
        token = args.run if step["argv"][1] == "blast" else args.directory
        assert os.path.realpath(cli.resolve_run_alias(token)) == os.path.realpath(run_dir), step["argv"]
        checked += 1
    assert checked == 3


def test_a_run_outside_a_store_keeps_its_path(tmp_path):
    assert findings.run_token(str(tmp_path / "run")) == str(tmp_path / "run")


def test_a_relative_store_path_is_the_same_run(store, monkeypatch):
    """`UX-1263`: `.bga/runs/<stamp>/run` from the project dir reads as the absolute spelling."""
    relative = os.path.join(".bga", "runs", STAMPS[1], "run")
    monkeypatch.chdir(store)
    assert findings.run_token(relative) == findings.run_token(str(store / relative)) == "@" + STAMPS[1]
    ids = [s["id"] for s in _steps(relative)]
    assert ids == [s["id"] for s in _steps(store / relative)], ids
    assert [s["argv"] for s in _steps(relative)] == [s["argv"] for s in _steps(store / relative)]
