"""UX-1144 (styleguide §6e.2.1): one concept, one label, on every surface.

Reads §6e.2.1's keyed-concept table, boots the two-plane synthetic page
(`gen-synthetic --layers 8 --width 14` plus its Plane 2 report),
`golden` and `macro_micro`, collects every label by its data key and
asserts each concept's label set (first letter folded) is the table's one word.
"""

import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
NOT_TWO_PLANE = "only the two-plane page carries every concept"

_STYLEGUIDE = (REPO / "docs" / "design" / "styleguide.md").read_text(encoding="utf-8")

#: `[key, label]` for every labelled value: a keyed `dt`, the `dt`
#: before a `dd[data-field]`, a waterfall row, a drawing tick (its
#: value stripped).
_COLLECT = r"""
(() => {
  const pairs = [];
  for (const dt of document.querySelectorAll('dt[data-key]'))
    pairs.push([dt.getAttribute('data-key'), dt.textContent]);
  for (const dd of document.querySelectorAll('dd[data-field]')) {
    const dt = dd.previousElementSibling;
    if (dt && dt.tagName === 'DT') pairs.push([dd.getAttribute('data-field'), dt.textContent]);
  }
  for (const row of document.querySelectorAll('.wf-row[data-field]'))
    pairs.push([row.getAttribute('data-field'), row.querySelector('.wf-label')?.textContent ?? '']);
  for (const tick of document.querySelectorAll('.draw-tick[data-mark]'))
    pairs.push([tick.getAttribute('data-mark'),
                tick.textContent.replace(/\s+[-\d.,]+\s*\S*$/, '')]);
  const texts = [];
  const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  for (let n = walker.nextNode(); n; n = walker.nextNode()) {
    const parent = n.parentElement;
    if (parent && !parent.closest('script, style, code, [data-raw-json]')) texts.push(n.textContent.trim());
  }
  return { pairs: pairs.map(([k, v]) => [k, v.trim()]), texts };
})()
"""


REJECTED = set()
#: Rejected for one concept, a chapter or a plain phrase elsewhere.
GENERIC = {"critical path", "primary"}


def _folded(label):
    """Sentence case moves the first letter only, so "Lb" is not "LB"."""
    return label[:1].lower() + label[1:]


def _concepts(guide):
    section = guide.split("#### 6e.2.1. Keyed concepts", 1)[1]
    section = section.split("\n#", 1)[0]
    rows = [line for line in section.splitlines() if line.startswith("|")][2:]
    out = {}
    for row in rows:
        cells = [c.strip() for c in row.strip("|").split("|")]
        out[cells[0]] = (re.findall(r"`([^`]+)`", cells[1]), cells[2])
        REJECTED.update(_folded(w.strip()) for w in cells[3].split(",") if w.strip() not in ("", "—"))
    return out


CONCEPTS = _concepts(_STYLEGUIDE)


def _matches(field, key):
    return field == key or field.endswith("." + key)


def _labels(pairs):
    """`{concept: {folded label, ...}}` for the concepts present."""
    found = {}
    for concept, (keys, _word) in CONCEPTS.items():
        for field, label in pairs:
            if any(_matches(field, key) for key in keys):
                found.setdefault(concept, set()).add(_folded(label))
    return found


def _two_plane(into):
    import tools.bga_view as view

    run = pages.two_plane_run(into, shape=("--layers", "8", "--width", "14"))
    page = pathlib.Path(into) / "report.html"
    view.export(str(run), str(page))
    return page.as_uri()


@pytest.fixture(scope="module", params=["two_plane", "golden", "macro_micro"])
def collected(request, tmp_path_factory):
    tmp = tmp_path_factory.mktemp(f"one-label-{request.param}")
    two = request.param == "two_plane"
    uri = _two_plane(tmp) if two else pages.export_uri(pages.FIXTURES[request.param], tmp)
    with Browser(chrome) as opened:
        out = opened.measure(uri, _COLLECT)
    return request.param, _labels(out["pairs"]), out["texts"]


def test_the_table_names_every_concept():
    assert len(CONCEPTS) == 9, sorted(CONCEPTS)
    assert all(keys and word for keys, word in CONCEPTS.values())


@needs_browser
def test_each_concept_carries_its_one_word(collected):
    label, found, _texts = collected
    wrong = {concept: sorted(labels) for concept, labels in found.items() if labels != {_folded(CONCEPTS[concept][1])}}
    assert not wrong, f"{label}: a concept read under another name: {wrong}"


@needs_browser
def test_the_two_plane_page_shows_every_concept(collected):
    label, found, _texts = collected
    if label != "two_plane":
        pytest.skip(NOT_TWO_PLANE)
    assert set(found) == set(CONCEPTS), sorted(set(CONCEPTS) - set(found))


@needs_browser
def test_no_text_node_is_a_rejected_spelling(collected):
    """A label with no data key (a rail row, a finding's words) still says the one word."""
    label, _found, texts = collected
    banned = REJECTED - {_folded(w) for _k, w in CONCEPTS.values()} - GENERIC
    said = sorted({t for t in texts if _folded(t) in banned})
    assert not said, f"{label}: a rejected spelling is on the page: {said}"
