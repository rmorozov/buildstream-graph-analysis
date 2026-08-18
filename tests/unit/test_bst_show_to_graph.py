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
import os
import shutil
from pathlib import Path

import pytest

from tools.bst_show_to_graph import (
    FIELD_SEP, RECORD_SEP, _parse_dep_list, _parse_max_jobs, _parse_notparallel,
    build_graph, extract_graph,
)

FIXTURE_PROJECT = Path(__file__).resolve().parents[1] / "fixtures" / "bst_show_project"

BST_AVAILABLE = shutil.which("bst") is not None


def _record(name, key, build_deps, runtime_deps, kind="import", public="", variables=""):
    # UX-31 added a 7th field (`%{vars}`), the real source of per-element
    # resolved max-jobs and `notparallel`.
    return FIELD_SEP.join([name, key, kind, build_deps, runtime_deps, public, variables])


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
        "uid": "app.bst", "cache_key": "abc123", "requested_target": True,
        # UX-31 added `notparallel` alongside the existing max_jobs.
        "max_jobs": None, "notparallel": None, "element_kind": "manual",
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
    """A record with 5 fields (the pre-UX-22, pre-%{public} shape) is
    exactly the "malformed" case now - a future/different bst version
    changing --format's output shape must be visible, not silently
    misparsed."""
    five_field_record = FIELD_SEP.join(["old.bst", "k1", "import", "[]", "[]"]) + RECORD_SEP
    stdout = five_field_record + _record("app.bst", "k1", "[]", "[]") + RECORD_SEP
    graph = build_graph(stdout, targets=[])
    assert [e["uid"] for e in graph["elements"]] == ["app.bst"]


# --- Per-element max-jobs capture (UX-22) ------------------------------

def test_parse_max_jobs_absent_is_none():
    """The element doesn't override max-jobs - the real, common case.
    `bst.split-rules`-only content, no `max-jobs` key at all."""
    assert _parse_max_jobs("bst:\n  split-rules:\n    devel:\n    - /usr/include\n") is None


def test_parse_max_jobs_present_is_captured():
    assert _parse_max_jobs("bst:\n  max-jobs: 16\n  split-rules: {}\n") == 16


def test_parse_max_jobs_empty_public_is_none():
    assert _parse_max_jobs("") is None
    assert _parse_max_jobs("{}") is None


def test_build_graph_captures_resolved_max_jobs_from_vars():
    """UX-31: `%{vars}` carries the *resolved* per-element value - what
    really reaches `make -jN` - which is what the report needs. Confirmed
    against a real BuildStream 2.7.0 build: an element with
    `notparallel: True` reports `max-jobs: 1` while its siblings report
    the project default."""
    stdout = (
        _record("normal.bst", "k1", "[]", "[]", variables="max-jobs: 4\n") + RECORD_SEP
        + _record(
            "pinned.bst", "k2", "[]", "[]",
            variables="max-jobs: 1\nnotparallel: True\n",
        ) + RECORD_SEP
    )
    graph = build_graph(stdout, targets=[])
    by_uid = {e["uid"]: e for e in graph["elements"]}
    assert by_uid["normal.bst"]["max_jobs"] == 4
    assert by_uid["normal.bst"]["notparallel"] is None
    assert by_uid["pinned.bst"]["max_jobs"] == 1
    assert by_uid["pinned.bst"]["notparallel"] is True


def test_build_graph_falls_back_to_public_max_jobs_when_vars_absent():
    """UX-31 keeps UX-22's `public: bst: max-jobs:` read as a fallback so
    an older captured graph.json keeps meaning what it meant - BuildStream
    itself never reads that key, so it cannot describe a real build, but
    silently changing what an existing capture means would be worse."""
    stdout = _record(
        "legacy.bst", "k1", "[]", "[]", public="bst:\n  max-jobs: 16\n",
    ) + RECORD_SEP
    graph = build_graph(stdout, targets=[])
    assert graph["elements"][0]["max_jobs"] == 16


def test_parse_notparallel_distinguishes_unset_from_false():
    assert _parse_notparallel("notparallel: True\n") is True
    assert _parse_notparallel("notparallel: False\n") is False
    assert _parse_notparallel("max-jobs: 4\n") is None


# --- Real end-to-end test against a live `bst` binary ------------------

@pytest.mark.bst
@pytest.mark.skipif(not BST_AVAILABLE, reason="bst not found on PATH - see docs/ingestion-pipeline.md")
def test_real_bst_show_against_fixture_project(tmp_path):
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

    # UX-31/UX-84: `max_jobs` is the *effective, resolved* figure - what
    # `%{max-jobs}` really expands to for this element, i.e. what reaches
    # `make`. None of app.bst's dependency set carries `notparallel`, so
    # every one of them resolves to the project default, which is the
    # host core count. Asserting the host's own count rather than a
    # literal keeps this true on any runner.
    assert {e["max_jobs"] for e in graph["elements"]} == {os.cpu_count()}


@pytest.mark.bst
@pytest.mark.skipif(not BST_AVAILABLE, reason="bst not found on PATH - see docs/ingestion-pipeline.md")
def test_real_bst_show_captures_per_element_max_jobs_override(tmp_path):
    """UX-31, re-baselined by UX-84: the per-element parallelism control
    BuildStream 2.7 actually honours is `variables: notparallel: True`,
    and the captured figure is the *resolved* one.

    This test used to assert 16 for `manual.bst`, which declares
    `public: bst: max-jobs: 16`. Against a live bst 2.7 the extractor
    returns the host core count instead, and that is right, not a
    regression: `%{public}` really does carry the 16 (verified:
    `bst show --format '%{public}'` prints `bst: max-jobs: 16`), and
    BuildStream really does ignore it - `%{vars}` reports `max-jobs: 4`
    on a 4-core host for `manual.bst` and for `base.bst` alike, and
    `%{max-jobs}` is what the plugins' `environment: JOBS: -j%{max-jobs}`
    expands. Recording 16 would have recorded a number no build ever
    used. `UX-22` settled on the `public:` route before `UX-31` found the
    real one; the assertion outlived the mechanism because no CI job ran
    the bst-gated tier (that gap is the rest of UX-84).

    So what is asserted now is the *discrimination* the capture exists
    for: `notparallel.bst` resolves to 1 while its siblings resolve to
    the host default. That is the signal every downstream consumer reads
    - it is how `analyze --plane2` names an element that asked its native
    build for -j1 as free capacity."""
    graph = extract_graph(str(FIXTURE_PROJECT), targets=["notparallel.bst"])
    max_jobs = {e["uid"]: e["max_jobs"] for e in graph["elements"]}
    assert max_jobs["notparallel.bst"] == 1
    assert max_jobs["base.bst"] == os.cpu_count()
    assert max_jobs["notparallel.bst"] < max_jobs["base.bst"]

    # And the superseded route is inert rather than merely outranked:
    # `manual.bst`'s `public: bst: max-jobs: 16` reaches the graph as the
    # host default, not as 16.
    manual = extract_graph(str(FIXTURE_PROJECT), targets=["manual.bst"])
    assert {e["uid"]: e["max_jobs"] for e in manual["elements"]}["manual.bst"] == os.cpu_count()


@pytest.mark.bst
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
