"""UX-1366 (a): build-only reach is described, never read as a build tool: the blast keeps its finding.

Page: styleguide §1b, a published field reaches a reader.
"""

import copy
import json
import pathlib
import shutil
import sys
from types import SimpleNamespace

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages
from browser import Browser, find_chrome

from bga import findings, sources
from bga.ingest.models import DependencyEdge

FIXTURE = REPO / "tests/fixtures/macro_micro"
chrome = find_chrome()
NO_CHROME = "no chrome/chromium for the geometry guards (set BGA_CHROME)"
SHARED = {"kind": "tar", "identity": "ftp/autoconf-2.73.tar.xz", "keying": "ref", "staged_at": None}
MONOREPO = {"kind": "git", "identity": "https://example.com/monorepo.git", "keying": "ref", "staged_at": None}
STATIC_LIBS = ("lib-a.bst", "lib-b.bst", "lib-c.bst", "lib-d.bst", "lib-e.bst", "lib-f.bst")


def _edges(runtime=()):
    """`runtime` predecessors take `app.bst` as a runtime dependent; their other dependents stay build."""
    graph = json.loads((FIXTURE / "run/graph.json").read_text())
    return [
        DependencyEdge(
            d["predecessor"],
            d["successor"],
            "runtime" if d["predecessor"] in runtime and d["successor"] == "app.bst" else d["dependency_type"],
        )
        for d in graph["dependencies"]
    ]


def _blast(runtime=(), sharing=("toolchain.bst", "codegen.bst"), source=SHARED):
    """`sharing` source one `source`; `runtime` as in `_edges`."""
    edges = _edges(runtime)
    downstream: dict[str, set] = {}
    for edge in edges:
        downstream.setdefault(edge.predecessor, set()).add(edge.successor)
    for _ in range(10):
        for below in list(downstream.values()):
            for each in list(below):
                below |= downstream.get(each, set())
    inventory = {"elements": {uid: [source] for uid in sharing}}
    rows = sources.mark_build_only_reach(
        sources.resource_blast(inventory, downstream, {}), sources.build_only_elements(edges)
    )
    blast = {"rows": rows, "element_count": 11, "headline": sources.monorepo_headline(rows, 11)}
    return rows[0], blast


def _finding(**kw):
    return findings._shared_source_findings(SimpleNamespace(resource_blast=_blast(**kw)[1]))[0]


def _said(finding):
    return " ".join([finding["title"], *finding["detail"], finding["step"].get("text", "")])


def test_build_only_reach_is_derived_from_the_dependency_types_and_only_described():
    row, blast = _blast()
    assert row["build_only_reach"] is True and row["blast_count"] > 5
    assert blast["headline"].startswith("One repository decides most of this build")
    assert "through build dependencies only" in blast["headline"]
    assert sources.BUILD_ONLY_NOTE in sources.keying_clause(row)


def test_a_runtime_dependent_clears_the_note():
    row, blast = _blast(runtime={"toolchain.bst"})
    assert row["build_only_reach"] is False
    assert "build dependencies only" not in blast["headline"]
    assert sources.BUILD_ONLY_NOTE not in sources.keying_clause(row)


@pytest.mark.parametrize("runtime", [(), ("toolchain.bst",)])
def test_the_finding_keeps_its_severity_and_advice_either_way(runtime):
    finding = _finding(runtime=runtime)
    assert finding["severity"] == findings.SEVERITY_MEDIUM
    assert finding["step"]["text"].startswith("Narrow which elements")


def test_a_monorepo_split_into_build_only_static_libraries_keeps_its_blast():
    """The negative case: six static libraries, every dependent a build one, one shared ref."""
    row, _ = _blast(sharing=STATIC_LIBS, source=MONOREPO)
    assert row["build_only_reach"] is True and row["direct_count"] == 6
    finding = _finding(sharing=STATIC_LIBS, source=MONOREPO)
    assert finding["severity"] == findings.SEVERITY_MEDIUM
    assert finding["step"]["text"].startswith("Narrow which elements take this source")
    assert finding["evidence"]["build_only_reach"] is True
    said = _said(finding)
    assert "through build dependencies only" in said
    assert "expected" not in said and "build tool" not in said


@pytest.mark.skipif(chrome is None, reason=NO_CHROME)
@pytest.mark.medium
def test_the_page_keeps_the_advice_and_says_the_note(tmp_path):
    snap = tmp_path / "snap"
    shutil.copytree(FIXTURE / "run", snap / "run")
    inventory = {
        "schema": sources.SCHEMA,
        "elements": {u: [copy.deepcopy(MONOREPO)] for u in STATIC_LIBS},
    }
    (snap / "run/sources.json").write_text(json.dumps(inventory))
    with Browser(chrome) as browser:
        text = browser.measure(
            pages.export_uri(snap / "run", tmp_path / "out"), "document.body.textContent.replace(/\\s+/g, ' ')"
        )
    assert "Narrow which elements take this source" in text
    assert "through build dependencies only" in text
    assert "as expected of a build tool" not in text
