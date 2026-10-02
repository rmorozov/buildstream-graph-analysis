"""UX-1277: a finding says whether it is new, still open or resolved since the run before.

A three-run two-plane store, the oldest two with published analyses: @prev's
gains a finding @last lacks and loses one @last holds. `bga compare` keys the
diff on finding id, so ids are asserted unique per document first.
"""

import json
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import run_store
from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)

GONE = {"id": "ux1277-gone", "severity": "info", "title": "A finding only the run before had"}

_MEASURE = r"""
(() => {
  const section = document.querySelector('[data-section="findings"]');
  const line = section?.querySelector('[data-role="findings-resolved"]');
  return {
    cards: [...section.querySelectorAll("article.finding")].map((a) => ({
      id: a.dataset.findingId, since: a.dataset.since ?? null,
      mark: a.querySelector(".badge.since")?.textContent ?? null })),
    resolved: line ? [...line.querySelectorAll("[data-finding-id]")].map((s) => s.dataset.findingId) : null,
    resolvedText: line?.textContent ?? null,
  };
})()
"""


def _analyze(run) -> dict:
    out = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(run), "--format", "json"],
        check=True,
        capture_output=True,
        cwd=str(REPO),
    )
    return json.loads(out.stdout)


def _ids(document) -> list:
    return [f["id"] for f in document.get("findings") or []]


@pytest.fixture(scope="module")
def store(tmp_path_factory):
    into = tmp_path_factory.mktemp("u1277")
    newest = pages.two_plane_run(into, ("--layers", "4", "--width", "6"), runs=3)
    oldest, prev, _ = run_store.list_runs(str(into / "both"))
    documents = {name: _analyze(pathlib.Path(snap) / "run") for name, snap in (("oldest", oldest), ("prev", prev))}
    documents["last"] = _analyze(newest)
    shared = [fid for fid in _ids(documents["last"]) if fid in _ids(documents["prev"])]
    dropped = shared[-1]
    edited = dict(documents["prev"])
    edited["findings"] = [f for f in documents["prev"]["findings"] if f["id"] != dropped] + [GONE]
    (pathlib.Path(oldest) / run_store.ANALYSIS_NAME).write_text(json.dumps(documents["oldest"]), encoding="utf-8")
    (pathlib.Path(prev) / run_store.ANALYSIS_NAME).write_text(json.dumps(edited), encoding="utf-8")
    return {"newest": newest, "into": into, "documents": documents, "edited": edited, "dropped": dropped}


def test_finding_ids_are_unique_per_document(store):
    """The identity's precondition: one id names one finding in a document."""
    documents = [*store["documents"].values()] + [_analyze(pages.FIXTURES[label]) for label in pages.FIXTURES]
    for document in documents:
        ids = _ids(document)
        assert ids and len(ids) == len(set(ids)), ids


@needs_browser
def test_the_page_marks_new_persisting_and_resolved(store):
    last, edited = set(_ids(store["documents"]["last"])), set(_ids(store["edited"]))
    oldest = set(_ids(store["documents"]["oldest"]))
    uri = pages.export_uri(store["newest"], store["into"], store=True)
    with Browser(chrome) as opened:
        page = opened.measure(uri, _MEASURE)
    by_since = {kind: {c["id"] for c in page["cards"] if c["since"] == kind} for kind in ("new", "persisting")}
    assert store["dropped"] in by_since["new"], page
    assert by_since["new"] == last - edited, page
    assert by_since["persisting"] == last & edited and len(by_since["persisting"]) >= 3, page
    assert GONE["id"] in page["resolved"] and set(page["resolved"]) == edited - last, page
    assert len(page["resolved"]) == len(edited - last) and GONE["title"] in page["resolvedText"], page
    marks = {c["id"]: c["mark"] for c in page["cards"] if c["since"] == "persisting"}
    for fid, mark in marks.items():
        assert mark == f"Still open · {3 if fid in oldest else 2} runs", (fid, mark)
