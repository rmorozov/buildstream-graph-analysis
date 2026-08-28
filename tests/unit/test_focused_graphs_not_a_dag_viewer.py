"""UX-206: focused graphs, not a DAG viewer.

The external review and Direction 7 arrived at the same restraint
independently: a general BuildStream DAG rendering answers no question
anyone asks. What is drawn here is the two pictures that *are*
questions - the critical path as a list with widths, and the blast
answer as an indented list - and neither needs a layout algorithm.

Both are under `UX-196`'s discipline: published JSON only, no viewer
arithmetic, geometry asserted from data attributes. The widths are
`share_of_path`, a field the report already publishes; the indentation
is `depth`, a field that had to *enter* `blast/v2` first, because the
filing's premise that the payload already carried it was wrong.
"""
import io
import json
import os
import re
import shutil
import subprocess
import tempfile

import pytest

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"
REAL = "examples/06-macro-micro-optimization/.bga/runs/20260821T170127Z/run"

# `UX-213`: every guard an acceptance names runs on a run that is **in
# the repository**. The real capture stays as extra coverage where it
# exists, but it is never the only place a mutation would be caught -
# round 23 proved that uniform widths and a flattened depth kept the
# whole file green on a fresh clone, because the two guards that would
# have caught them were pinned to a timestamped snapshot no CI creates.
#
# The golden fixture carries what both drawings need: a three-element
# critical path with distinct shares (0.43 / 0.36 / 0.21) and, from
# `base.bst`, a three-level blast tree (depths 0, 1, 2).
_needs_real = pytest.mark.skipif(not os.path.isdir(REAL),
                                 reason="no real capture here")
# `(run, blast target)` - the target differs because the fixtures do.
RUNS = [
    pytest.param(GOLDEN, "base.bst", id="committed"),
    pytest.param(REAL, "toolchain.bst", id="real-capture", marks=_needs_real),
]


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


def _decl(style, name):
    """The value of one declaration in a browser-serialised `style`.

    A real DOM writes `flex-grow: 428.571;` — with the semicolon, and
    with any other declarations beside it. The `.replace("flex-grow: ",
    "")` this replaced read the shim's semicolon-less form and would
    have broken on the real one, which is `UX-263`'s lesson in the
    guard rather than in the page.
    """
    for part in style.split(";"):
        key, _, value = part.partition(":")
        if key.strip() == name:
            return value.strip()
    raise AssertionError(f"no `{name}` declaration in {style!r}")


class TestTheDepthThatHadToBePublished:
    """The filing said the tree was "a `<details>` tree over data
    `blast/v2` already carries". It was not: the payload had
    `direct_elements` and `blast_elements`, two flat lists, and no
    per-element depth, kind or cost. Deriving depth in the viewer means
    walking the graph in JavaScript, which is the second analysis the
    no-arithmetic rule exists to prevent."""

    @pytest.mark.parametrize("run,target", RUNS)
    def test_blast_publishes_each_element_at_a_depth(self, run, target):
        answer = _blast(run, target)
        tree = answer["blast_tree"]
        assert tree, "blast/v2 carries no tree"
        assert {row["element_uid"] for row in tree} == set(answer["blast_elements"])
        assert all(row["depth"] >= 0 for row in tree)

    @pytest.mark.parametrize("run,target", RUNS)
    def test_the_direct_consumers_are_depth_zero(self, run, target):
        answer = _blast(run, target)
        zero = {row["element_uid"] for row in answer["blast_tree"]
                if row["depth"] == 0}
        assert zero == set(answer["direct_elements"])

    @pytest.mark.parametrize("run,target", RUNS)
    def test_depth_is_hops_not_position_in_the_list(self, run, target):
        """The bug the first attempt had: `compute_reachability` returns
        the *transitive* closure, so a breadth-first walk over it put
        every element at depth 1 and the tree was flat. It walks the
        immediate successors now.

        `UX-213`: this is one of the two guards the `UX-206` acceptance
        names, and it used to run only where the real capture lived - so
        hardcoding `depth` kept a fresh clone entirely green. The golden
        fixture is a three-element chain, so `base.bst` reaches
        `app.bst` at depth 2 through `lib.bst`, and flattening the walk
        reddens *here*, in the repository.
        """
        answer = _blast(run, target)
        depths = {row["element_uid"]: row["depth"] for row in answer["blast_tree"]}
        assert max(depths.values()) >= 2, (
            f"nothing is more than one hop away, so a flattened walk "
            f"would look identical: {depths}")
        # Someone is strictly further away than someone else - the
        # property a hardcoded depth destroys.
        assert len(set(depths.values())) >= 3, depths

    @pytest.mark.parametrize("run,target", RUNS)
    def test_each_row_carries_its_kind_and_its_measured_work(self, run, target):
        answer = _blast(run, target)
        for row in answer["blast_tree"]:
            assert row["element_kind"], row
        costed = [r for r in answer["blast_tree"]
                  # `UX-341`: an integer count of microseconds, not a float
                  # of seconds under a new name.
                  if isinstance(r["measured_us"], int)]
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
    @pytest.mark.parametrize("run,target", RUNS)
    def test_the_widths_are_the_published_share(self, run, target):
        """The acceptance's mutation: uniform widths reddens.

        `UX-213`: and it now reddens on the committed fixture too. This
        guard was pinned to the real capture, so `flex-grow: 1` passed
        everywhere the capture was absent - which is everywhere but one
        container. The golden chain's three shares are distinct
        (0.43 / 0.36 / 0.21), which is all the property needs.
        """
        payload = _analyze(run)
        out = _render("renderCriticalPath", payload)
        detail = payload["critical_path_detail"]
        assert len(out["boxes"]) == len(detail)
        by_uid = {e["element_uid"]: e for e in detail}
        widths = set()
        for box in out["boxes"]:
            published = by_uid[box["element"]]["share_of_path"]
            assert float(box["share"]) == published, box
            # The style carries the same number, so the *drawing* is the
            # published share rather than a coincidence in an attribute.
            grow = float(_decl(box["style"], "flex-grow"))
            assert grow == pytest.approx(published * 1000), box
            widths.add(box["style"])
        assert len(widths) > 1, "every box is the same width - nothing is drawn"

    def test_a_run_with_no_chain_draws_nothing(self):
        out = _render("renderCriticalPath", {})
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
                      {"critical_path_detail": detail})
        assert out["folded"] == 1202 - 6 - 3, out["folded"]
        assert out["hidden_before"] == out["folded"]
        # Clicked: the middle appears between the two ends rather than
        # sending the reader elsewhere.
        assert out["hidden_after"] == 0
        assert out["boxes_after"] == 1202

    def test_a_short_chain_is_not_folded(self):
        out = _render("renderCriticalPath", {"critical_path_detail": [
            {"element_uid": "a.bst", "duration_us": 10, "share_of_path": 0.5},
            {"element_uid": "b.bst", "duration_us": 10, "share_of_path": 0.5},
        ]})
        assert out["folded"] is None
        assert out["hidden_before"] == 0

    @pytest.mark.parametrize("run,target", RUNS)
    def test_each_box_links_to_the_element_it_names(self, run, target):
        """`UX-206` pointed every box at `#signals` - the section that
        explains the drawing. `UX-216` points each one at the *element*
        instead, deliberately: a reader who clicks a box asked about
        that element, not about the table it came from, and the element
        now has a section of its own to arrive at.

        Asserted per box against the uid it draws, so a box linking to
        some other element's section is a failure rather than a
        rounding of the old promise."""
        out = _render("renderCriticalPath", _analyze(run))
        assert out["boxes"], "the chain drew nothing"
        for box in out["boxes"]:
            expected = "element-" + re.sub(r"[^\w-]+", "-", box["element"])
            assert box["href"] == f"#{expected}", box


@needs_node
class TestTheBlastTreeDrawn:
    @pytest.mark.parametrize("run,target", RUNS)
    def test_the_indentation_is_the_published_depth(self, run, target):
        """The nesting is asserted against the JSON, not against the
        order rows happen to appear in."""
        answer = _blast(run, target)
        out = _render("renderBlastTree", answer)
        published = {row["element_uid"]: row["depth"] for row in answer["blast_tree"]}
        assert out["rows"], "the tree rendered nothing"
        for row in out["rows"]:
            assert int(row["depth"]) == published[row["element"]], row
            # Indentation follows depth, so a nested row is visibly
            # nested rather than merely labelled.
            indent = float(_decl(row["indent"], "padding-left")
                           .replace("rem", ""))
            assert indent == pytest.approx(published[row["element"]] * 1.4), row

    @pytest.mark.parametrize("run,target", RUNS)
    def test_the_kind_badges_come_from_the_declared_item_shape(self, run, target):
        answer = _blast(run, target)
        out = _render("renderBlastTree", answer)
        kinds = {row["element_uid"]: row["element_kind"]
                 for row in answer["blast_tree"]}
        for row in out["rows"]:
            assert row["kind"] == kinds[row["element"]], row

    def test_an_answer_with_no_tree_draws_nothing(self):
        out = _render("renderBlastTree", {"target": "x", "blast_count": 0})
        assert out["rendered"] is False


class TestTheGuardsGuardEverywhere:
    """`UX-213`. The defect this file carried was not a wrong assertion -
    every assertion here was right. It was that the only place two of
    them ran was a machine with an untracked capture on it, so the
    mutations the `UX-206` acceptance names passed on a fresh clone.

    A skip on a genuinely optional input is fine. An *acceptance* that
    lives entirely behind one is not, and nothing said so out loud."""

    def test_the_fixture_matrix_names_a_run_that_is_in_the_repository(self):
        import subprocess

        unmarked = [param for param in RUNS if not param.marks]
        assert unmarked, (
            "every run in the matrix is conditional, so every guard using "
            "it can vanish at once")
        for param in unmarked:
            run = param.values[0]
            tracked = subprocess.run(
                ["git", "ls-files", "--error-unmatch", run],
                capture_output=True, text=True)
            assert tracked.returncode == 0, (
                f"{run} is not tracked by git, so a fresh clone would skip "
                f"the guards pinned to it - which is exactly UX-213")

    def test_the_real_capture_is_extra_coverage_not_the_only_coverage(self):
        """The property, stated where the next person will read it: if
        the real-capture entry were dropped entirely, every mutation
        guard in this file would still have somewhere to run."""
        conditional = [param for param in RUNS if param.marks]
        assert len(conditional) < len(RUNS)


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
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;

function make(tag) {
  const node = _makeNode(tag);
  return node;
}
globalThis.document = { createElement: make, createElementNS: (_n, t) => make(t),
                        getElementById: () => null };

const views = await import("./tests/viewer.mjs");
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
