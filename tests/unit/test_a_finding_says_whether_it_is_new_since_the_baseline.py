"""UX-1277: a finding says whether it is new, still open or resolved since the run before.

Two stores. `mixed`: only @last has Plane 2, so a finding on one side only is
not compared. `same`: every run has Plane 2; the oldest is unpublished, the
second's analysis drops one finding, @prev's gains one @last lacks and loses one
@last holds. `bga compare` keys on finding id, so ids are asserted unique first.

Styleguide §1b.
"""

import gzip
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
SHAPE = ("--layers", "4", "--width", "6")

_MEASURE = r"""
(() => {
  const section = document.querySelector('[data-section="findings"]');
  const ids = (role) => {
    const line = section?.querySelector(`[data-role="${role}"]`);
    return line ? [...line.querySelectorAll("[data-finding-id]")].map((s) => s.dataset.findingId) : [];
  };
  return {
    cards: [...section.querySelectorAll("article.finding")].map((a) => ({
      id: a.dataset.findingId, since: a.dataset.since ?? null,
      mark: a.querySelector(".badge.since")?.textContent ?? null })),
    resolved: ids("findings-resolved"),
    notCompared: ids("findings-not-compared"),
    resolvedText: section?.querySelector('[data-role="findings-resolved"]')?.textContent ?? "",
    notComparedText: section?.querySelector('[data-role="findings-not-compared"]')?.textContent ?? "",
  };
})()
"""


def _cli(*argv) -> bytes:
    return subprocess.run(
        [sys.executable, "-m", "bga.cli", *argv], check=True, capture_output=True, cwd=str(REPO)
    ).stdout


def _analyze(run) -> dict:
    return json.loads(_cli("analyze", str(run), "--format", "json"))


def _ids(document) -> list:
    return [f["id"] for f in document.get("findings") or []]


def _publish(snapshot, document):
    (pathlib.Path(snapshot) / run_store.ANALYSIS_NAME).write_text(json.dumps(document), encoding="utf-8")


def _page(newest, into) -> dict:
    with Browser(chrome) as opened:
        return opened.measure(pages.export_uri(newest, into, store=True), _MEASURE)


@pytest.fixture(scope="module")
def mixed(tmp_path_factory):
    into = tmp_path_factory.mktemp("u1277-mixed")
    newest = pages.two_plane_run(into, SHAPE, runs=3)
    oldest, prev, _ = run_store.list_runs(str(into / "both"))
    documents = {"oldest": _analyze(pathlib.Path(oldest) / "run"), "prev": _analyze(pathlib.Path(prev) / "run")}
    documents["last"] = _analyze(newest)
    _publish(oldest, documents["oldest"])
    _publish(prev, documents["prev"])
    return {"newest": newest, "into": into, "documents": documents}


@pytest.fixture(scope="module")
def same(tmp_path_factory):
    into = tmp_path_factory.mktemp("u1277-same")
    newest = pages.two_plane_run(into, SHAPE, runs=4)
    project = into / "both"
    snapshots = [pathlib.Path(s) for s in run_store.list_runs(str(project))]
    for snapshot in snapshots[:-1]:
        raw = into / f"{snapshot.name}.log"
        with gzip.open(snapshot / run_store.RAW_LOG_NAME, "rb") as packed:
            raw.write_bytes(packed.read())
        report = _cli("capture", "report", "--json", "--project-dir", str(project), str(raw))
        (snapshot / run_store.PLANE2_NAME).write_bytes(report)
    _, second, prev, _ = snapshots
    last, before = _analyze(newest), _analyze(prev / "run")
    shared = [fid for fid in _ids(last) if fid in _ids(before)]
    dropped, broken = shared[-1], shared[0]
    edited = dict(before, findings=[f for f in before["findings"] if f["id"] != dropped] + [GONE])
    walked = _analyze(second / "run")
    walked["findings"] = [f for f in walked["findings"] if f["id"] != broken]
    _publish(prev, edited)
    _publish(second, walked)
    return {
        "newest": newest,
        "into": into,
        "last": last,
        "edited": edited,
        "walked": walked,
        "dropped": dropped,
        "broken": broken,
    }


def test_finding_ids_are_unique_per_document(mixed):
    """The identity's precondition: one id names one finding in a document."""
    documents = [*mixed["documents"].values()] + [_analyze(pages.FIXTURES[label]) for label in pages.FIXTURES]
    for document in documents:
        ids = _ids(document)
        assert ids and len(ids) == len(set(ids)), ids


@needs_browser
def test_a_plane_one_side_lacks_is_neither_new_nor_resolved(mixed):
    """Only @last has Plane 2: its Plane 2 findings and the one it displaces are not compared."""
    page = _page(mixed["newest"], mixed["into"])
    last, prev = set(_ids(mixed["documents"]["last"])), set(_ids(mixed["documents"]["prev"]))
    assert "shared-source-blast" in prev - last, "the store no longer shows the plane difference"
    assert "shared-source-blast" not in page["resolved"] and page["resolved"] == [], page
    assert not [c for c in page["cards"] if c["since"] == "new"], page
    assert set(page["notCompared"]) == (last - prev) | (prev - last), page
    assert "Plane 2 recorded on one side only" in page["notComparedText"], page


@needs_browser
def test_the_page_marks_new_persisting_and_resolved(same):
    page = _page(same["newest"], same["into"])
    last, edited = set(_ids(same["last"])), set(_ids(same["edited"]))
    by_since = {kind: {c["id"] for c in page["cards"] if c["since"] == kind} for kind in ("new", "persisting")}
    assert same["dropped"] in by_since["new"] and by_since["new"] == last - edited, page
    assert by_since["persisting"] == last & edited and len(by_since["persisting"]) >= 3, page
    assert GONE["id"] in page["resolved"] and set(page["resolved"]) == edited - last, page
    assert GONE["title"] in page["resolvedText"] and page["notCompared"] == [], page


@needs_browser
def test_an_age_the_walk_could_not_finish_is_a_floor(same):
    """The oldest run is unpublished: a finding the second run holds reads "at least 3";
    the one the second run lacks reads exactly 2."""
    page = _page(same["newest"], same["into"])
    walked = set(_ids(same["walked"]))
    marks = {c["id"]: c["mark"] for c in page["cards"] if c["since"] == "persisting"}
    assert marks[same["broken"]] == "Still open · 2 runs", marks
    floors = {fid for fid in marks if fid in walked}
    assert floors, marks
    for fid in floors:
        assert marks[fid] == "Still open · at least 3 runs", (fid, marks[fid])
