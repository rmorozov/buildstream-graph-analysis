"""UX-1356: `bst build j.bst:x.bst` prints `Targets: x.bst` (bst 2.8.1's
`Element.name`), and the extraction replayed that into `bst show x.bst`,
which the top project cannot find. The typed command qualifies it.
"""

import json
import os
import shutil

import pytest

from tools import bst_extract_run as mod
from tools import bst_native_build_tracer as tracer

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURE_PROJECT = os.path.join(REPO, "tests", "fixtures", "bst_show_project")

BST_AVAILABLE = shutil.which("bst") is not None
BST_SKIP_REASON = "bst not found on PATH - see docs/spec/ingestion-pipeline.md"

_LOG = (
    "[wrapper][2026-01-01 00:00:00,000] INFO: Executing command: {cmd}\n"
    "[wrapper][2026-01-01 00:00:00,001] INFO:     Targets:       {header}\n"
)


def _graph_targets(tmp_path, monkeypatch, cmd, header):
    """The targets `extract_run` hands `bst show`, for a log whose header
    reads `header` and a capture of `cmd`."""
    seen = []

    def _fake(project_dir, targets, bst_bin="bst", bst_options=None):
        seen.append(list(targets))
        return {"elements": [], "dependencies": []}

    monkeypatch.setattr(mod, "extract_graph", _fake)
    log = tmp_path / "build.log"
    log.write_text(_LOG.format(cmd=" ".join(cmd), header=header))
    summary = mod.extract_run(
        str(tmp_path),
        str(log),
        str(tmp_path / "run"),
        log_format="wrapped",
        command_targets=tracer._cmd_targets(cmd),
    )
    assert summary["targets"] == seen[0]
    return seen[0]


def test_the_field_report_reaches_bst_show_qualified(tmp_path, monkeypatch):
    cmd = ["bst", "build", "some_junction.bst:my_recipe.bst"]
    assert _graph_targets(tmp_path, monkeypatch, cmd, "my_recipe.bst") == ["some_junction.bst:my_recipe.bst"]


def test_nested_and_mixed_targets_keep_their_order_past_options(tmp_path, monkeypatch):
    cmd = ["bst", "--max-jobs", "2", "build", "--deps", "all", "top.bst", "a.bst:b.bst:c.bst", "j.bst:x.bst"]
    assert _graph_targets(tmp_path, monkeypatch, cmd, "top.bst, c.bst, x.bst") == [
        "top.bst",
        "a.bst:b.bst:c.bst",
        "j.bst:x.bst",
    ]


def test_two_junctions_shipping_one_name_each_keep_their_own(tmp_path, monkeypatch):
    cmd = ["bst", "build", "j1.bst:x.bst", "j2.bst:x.bst"]
    assert _graph_targets(tmp_path, monkeypatch, cmd, "x.bst, x.bst") == ["j1.bst:x.bst", "j2.bst:x.bst"]


def test_a_top_level_name_and_a_wrapper_script_stand_as_printed():
    assert mod.qualify_targets(["x.bst"], ["x.bst"]) == ["x.bst"]
    assert mod.qualify_targets(["x.bst"], []) == ["x.bst"]
    assert mod.qualify_targets(["x.bst"], ["j.bst:y.bst"]) == ["x.bst"]


def test_the_capture_hands_its_own_command_to_the_extraction(tmp_path, monkeypatch):
    """`tracer.main(["run", "--run-dir", ...])` - the path `bga snapshot`
    takes - with the build faked and `bst show` recorded."""
    seen = []

    def _fake_graph(project_dir, targets, bst_bin="bst", bst_options=None):
        seen.append(list(targets))
        return {"elements": [], "dependencies": []}

    def _fake_build(project_dir, cmd, raw_log_path, wrapped_log_path=None, **kwargs):
        with open(wrapped_log_path, "w", encoding="utf-8") as f:
            f.write(_LOG.format(cmd=" ".join(cmd), header="my_recipe.bst"))
        return 0

    monkeypatch.setattr(mod, "extract_graph", _fake_graph)
    monkeypatch.setattr(tracer, "run_traced_build", _fake_build)
    (tmp_path / "raw.log").write_bytes(b"")
    rc = tracer.main(
        [
            "run",
            "--raw-log",
            str(tmp_path / "raw.log"),
            "--wrapped-log",
            str(tmp_path / "wrapped.log"),
            "--run-dir",
            str(tmp_path / "run"),
            str(tmp_path),
            str(tmp_path / "report.json"),
            "--",
            "/bin/true",
            "build",
            "some_junction.bst:my_recipe.bst",
        ]
    )
    assert rc == 0
    assert seen == [["some_junction.bst:my_recipe.bst"]]


@pytest.mark.bst
@pytest.mark.skipif(not BST_AVAILABLE, reason=BST_SKIP_REASON)
def test_a_real_junctioned_build_extracts_its_own_target(tmp_path):
    from tests.unit._bst_env import bst_env

    cmd = ["bst", "--no-colors", "build", "subproj-junction.bst:libfoo.bst"]
    wrapped_log = str(tmp_path / "wrapped.log")
    with bst_env(tmp_path / "home"):
        tracer.run_traced_build(FIXTURE_PROJECT, cmd, str(tmp_path / "raw.log"), wrapped_log_path=wrapped_log)
        with open(wrapped_log, encoding="utf-8") as f:
            assert "Targets:       libfoo.bst\n" in f.read()
        summary = mod.extract_run(
            FIXTURE_PROJECT,
            wrapped_log,
            str(tmp_path / "run"),
            log_format="wrapped",
            command_targets=tracer._cmd_targets(cmd),
        )
    with open(tmp_path / "run" / "graph.json", encoding="utf-8") as f:
        graph = json.load(f)
    assert summary["targets"] == ["subproj-junction.bst:libfoo.bst"]
    assert [e["uid"] for e in graph["elements"] if e.get("requested_target")] == ["subproj-junction.bst:libfoo.bst"]
