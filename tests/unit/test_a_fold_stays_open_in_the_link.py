"""UX-642: a fold's identity is one thing under two attribute names.

`viewstate.js` collected the open disclosures with
`details[data-fold]`. Every fold `structured.js` builds names itself by
the payload path it holds — `data-fold-path` — so the selector matched
none of them: the nested-value folds, one per rabbit hole, were neither
captured into the link nor restored from it. Counted on the exported
fixtures, in Chromium, before the fix:

```text
                     details  data-fold  data-fold-path  both
golden                    25          5               5     0
macro_micro               52         16              12     0
```

Disjoint, and neither convention is a subset of the other, so reading
one attribute drops the other half whichever one is read.

`viewstate.js` reads both rather than `structured.js` setting a second
attribute: `data-fold-path` *is* the fold's identity, being the payload
path the fold holds, and it is the name the shorter one would have to
be derived from.

Both sites are covered separately — `captureView` writes `o=` and
`applyView` reads it, and a guard that only round-trips through the
pair cannot say which of the two it proved.
"""
import json
import pathlib
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import pages    # noqa: E402
from browser import NO_BROWSER, Browser, find_chrome    # noqa: E402

chrome = find_chrome()
needs_browser = pytest.mark.skipif(chrome is None, reason=NO_BROWSER)
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

#: The fold this item is about, by the path `renderStructured` gives it
#: on the value below, and the one that already worked beside it.
PATH_FOLD = "utilisation.buckets"
DECLARED_FOLD = "evidence"


def _node(script, timeout=120):
    result = subprocess.run([node, "--input-type=module", "-e", script],
                            capture_output=True, text=True, cwd=str(REPO),
                            timeout=timeout)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def folds():
    return _node(_SHIM + _FOLDS)


@needs_node
class TestBothConventionsReachTheCapture:
    def test_the_two_producers_still_disagree_about_the_attribute(self, folds):
        """Non-vacuity. Every clause below is about a page carrying one
        fold of each convention; if a producer ever set both, or the
        same one, this file would be measuring nothing."""
        assert folds["identities"] == {
            PATH_FOLD: ["data-fold-path"],
            DECLARED_FOLD: ["data-fold"]}, folds

    def test_a_structured_fold_reaches_the_link(self, folds):
        """The clause the defect fails: `o=` was written without it."""
        assert folds["captured_path"] == PATH_FOLD, folds

    def test_a_declared_fold_still_reaches_the_link(self, folds):
        assert folds["captured_declared"] == DECLARED_FOLD, folds

    def test_one_capture_carries_both(self, folds):
        assert sorted(folds["captured_both"].split(",")) == sorted(
            [DECLARED_FOLD, PATH_FOLD]), folds

    def test_a_fold_nobody_opened_is_not_in_the_link(self, folds):
        """`utilisation` and the two `.a` folds are on the same page and
        shut. A capture that named them would restore a page nobody was
        looking at."""
        assert folds["captured_none"] == "", folds


@needs_node
class TestBothConventionsAreRestored:
    def test_a_hand_written_link_opens_a_structured_fold(self, folds):
        """The restore site on its own, driven by a query no
        `captureView` produced - so this clause reddens for the reader
        of `o=` and not for its writer."""
        assert folds["applied_path"] == [f"o:{PATH_FOLD}"], folds
        assert folds["restored_path"] is True, folds

    def test_a_hand_written_link_still_opens_a_declared_fold(self, folds):
        assert folds["applied_declared"] == [f"o:{DECLARED_FOLD}"], folds
        assert folds["restored_declared"] is True, folds

    def test_the_round_trip_lands_both_in_a_fresh_render(self, folds):
        """The acceptance test: open, capture, restore into a page built
        from scratch."""
        assert folds["round_trip"] == {PATH_FOLD: True,
                                       DECLARED_FOLD: True}, folds

    def test_the_fresh_render_leaves_the_rest_shut(self, folds):
        assert folds["round_trip_shut"] == ["utilisation",
                                            "utilisation.buckets.0.a",
                                            "utilisation.buckets.1.a"], folds


@pytest.fixture(scope="module")
def handed_over(tmp_path_factory):
    """The page a reader gets, a fold opened on it, and the link that
    came back opened as a **second document**.

    Two exported copies rather than one: a navigation that differs only
    in the fragment is a same-document navigation, so the DOM - and the
    fold left open on it - survives, and the reload would prove nothing.
    """
    into = tmp_path_factory.mktemp("u642")
    first = pages.export_uri(pages.FIXTURES["macro_micro"], into, "first.html")
    second = pages.export_uri(pages.FIXTURES["macro_micro"], into,
                              "second.html")
    with Browser(chrome) as opened:
        wrote = opened.measure(first, _OPEN)
        read = opened.measure(second + wrote["hash"], _READ)
    return {"wrote": wrote, "read": read}


def _open_set(hash_text):
    """The `o=` set out of a fragment, the way the page's reader is."""
    import urllib.parse

    query = str(hash_text).lstrip("#").partition("~")[2]
    got = urllib.parse.parse_qs(query, keep_blank_values=True).get("o", [""])
    return [name for name in got[0].split(",") if name]


@needs_browser
class TestTheLinkAReaderHandsOver:
    def test_the_page_carries_both_populations_and_shares_none(
            self, handed_over):
        """The measurement in the docstring, held: two conventions, and
        neither a subset of the other, so a selector reading one drops
        the other whichever it reads."""
        census = handed_over["wrote"]["census"]
        assert census["both"] == 0, census
        assert census["fold"] and census["path"], census

    def test_a_structured_fold_reaches_the_fragment(self, handed_over):
        """What the reader pastes. The defect wrote `o=` without it."""
        wrote = handed_over["wrote"]
        assert wrote["structuredOpen"] is True, wrote
        assert wrote["structured"] in _open_set(wrote["hash"]), wrote

    def test_the_link_opens_it_again_in_a_fresh_document(self, handed_over):
        wrote, read = handed_over["wrote"], handed_over["read"]
        assert read["fresh"] is True, "the second load reused the first DOM"
        assert wrote["structured"] in read["open"], read


#: A structured fold opened on the real page, and what the fragment
#: said afterwards.
#:
#: One summary, and a turn to settle: `UX-646` fixed the lag this used
#: to buy off by clicking a second one. `test_the_fragment_keeps_up_
#: with_the_fold.py` is the guard for the timing itself.
_OPEN = """(async () => {
  const census = {
    details: document.querySelectorAll("details").length,
    fold: document.querySelectorAll("details[data-fold]").length,
    path: document.querySelectorAll("details[data-fold-path]").length,
    both: document.querySelectorAll(
      "details[data-fold][data-fold-path]").length,
  };
  const structured = document.querySelector("details[data-fold-path]");
  structured.querySelector("summary").click();
  await new Promise((go) => setTimeout(go, 120));
  window.__u642 = true;
  return { census, hash: location.hash,
           structured: structured.getAttribute("data-fold-path"),
           structuredOpen: structured.open };
})()"""

#: The same report at a second URL, opened at that fragment. `fresh`
#: says the first document was left behind rather than re-shown.
_READ = """(() => {
  const key = (node) => node.getAttribute("data-fold")
    ?? node.getAttribute("data-fold-path");
  return {
    fresh: window.__u642 !== true,
    open: [...document.querySelectorAll("details")]
      .filter((node) => node.open).map(key),
  };
})()"""

_SHIM = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;

function make(tag) {
  const node = _makeNode(tag);
  node.open = false;
  return node;
}
globalThis.Event = class { constructor(type) { this.type = type; } };
_installDocument({
  createElement: make,
  createElementNS: (_n, t) => make(t),
});
"""

_FOLDS = """
const app = await import("./tests/viewer.mjs");
const vs = await import("./bga/viewer/viewstate.js");

// One fold from each producer. `renderStructured` names every fold it
// builds by the payload path it holds; `renderFindingEvidence` sets
// `data-fold` by hand, as `element.js`, `views.js` and `questions.js`
// also do. The value is nested past the cell limit and the evidence has
// more than `EVIDENCE_SHOWN` scalars, which is what earns each a fold.
const VALUE = { buckets: [
  { a: { deep: { deeper: [1, 2, 3] } }, b: 2 },
  { a: { deep: { deeper: [4, 5, 6] } }, b: 3 }] };
const EVIDENCE = { p: 1, q: 2, r: 3, s: 4, t: 5 };

function page() {
  const root = make("div");
  root.append(app.renderStructured("utilisation", VALUE));
  root.append(app.renderFindingEvidence(EVIDENCE));
  return root;
}
const key = (node) => node.getAttribute("data-fold")
  ?? node.getAttribute("data-fold-path");
const fold = (root, wanted) => root.querySelectorAll("details")
  .filter((node) => key(node) === wanted)[0];
const openState = (root) => Object.fromEntries(
  root.querySelectorAll("details").map((node) => [key(node), node.open]));

const identities = {};
for (const name of ["utilisation.buckets", "evidence"]) {
  const node = fold(page(), name);
  identities[name] = ["data-fold", "data-fold-path"].filter(
    (attr) => node.getAttribute(attr) !== null);
}

// Capture, one convention at a time and then both, so a selector that
// reads either half alone is visible as which half it dropped.
const only = (wanted) => {
  const root = page();
  fold(root, wanted).open = true;
  return new URLSearchParams(vs.captureView(root)).get("o") ?? "";
};
const both = page();
fold(both, "utilisation.buckets").open = true;
fold(both, "evidence").open = true;
const capturedBoth = new URLSearchParams(vs.captureView(both)).get("o") ?? "";

// Restore, from a query written here rather than by `captureView`.
const restore = (wanted) => {
  const root = page();
  const applied = vs.applyView(root, `o=${wanted}`).filter(
    (entry) => entry.startsWith("o:"));
  return { applied, open: fold(root, wanted).open };
};
const path = restore("utilisation.buckets");
const declared = restore("evidence");

// The round trip: open both, capture, apply to a page built from
// scratch.
const fresh = page();
vs.applyView(fresh, vs.captureView(both));
const after = openState(fresh);

console.log(JSON.stringify({
  identities,
  captured_path: only("utilisation.buckets"),
  captured_declared: only("evidence"),
  captured_both: capturedBoth,
  captured_none: new URLSearchParams(vs.captureView(page())).get("o") ?? "",
  applied_path: path.applied, restored_path: path.open,
  applied_declared: declared.applied, restored_declared: declared.open,
  round_trip: { "utilisation.buckets": after["utilisation.buckets"],
                evidence: after.evidence },
  round_trip_shut: Object.keys(after).filter((name) => !after[name]).sort(),
}));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
