"""UX-646: the fragment names the fold the reader just opened.

`wireViewState` wrote the hash on the bubbling `click`. A `<summary>`
flips its parent's `open` **after** that dispatch, and the `toggle`
listener beside it never fired because `toggle` does not bubble - so
every fragment described the fold state as it was one interaction ago.
Measured served on `macro_micro`, Chromium, round 88, one fold opened
and nothing else touched:

```text
before                #~c=decision&v.elements=All+elements&n.…
after one summary     #~c=decision&v.elements=All+elements&n.…
after a second        #~c=decision&v.elements=All+elements&n.…&o=evidence
```

`o=evidence` is the *first* fold, arriving on the second click. The
guard here opens exactly one and reads the fragment - which is the
clause `UX-642` could not write and said so at its own site.

The node clause below is the timing on its own, with no browser: the
document's listener is called, and only *then* is `open` flipped, the
way a summary's activation does it. A writer that has finished by the
end of the dispatch cannot see it.
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


def _open_set(hash_text):
    """The `o=` set out of a fragment, the way the page's reader is."""
    query = str(hash_text).lstrip("#").partition("~")[2]
    got = urllib.parse.parse_qs(query, keep_blank_values=True).get("o", [""])
    return [name for name in got[0].split(",") if name]


#: One summary clicked, and nothing else. The fold is chosen for a key
#: no other fold on the page shares - `macro_micro` carries several
#: `data-fold="evidence"` - so `o=` naming it is this click's doing.
_FOLD = r"""(async () => {
  const settle = () => new Promise((go) => setTimeout(go, 120));
  const key = (n) => n.getAttribute("data-fold")
    ?? n.getAttribute("data-fold-path");
  const folds = [...document.querySelectorAll(
    "#report details[data-fold],#report details[data-fold-path]")];
  const seen = {};
  for (const n of folds) seen[key(n)] = (seen[key(n)] ?? 0) + 1;
  const unique = folds.filter((n) => !n.open && seen[key(n)] === 1);
  const one = unique[0];
  const before = location.hash;
  one.querySelector("summary").click();
  await settle();
  const after = location.hash;
  // A fold nothing clicked. The browser opens one itself to show a
  // find-in-page hit, and `toggle` is the only event it fires - so
  // this is the capture-phase listener or nothing.
  const two = unique[1];
  two.open = true;
  await settle();
  return { opened: key(one), open: one.open, before, after,
           folds: folds.length, unclicked: key(two),
           afterUnclicked: location.hash,
           openNow: folds.filter((n) => n.open).map(key) };
})()"""


@pytest.fixture(scope="module")
def folded(tmp_path_factory):
    """Both fixtures, served - where round 87 measured the lag."""
    if chrome is None or node is None:                   # pragma: no cover
        pytest.skip(NO_BROWSER)
    from tools.bga_view import serve

    out = {}
    with Browser(chrome) as opened:
        for label, fixture in pages.FIXTURES.items():
            run = pages.snapshot_copy(
                fixture, tmp_path_factory.mktemp(f"fold-{label}"))
            httpd, url = serve(str(run), port=0)
            threading.Thread(target=httpd.serve_forever, daemon=True).start()
            time.sleep(0.3)
            try:
                out[label] = opened.measure(url, _FOLD, 1440, 900)
            finally:
                httpd.shutdown()
    return out


@needs_browser
class TestExactlyOneFoldWasOpened:
    def test_the_page_has_folds_and_none_were_open(self, folded):
        """Non-vacuity both ways: something to open, and a fragment that
        did not already name it."""
        for label, out in folded.items():
            assert out["folds"] >= 5, (label, out)
            assert _open_set(out["before"]) == [], (label, out)

    def test_one_click_left_one_fold_open(self, folded):
        """The clause `UX-642`'s guard had to buy with a second click.
        Read before the unclicked fold below is opened."""
        for label, out in folded.items():
            assert out["open"] is True, (label, out)
            assert _open_set(out["after"]) != [], (label, out)


@needs_browser
class TestTheFragmentNamesThatFold:
    def test_the_fold_just_opened_is_in_the_link(self, folded):
        for label, out in folded.items():
            assert _open_set(out["after"]) == [out["opened"]], (label, out)

    def test_a_fold_the_page_opened_is_in_the_link_too(self, folded):
        """`toggle` in the capture phase, in a real browser: no click
        was dispatched, and a bubbling listener on the document would
        never have run."""
        for label, out in folded.items():
            assert _open_set(out["afterUnclicked"]) == [
                out["opened"], out["unclicked"]], (label, out)


#: The timing, without a browser. The document's listener is called -
#: the click - and `open` is flipped *after* it returns, which is the
#: order a `<summary>`'s activation behaviour runs in. Then the write
#: the wiring deferred is run, and it is the one that can see the fold.
_TIMING = """
const shim = await import(process.env.BGA_DOM_SHIM);
const vs = await import("./bga/viewer/viewstate.js");

const root = shim.makeNode("div");
const fold = shim.makeNode("details");
fold.open = false;
fold.setAttribute("data-fold", "evidence");
root.append(fold);

const heard = {};
root.ownerDocument = {
  addEventListener(name, fn) { (heard[name] ??= []).push(fn); },
};
const where = { hash: "#floors" };
const past = { replaceState(_state, _title, url) { where.hash = url; } };
const deferred = [];
vs.wireViewState(root, { location: where, history: past,
                         defer: (fn) => deferred.push(fn) });

// Wherever the wiring put them: this file is about *when* the write
// happens and `test_a_rail_click_reaches_the_writer.py` about where it
// listens, so a change of root must not redden this one.
const listeners = (name) => [...(heard[name] ?? []),
                             ...((root.listeners ?? {})[name] ?? [])];
const click = () => { for (const fn of listeners("click")) fn({}); };
click();
const duringTheDispatch = where.hash;
// What the browser does next, and what no listener on that click can
// have seen: the summary's activation flips `open`.
fold.open = true;
const stillDuring = where.hash;
const queuedByOneClick = deferred.length;
for (const fn of deferred.splice(0)) fn();
const afterTheTurn = where.hash;

// One deferred write per burst: a filter box fires `input` per
// keystroke and `captureView` walks every table.
click(); click(); click();
const queuedByThree = deferred.length;
for (const fn of deferred.splice(0)) fn();

// A fold that opened with no click on it. `toggle` is the only event
// a `<details>` fires when something other than the reader's pointer
// opens it, and it does not bubble - so this is the capture listener
// or nothing.
const second = shim.makeNode("details");
second.open = true;
second.setAttribute("data-fold-path", "utilisation.buckets");
root.append(second);
for (const fn of listeners("toggle")) fn({ type: "toggle" });
for (const fn of deferred.splice(0)) fn();
const afterToggle = where.hash;

console.log(JSON.stringify({ duringTheDispatch, stillDuring, afterTheTurn,
                             queuedByOneClick, queuedByThree, afterToggle,
                             heardToggle: listeners("toggle").length }));
"""


@pytest.fixture(scope="module")
def timing():
    done = subprocess.run([node, "--input-type=module", "-e", _TIMING],
                          capture_output=True, text=True, cwd=str(REPO),
                          timeout=120)
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


@needs_node
class TestTheWriteOutlivesTheDispatch:
    def test_the_dispatch_itself_cannot_see_the_fold(self, timing):
        """Nothing is written during the dispatch at all - a write made
        there is one interaction behind by construction, which is the
        defect. The fragment is untouched until the turn below."""
        assert timing["duringTheDispatch"] == "#floors", timing
        assert timing["stillDuring"] == "#floors", timing

    def test_the_deferred_write_names_the_fold(self, timing):
        assert _open_set(timing["afterTheTurn"]) == ["evidence"], timing

    def test_a_burst_of_events_defers_one_write(self, timing):
        assert timing["queuedByOneClick"] == 1, timing
        assert timing["queuedByThree"] == 1, timing

    def test_a_toggle_with_no_click_reaches_the_writer(self, timing):
        """The other half of the Required Fix: `toggle` does not bubble,
        so a fold nothing clicked was invisible to a delegating root."""
        assert timing["heardToggle"] == 1, timing
        assert _open_set(timing["afterToggle"]) == [
            "evidence", "utilisation.buckets"], timing


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
