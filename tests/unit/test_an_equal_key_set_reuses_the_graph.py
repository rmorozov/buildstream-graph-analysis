"""UX-1083: an equal whole-graph fingerprint (key set, requested
targets, `bst` global options, resolved max-jobs, `bga-foundation`)
reuses a baseline's `graph.json` instead of paying another `bst show
--deps all`. Hermetic throughout: `tools.bst_extract_run.extract_graph`
is monkeypatched to a counter, since the point under test is *whether*
it is called, not what a real one returns (that is
`tests/unit/test_bst_show_to_graph.py`'s job).
"""

import json

import pytest

from tools import bst_extract_run as mod
from tools.bst_extract_run import extract_run

_LOG = (
    "[wrapper][2026-01-01 00:00:00,000] INFO: Executing command: bst build {targets}\n"
    "[wrapper][2026-01-01 00:00:00,001] INFO: Targets:       {targets}\n"
)


@pytest.fixture(autouse=True)
def fake_extract_graph(monkeypatch):
    calls = []

    def _fake(project_dir, targets, bst_bin="bst", bst_options=None):
        calls.append({"targets": list(targets), "bst_options": list(bst_options or [])})
        return {
            "elements": [
                {
                    "uid": t,
                    "cache_key": f"key-{t}",
                    "requested_target": False,
                    "max_jobs": 4,
                    "notparallel": None,
                    "element_kind": "import",
                }
                for t in targets
            ],
            "dependencies": [],
        }

    monkeypatch.setattr(mod, "extract_graph", _fake)
    return calls


def _write_log(path, targets="app.bst"):
    with open(path, "w", encoding="utf-8") as f:
        f.write(_LOG.format(targets=targets))


def _extract(tmp_path, name, project_dir=None, **kwargs):
    log = tmp_path / f"{name}.log"
    _write_log(log, targets=kwargs.pop("targets_line", "app.bst"))
    out = tmp_path / name
    summary = extract_run(str(project_dir or tmp_path / "proj"), str(log), str(out), log_format="wrapped", **kwargs)
    with open(out / "graph.json", encoding="utf-8") as f:
        graph = json.load(f)
    return summary, graph


def test_an_equal_fingerprint_issues_one_bst_show_between_two_snapshots(tmp_path, fake_extract_graph):
    key_set = {"sha256": "same", "elements": 1}

    summary1, graph1 = _extract(tmp_path, "run1", cache_key_set=key_set)
    assert len(fake_extract_graph) == 1
    assert summary1["graph_reused"] is False

    summary2, graph2 = _extract(tmp_path, "run2", cache_key_set=key_set, baseline_run_dir=str(tmp_path / "run1"))

    # One `bst show --deps all` between the two snapshots, not two.
    assert len(fake_extract_graph) == 1
    assert summary2["graph_reused"] is True
    assert graph2["elements"] == graph1["elements"]
    assert graph2["dependencies"] == graph1["dependencies"]


def test_a_changed_key_runs_bst_show_again(tmp_path, fake_extract_graph):
    _extract(tmp_path, "run1", cache_key_set={"sha256": "one", "elements": 1})
    summary2, graph2 = _extract(
        tmp_path, "run2", cache_key_set={"sha256": "two", "elements": 1}, baseline_run_dir=str(tmp_path / "run1")
    )

    assert len(fake_extract_graph) == 2
    assert summary2["graph_reused"] is False
    # Matches what a fresh extraction produces for this key.
    assert graph2["elements"][0]["cache_key"] == "key-app.bst"


def test_the_same_keys_under_different_targets_runs_bst_show_again(tmp_path, fake_extract_graph):
    """B depends on A: building B alone and building A and B together can
    resolve the same key set, but `requested_target` must differ."""
    key_set = {"sha256": "same", "elements": 2}

    _extract(tmp_path, "run1", cache_key_set=key_set, targets_line="b.bst")
    summary2, graph2 = _extract(
        tmp_path, "run2", cache_key_set=key_set, targets_line="a.bst, b.bst", baseline_run_dir=str(tmp_path / "run1")
    )

    assert len(fake_extract_graph) == 2
    assert summary2["graph_reused"] is False
    requested = {e["uid"] for e in graph2["elements"] if e["requested_target"]}
    assert requested == {"a.bst", "b.bst"}


def test_a_changed_foundation_runs_bst_show_again(tmp_path, fake_extract_graph):
    key_set = {"sha256": "same", "elements": 1}
    _extract(tmp_path, "run1", cache_key_set=key_set, foundation=["app.bst"])
    summary2, graph2 = _extract(
        tmp_path, "run2", cache_key_set=key_set, foundation=[], baseline_run_dir=str(tmp_path / "run1")
    )

    assert len(fake_extract_graph) == 2
    assert summary2["graph_reused"] is False
    assert graph2["foundation"] == []


def test_a_changed_max_jobs_runs_bst_show_again(tmp_path, fake_extract_graph):
    key_set = {"sha256": "same", "elements": 1}

    log1 = tmp_path / "run1.log"
    log1.write_text(
        "[wrapper][2026-01-01 00:00:00,000] INFO: Executing command: "
        "bst --max-jobs 2 build app.bst\n"
        "[wrapper][2026-01-01 00:00:00,001] INFO: Targets:       app.bst\n"
    )
    extract_run(str(tmp_path / "proj"), str(log1), str(tmp_path / "run1"), log_format="wrapped", cache_key_set=key_set)
    assert len(fake_extract_graph) == 1

    log2 = tmp_path / "run2.log"
    log2.write_text(
        "[wrapper][2026-01-01 00:00:00,000] INFO: Executing command: "
        "bst --max-jobs 4 build app.bst\n"
        "[wrapper][2026-01-01 00:00:00,001] INFO: Targets:       app.bst\n"
    )
    summary2 = extract_run(
        str(tmp_path / "proj"),
        str(log2),
        str(tmp_path / "run2"),
        log_format="wrapped",
        cache_key_set=key_set,
        baseline_run_dir=str(tmp_path / "run1"),
    )

    assert len(fake_extract_graph) == 2
    assert summary2["graph_reused"] is False


def test_an_unread_key_set_never_reuses(tmp_path, fake_extract_graph):
    """UX-1082's `None` ("unread") is never a foundation to reuse from,
    and never reused into - the whole point of "unread rather than
    guessing" carries through here."""
    _extract(tmp_path, "run1", cache_key_set=None)
    summary2, _ = _extract(tmp_path, "run2", cache_key_set=None, baseline_run_dir=str(tmp_path / "run1"))

    assert len(fake_extract_graph) == 2
    assert summary2["graph_reused"] is False


def test_a_baseline_without_a_graph_json_runs_bst_show(tmp_path, fake_extract_graph):
    missing = tmp_path / "no-such-run"
    summary, _ = _extract(tmp_path, "run1", cache_key_set={"sha256": "x", "elements": 1}, baseline_run_dir=str(missing))

    assert len(fake_extract_graph) == 1
    assert summary["graph_reused"] is False


def test_different_bst_global_options_with_equal_keys_runs_bst_show_again(tmp_path, fake_extract_graph):
    key_set = {"sha256": "same", "elements": 1}
    _extract(tmp_path, "run1", cache_key_set=key_set, bst_global_options=["-o", "variant", "a"])
    summary2, _ = _extract(
        tmp_path,
        "run2",
        cache_key_set=key_set,
        bst_global_options=["-o", "variant", "b"],
        baseline_run_dir=str(tmp_path / "run1"),
    )

    assert len(fake_extract_graph) == 2
    assert summary2["graph_reused"] is False
