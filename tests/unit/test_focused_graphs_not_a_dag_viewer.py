"""UX-206: focused graphs, not a DAG viewer.

The external review and Direction 7 arrived at the same restraint
independently: a general BuildStream DAG rendering answers no question
anyone asks. What is drawn here is the two pictures that *are*
questions - the critical path as a list with widths, and the blast
answer as an indented list - and neither needs a layout algorithm.

Both are under `UX-196`'s discipline: published JSON only, no viewer
arithmetic, geometry asserted from data attributes. The widths are
`share_of_path`, a field the report already publishes; the indentation
is `depth`, a field that had to *enter* `blast/v1` first, because the
filing's premise that the payload already carried it was wrong.
"""
import io
import json
import os
import shutil
import subprocess
import tempfile

import pytest

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"
REAL = "examples/06-macro-micro-optimization/.bga/runs/20260821T170127Z/run"


def _node(script, timeout=120):
    result = subprocess.run([node, "--input-type=module", "-e", script],
                            capture_output=True, text=True, cwd=os.getcwd(),
                            timeout=timeout)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _analyze(run):
    import contextlib

    from bga.cli import main

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        main(["analyze", run, "--format", "json"])
    return json.loads(buffer.getvalue())


def _blast(run, target):
    from bga.blast import blast

    return blast(run, target)


def _render(fn, payload, timeout=120):
    """The payload goes through a file, not through argv.

    A 1,202-element chain inlined into `node -e` is `OSError: [Errno 7]
    Argument list too long` - which is a fact about the harness, not
    about the renderer, and would have quietly limited every scale test
    written after it to whatever fits in one command line.
    """
    scratch = tempfile.mkdtemp()
    path = os.path.join(scratch, "payload.json")
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    try:
        return _node(_HARNESS % (json.dumps(path), fn), timeout=timeout)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


class TestTheDepthThatHadToBePublished:
    """The filing said the tree was "a `<details>` tree over data
    `blast/v1` already carries". It was not: the payload had
    `direct_elements` and `blast_elements`, two flat lists, and no
    per-element depth, kind or cost. Deriving depth in the viewer means
    walking the graph in JavaScript, which is the second analysis the
    no-arithmetic rule exists to prevent."""

    @pytest.mark.skipif(not os.path.isdir(REAL), reason="no real capture here")
    def test_blast_publishes_each_element_at_a_depth(self):
        answer = _blast(REAL, "toolchain.bst")
        tree = answer["blast_tree"]
        assert tree, "blast/v1 carries no tree"
        assert {row["element_uid"] for row in tree} == set(answer["blast_elements"])
        assert all(row["depth"] >= 0 for row in tree)

    @pytest.mark.skipif(not os.path.isdir(REAL), reason="no real capture here")
    def test_the_direct_consumers_are_depth_zero(self):
        answer = _blast(REAL, "toolchain.bst")
        zero = {row["element_uid"] for row in answer["blast_tree"]
                if row["depth"] == 0}
        assert zero == set(answer["direct_elements"])

    @pytest.mark.skipif(not os.path.isdir(REAL), reason="no real capture here")
    def test_depth_is_hops_not_position_in_the_list(self):
        """The bug the first attempt had: `compute_reachability` returns
        the *transitive* closure, so a breadth-first walk over it put
        every element at depth 1 and the tree was flat. It walks the
        immediate successors now - `all.bst`, which consumes `app.bst`,
        is two hops from `toolchain.bst` and says so."""
        answer = _blast(REAL, "toolchain.bst")
        depths = {row["element_uid"]: row["depth"] for row in answer["blast_tree"]}
        assert depths["all.bst"] > depths["app.bst"], depths
        assert max(depths.values()) >= 2, depths

    @pytest.mark.skipif(not os.path.isdir(REAL), reason="no real capture here")
    def test_each_row_carries_its_kind_and_its_measured_work(self):
        answer = _blast(REAL, "toolchain.bst")
        for row in answer["blast_tree"]:
            assert row["element_kind"], row
        costed = [r for r in answer["blast_tree"]
                  if isinstance(r["measured_seconds"], float)]
        assert costed, "nothing carried a measured cost"

    def test_the_schema_declares_it(self):
        from bga import schemas

        declared = schemas.schema(schemas.BLAST)["properties"]
        assert "blast_tree" in declared
        columns = declared["blast_tree"]["bga:columns"]
        assert any(c["key"] == "depth" and c["quantity"] == "count"
                   for c in columns), columns


@needs_node
class TestTheChainDrawn:
    @pytest.mark.skipif(not os.path.isdir(REAL), reason="no real capture here")
    def test_the_widths_are_the_published_share(self):
        """The acceptance's mutation: uniform widths reddens."""
        payload = _analyze(REAL)
        out = _render("renderCriticalPath", payload)
        detail = payload["signals"]["critical_path_detail"]
        assert len(out["boxes"]) == len(detail)
        by_uid = {e["element_uid"]: e for e in detail}
        widths = set()
        for box in out["boxes"]:
            published = by_uid[box["element"]]["share_of_path"]
            assert float(box["share"]) == published, box
            # The style carries the same number, so the *drawing* is the
            # published share rather than a coincidence in an attribute.
            grow = float(box["style"].replace("flex-grow: ", ""))
            assert grow == pytest.approx(published * 1000), box
            widths.add(box["style"])
        assert len(widths) > 1, "every box is the same width - nothing is drawn"

    def test_a_run_with_no_chain_draws_nothing(self):
        out = _render("renderCriticalPath", {"signals": {}})
        assert out["rendered"] is False

    def test_a_long_chain_folds_and_the_fold_opens_in_place(self):
        """At 1,202 elements - the scale probe's size - the chain is not
        a drawing, and the middle is where a reader stops looking. This
        view's input *is* `critical_path_detail`, so the published field
        at that length is the 1,202-element case for it."""
        detail = [{"element_uid": f"element-{i}.bst",
                   "element_kind": "cmake",
                   "duration_us": (i % 40 + 1) * 100000,
                   "share_of_path": (i % 40 + 1) / 24040}
                  for i in range(1202)]
        out = _render("renderCriticalPath",
                      {"signals": {"critical_path_detail": detail}})
        assert out["folded"] == 1202 - 6 - 3, out["folded"]
        assert out["hidden_before"] == out["folded"]
        # Clicked: the middle appears between the two ends rather than
        # sending the reader elsewhere.
        assert out["hidden_after"] == 0
        assert out["boxes_after"] == 1202

    def test_a_short_chain_is_not_folded(self):
        out = _render("renderCriticalPath", {"signals": {"critical_path_detail": [
            {"element_uid": "a.bst", "duration_us": 10, "share_of_path": 0.5},
            {"element_uid": "b.bst", "duration_us": 10, "share_of_path": 0.5},
        ]}})
        assert out["folded"] is None
        assert out["hidden_before"] == 0

    @pytest.mark.skipif(not os.path.isdir(REAL), reason="no real capture here")
    def test_each_box_links_to_the_section_that_explains_it(self):
        out = _render("renderCriticalPath", _analyze(REAL))
        assert all(box["href"] == "#signals" for box in out["boxes"]), out["boxes"]


@needs_node
class TestTheBlastTreeDrawn:
    @pytest.mark.skipif(not os.path.isdir(REAL), reason="no real capture here")
    def test_the_indentation_is_the_published_depth(self):
        """The nesting is asserted against the JSON, not against the
        order rows happen to appear in."""
        answer = _blast(REAL, "toolchain.bst")
        out = _render("renderBlastTree", answer)
        published = {row["element_uid"]: row["depth"] for row in answer["blast_tree"]}
        assert out["rows"], "the tree rendered nothing"
        for row in out["rows"]:
            assert int(row["depth"]) == published[row["element"]], row
            # Indentation follows depth, so a nested row is visibly
            # nested rather than merely labelled.
            indent = float(row["indent"].replace("padding-left: ", "")
                                        .replace("rem", ""))
            assert indent == pytest.approx(published[row["element"]] * 1.4), row

    @pytest.mark.skipif(not os.path.isdir(REAL), reason="no real capture here")
    def test_the_kind_badges_come_from_the_declared_item_shape(self):
        answer = _blast(REAL, "toolchain.bst")
        out = _render("renderBlastTree", answer)
        kinds = {row["element_uid"]: row["element_kind"]
                 for row in answer["blast_tree"]}
        for row in out["rows"]:
            assert row["kind"] == kinds[row["element"]], row

    def test_an_answer_with_no_tree_draws_nothing(self):
        out = _render("renderBlastTree", {"target": "x", "blast_count": 0})
        assert out["rendered"] is False


class TestTheRestraintHolds:
    def test_no_new_module_and_no_layout_library(self):
        """"No new files beyond the views module growing" - the
        acceptance's own constraint, and the deferral of the general DAG
        that goes with it."""
        assert not os.path.exists("bga/viewer/graph.js")
        source = open("bga/viewer/views.js", encoding="utf-8").read()
        assert "import(" not in source, "views.js reaches for something at runtime"
        for banned in ("d3", "cytoscape", "dagre", "elk", "vis-network"):
            assert banned not in source, f"a layout library appeared: {banned}"


_HARNESS = """
function make(tag) {
  return {
    tagName: tag, nodeType: 1, attrs: {}, children: [], textContent: "",
    className: "", hidden: false, listeners: {},
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return this.attrs[k] ?? null; },
    removeAttribute(k) { delete this.attrs[k]; },
    addEventListener(name, fn) { (this.listeners[name] ??= []).push(fn); },
    append(...xs) { for (const x of xs) { if (x == null) continue;
      typeof x === "string" ? this.textContent += x : this.children.push(x); } },
  };
}
globalThis.document = { createElement: make, createElementNS: (_n, t) => make(t),
                        getElementById: () => null };

const views = await import("./bga/viewer/views.js");
const { readFileSync } = await import("node:fs");
const payload = JSON.parse(readFileSync(%s, "utf8"));
const node = views["%s"](payload);

function collect(root, className, fn) {
  const found = [];
  (function walk(n) {
    if (!n) return;
    if (n.className === className) found.push(fn(n));
    (n.children ?? []).forEach(walk);
  })(root);
  return found;
}
function find(root, className) {
  let hit = null;
  (function walk(n) {
    if (!n || hit) return;
    if (n.className === className) { hit = n; return; }
    (n.children ?? []).forEach(walk);
  })(root);
  return hit;
}

const box = (n) => ({ element: n.attrs["data-element"],
                      share: n.attrs["data-share"],
                      style: n.attrs["style"] ?? "",
                      href: n.attrs["href"] ?? null,
                      hidden: n.hidden });
const hiddenCount = () => collect(node, "path-box", box)
  .filter((b) => b.hidden).length;

const before = hiddenCount();
const more = find(node, "path-more");
if (more) (more.listeners.click ?? []).forEach((f) => f());
const after = hiddenCount();

console.log(JSON.stringify({
  rendered: Boolean(node),
  boxes: node ? collect(node, "path-box", box) : [],
  boxes_after: node ? collect(node, "path-box", box).length : 0,
  folded: more ? Number(more.attrs["data-folded"]) : null,
  hidden_before: before,
  hidden_after: after,
  rows: node ? collect(node, "blast-row", (n) => ({
    element: n.attrs["data-element"],
    depth: n.attrs["data-depth"],
    indent: n.attrs["style"] ?? "",
    kind: (n.children.find((c) => c.className === "kind") ?? {}).textContent
          ?? null,
  })) : [],
}));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
