"""UX-1083 (review, PR #300): a fresh `graph.json` is extracted under the
build's own graph-affecting `bst` global options - `-o variant b` builds
graph variant B, not the default - and a reused one is only ever B's.
"""
import json
import os
import shutil
import subprocess

import pytest

from tools import bst_extract_run as mod
from tools import bst_native_build_tracer as tracer

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
FIXTURE_PROJECT = os.path.join(REPO, "tests", "fixtures", "bst_option_project")

BST_AVAILABLE = shutil.which("bst") is not None
BST_SKIP_REASON = "bst not found on PATH - see docs/spec/ingestion-pipeline.md"

_LOG = (
    "[wrapper][2026-01-01 00:00:00,000] INFO: Executing command: {cmd}\n"
    "[wrapper][2026-01-01 00:00:00,001] INFO: Targets:       app.bst\n"
)


# --- Which options reach `bst show` (hermetic) ----------------------------

def test_only_the_graph_affecting_options_are_kept_in_order():
    cmd = ["bst", "--no-colors", "--max-jobs", "3", "-o", "variant", "b",
           "--log-file", "-o", "--config", "c.yml", "-C", "sub", "--strict",
           "--directory=sub2", "--builders", "2", "build", "app.bst"]
    opts = tracer._bst_global_options(cmd)[0]
    assert mod._graph_affecting_options(opts) == [
        "-o", "variant", "b", "--config", "c.yml", "-C", "sub", "--strict",
        "--directory=sub2"]


def test_extract_run_hands_the_options_to_bst_show_with_one_max_jobs(tmp_path, monkeypatch):
    calls = []

    def _fake(project_dir, targets, bst_bin="bst", bst_options=None):
        calls.append(list(bst_options or []))
        return {"elements": [{"uid": "app.bst", "cache_key": "k", "requested_target": True,
                              "max_jobs": 2, "notparallel": None, "element_kind": "manual"}],
                "dependencies": []}

    monkeypatch.setattr(mod, "extract_graph", _fake)
    cmd = ["bst", "--max-jobs", "2", "-o", "variant", "b", "build", "app.bst"]
    log = tmp_path / "build.log"
    log.write_text(_LOG.format(cmd=" ".join(cmd)))
    mod.extract_run(str(tmp_path), str(log), str(tmp_path / "run"), log_format="wrapped",
                    bst_global_options=tracer._bst_global_options(cmd)[0])
    assert calls == [["-o", "variant", "b", "--max-jobs", "2"]]


# --- Real bst, two variants (bst-marked) ----------------------------------

def _option_aware_graph(global_opts):
    """An independent `bst <opts> show --deps all`: the element set, each
    key, and every (predecessor, successor) pair."""
    import yaml
    proc = subprocess.run(
        ["bst", *global_opts, "--no-colors", "show", "--deps", "all", "--format",
         "%{name}\x1e%{key}\x1e%{build-deps}\x1e%{runtime-deps}\x1d", "app.bst"],
        cwd=FIXTURE_PROJECT, capture_output=True, text=True, check=True,
        stdin=subprocess.DEVNULL)
    elements, edges = {}, set()
    for record in proc.stdout.split("\x1d"):
        if not record.strip():
            continue
        name, key, build_deps, runtime_deps = record.strip().split("\x1e")
        elements[name] = key
        for dep in (yaml.safe_load(build_deps) or []) + (yaml.safe_load(runtime_deps) or []):
            edges.add((dep, name))
    return elements, edges


def _graph_of(run_dir):
    with open(os.path.join(run_dir, "graph.json"), encoding="utf-8") as f:
        graph = json.load(f)
    return ({e["uid"]: e["cache_key"] for e in graph["elements"]},
            {(d["predecessor"], d["successor"]) for d in graph["dependencies"]})


@pytest.mark.bst
@pytest.mark.skipif(not BST_AVAILABLE, reason=BST_SKIP_REASON)
def test_each_variant_captures_its_own_graph_and_reuses_only_its_own(tmp_path):
    """Real builds of the fixture as variant A and B: each fresh
    `graph.json` equals an option-aware `bst show`; B after B reuses B's
    graph, B after A extracts B's rather than inheriting A's."""
    from tests.unit._bst_env import bst_env

    def _capture(global_opts, name, baseline=None):
        cmd = ["bst", *global_opts, "--no-colors", "build", "app.bst"]
        raw_log = str(tmp_path / f"{name}-raw.log")
        wrapped_log = str(tmp_path / f"{name}-wrapped.log")
        run_dir = str(tmp_path / name)
        tracer.run_traced_build(FIXTURE_PROJECT, cmd, raw_log, wrapped_log_path=wrapped_log)
        summary = mod.extract_run(
            FIXTURE_PROJECT, wrapped_log, run_dir, log_format="wrapped",
            cache_key_set=tracer.read_cache_key_set_from_plane1_log(wrapped_log),
            bst_global_options=tracer._bst_global_options(cmd)[0],
            baseline_run_dir=baseline)
        return summary, run_dir

    with bst_env(tmp_path / "home"):
        expected_a = _option_aware_graph(["-o", "variant", "a"])
        expected_b = _option_aware_graph(["-o", "variant", "b"])
        assert expected_a != expected_b
        assert ("base-b.bst", "app.bst") in expected_b[1]

        summary_a, run_a = _capture(["-o", "variant", "a"], "a")
        summary_b1, run_b1 = _capture(["-o", "variant", "b"], "b1")
        summary_b2, run_b2 = _capture(["-o", "variant", "b"], "b2", baseline=run_b1)
        summary_b3, run_b3 = _capture(["-o", "variant", "b"], "b3", baseline=run_a)

    assert summary_a["graph_reused"] is False and _graph_of(run_a) == expected_a
    assert summary_b1["graph_reused"] is False and _graph_of(run_b1) == expected_b
    assert summary_b2["graph_reused"] is True and _graph_of(run_b2) == expected_b
    assert summary_b3["graph_reused"] is False and _graph_of(run_b3) == expected_b
