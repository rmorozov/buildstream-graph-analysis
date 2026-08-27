"""UX-211 + UX-212: the view in the link, and the verdict without the palette.

Two items about handing an investigation to somebody else. `UX-211`:
`nav.js` sells the section ids as something that "can be pasted into an
issue", and the promise stopped at the anchor — the filter, the
threshold, the sort, the Top-10 and the collapse all lived in DOM state
and `localStorage`, so the pasted link opened the unfiltered wall.
`UX-212`: the trend encoded the verdict as fill colour alone, so a
grayscale print or a colour-blind reader lost the direction of the one
chart that answers "is this project drifting".
"""
import json
import os
import shutil
import subprocess

import pytest

from bga import schemas

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _node(script, timeout=120):
    result = subprocess.run([node, "--input-type=module", "-e", script],
                            capture_output=True, text=True, cwd=os.getcwd(),
                            timeout=timeout)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


class TestTheMarkerVocabularyIsDeclared:
    def test_every_verdict_kind_has_a_shape(self):
        """Covering the vocabulary is validated where the map is
        written, so a sixth verdict kind cannot enter `VERDICT_KINDS`
        and quietly draw as everything else."""
        assert set(schemas.VERDICT_MARKERS) == set(schemas.VERDICT_KINDS)

    def test_no_two_kinds_share_a_shape(self):
        shapes = list(schemas.VERDICT_MARKERS.values())
        assert len(set(shapes)) == len(shapes), shapes
        assert set(shapes) <= set(schemas.MARKER_SHAPES)

    def test_a_map_that_misses_a_kind_is_rejected(self):
        with pytest.raises(ValueError, match="no shape for"):
            schemas._check_hint("x/v1", "k", {
                schemas.MARKERS: {"improved": "circle"}})

    def test_a_map_that_repeats_a_shape_is_rejected(self):
        """The mutation the item is really about: a declaration that
        assigns two verdicts the same shape is a colour-only encoding
        again, wearing a declaration."""
        same = dict.fromkeys(schemas.VERDICT_KINDS, "circle")
        with pytest.raises(ValueError, match="same shape"):
            schemas._check_hint("x/v1", "k", {schemas.MARKERS: same})

    def test_a_shape_no_renderer_draws_is_rejected(self):
        bad = dict(schemas.VERDICT_MARKERS, improved="hexagram")
        with pytest.raises(ValueError, match="not one of"):
            schemas._check_hint("x/v1", "k", {schemas.MARKERS: bad})

    def test_the_store_schema_publishes_it(self):
        declared = schemas.schema(schemas.STORE)["properties"]["snapshots"][
            "items"]["properties"]["verdict_kind"]
        assert declared[schemas.MARKERS] == schemas.VERDICT_MARKERS


@needs_node
class TestTheTrendDrawsTheShapeTheSchemaAssigns:
    def test_different_verdicts_differ_without_colour(self):
        out = _node(_SHIM + _TREND % json.dumps(
            schemas.schema(schemas.STORE)))
        markers = {row["verdict"]: row["marker"] for row in out["points"]}
        assert markers["improved"] != markers["regressed"], markers
        for kind, marker in markers.items():
            assert marker == schemas.VERDICT_MARKERS[kind], (kind, marker)
        # Asserted from the element, not from computed style: a
        # stylesheet is exactly what `filter: grayscale` takes away.
        for row in out["points"]:
            assert row["tag"] in ("circle", "polygon"), row
            if row["marker"].startswith("triangle") or row["marker"] == "diamond":
                assert row["tag"] == "polygon", row

    def test_the_y_position_is_readable_whatever_the_shape(self):
        """`data-cy` on every marker. Without it a guard on the y axis
        has to know which verdict happened to draw a circle - which is
        how this change first reddened an unrelated test."""
        out = _node(_SHIM + _TREND % json.dumps(
            schemas.schema(schemas.STORE)))
        ys = [float(row["cy"]) for row in out["points"]]
        assert len(ys) == 3 and len(set(ys)) == 3, ys

    def test_without_the_declaration_nothing_errors_and_nothing_lies(self):
        """The acceptance's other half. A page handed no schema draws
        one shape for everything rather than inventing an encoding of
        its own."""
        out = _node(_SHIM + _TREND % "null")
        assert {row["marker"] for row in out["points"]} == {"circle"}

    def test_the_band_rectangles_differ_without_colour(self):
        out = _node(_SHIM + _BAND)
        assert out["observed"]["outline"] == "dashed"
        assert out["band"]["outline"] == "solid"
        assert out["observed"]["dash"], "the extent has no dash pattern"
        assert out["band"]["dash"] is None, "both rectangles dash the same"

    def test_the_viewer_names_no_verdict_of_its_own(self):
        """`UX-214`'s lesson, applied before it could happen again: the
        shapes are a schema declaration, so there is no second list of
        verdict kinds in JavaScript to drift from `VERDICT_KINDS`."""
        source = open("bga/viewer/views.js", encoding="utf-8").read()
        for kind in schemas.VERDICT_KINDS:
            assert kind not in source, (
                f"{kind} is named in the viewer; the vocabulary belongs "
                f"to the schema")


@needs_node
class TestTheFragmentCarriesTheView:
    def test_a_filter_and_a_collapse_both_reach_the_hash(self):
        out = _node(_SHIM + _VIEWSTATE)
        assert "f.elements=openssl" in out["captured"], out["captured"]
        assert "c=floors" in out["captured"], out["captured"]

    def test_applying_it_restores_the_same_shown_rows(self):
        """Round-trip on the real controls: capture, rebuild the page
        from scratch, apply, and compare the badge - not the internal
        state object, which would only prove the object survived."""
        out = _node(_SHIM + _VIEWSTATE)
        assert out["before_badge"] == out["after_badge"], out
        assert out["before_visible"] == out["after_visible"] > 0, out

    def test_a_hash_free_load_changes_nothing(self):
        """The acceptance names this one: today's behaviour must be
        exactly today's behaviour when the fragment is silent."""
        out = _node(_SHIM + _VIEWSTATE)
        assert out["untouched"] == [], out["untouched"]

    def test_a_silent_hash_leaves_what_the_reader_remembered(self):
        """"The hash wins where it speaks; `localStorage` remains the
        default where it is silent" - which only means something if a
        silent hash cannot *expand* what storage collapsed. Measured on
        a page whose section is already shut."""
        out = _node(_SHIM + _VIEWSTATE)
        assert out["remembered_after_silence"] == "true", out
        assert out["remembered_after_speaking"] == "false", (
            "a hash that names its collapse set must win")

    def test_a_key_naming_something_this_run_does_not_have_is_dropped(self):
        out = _node(_SHIM + _VIEWSTATE)
        assert out["foreign"] == [], out["foreign"]

    def test_the_anchor_survives_the_state(self):
        out = _node(
            'const v = await import("./bga/viewer/viewstate.js");'
            'console.log(JSON.stringify({'
            '  plain: v.splitHash("#floors"),'
            '  both: v.splitHash("#floors~c=a&f.b=x"),'
            '  joined: v.joinHash("floors", "c=a"),'
            '  nostate: v.joinHash("floors", "") }));')
        assert out["plain"] == {"anchor": "floors", "query": ""}
        assert out["both"] == {"anchor": "floors", "query": "c=a&f.b=x"}
        assert out["joined"] == "#floors~c=a"
        assert out["nostate"] == "#floors", (
            "a stateless link must stay the link that was already pasted "
            "into an issue")

    def test_the_link_is_this_document_at_this_view(self):
        out = _node(_SHIM + _LINK)
        assert out["link"].startswith("file:///tmp/r.html#"), out["link"]
        assert "f.elements=openssl" in out["link"], out["link"]

    def test_the_module_reaches_the_export(self):
        import tools.bga_view as view

        assert "viewstate.js" in view.ASSETS
        assert "viewstate.js" in view._module_order()


_SHIM = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;

function make(tag) {
  const node = _makeNode(tag);
  node.open = false;
  return node;
}
globalThis.Event = class { constructor(type) { this.type = type; } };
globalThis.document = { createElement: make, createElementNS: (_n, t) => make(t),
                        getElementById: () => null };
const all = (n, p, f = []) => { if (!n) return f; if (p(n)) f.push(n);
  (n.children ?? []).forEach((c) => all(c, p, f)); return f; };
"""

_TREND = """
const views = await import("./tests/viewer.mjs");
const schema = %s;
const rows = [
  { stamp: "a", total_duration_us: 300, verdict_kind: "improved" },
  { stamp: "b", total_duration_us: 200, verdict_kind: "regressed" },
  { stamp: "c", total_duration_us: 100, verdict_kind: "not_comparable" },
];
const node = views.renderTrend({ snapshots: rows }, schema);
const points = all(node, (n) => n.attrs["data-marker"]).map((n) => ({
  tag: n.tagName, marker: n.attrs["data-marker"], cy: n.attrs["data-cy"],
  verdict: n.attrs["data-verdict"],
}));
console.log(JSON.stringify({ points }));
"""

_BAND = """
const views = await import("./tests/viewer.mjs");
const node = views.renderBand({
  baseline_band: { low_us: 99, high_us: 101, median_us: 100,
                   observed_low_us: 90, observed_high_us: 200 },
  candidate: { total_duration_us: 150 },
});
const rect = (role) => all(node, (n) => n.attrs["data-role"] === role)[0];
const read = (n) => ({ outline: n.attrs["data-outline"] ?? null,
                       dash: n.attrs["stroke-dasharray"] ?? null });
console.log(JSON.stringify({
  observed: read(rect("observed")), band: read(rect("band")) }));
"""

# One table, driven the way a reader drives it, then rebuilt from
# scratch and restored from the fragment alone.
_VIEWSTATE = """
const app = await import("./tests/viewer.mjs");
const vs = await import("./bga/viewer/viewstate.js");
const rows = [
  { element_uid: "openssl.bst", duration_us: 900000 },
  { element_uid: "openssl-docs.bst", duration_us: 400000 },
  { element_uid: "zlib.bst", duration_us: 100000 },
];
const hint = { "bga:columns": [
  { key: "element_uid", title: "Element", role: "element" },
  { key: "duration_us", title: "Duration", quantity: "duration_us" } ] };

function page() {
  const root = make("div");
  root.append(app.renderTable("elements", rows, hint));
  const floors = make("section");
  floors.setAttribute("data-section", "floors");
  floors.setAttribute("data-collapsed", "false");
  const button = make("button");
  button.setAttribute("data-collapse", "floors");
  button.addEventListener("click", () => {
    const shut = floors.getAttribute("data-collapsed") === "true";
    floors.setAttribute("data-collapsed", String(!shut));
  });
  floors.append(button);
  root.append(floors);
  return root;
}
const badge = (root) =>
  all(root, (n) => n.className === "badge")[0].textContent;
const visible = (root) => root.querySelectorAll("tbody tr")
  .filter((tr) => !tr.hidden).length;

const first = page();
const box = first.querySelectorAll("input")[0];
box.value = "openssl";
box.dispatchEvent(new Event("input"));
first.querySelector("button[data-collapse]").dispatchEvent(new Event("click"));
const captured = vs.captureView(first);

const second = page();
const untouched = vs.applyView(second, "");
const before = { badge: badge(first), visible: visible(first) };
vs.applyView(second, captured);
const foreign = vs.applyView(page(), "f.no_such_table=x&t.nope.col=>1s");

// A page the reader had already collapsed, met by a fragment that says
// nothing about collapse, and then by one that does.
const remembered = page();
remembered.querySelector("button[data-collapse]").dispatchEvent(new Event("click"));
vs.applyView(remembered, "f.elements=zlib");
const afterSilence = remembered.querySelector("[data-section=floors]")
  .getAttribute("data-collapsed");
vs.applyView(remembered, "c=");
const afterSpeaking = remembered.querySelector("[data-section=floors]")
  .getAttribute("data-collapsed");

console.log(JSON.stringify({
  captured, untouched, foreign,
  remembered_after_silence: afterSilence,
  remembered_after_speaking: afterSpeaking,
  before_badge: before.badge, after_badge: badge(second),
  before_visible: before.visible, after_visible: visible(second),
}));
"""

_LINK = """
const app = await import("./tests/viewer.mjs");
const vs = await import("./bga/viewer/viewstate.js");
const rows = [{ element_uid: "openssl.bst", duration_us: 900000 },
              { element_uid: "zlib.bst", duration_us: 100000 }];
const hint = { "bga:columns": [
  { key: "element_uid", title: "Element" },
  { key: "duration_us", title: "Duration", quantity: "duration_us" } ] };
const root = make("div");
root.append(app.renderTable("elements", rows, hint));
const box = root.querySelectorAll("input")[0];
box.value = "openssl";
box.dispatchEvent(new Event("input"));
console.log(JSON.stringify({
  link: vs.viewLink(root, { href: "file:///tmp/r.html", hash: "" }) }));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
