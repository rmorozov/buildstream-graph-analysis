"""UX-1269: each wait quantity has one drawn name, the decision states how the
gap relates to resource wait, the Effective CPUs gloss agrees with its source,
and a costliest binary under the opportunity floor carries no step."""

import json
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

PAGE_SHAPE = ("--layers", "40", "--width", "60", "--workload", "binaries")

#: A drawing tick's mark, as the key it draws.
MARKS = {
    "execution": "execution_on_chain_us",
    "dependency": "dependency_wait_us",
    "resource": "resource_wait_us",
    "scheduler": "scheduler_wait_us",
    "idle": "idle_us",
    "retry": "retry_wait_us",
    "head": "untracked_head_us",
    "tail": "untracked_tail_us",
    "gap": "scheduling_gap_us",
}
WAIT_KEYS = set(MARKS.values()) | {"certified_headroom", "certified_headroom_us"}
#: A capacity kind a gloss could name; the source line must name the same one.
KINDS = ("host core", "builder slot", "cpu budget")

_READ = r"""
(() => {
  const pairs = [];
  for (const dt of document.querySelectorAll('dt[data-key]')) pairs.push([dt.getAttribute('data-key'), dt.textContent]);
  for (const dd of document.querySelectorAll('dd[data-field]')) {
    const dt = dd.previousElementSibling;
    if (dt && dt.tagName === 'DT') pairs.push([dd.getAttribute('data-field'), dt.textContent]);
  }
  for (const row of document.querySelectorAll('.wf-row[data-field]'))
    pairs.push([row.getAttribute('data-field'), row.querySelector('.wf-label')?.textContent ?? '']);
  for (const tick of document.querySelectorAll('.draw-tick[data-mark]'))
    pairs.push(['mark:' + tick.getAttribute('data-mark'), tick.textContent.replace(/\s+[-\d.,]+\s*\S*$/, '')]);
  const util = document.getElementById('utilisation');
  return {
    pairs: pairs.map(([k, v]) => [k, v.trim()]),
    relation: document.querySelector('#overview [data-role="wait-relation"]')?.textContent ?? '',
    floors: [...document.querySelectorAll('#overview [data-field^="floors."]')].length,
    split: [...document.querySelectorAll('dl.opportunity dt')].map((dt) => dt.textContent),
    gloss: util?.querySelector('[data-describes="effective_cpus"]')?.textContent ?? '',
    source: util?.querySelector('dt[data-key="effective_cpus_source"] + dd [data-raw]')?.textContent ?? '',
  };
})()
"""


@pytest.fixture(scope="module")
def page(tmp_path_factory):
    import contextlib
    import io

    import tools.bga_view as view
    from bga.cli import main

    tmp = tmp_path_factory.mktemp("one-name")
    run = pages.two_plane_run(tmp, shape=PAGE_SHAPE, runs=2)
    out = tmp / "report.html"
    view.export(str(run), str(out))
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(io.StringIO()):
        main(["analyze", str(run), "--format", "json"])
    with Browser(chrome) as opened:
        read = opened.measure(out.as_uri(), _READ)
    return read, json.loads(buffer.getvalue())


def _key(field):
    if field.startswith("mark:"):
        return MARKS.get(field[5:])
    return field.rsplit(".", 1)[-1]


@needs_browser
def test_each_wait_key_is_drawn_under_one_name(page):
    read, _doc = page
    names = {}
    for field, label in read["pairs"]:
        key = _key(field)
        if key in WAIT_KEYS:
            names.setdefault(key, set()).add(label[:1].lower() + label[1:])
    assert {"resource_wait_us", "scheduling_gap_us", "execution_on_chain_us"} <= set(names), sorted(names)
    two = {key: sorted(labels) for key, labels in names.items() if len(labels) > 1}
    assert not two, f"a wait quantity drawn under two names: {two}"


@needs_browser
def test_the_time_chapter_states_the_waits_against_the_gaps(page):
    """The waterfall and the floors drawn together say how the decision's gap relates to the waits."""
    read, _doc = page
    assert "Scheduling gap" in read["split"] and read["floors"], read
    for term in ("Scheduling gap", "Waiting on resources", "Chain floor T∞"):
        assert term in read["relation"], (term, read["relation"])


@needs_browser
def test_the_effective_cpus_gloss_agrees_with_its_source(page):
    read, _doc = page
    gloss, source = read["gloss"].lower(), read["source"].lower()
    assert gloss and source, read
    named = [kind for kind in KINDS if kind in gloss]
    assert all(kind in source for kind in named), (read["gloss"], read["source"])
    assert not re.search(r"\bnot (host cores|builder slots|a declared)", gloss), read["gloss"]


@needs_browser
def test_a_costliest_binary_under_the_floor_carries_no_step(page):
    _read, doc = page
    finding = next(f for f in doc["findings"] if f["id"] == "costliest-binary")
    share = finding["evidence"]["cpu_us"] / doc["utilisation"]["capacity_cpu_us"]
    assert share < 0.01, share
    assert "text" not in finding["step"] and finding["step"]["why_none"], finding["step"]
