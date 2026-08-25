"""UX-278: no Inspect anchor resolves to nothing.

Reported: *"when i click magnifier icon near some element - it opens
only if it is present on critical, otherwise it opens nothing."* The
mechanism is not the critical path, it is a **cap**: `UX-216` gives
every element-valued cell an anchor at `#element-<uid>`, and the detail
sections are bounded at `ELEMENTS_SHOWN` so a 4,000-element report stays
readable (`UX-187`). Nothing reconciled the two.

**This guard has to run at scale.** The committed 11-element fixture has
every element in the detail section, so it cannot see the defect at all
- measured, both before and after:

```text
run                 elements  eager blocks  anchors  dead before  dead after
macro_micro (11)          11            11       52            0           0
synthetic  (1,202)     1,202            24       53            7           0
```

Seven dead anchors, not the two `UX-278` was filed with: `UX-283` gave
the structural block its Inspect route in the same round, so more of the
page now points at elements the ranking never reached. All seven are
built on demand and none is unresolvable.

The 1,202-element run is generated rather than committed (`UX-189`), so
this file **builds it** from the committed generator, which is
byte-reproducible from its seed - the run is not a tracked path, but the
thing that makes it is.
"""
import json
import os
import pathlib
import shutil
import subprocess

import pytest

from bga import schemas

REPO = pathlib.Path(__file__).resolve().parents[2]
SMALL = REPO / "tests/fixtures/macro_micro/run"
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _analyze(run):
    done = subprocess.run(
        ["python", "-m", "bga.cli", "analyze", str(run), "--format", "json"],
        capture_output=True, text=True, cwd=REPO, timeout=300)
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


@pytest.fixture(scope="module")
def small():
    return _analyze(SMALL)


@pytest.fixture(scope="module")
def scale(tmp_path_factory):
    """The 1,202-element run, generated from the committed tool."""
    out = tmp_path_factory.mktemp("scale") / "run"
    done = subprocess.run(
        ["python", "-m", "tools.gen_synthetic_scale_run", str(out)],
        capture_output=True, text=True, cwd=REPO, timeout=600)
    assert done.returncode == 0, done.stderr[-2000:]
    return _analyze(out)


_HARNESS = r"""
const shim = await import(process.env.BGA_DOM_SHIM);
globalThis._makeNode ??= shim.makeNode;
globalThis.Event ??= class { constructor(t, o = {}) { this.type = t; Object.assign(this, o); } };
shim.installDocument();
globalThis.window = { location: { hash: "", search: "" }, addEventListener() {},
                      matchMedia: () => ({ matches: false, addEventListener() {} }) };
const app = await import("%(app)s");
const views = await import("%(views)s");
const { readFileSync } = await import("node:fs");
const payload = JSON.parse(readFileSync(%(payload)s, "utf8"));
const root = shim.makeNode("div");
app.render(payload, JSON.parse(readFileSync(%(schema)s, "utf8")), root);
for (const node of views.renderElementSections(payload, root, {})) root.append(node);

const ids = () => new Set(root.querySelectorAll("[data-section]")
  .map((s) => s.getAttribute("data-section")));
const anchors = root.querySelectorAll("a.inspect")
  .map((a) => a.getAttribute("href")).filter((h) => h && h.startsWith("#"));

const before = ids();
const dead = [...new Set(anchors.filter((h) => !before.has(h.slice(1))))];
let built = 0;
const unresolvable = [];
for (const href of dead) {
  const id = href.slice(1);
  const uid = views.uidForAnchor(payload, id);
  if (!uid) { unresolvable.push(id); continue; }
  if (views.ensureElementSection(payload, root, uid, {})) built += 1;
}

// And an element the page names nowhere near the top: the last key of
// the run's own element table, which no ranking reaches.
const every = Object.keys(payload.signals?.element_durations ?? {});
const deep = every[every.length - 1];
const deepSection = deep
  ? views.ensureElementSection(payload, root, deep, {}) : null;
const deepRows = deepSection
  ? deepSection.querySelectorAll("dd").length : 0;

// Following the same anchor twice must not make two blocks.
const twice = deep ? views.ensureElementSection(payload, root, deep, {}) : null;
const duplicates = root.querySelectorAll(
  `[data-section="${deep ? views.elementAnchor(deep) : "none"}"]`).length;

const after = ids();
console.log(JSON.stringify({
  elements: every.length,
  eager_blocks: [...before].filter((k) => k.startsWith("element-")).length,
  anchors: anchors.length,
  dead_before: dead.length,
  built_on_demand: built,
  dead_after: anchors.filter((h) => !after.has(h.slice(1))).length,
  unresolvable,
  deep_element: deep,
  deep_rows: deepRows,
  deep_is_idempotent: twice === deepSection && duplicates === 1,
  empty_note: deepSection
    ? deepSection.querySelectorAll("[data-empty-element]").length : -1,
}));
"""


def _follow(payload):
    import tempfile
    scratch = tempfile.mkdtemp()
    try:
        run = pathlib.Path(scratch, "payload.json")
        run.write_text(json.dumps(payload), encoding="utf-8")
        doc = pathlib.Path(scratch, "schema.json")
        doc.write_text(json.dumps(schemas.schema(schemas.ANALYZE)),
                       encoding="utf-8")
        script = _HARNESS % {
            "app": (REPO / "bga/viewer/app.js").as_uri(),
            "views": (REPO / "bga/viewer/views.js").as_uri(),
            "payload": json.dumps(str(run)), "schema": json.dumps(str(doc))}
        done = subprocess.run([node, "--input-type=module", "-e", script],
                              capture_output=True, text=True, cwd=REPO,
                              timeout=300,
                              env={**os.environ, "BGA_DOM_SHIM":
                                   (REPO / "tests/dom_shim.mjs").as_uri()})
        assert done.returncode == 0, done.stderr[-3000:]
        return json.loads(done.stdout)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


@needs_node
class TestAtScale:
    def test_the_run_is_big_enough_to_show_the_defect(self, scale):
        """`UX-278`'s own warning: the small fixture has every element in
        the detail section, so a guard that only ran there would pass on
        a page where every anchor was dead."""
        drawn = _follow(scale)
        assert drawn["elements"] > 1_000, drawn["elements"]
        assert drawn["eager_blocks"] < drawn["elements"] / 10, (
            f"{drawn['eager_blocks']} blocks for {drawn['elements']} elements "
            f"- the cap is not capping, so this run cannot see the defect")

    def test_the_page_ships_with_dead_anchors_before_they_are_followed(
            self, scale):
        """The defect, still present as a *state*: the cap is right and
        stays. What changed is that following one resolves."""
        assert _follow(scale)["dead_before"] > 0

    def test_following_every_dead_anchor_resolves_it(self, scale):
        drawn = _follow(scale)
        assert drawn["unresolvable"] == [], drawn["unresolvable"]
        assert drawn["built_on_demand"] == drawn["dead_before"]
        assert drawn["dead_after"] == 0, (
            f"{drawn['dead_after']} anchors still resolve to nothing")

    def test_an_element_no_ranking_reaches_can_still_be_inspected(self, scale):
        """The other 1,178. The last key of the element table is not on
        the path, not a top action and not a finding - and it opens."""
        drawn = _follow(scale)
        assert drawn["deep_element"], "the run names no elements"
        assert drawn["deep_rows"] >= 3, (
            f"{drawn['deep_element']} opened with {drawn['deep_rows']} facts")
        assert drawn["empty_note"] == 0, (
            "an element with facts was told it has none")

    def test_opening_the_same_element_twice_is_one_block(self, scale):
        assert _follow(scale)["deep_is_idempotent"]


@needs_node
class TestOnTheCommittedRun:
    def test_nothing_is_dead_there_either(self, small):
        drawn = _follow(small)
        assert drawn["dead_after"] == 0
        assert drawn["unresolvable"] == []

    def test_and_it_could_not_have_seen_the_defect(self, small):
        """Recorded rather than assumed: this fixture has every element
        in the detail section, which is why the scale run above is the
        one that matters."""
        drawn = _follow(small)
        assert drawn["dead_before"] == 0, (
            "the committed run now has dead anchors too, so the note in "
            "this file's docstring is out of date")


@needs_node
class TestAnElementWithNothingSaysSo:
    def test_it_says_so_rather_than_drawing_an_empty_block(self, small):
        """`UX-278` item 2. "This run records nothing for it" and "this
        anchor is broken" must not look alike, so the block exists and
        says which one it is."""
        drawn = _follow_uid(small, "ghost-element.bst")
        assert drawn["rows"] == 0
        assert drawn["note"] == 1, "an element with no data said nothing"

    def test_and_an_element_with_data_is_not_told_it_has_none(self, small):
        """The other side, so the note above cannot be unconditional."""
        real = next(iter(small["signals"]["element_durations"]))
        drawn = _follow_uid(small, real)
        assert drawn["rows"] > 0, real
        assert drawn["note"] == 0


_ONE = r"""
const shim = await import(process.env.BGA_DOM_SHIM);
globalThis._makeNode ??= shim.makeNode;
shim.installDocument();
const views = await import("%(views)s");
const { readFileSync } = await import("node:fs");
const payload = JSON.parse(readFileSync(%(payload)s, "utf8"));
const root = shim.makeNode("div");
const section = views.ensureElementSection(payload, root, %(uid)s, {});
console.log(JSON.stringify({
  rows: section.querySelectorAll("dd").length,
  note: section.querySelectorAll("[data-empty-element]").length,
}));
"""


def _follow_uid(payload, uid):
    import tempfile
    scratch = tempfile.mkdtemp()
    try:
        run = pathlib.Path(scratch, "payload.json")
        run.write_text(json.dumps(payload), encoding="utf-8")
        script = _ONE % {"views": (REPO / "bga/viewer/views.js").as_uri(),
                         "payload": json.dumps(str(run)),
                         "uid": json.dumps(uid)}
        done = subprocess.run([node, "--input-type=module", "-e", script],
                              capture_output=True, text=True, cwd=REPO,
                              timeout=120,
                              env={**os.environ, "BGA_DOM_SHIM":
                                   (REPO / "tests/dom_shim.mjs").as_uri()})
        assert done.returncode == 0, done.stderr[-3000:]
        return json.loads(done.stdout)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
