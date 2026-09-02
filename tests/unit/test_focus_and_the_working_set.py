"""UX-222 and UX-225: one element at a time, and where the reader got to.

Two items, one mechanism. `data-element` is already on path boxes, table
rows, blast rows, top actions, horizon steps, culprit rows and finding
element lists, so "show me only this element" and "I have dealt with
this element" are both a predicate over an attribute the document
already carries. No new data model, no second render.

Both are *view state*, so both travel in UX-211's fragment. Not
`localStorage`: it remembers for me, on this browser, and an exported
report opened from `file://` may get none at all. Not the store: the
viewer has no write method and must not grow one.

The two invariants these guards exist for:

* **focus dims, it never removes.** The reader must be able to see what
  they are not looking at, and the document underneath must stay
  byte-identical or Ctrl-F, the anchors and the export all become
  lies.
* **a mark annotates, it never filters.** An element marked `done` is
  still ranked and still in the horizon. A ranking that quietly drops
  what the reader dismissed is one they cannot check.
"""
import json
import os
import shutil
import subprocess

import pytest

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# A shim with the few selector shapes these modules use. `matches` is a
# real matcher over tag/attribute rather than a stub that answers true,
# because a stub would make every guard below pass for the wrong reason.
_SHIM = """
function matches(node, selector) {
  if (node.nodeType !== 1) return false;
  return selector.split(",").map((s) => s.trim()).some((one) => {
    const attr = one.match(/^([a-z]*)\\[([a-z-]+)(?:=([^\\]]+))?\\]$/);
    if (attr) {
      const [, tag, name, value] = attr;
      if (tag && node.tagName !== tag) return false;
      const got = node.attrs[name];
      if (got === undefined) return false;
      return value === undefined || got === value.replace(/^["']|["']$/g, "");
    }
    return node.tagName === one;
  });
}
function walk(node, out = []) {
  for (const child of node.children ?? []) { out.push(child); walk(child, out); }
  return out;
}
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;

function make(tag) {
  const node = _makeNode(tag);
  return node;
}
globalThis.Event = class { constructor(type) { this.type = type; } };
_installDocument();

// A small document with the shapes both features act on: two sections
// that mention elements, one that mentions none.
function fixture() {
  const root = make("div");
  const mk = (key, uids) => {
    const s = make("section");
    s.setAttribute("data-section", key);
    if (uids.length === 1) s.setAttribute("data-element", uids[0]);
    for (const uid of uids) {
      const row = make("li");
      row.setAttribute("data-element", uid);
      s.append(row);
    }
    root.append(s);
    return s;
  };
  mk("element-core-bst", ["core.bst"]);
  mk("element-lib-bst", ["lib.bst"]);
  mk("elements", ["core.bst", "lib.bst", "app.bst"]);
  const bare = make("section");
  bare.setAttribute("data-section", "floors");
  root.append(bare);
  return root;
}
// `_parent`/`parentElement` join the skip list because the shared shim
// populates them the way a browser does, which makes the tree cyclic
// (`UX-264`). The old per-file shim declared `parentNode` and never
// set it, so this snapshot was of a forest, not the document.
const snapshot = (root) => JSON.stringify(root, (k, v) =>
  (k === "parentNode" || k === "parentElement" || k === "_parent"
   || k === "listeners" || k === "_style") ? undefined : v);
"""


def _js(body):
    result = subprocess.run([node, "--input-type=module", "-e", _SHIM + body],
                            capture_output=True, text=True, cwd=REPO, timeout=60)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@needs_node
class TestFocusDimsAndNeverRemoves:

    def test_only_the_other_elements_are_dimmed(self):
        out = _js('''
          const f = await import("./bga/viewer/focus.js");
          const root = fixture();
          f.applyFocus(root, "core.bst");
          const nodes = root.querySelectorAll("[data-element]");
          console.log(JSON.stringify({
            matching: nodes.filter((n) => n.attrs["data-element"] === "core.bst")
                           .map((n) => n.attrs["data-dimmed"] ?? null),
            others: nodes.filter((n) => n.attrs["data-element"] !== "core.bst")
                         .map((n) => n.attrs["data-dimmed"] ?? null),
          }));
        ''')
        assert out["matching"], "fixture has no matching nodes"
        assert set(out["matching"]) == {None}, out
        assert out["others"], "fixture has no other nodes"
        assert set(out["others"]) == {"true"}, out

    def test_a_section_mentioning_nothing_is_collapsed_not_removed(self):
        out = _js('''
          const f = await import("./bga/viewer/focus.js");
          const root = fixture();
          const before = root.querySelectorAll("section[data-section]").length;
          f.applyFocus(root, "core.bst");
          const sections = root.querySelectorAll("section[data-section]");
          console.log(JSON.stringify({
            before, after: sections.length,
            unfocused: sections.filter((s) => s.attrs["data-unfocused"] === "true")
                               .map((s) => s.attrs["data-section"]),
          }));
        ''')
        assert out["after"] == out["before"], "a section was removed"
        assert out["unfocused"] == ["element-lib-bst", "floors"], out

    def test_clearing_restores_the_document_exactly(self):
        """The acceptance's own words: byte-identical after clearing."""
        out = _js('''
          const f = await import("./bga/viewer/focus.js");
          const root = fixture();
          const before = snapshot(root);
          f.applyFocus(root, "core.bst");
          const focused = snapshot(root);
          f.clearFocus(root);
          console.log(JSON.stringify({
            restored: snapshot(root) === before,
            changedWhileFocused: focused !== before,
          }));
        ''')
        assert out["changedWhileFocused"] is True, "focus did nothing at all"
        assert out["restored"] is True

    def test_focus_never_removes_nodes_from_the_document(self):
        out = _js('''
          const f = await import("./bga/viewer/focus.js");
          const root = fixture();
          const before = root.querySelectorAll("[data-element]").length;
          f.applyFocus(root, "core.bst");
          console.log(JSON.stringify({
            before, after: root.querySelectorAll("[data-element]").length}));
        ''')
        assert out["after"] == out["before"]

    def test_the_bar_names_what_is_focused(self):
        out = _js('''
          const f = await import("./bga/viewer/focus.js");
          const bar = f.renderFocusBar("core.bst");
          console.log(JSON.stringify({
            element: bar.attrs["data-element"],
            role: bar.attrs["data-role"],
            hasClear: bar.children.some((c) => c.className === "focus-clear"),
          }));
        ''')
        assert out == {"element": "core.bst", "role": "focus-bar", "hasClear": True}


@needs_node
class TestMarksAnnotateAndNeverFilter:

    def test_a_mark_lands_on_every_occurrence(self):
        out = _js('''
          const f = await import("./bga/viewer/focus.js");
          const root = fixture();
          f.applyMarks(root, { "core.bst": "done" });
          console.log(JSON.stringify(
            root.querySelectorAll("[data-element]")
                .filter((n) => n.attrs["data-element"] === "core.bst")
                .map((n) => n.attrs["data-mark"] ?? null)));
        ''')
        assert len(out) > 1, "fixture must mention core.bst more than once"
        assert set(out) == {"done"}

    def test_a_marked_element_is_still_in_the_document(self):
        """Clause 3: still ranked, only annotated."""
        out = _js('''
          const f = await import("./bga/viewer/focus.js");
          const root = fixture();
          const before = root.querySelectorAll("[data-element]").length;
          f.applyMarks(root, { "core.bst": "done", "lib.bst": "aside" });
          console.log(JSON.stringify({
            before, after: root.querySelectorAll("[data-element]").length,
            stillThere: root.querySelectorAll("[data-element]")
              .some((n) => n.attrs["data-element"] === "core.bst"),
          }));
        ''')
        assert out["after"] == out["before"]
        assert out["stillThere"] is True

    def test_an_unknown_mark_is_refused(self):
        out = _js('''
          const f = await import("./bga/viewer/focus.js");
          const root = fixture();
          f.applyMarks(root, { "core.bst": "probably" });
          console.log(JSON.stringify(
            root.querySelectorAll("[data-mark]").length));
        ''')
        assert out == 0

    def test_the_summary_counts_the_marks(self):
        out = _js('''
          const f = await import("./bga/viewer/focus.js");
          console.log(JSON.stringify(f.summariseMarks(
            { "a.bst": "working", "b.bst": "working",
              "c.bst": "done", "d.bst": "aside" })));
        ''')
        assert out == "2 working · 1 done · 1 set aside"

    def test_no_marks_means_no_summary(self):
        out = _js('''
          const f = await import("./bga/viewer/focus.js");
          console.log(JSON.stringify(f.renderMarkSummary({}) === null));
        ''')
        assert out is True

    def test_the_vocabulary_matches_the_one_views_renders(self):
        """`views.js` imports nothing, so it spells the closed set out.
        This is what stops the two copies drifting."""
        out = _js('''
          const f = await import("./bga/viewer/focus.js");
          const v = await import("./tests/viewer.mjs");
          console.log(JSON.stringify({ focus: f.MARKS, views: v.ELEMENT_MARKS }));
        ''')
        assert out["focus"] == out["views"]


@needs_node
class TestBothTravelInTheFragment:

    def test_focus_round_trips(self):
        out = _js('''
          const f = await import("./bga/viewer/focus.js");
          const vs = await import("./bga/viewer/viewstate.js");
          const first = fixture();
          f.applyFocus(first, "lib.bst");
          const query = vs.captureView(first);
          const fresh = fixture();
          vs.applyView(fresh, query);
          console.log(JSON.stringify({
            query,
            focus: fresh.attrs["data-focus"],
            dimmed: fresh.querySelectorAll("[data-element]")
              .filter((n) => n.attrs["data-dimmed"] === "true")
              .map((n) => n.attrs["data-element"]),
          }));
        ''')
        assert "focus=lib.bst" in out["query"]
        assert out["focus"] == "lib.bst"
        assert "lib.bst" not in out["dimmed"]
        assert set(out["dimmed"]) == {"core.bst", "app.bst"}

    def test_marks_round_trip_with_no_storage_at_all(self):
        """The acceptance: a fresh context with nothing remembered."""
        out = _js('''
          const f = await import("./bga/viewer/focus.js");
          const vs = await import("./bga/viewer/viewstate.js");
          const first = fixture();
          f.applyMarks(first, { "core.bst": "done", "app.bst": "working" });
          const query = vs.captureView(first);
          const fresh = fixture();
          vs.applyView(fresh, query);
          console.log(JSON.stringify({
            query,
            marks: f.readMarks(fresh),
            summary: f.summariseMarks(f.readMarks(fresh)),
          }));
        ''')
        assert "mk=" in out["query"]
        assert out["marks"] == {"core.bst": "done", "app.bst": "working"}
        assert out["summary"] == "1 working · 1 done"

    def test_the_two_travel_together(self):
        out = _js('''
          const f = await import("./bga/viewer/focus.js");
          const vs = await import("./bga/viewer/viewstate.js");
          const first = fixture();
          f.applyMarks(first, { "core.bst": "aside" });
          f.applyFocus(first, "core.bst");
          const fresh = fixture();
          vs.applyView(fresh, vs.captureView(first));
          console.log(JSON.stringify({
            focus: fresh.attrs["data-focus"],
            marks: f.readMarks(fresh),
          }));
        ''')
        assert out["focus"] == "core.bst"
        assert out["marks"] == {"core.bst": "aside"}

    def test_a_hash_naming_an_element_this_run_lacks_is_dropped(self):
        out = _js('''
          const vs = await import("./bga/viewer/viewstate.js");
          const f = await import("./bga/viewer/focus.js");
          const root = fixture();
          vs.applyView(root, "focus=nowhere.bst&mk=absent.bst:done");
          console.log(JSON.stringify({
            focus: root.attrs["data-focus"] ?? null,
            marks: f.readMarks(root),
            dimmed: root.querySelectorAll("[data-dimmed]").length,
          }));
        ''')
        # The focus attribute is set - it is the reader's stated intent -
        # but nothing in this document matches, so nothing is annotated.
        assert out["marks"] == {}

    def test_the_marks_are_not_in_local_storage(self):
        """The channel decision, asserted as an absence.

        Comments are stripped first: this module's own header explains
        at length *why* `localStorage` is the wrong channel here, and a
        guard that fired on the explanation would be rewarding silence
        about the decision.
        """
        source = open(os.path.join(REPO, "bga/viewer/focus.js"),
                      encoding="utf-8").read()
        code = "\n".join(line for line in source.splitlines()
                         if not line.lstrip().startswith("//"))
        for banned in ("localStorage", "sessionStorage", "indexedDB"):
            assert banned not in code, (
                f"{banned} remembers for one reader on one browser; the "
                f"fragment is the channel these two travel in")


@needs_node
class TestTheControlsAreOnEveryElement:

    def test_each_element_section_offers_focus_and_the_three_marks(self):
        out = _js('''
          const v = await import("./tests/viewer.mjs");
          const payload = { critical_path_detail: [
            { element_uid: "core.bst", duration_us: 10, share_of_path: 0.5 }] };
          const root = make("div");
          const nodes = v.renderElementSections(payload, root, {});
          const section = nodes[0];
          const buttons = section.querySelectorAll("button");
          console.log(JSON.stringify({
            focus: buttons.filter((b) => b.attrs["data-focus-element"])
                          .map((b) => b.attrs["data-focus-element"]),
            marks: buttons.filter((b) => b.attrs["data-mark-element"])
                          .map((b) => b.attrs["data-mark-value"]),
          }));
        ''')
        assert out["focus"] == ["core.bst"]
        assert out["marks"] == ["working", "done", "aside"]
