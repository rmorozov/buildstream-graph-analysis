"""UX-1366 (a): a source whose direct elements are build tools rebuilds its consumers by design.

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


def _edges(runtime=()):
    graph = json.loads((FIXTURE / "run/graph.json").read_text())
    return [
        DependencyEdge(
            d["predecessor"], d["successor"], "runtime" if d["predecessor"] in runtime else d["dependency_type"]
        )
        for d in graph["dependencies"]
    ]


def _blast(runtime=()):
    """toolchain.bst and codegen.bst share one source; `runtime` names predecessors with a runtime dependent."""
    edges = _edges(runtime)
    downstream: dict[str, set] = {}
    for edge in edges:
        downstream.setdefault(edge.predecessor, set()).add(edge.successor)
    for _ in range(10):
        for below in list(downstream.values()):
            for each in list(below):
                below |= downstream.get(each, set())
    inventory = {"elements": {"toolchain.bst": [SHARED], "codegen.bst": [SHARED]}}
    rows = sources.mark_build_tools(
        sources.resource_blast(inventory, downstream, {}), sources.build_only_elements(edges)
    )
    blast = {"rows": rows, "element_count": 11, "headline": sources.monorepo_headline(rows, 11)}
    return rows[0], blast


def test_a_build_tool_is_derived_from_the_dependency_types():
    row, blast = _blast()
    assert row["build_tool"] is True and row["blast_count"] > 5
    assert "as expected" in blast["headline"] and "build tools" in blast["headline"]
    assert sources.BUILD_TOOL_CLAUSE in sources.keying_clause(row)


def test_a_runtime_dependent_makes_it_a_source_not_a_tool():
    row, blast = _blast(runtime={"toolchain.bst"})
    assert row["build_tool"] is False
    assert "One repository decides most of this build" in blast["headline"]
    assert sources.BUILD_TOOL_CLAUSE not in sources.keying_clause(row)


def test_the_finding_is_expected_for_a_tool_and_advice_for_a_source():
    tool = findings._shared_source_findings(SimpleNamespace(resource_blast=_blast()[1]))[0]
    assert tool["severity"] == findings.SEVERITY_INFO
    assert "text" not in tool["step"] and "why_none" in tool["step"]
    assert "as expected" in tool["title"]
    source = findings._shared_source_findings(SimpleNamespace(resource_blast=_blast(runtime={"toolchain.bst"})[1]))[0]
    assert source["severity"] == findings.SEVERITY_MEDIUM
    assert source["step"]["text"].startswith("Narrow which elements")


@pytest.mark.skipif(chrome is None, reason=NO_CHROME)
@pytest.mark.medium
def test_the_page_says_expected(tmp_path):
    snap = tmp_path / "snap"
    shutil.copytree(FIXTURE / "run", snap / "run")
    inventory = {
        "schema": sources.SCHEMA,
        "elements": {u: [copy.deepcopy(SHARED)] for u in ("toolchain.bst", "codegen.bst")},
    }
    (snap / "run/sources.json").write_text(json.dumps(inventory))
    with Browser(chrome) as browser:
        text = browser.measure(
            pages.export_uri(snap / "run", tmp_path / "out"), "document.body.textContent.replace(/\\s+/g, ' ')"
        )
    assert "as expected of a build tool" in text
    assert "Narrow which elements take this source" not in text
