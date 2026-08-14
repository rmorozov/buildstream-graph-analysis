"""Tests for tools/bst_show_to_graph.py (P4-08).

Two layers:
1. Pure parser tests (build_graph, _parse_dep_list) against hand-built
   `bst show` stdout blobs - fast, hermetic, always run.
2. A real end-to-end test that actually shells out to a real `bst`
   binary against tests/fixtures/bst_show_project/ - skipped whenever
   `bst` isn't on PATH (BuildStream + bubblewrap are heavy, non-pip-
   only dependencies not assumed to be present in every dev/CI
   environment; see pyproject.toml's `bst` optional extra and
   docs/ingestion-pipeline.md for how to install them locally).
"""
import json
import shutil
from pathlib import Path

import pytest

from tools.bst_show_to_graph import FIELD_SEP, RECORD_SEP, _parse_dep_list, build_graph, extract_graph

FIXTURE_PROJECT = Path(__file__).resolve().parents[1] / "fixtures" / "bst_show_project"

BST_AVAILABLE = shutil.which("bst") is not None


def _record(name, key, build_deps, runtime_deps, kind="import"):
    return FIELD_SEP.join([name, key, kind, build_deps, runtime_deps])


# --- Pure parser tests ------------------------------------------------

def test_parse_dep_list_empty():
    assert _parse_dep_list("[]") == []
    assert _parse_dep_list("") == []


def test_parse_dep_list_single():
    assert _parse_dep_list("- base.bst") == ["base.bst"]


def test_parse_dep_list_multiple_with_embedded_newline():
    """The exact shape confirmed against real bst show output: multiple
    dependencies render as one "- name" line per dependency, joined by
    a literal newline *within* a single element's field value - not a
    record/field boundary."""
    assert _parse_dep_list("- base.bst\n- base2.bst") == ["base.bst", "base2.bst"]


def test_build_graph_marks_requested_target():
    stdout = _record("app.bst", "abc123", "[]", "[]", kind="manual") + RECORD_SEP
    graph = build_graph(stdout, targets=["app.bst"])
    assert graph["elements"] == [{
        "uid": "app.bst", "cache_key": "abc123", "requested_target": True, "element_kind": "manual",
    }]


def test_build_graph_captures_element_kind():
    stdout = (
        _record("sub.bst", "k1", "[]", "[]", kind="junction") + RECORD_SEP
        + _record("app.bst", "k2", "[]", "[]", kind="autotools") + RECORD_SEP
    )
    graph = build_graph(stdout, targets=[])
    kinds = {e["uid"]: e["element_kind"] for e in graph["elements"]}
    assert kinds == {"sub.bst": "junction", "app.bst": "autotools"}


def test_build_graph_empty_kind_becomes_null():
    stdout = _record("app.bst", "k1", "[]", "[]", kind="") + RECORD_SEP
    graph = build_graph(stdout, targets=[])
    assert graph["elements"][0]["element_kind"] is None


def test_build_graph_empty_cache_key_becomes_null():
    stdout = _record("app.bst", "", "[]", "[]") + RECORD_SEP
    graph = build_graph(stdout, targets=[])
    assert graph["elements"][0]["cache_key"] is None


def test_build_graph_build_dep_type():
    stdout = (
        _record("base.bst", "k1", "[]", "[]") + RECORD_SEP
        + _record("app.bst", "k2", "- base.bst", "[]") + RECORD_SEP
    )
    graph = build_graph(stdout, targets=["app.bst"])
    assert graph["dependencies"] == [
        {"predecessor": "base.bst", "successor": "app.bst", "dependency_type": "build"},
    ]


def test_build_graph_runtime_only_dep_type():
    stdout = (
        _record("lib.bst", "k1", "[]", "[]") + RECORD_SEP
        + _record("app.bst", "k2", "[]", "- lib.bst") + RECORD_SEP
    )
    graph = build_graph(stdout, targets=["app.bst"])
    assert graph["dependencies"] == [
        {"predecessor": "lib.bst", "successor": "app.bst", "dependency_type": "runtime"},
    ]


def test_build_graph_dep_in_both_lists_is_reported_as_build():
    """BuildStream's default dependency type ("all") makes a dependency
    appear in both %{build-deps} and %{runtime-deps} for the same
    element - build/all collapses to "build" (a strict superset of
    what "runtime" alone constrains), not two separate edges."""
    stdout = (
        _record("lib.bst", "k1", "[]", "[]") + RECORD_SEP
        + _record("app.bst", "k2", "- lib.bst", "- lib.bst") + RECORD_SEP
    )
    graph = build_graph(stdout, targets=["app.bst"])
    assert graph["dependencies"] == [
        {"predecessor": "lib.bst", "successor": "app.bst", "dependency_type": "build"},
    ]


def test_build_graph_junction_qualified_name_preserved():
    stdout = _record("sub.bst:lib.bst", "k1", "[]", "[]") + RECORD_SEP
    graph = build_graph(stdout, targets=[])
    assert graph["elements"][0]["uid"] == "sub.bst:lib.bst"


def test_build_graph_skips_malformed_record():
    stdout = "not|enough|fields" + RECORD_SEP + _record("app.bst", "k1", "[]", "[]") + RECORD_SEP
    graph = build_graph(stdout, targets=[])
    assert [e["uid"] for e in graph["elements"]] == ["app.bst"]


def test_build_graph_skips_record_with_wrong_field_count():
    """A record with 4 fields (the pre-element_kind shape) is exactly the
    "malformed" case now - a future/different bst version changing
    --format's output shape must be visible, not silently misparsed."""
    four_field_record = FIELD_SEP.join(["old.bst", "k1", "[]", "[]"]) + RECORD_SEP
    stdout = four_field_record + _record("app.bst", "k1", "[]", "[]") + RECORD_SEP
    graph = build_graph(stdout, targets=[])
    assert [e["uid"] for e in graph["elements"]] == ["app.bst"]


# --- Real end-to-end test against a live `bst` binary ------------------

@pytest.mark.skipif(not BST_AVAILABLE, reason="bst not found on PATH - see docs/ingestion-pipeline.md")
def test_real_bst_show_against_fixture_project(tmp_path):
    output_json = tmp_path / "graph.json"
    graph = extract_graph(str(FIXTURE_PROJECT), targets=["app.bst"])

    uids = {e["uid"] for e in graph["elements"]}
    assert uids == {"base.bst", "base2.bst", "subproj-junction.bst:libfoo.bst", "app.bst"}

    requested = {e["uid"] for e in graph["elements"] if e["requested_target"]}
    assert requested == {"app.bst"}

    deps_by_pair = {(d["predecessor"], d["successor"]): d["dependency_type"] for d in graph["dependencies"]}
    assert deps_by_pair[("base.bst", "app.bst")] == "build"
    assert deps_by_pair[("base2.bst", "app.bst")] == "build"
    assert deps_by_pair[("subproj-junction.bst:libfoo.bst", "app.bst")] == "runtime"

    # Every element got a real, non-empty cache key (local sources are
    # always consistent - no network resolution needed).
    for elem in graph["elements"]:
        assert elem["cache_key"], f"{elem['uid']} has no cache_key"

    # Every element in this fixture is `kind: import` (see
    # tests/fixtures/bst_show_project/elements/*.bst); the junction
    # dependency's own element is `kind: import` too (subproj/elements/libfoo.bst).
    kinds = {e["uid"]: e["element_kind"] for e in graph["elements"]}
    assert kinds == {
        "base.bst": "import", "base2.bst": "import",
        "subproj-junction.bst:libfoo.bst": "import", "app.bst": "import",
    }

    output_json.write_text(json.dumps(graph))


@pytest.mark.skipif(not BST_AVAILABLE, reason="bst not found on PATH - see docs/ingestion-pipeline.md")
def test_real_graph_output_loads_into_bga(tmp_path):
    """The extracted graph.json must be directly consumable by bga's
    own loader, not just superficially JSON-shaped."""
    from bga.ingest.loader import load_graph

    graph = extract_graph(str(FIXTURE_PROJECT), targets=["app.bst"])
    output_json = tmp_path / "graph.json"
    output_json.write_text(json.dumps(graph))

    loaded = load_graph(output_json)
    assert {e.uid for e in loaded.elements} == {
        "base.bst", "base2.bst", "subproj-junction.bst:libfoo.bst", "app.bst",
    }
    assert any(d.dependency_type == "runtime" for d in loaded.dependencies)
    assert any(d.dependency_type == "build" for d in loaded.dependencies)
    assert all(e.element_kind == "import" for e in loaded.elements)
