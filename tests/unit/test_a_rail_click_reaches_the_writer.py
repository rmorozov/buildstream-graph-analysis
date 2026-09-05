"""UX-647: a rail click reaches the view-state writer.

`wireViewState` delegated from `#report`, and `app.js` draws the rail
as its **sibling** - so no rail click reached the writer and the
fragment it should have refreshed was replaced by the bare anchor the
link carries. Measured served on `macro_micro`, Chromium, round 88:

```text
report.contains(rail entry)                   false

after collapsing `decision`
  #~c=decision&v.elements=All+elements&n.binary_cost=25%3Acalls
after clicking rail `readers`
  #readers                                    <- the working set, gone
after the next click anywhere inside #report
  #readers~c=decision&v.elements=All+elements&n.binary_cost=25%3Acalls
```

The document kept `data-collapsed="true"` throughout: only the *link*
lost it, and only until the reader happened to click inside the report.

Two instruments, because they answer different halves. The served
clauses are the reader's own path - a real rail, a real anchor
navigation - and they skip where there is no Chrome. The node clause
below them holds the wiring itself: an event that arrives at the
document, from a control drawn nowhere near `root`, writes the
fragment. It runs everywhere.
"""
import json
import pathlib
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import pages
from tests.browser import NO_BROWSER, Browser, find_chrome

chrome = find_chrome()
node = shutil.which("node")
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _query(hash_text):
    """The `~`-separated view half of a fragment, parsed."""
    query = str(hash_text).lstrip("#").partition("~")[2]
    return urllib.parse.parse_qs(query, keep_blank_values=True)


#: Collapse a section, click a rail entry, and read the fragment with
#: **no** further interaction. The entry is chosen outside the
#: collapsed section so the hashchange reveal cannot be what re-opens
#: it, and the anchor is a real `<a href="#key">` click rather than a
#: dispatched event: the navigation that used to overwrite the query
#: is the browser's own default action and only a real click runs it.
_RAIL = r"""(async () => {
  const settle = () => new Promise((go) => setTimeout(go, 120));
  const report = document.getElementById("report");
  const collapse = report.querySelector(
    "section[data-section] button[data-collapse]");
  const section = collapse.closest("section[data-section]");
  const key = section.getAttribute("data-section");
  collapse.click();
  await settle();
  const set = location.hash;
  const entry = [...document.querySelectorAll("nav.toc [data-toc]")].find(
    (a) => {
      const target = document.getElementById(a.getAttribute("data-toc"));
      return target && !section.contains(target) && target !== section;
    });
  const to = entry.getAttribute("data-toc");
  const inReport = report.contains(entry);
  entry.click();
  await settle();
  return { key, to, inReport, set, after: location.hash,
           collapsed: section.getAttribute("data-collapsed") };
})()"""


@pytest.fixture(scope="module")
def railed(tmp_path_factory):
    """Both fixtures, served - which is where round 87 measured it."""
    if chrome is None or node is None:                   # pragma: no cover
        pytest.skip(NO_BROWSER)
    from tools.bga_view import serve

    out = {}
    with Browser(chrome) as opened:
        for label, fixture in pages.FIXTURES.items():
            run = pages.snapshot_copy(
                fixture, tmp_path_factory.mktemp(f"rail-{label}"))
            httpd, url = serve(str(run), port=0)
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            time.sleep(0.3)
            try:
                out[label] = opened.measure(url, _RAIL, 1440, 900)
            finally:
                httpd.shutdown()
    return out


@needs_browser
class TestTheRailIsOutsideTheReport:
    def test_the_rail_is_not_in_the_delegation_root(self, railed):
        """Non-vacuity, and the whole reason this item exists. If the
        rail were inside `#report` every clause below would be true of
        the defect too."""
        for label, out in railed.items():
            assert out["inReport"] is False, (label, out)

    def test_there_was_a_working_set_to_lose(self, railed):
        """The collapse reached the fragment, so what the rail click
        does to it afterwards is about the rail and not the collapse."""
        for label, out in railed.items():
            assert out["key"] in _query(out["set"]).get("c", [""])[0], (
                label, out)


@needs_browser
class TestTheFragmentSurvivesARailClick:
    def test_the_query_is_still_there_after_the_rail_click(self, railed):
        """The measurement in the docstring. One click, no second."""
        for label, out in railed.items():
            collapsed = _query(out["after"]).get("c", [""])[0]
            assert out["key"] in collapsed.split(","), (label, out)

    def test_the_rail_still_takes_the_reader_to_the_section(self, railed):
        """The anchor half is untouched: `UX-640` established the hrefs
        are `#${key}`, and the fix must not have cost the navigation.
        Read apart from the query, so this says only that the reader
        arrived."""
        for label, out in railed.items():
            anchor = out["after"].lstrip("#").partition("~")[0]
            assert anchor == out["to"], (label, out)

    def test_the_document_kept_the_state_all_along(self, railed):
        """Which is what made this invisible on screen: nothing looked
        broken, and only the link was wrong."""
        for label, out in railed.items():
            assert out["collapsed"] == "true", (label, out)


#: The wiring itself, on the shim: a `root` whose `ownerDocument` is a
#: recorder. `wireViewState` is asked to write, and then the listener
#: **the document** received is called - which is the only thing a
#: control drawn outside `root` can do. A writer wired to `root` leaves
#: the document with nothing to call.
_WIRED = """
const shim = await import(process.env.BGA_DOM_SHIM);
const vs = await import("./bga/viewer/viewstate.js");

const root = shim.makeNode("div");
const section = shim.makeNode("section");
section.setAttribute("data-section", "floors");
section.setAttribute("data-collapsed", "true");
root.append(section);

const heard = {};
root.ownerDocument = {
  addEventListener(name, fn) { (heard[name] ??= []).push(fn); },
};

const where = { hash: "#floors" };
const past = { replaceState(_state, _title, url) { where.hash = url; } };
const deferred = [];
vs.wireViewState(root, { location: where, history: past,
                         defer: (fn) => deferred.push(fn) });

const onRoot = Object.keys(root.listeners).sort();
const onDocument = Object.keys(heard).sort();
// The click a rail entry dispatches: it never touches `root`, so this
// is the document's listener or nothing. The write it defers is run
// here rather than waited for - `UX-646` owns *when*, this owns where.
for (const fn of heard.click ?? []) fn({ type: "click" });
for (const fn of deferred.splice(0)) fn();

console.log(JSON.stringify({ onRoot, onDocument, wrote: where.hash }));
"""


@pytest.fixture(scope="module")
def wired():
    done = subprocess.run([node, "--input-type=module", "-e", _WIRED],
                          capture_output=True, text=True, cwd=str(REPO),
                          timeout=120)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


@needs_node
class TestTheWriterListensWhereTheControlsAre:
    def test_the_document_is_what_hears_the_events(self, wired):
        """The three a control outside the report fires. Which events
        are listened for at all is `UX-646`'s clause, not this one."""
        assert set(wired["onDocument"]) >= {"input", "change", "click"}, wired

    def test_nothing_is_wired_to_the_root_alone(self, wired):
        """The defect: `#report`'s own listeners are `#report`'s own
        subtree, and the rail is not in it."""
        assert wired["onRoot"] == [], wired

    def test_an_event_from_outside_the_root_writes_the_view(
            self, wired):
        """Captured from `root` wherever it was heard - the anchor kept,
        the collapse set appended."""
        assert wired["wrote"] == "#floors~c=floors", wired


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
