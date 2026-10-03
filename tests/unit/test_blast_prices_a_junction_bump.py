"""UX-1321: `bga blast` on a junction, or on a path inside a junction's checkout, prices it.

A fixture project with two local junctions, nested (`top -> platform -> base`), its run's
graph, and the inventory `tools/bst_extract_run.py` itself writes for it.
"""

import json

import pytest

from bga.blast import blast, format_blast_text
from tools.bst_extract_run import build_source_inventory

P = "junctions/platform.bst:"
B = "junctions/platform.bst:junctions/base.bst:"

ELEMENTS = {
    B + "toolchain.bst": "import",
    B + "pkgs/zlib.bst": "cmake",
    B + "base.bst": "stack",
    P + "pkgs/dbus.bst": "cmake",
    P + "platform.bst": "stack",
    "pkgs/zlib.bst": "cmake",
    "apps/app.bst": "cmake",
    "tools/lint.bst": "cmake",
    # A sibling junction whose name extends `junctions/platform.bst`: only the `:` tells them apart.
    "junctions/platform.bst-extra.bst:pkgs/x.bst": "cmake",
}
EDGES = [
    (B + "toolchain.bst", B + "pkgs/zlib.bst"),
    (B + "pkgs/zlib.bst", B + "base.bst"),
    (B + "base.bst", P + "pkgs/dbus.bst"),
    (P + "pkgs/dbus.bst", P + "platform.bst"),
    (P + "platform.bst", "apps/app.bst"),
]
CMAKE = "kind: cmake\nsources:\n- kind: local\n  path: files/gen/cmake\n"


def _project(root, name, elements):
    (root / "project.conf").write_text(f"name: {name}\nmin-version: 2.0\nelement-path: elements\n")
    for path, text in elements.items():
        (root / "elements" / path).parent.mkdir(parents=True, exist_ok=True)
        (root / "elements" / path).write_text(text)
    (root / "files" / "gen" / "cmake").mkdir(parents=True)
    (root / "files" / "gen" / "cmake" / "CMakeLists.txt").write_text("project(x)\n")


def _junction(path):
    return f"kind: junction\nsources:\n- kind: local\n  path: {path}\n"


@pytest.fixture
def run(tmp_path):
    project = tmp_path / "top"
    platform = project / "subprojects" / "platform"
    base = platform / "subprojects" / "base"
    for where in (project, platform, base):
        where.mkdir(parents=True)
    _project(
        base,
        "base",
        {
            "toolchain.bst": "kind: import\nsources:\n- kind: local\n  path: files/toolchain\n",
            "pkgs/zlib.bst": CMAKE,
            "base.bst": "kind: stack\n",
        },
    )
    _project(
        platform,
        "platform",
        {"junctions/base.bst": _junction("subprojects/base"), "pkgs/dbus.bst": CMAKE, "platform.bst": "kind: stack\n"},
    )
    _project(
        project,
        "top",
        {
            "junctions/platform.bst": _junction("subprojects/platform"),
            "pkgs/zlib.bst": CMAKE,
            "apps/app.bst": "kind: cmake\n",
            "tools/lint.bst": "kind: cmake\n",
        },
    )
    # A project nobody junctions: a path inside it cannot be resolved.
    (project / "vendor" / "other" / "files").mkdir(parents=True)
    (project / "vendor" / "other" / "project.conf").write_text("name: other\n")

    run_dir = tmp_path / "run"
    run_dir.mkdir()
    graph = {
        "elements": [{"uid": uid, "element_kind": kind} for uid, kind in ELEMENTS.items()],
        "dependencies": [{"predecessor": a, "successor": b, "dependency_type": "build"} for a, b in EDGES],
    }
    (run_dir / "graph.json").write_text(json.dumps(graph))
    (run_dir / "trace.json").write_text(json.dumps({"spans": [], "phases": []}))
    (run_dir / "run-context.json").write_text(json.dumps({"wall_clock": {"start_us": 0, "end_us": 1}}))
    inventory = build_source_inventory(str(project), list(ELEMENTS))
    (run_dir / "sources.json").write_text(json.dumps(inventory))
    return run_dir, str(project)


def _ask(run, target):
    run_dir, project = run
    answer = blast(run_dir, target, project_dir=project, measure=False)
    return answer, format_blast_text(answer)


@pytest.mark.parametrize("target", ["junctions/platform.bst", "elements/junctions/platform.bst"])
def test_a_junction_blasts_everything_behind_it_and_downstream(run, target):
    answer, text = _ask(run, target)
    assert answer["resolved_as"] == "junction", text
    assert answer["direct_elements"] == sorted(uid for uid in ELEMENTS if uid.startswith(P))
    assert answer["blast_count"] == 6, text
    assert "junctions/platform.bst-extra.bst:pkgs/x.bst" not in answer["blast_elements"], text
    assert "tools/lint.bst" not in answer["blast_elements"] and "pkgs/zlib.bst" not in answer["blast_elements"]
    assert "Read as a junction" in text and "rebuilds nothing" not in text


def test_a_nested_junction_blasts_its_own_prefix(run):
    answer, text = _ask(run, P + "junctions/base.bst")
    assert answer["resolved_as"] == "junction", text
    assert answer["direct_count"] == 3 and answer["blast_count"] == 6, text
    assert answer["junction"]["checkout"] == "subprojects/platform/subprojects/base"


def test_a_path_in_a_nested_checkout_maps_to_the_identity_the_inventory_stores(run):
    answer, text = _ask(run, "subprojects/platform/subprojects/base/files/gen/cmake/CMakeLists.txt")
    assert answer["direct_elements"] == [B + "pkgs/zlib.bst"], text
    assert answer["blast_count"] == 5, text
    assert answer["junction"]["identity"] == B + "files/gen/cmake/CMakeLists.txt"


def test_a_path_in_a_checkout_does_not_match_the_top_projects_same_spelling(run):
    answer, text = _ask(run, "subprojects/platform/files/gen/cmake")
    assert answer["direct_elements"] == [P + "pkgs/dbus.bst"], text


def test_an_unstaged_path_in_a_checkout_never_rebuilds_nothing(run):
    _answer, text = _ask(run, "subprojects/platform/project.conf")
    assert "rebuilds nothing" not in text
    assert "inside the checkout of junction junctions/platform.bst" in text


def test_a_path_in_a_project_no_junction_checks_out_says_it_could_not_resolve(run):
    _answer, text = _ask(run, "vendor/other/files/x.c")
    assert "rebuilds nothing" not in text and "could not be resolved" in text


def test_a_path_under_no_junction_and_sourced_by_nothing_keeps_todays_answer(run):
    answer, text = _ask(run, "docs/readme.md")
    assert answer["junction"] is None
    assert "Touching it rebuilds nothing here." in text
