"""UX-228: focus is an investigation, not a dimmer.

`UX-222` built focus as visual state and that is still exactly what it
does to the document. What the reader wanted was "show me the evidence
about *this*" - and today that evidence is in four places: the element's
own section, its blast, its history, the finding that names it.

Three properties are asserted: the panel assembles four groups from
published objects, every value it shows resolves to the field it cites,
and **unfocusing leaves the document byte-identical to never-focused**,
compared by serialisation rather than by eye.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

from bga import provenance

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _report(run=GOLDEN):
    result = subprocess.run(
        [sys.executable, "-c",
         "from bga.cli import main; raise SystemExit(main(%r))"
         % (["analyze", run, "--format", "json", "--diagnostics"],)],
        capture_output=True, text=True, cwd=os.getcwd())
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _node(script):
    result = subprocess.run([node, "--input-type=module", "-e", script],
                            capture_output=True, text=True,
                            cwd=os.getcwd(), timeout=60)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.fixture(scope="module")
def payload():
    return _report()


@needs_node
class TestTheEvidenceIsAssembled:
    def _panel(self, payload, uid, store=None):
        return _node(_PANEL.replace("__PAYLOAD__", json.dumps(payload))
                            .replace("__UID__", json.dumps(uid))
                            .replace("__STORE__", json.dumps(store)))

    def test_the_four_groups_the_item_names(self, payload):
        out = self._panel(payload, payload["critical_path_detail"][0]["element_uid"])
        assert out["groups"] == ["why", "evidence", "relationships", "actions"]

    def test_every_value_resolves_to_the_field_it_cites(self, payload):
        wrong = []
        for row in self._panel(payload,
                               payload["critical_path_detail"][0]["element_uid"])["rows"]:
            if not row["field"]:
                continue
            found = provenance.resolve(payload, row["field"])
            if found is provenance.UNRESOLVED:
                wrong.append(f"{row['field']} does not resolve")
            elif str(found) != row["raw"]:
                wrong.append(f"{row['field']}: shows {row['raw']!r}, "
                             f"payload has {found!r}")
        assert wrong == [], wrong

    def test_the_chain_neighbours_are_the_published_order(self, payload):
        chain = [e["element_uid"] for e in payload["critical_path_detail"]]
        assert len(chain) >= 3, chain
        out = self._panel(payload, chain[1])
        relations = {row["label"]: row["text"] for row in out["rows"]
                     if row["group"] == "relationships"}
        assert relations["Waits on (chain)"] == chain[0]
        assert relations["Blocks (chain)"] == chain[2]

    def test_an_absent_plane_says_so_rather_than_going_quiet(self, payload):
        """"Plane 2 saw nothing" and "Plane 2 was not run" are
        different facts; a list of only what exists collapses them."""
        out = self._panel(payload, payload["critical_path_detail"][0]["element_uid"])
        evidence = {row["label"]: row["text"] for row in out["rows"]
                    if row["group"] == "evidence"}
        assert evidence["Plane 2 (sandbox)"] == "not in this document"

    def test_an_element_the_document_does_not_know_measures_nothing(
            self, payload):
        """The evidence group still renders - saying *where it looked
        and found nothing* is the point - but nothing measured appears
        under "why it matters"."""
        out = self._panel(payload, "ghost.bst")
        assert "why" not in out["groups"], (
            "an unknown element got measured evidence from somewhere")
        presence = [row["present"] for row in out["rows"]
                    if row["group"] == "evidence" and row["present"]]
        assert set(presence) == {"false"}, presence

    def test_every_presence_row_says_where_it_looked(self, payload):
        """A path that resolves means present, and one that does not
        means absent - checked against the payload rather than trusted,
        so a row cannot say "yes" about a document it is not in."""
        for row in self._panel(payload,
                               payload["critical_path_detail"][0]["element_uid"])["rows"]:
            if not row["source"]:
                continue
            found = provenance.resolve(payload, row["source"])
            assert (found is not provenance.UNRESOLVED) == \
                (row["present"] == "true"), row


@needs_node
class TestUnfocusRestoresTheDocument:
    def test_the_dom_is_identical_to_never_focused(self, payload):
        """The item's own acceptance, by serialisation compare rather
        than by eye: focus, unfocus, and the tree must be what it was."""
        out = _node(_ROUNDTRIP.replace("__PAYLOAD__", json.dumps(payload)))
        assert out["before"] == out["after"], (
            "focus left something behind in the document")
        assert out["during"] != out["before"], (
            "focusing changed nothing, so the compare proves nothing")

    def test_the_panel_is_keyed_by_the_role_that_removes_it(self, payload):
        """Everything focus adds carries `data-role`, and the refresh
        removes exactly that set - which is *why* the compare above can
        pass. A panel added without one would survive an unfocus."""
        out = _node(_ROUNDTRIP.replace("__PAYLOAD__", json.dumps(payload)))
        assert out["roles"] == ["focus-bar", "focus-investigation"], out["roles"]


class TestTheExportStaysAPlainDocument:
    def test_no_investigation_output_is_baked_into_the_export(self, tmp_path):
        """Focus is served-mode state, like the palette. The export is
        the document, and a panel frozen into it would be one reader's
        session pretending to be the report."""
        import tools.bga_view as view

        out = tmp_path / "r.html"
        view.export(GOLDEN, str(out))
        html = out.read_text(encoding="utf-8")
        assert 'data-role="focus-investigation"' not in html
        assert "renderInvestigation" in html, (
            "the renderer itself should still ship - the served page "
            "needs it, and the export is one file")


_PANEL = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;

function make(tag) {
  const node = _makeNode(tag);
  return node;
}
_installDocument();
const views = await import("./tests/viewer.mjs");
const panel = views.renderInvestigation(__PAYLOAD__, __UID__,
                                        { store: __STORE__ });
const groups = [], rows = [];
if (panel) {
  for (const group of panel.children) {
    const key = group.attrs["data-group"];
    if (!key) continue;
    groups.push(key);
    let label = null;
    (function walk(n) {
      if (!n) return;
      if (n.tagName === "dt") label = n.textContent;
      if (n.tagName === "dd") {
        rows.push({ group: key, label,
                    field: n.attrs["data-field"] ?? null,
                    raw: n.attrs["data-raw"] ?? null,
                    source: n.attrs["data-source"] ?? null,
                    present: n.attrs["data-present"] ?? null,
                    text: n.textContent
                          || (n.children[0]?.textContent ?? "") });
      }
      (n.children ?? []).forEach(walk);
    })(group);
  }
}
console.log(JSON.stringify({ groups, rows }));
"""

_ROUNDTRIP = """
function make(tag) {
  const node = {
    tagName: tag, nodeType: 1, attrs: {}, children: [], textContent: "",
    className: "", listeners: {},
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return this.attrs[k] ?? null; },
    removeAttribute(k) { delete this.attrs[k]; },
    addEventListener(name, fn) { (this.listeners[name] ??= []).push(fn); },
    append(...xs) { for (const x of xs) { if (x == null) continue;
      typeof x === "string" ? this.textContent += x
        : (x.parentNode = this, this.children.push(x)); } },
    prepend(...xs) { for (const x of xs) { if (x == null) continue;
      x.parentNode = this; this.children.unshift(x); } },
    removeChild(child) {
      this.children = this.children.filter((c) => c !== child); return child; },
    querySelectorAll(selector) {
      const roles = [...selector.matchAll(/data-role=([a-z-]+)/g)]
        .map((m) => m[1]);
      const found = [];
      (function walk(n) {
        if (!n) return;
        if (roles.includes(n.attrs["data-role"])) found.push(n);
        (n.children ?? []).forEach(walk);
      })(this);
      return found;
    },
    dispatchEvent() { return true; },
  };
  return node;
}
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;
// `make` above is this file's own node, not the shim's - UX-537 moved
// the *document* here and left that second instrument standing.
_installDocument({
  createElement: make, createElementNS: (_n, t) => make(t),
  createTextNode: (text) => ({ tagName: "#text", nodeType: 3, attrs: {},
                               children: [], textContent: text }),
});
globalThis.Event = class { constructor(name) { this.type = name; } };
const app = await import("./tests/viewer.mjs");
const focus = await import("./bga/viewer/focus.js");
const payload = __PAYLOAD__;
const root = make("main");
const child = make("section");
child.setAttribute("data-section", "x");
child.setAttribute("data-element", payload.critical_path_detail[0].element_uid);
root.append(child);
const serialise = (n) => JSON.stringify({
  tag: n.tagName, attrs: n.attrs,
  children: (n.children ?? []).map(serialise) });
const before = serialise(root);
const refresh = app.wireFocusAndMarks(root, null, { payload });
focus.applyFocus(root, payload.critical_path_detail[0].element_uid);
refresh();
const during = serialise(root);
const roles = root.children.filter((c) => c.attrs["data-role"])
                           .map((c) => c.attrs["data-role"]);
focus.clearFocus(root);
refresh();
const after = serialise(root);
console.log(JSON.stringify({ before, during, after, roles }));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
