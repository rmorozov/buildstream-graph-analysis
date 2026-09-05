"""UX-286: the report has chapters, and every section is in one.

Measured at 1440x900 in Chrome 141 before this landed:

```text
                              1,202-element     macro_micro
sections                                48              39
document                          18.8 scr        20.1 scr
median section                    0.24 scr        0.35 scr
sections under 0.8 screens              46 (95%)        37 (94%)
```

Forty-eight fragments averaging a fifth of a screen, with nothing
grouping them - so the rail listed thirty-one top-level entries and the
reader's only unit of navigation was the fragment.

**What these guards check, and where.** Two instruments, because the
item makes two kinds of claim:

- *Which chapter a section is in* is read off the booted export's own
  document (`test_the_order_the_page_has.py`'s harness), never off the
  table that decides it. A guard that asked `chapters.js` where a
  section belongs would agree with itself about a page it never read.
- *That grouping costs no height* is a pixel claim, and lives with the
  other pixel claims in `test_the_page_has_geometry.py`.
"""
import functools
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile

import pytest

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")
REPO = pathlib.Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests" / "fixtures" / "golden" / "mixed_task_kinds"
#: `UX-414`: the two-plane run. Every section golden has, plus the ones
#: that exist only when a capture carried Plane 2 - which is where the
#: unchaptered sections were hiding.
MACRO_MICRO = REPO / "tests" / "fixtures" / "macro_micro" / "run"
FIXTURES = {"golden": GOLDEN, "macro_micro": MACRO_MICRO}
CHAPTERS_JS = REPO / "bga" / "viewer" / "chapters.js"

# The acceptance test's bound, stated here rather than counted off the
# module. Reading the table and asserting its length against itself is
# the mutation that passes.
CHAPTERS_AT_LEAST = 6
CHAPTERS_AT_MOST = 8


def _table():
    """`[(id, title)]`, read out of `chapters.js`."""
    source = CHAPTERS_JS.read_text(encoding="utf-8")
    block = source.split("export const CHAPTERS = [", 1)[1].split("\n];", 1)[0]
    found = re.findall(r'id:\s*"([a-z]+)",\s*\n\s*title:\s*"([^"]+)"', block)
    assert found, "could not read the chapter table"
    return found


_PROBE = r"""
const shim = await import(process.env.BGA_DOM_SHIM);
shim.installDocument();
globalThis.window = { location: { hash: "", search: "" }, addEventListener() {},
                      matchMedia: () => ({ matches: false, addEventListener() {} }) };
const chapters = await import(process.env.MOD);
const root = shim.makeNode("div");
for (const [key, rail] of JSON.parse(process.env.SECTIONS)) {
  const node = shim.makeNode("section");
  node.setAttribute("data-section", key);
  if (rail) node.setAttribute("data-rail", rail);
  root.append(node);
}
chapters.chapters(root, globalThis.document);
console.log(JSON.stringify(root.children.map((box) => ({
  chapter: box.getAttribute("data-chapter"),
  members: box.querySelectorAll("[data-section]")
    .map((n) => n.getAttribute("data-section")),
}))));
"""


_LATE_PROBE = r"""
const shim = await import(process.env.BGA_DOM_SHIM);
shim.installDocument();
const chapters = await import(process.env.MOD);
const root = shim.makeNode("div");
for (const key of ["findings", "structural", "producer"]) {
  const node = shim.makeNode("section");
  node.setAttribute("data-section", key);
  node.setAttribute("data-rail", key === "producer" ? "raw" : "decide");
  root.append(node);
}
chapters.chapters(root, globalThis.document);
// And now the block `UX-278` builds when an anchor is followed, long
// after the document was grouped.
const late = shim.makeNode("section");
late.setAttribute("data-section", "element-late-bst");
root.append(late);
chapters.fileInChapter(root, late, globalThis.document);
console.log(JSON.stringify({
  loose: root.children.filter((n) => n.getAttribute?.("data-section"))
    .map((n) => n.getAttribute("data-section")),
  home: late.parentNode?.getAttribute?.("data-chapter") ?? null,
  last: root.children[root.children.length - 1]
    ?.getAttribute?.("data-chapter") ?? null,
}));
"""


def _late():
    """Group a document, then hand it a section that arrives after."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    probe = tmp / "probe.mjs"
    probe.write_text(_LATE_PROBE, encoding="utf-8")
    done = subprocess.run(
        [node, str(probe)], capture_output=True, text=True, cwd=REPO, timeout=60,
        env=dict(os.environ,
                 BGA_DOM_SHIM=str(REPO / "tests/dom_shim.mjs"),
                 MOD=str(CHAPTERS_JS)))
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


def _group(sections):
    """Run the real grouping over a made-up document."""
    tmp = pathlib.Path(tempfile.mkdtemp())
    probe = tmp / "probe.mjs"
    probe.write_text(_PROBE, encoding="utf-8")
    done = subprocess.run(
        [node, str(probe)], capture_output=True, text=True, cwd=REPO, timeout=60,
        env=dict(os.environ,
                 BGA_DOM_SHIM=str(REPO / "tests/dom_shim.mjs"),
                 MOD=str(CHAPTERS_JS),
                 SECTIONS=json.dumps(sections)))
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


@functools.cache
def _cached_boot(source):
    """One export and one node boot per fixture, per process.

    `UX-418`'s new step measured this file at 15.9s once `UX-414` gave
    it a second fixture - over the large floor, for fifteen clauses
    reading the same two documents. The boot is deterministic and every
    clause only reads what it returns, so it is taken once. The
    inventory-carrying calls below are not cached: each one is a
    different document by construction.
    """
    return _boot_chapters_uncached(source=source)


def _boot_chapters(inventory=None, source=GOLDEN):
    if inventory is None:
        return _cached_boot(str(source))
    return _boot_chapters_uncached(inventory=inventory, source=source)


def _boot_chapters_uncached(inventory=None, source=GOLDEN):
    """What the booted export is actually grouped into.

    The export, not a shim document: this is the page a reader is sent
    (`UX-195`), assembled by `boot` rather than by a test that calls the
    same functions in the same order and proves nothing.

    `source` since `UX-414`. This booted `GOLDEN` and nothing else, and
    golden is a **single-plane** run: `restructuring` and `binary_cost`
    only exist when Plane 2 is present, so both sat in the fallback
    chapter while the clause asserting the fallback is empty was green.
    "Asserted on both runs" was true of the two runs this fixture has,
    and neither of them is a run where either section exists.
    """
    tmp = pathlib.Path(tempfile.mkdtemp())
    run = tmp / "run"
    shutil.copytree(source, run)
    # `UX-414`: the Plane 2 report is a *sibling* of the run directory,
    # not a file inside it, so a `copytree` of the run alone silently
    # produces a single-plane copy of a two-plane fixture. That is the
    # second half of this item's finding: the guard would have gained a
    # two-plane leg that measured the one-plane page.
    sidecar = pathlib.Path(source).parent / "plane2.json"
    if sidecar.exists():
        shutil.copy(sidecar, tmp / "plane2.json")
    if (run / "expected_output.json").exists():
        os.remove(run / "expected_output.json")
    if inventory is not None:
        (run / "sources.json").write_text(json.dumps(inventory), encoding="utf-8")

    import tools.bga_view as view

    page = tmp / "report.html"
    view.export(str(run), str(page))
    html = page.read_text(encoding="utf-8")
    module = tmp / "inline.mjs"
    module.write_text(
        re.search(r'<script type="module">(.*?)</script>', html, re.S).group(1),
        encoding="utf-8")
    probe = tmp / "probe.mjs"
    source = (REPO / "tests/unit/test_a_report_you_can_navigate.py").read_text()
    probe.write_text(source.split('_PROBE = r"""', 1)[1].rsplit('"""', 1)[0]
                     + CHAPTER_TAIL, encoding="utf-8")
    done = subprocess.run(
        [node, str(probe)], capture_output=True, text=True, cwd=REPO, timeout=90,
        env=dict(os.environ, PAGE=str(page), MOD=str(module), PROTOCOL="file:"))
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout.strip().splitlines()[-1])


# The navigation probe prints its own JSON and exits; this runs after it
# and prints one more line, so the chapters are read from the same boot
# rather than from a second one that might differ.
CHAPTER_TAIL = r"""
const box = globalThis.document.getElementById("report");
const boxes = box.children.filter((n) => n.getAttribute?.("data-chapter")
                                      && !n.getAttribute?.("data-section"));
console.log(JSON.stringify({
  chapters: boxes.map((n) => ({
    id: n.getAttribute("data-chapter"),
    // UX-347: the heading now carries the chapter's open/shut control,
    // the way a section's heading has carried its collapse caret since
    // UX-317. The chapter's *name* is the heading without it - compared
    // against `aria-label` below, which is what a screen reader reads.
    title: (() => {
      const head = n.children.find((c) => c.className === "chapter-title");
      if (!head) return undefined;
      const control = head.children.find(
        (c) => c.getAttribute?.("data-chapter-open"));
      return control
        ? String(head.textContent).replace(String(control.textContent), "")
        : head.textContent;
    })(),
    role: n.getAttribute("role"),
    label: n.getAttribute("aria-label"),
    id_attr: n.getAttribute("id"),
    members: n.querySelectorAll("[data-section]")
      .map((c) => c.getAttribute("data-section")),
  })),
  all: box.querySelectorAll("[data-section]")
    .map((n) => [n.getAttribute("data-section"), n.getAttribute("data-chapter")]),
  loose: box.children.filter((n) => n.getAttribute?.("data-section"))
    .map((n) => n.getAttribute("data-section")),
}));
"""


@needs_node
class TestTheReportHasChapters:

    def test_the_page_is_grouped_into_six_to_eight_chapters(self):
        """The acceptance test's first clause, on the booted page."""
        out = _boot_chapters()
        ids = [chapter["id"] for chapter in out["chapters"]]
        assert CHAPTERS_AT_LEAST <= len(ids) <= CHAPTERS_AT_MOST, ids

    def test_every_section_is_in_exactly_one_chapter(self):
        """The acceptance test's second clause. Both directions: every
        section names a chapter, and no section is left at the top
        level beside the chapters."""
        out = _boot_chapters()
        assert out["all"], "the page rendered no sections at all"
        homeless = [key for key, chapter in out["all"] if not chapter]
        assert homeless == [], f"{homeless} are in no chapter"
        assert out["loose"] == [], (
            f"{out['loose']} sit beside the chapters rather than inside one")
        counted = sum(len(chapter["members"]) for chapter in out["chapters"])
        assert counted == len(out["all"]), (
            f"{counted} members across chapters, {len(out['all'])} sections "
            f"on the page - a section is in two chapters")

    @pytest.mark.parametrize("fixture", sorted(FIXTURES))
    def test_nothing_falls_through_to_everything_else(self, fixture):
        """The fallback chapter is not a hiding place. A section with no
        entry in the table and no `bga:rail` lands there, and on a real
        run there is no such section - so a new one that arrives
        unclassified reddens this instead of appearing at the foot of
        the document under a heading that says nothing.

        `UX-414`: **on both runs, and now that means two different
        payloads.** This clause was green over one single-plane fixture
        while two Plane 2 sections sat in the bucket, which is the
        shape of hollow guard `UX-403`'s census exists to find - not a
        clause that cannot fail, but one whose only fixture cannot
        produce the case.
        """
        out = _boot_chapters(source=FIXTURES[fixture])
        assert out["chapters"], "the page drew no chapters; nothing checked"
        more = [c for c in out["chapters"] if c["id"] == "more"]
        assert more == [], f"Everything else holds {more[0]['members']}"

    #: `UX-414`: where the two Plane 2 sections belong, named because
    #: nothing else can name it. The fallback clause catches a section
    #: with *no* chapter; a section with a `bga:rail` always has one,
    #: so a section filed under the wrong heading is invisible to every
    #: other clause here. Both of these carry `bga:rail: act`, which
    #: `RAIL_CHAPTER` sends to "Where did the time go?" - right for
    #: `binary_cost`, wrong for `restructuring`, which is a list of
    #: dependency edges to delete.
    PLANE2_CHAPTERS = {"restructuring": "change", "binary_cost": "time"}

    def test_the_two_plane_sections_are_where_they_answer(self):
        where = dict(_boot_chapters(source=MACRO_MICRO)["all"])
        got = {key: where.get(key) for key in self.PLANE2_CHAPTERS}
        assert got == self.PLANE2_CHAPTERS, got

    def test_the_two_plane_run_publishes_more_than_the_one_plane_run(self):
        """What keeps the parametrisation above honest. If both
        fixtures drew the same sections, the second leg would cost a
        boot and assert nothing - and the sections it exists for are
        exactly the ones golden does not have."""
        one = {key for key, _ in _boot_chapters(source=GOLDEN)["all"]}
        two = {key for key, _ in _boot_chapters(source=MACRO_MICRO)["all"]}
        assert {"restructuring", "binary_cost"} <= two - one, (
            f"the two-plane fixture adds {sorted(two - one)}, which does "
            f"not include the sections this leg was added for")

    def test_each_chapter_is_a_named_landmark(self):
        """Item 2's other half: navigation moves chapter to chapter, and
        a chapter you cannot address is not a destination."""
        drawn = _boot_chapters()["chapters"]
        assert drawn, "the page drew no chapters; nothing checked"
        for chapter in drawn:
            assert chapter["title"], chapter
            assert chapter["id_attr"] == f"chapter-{chapter['id']}", chapter
            assert chapter["role"] == "region", chapter
            assert chapter["label"] == chapter["title"], chapter

    def test_the_chapters_come_in_the_declared_order(self):
        """Which order is declared is `chapters.js`'s business; that the
        page is in it is this guard's."""
        out = _boot_chapters()
        declared = [key for key, _ in _table()]
        drawn = [chapter["id"] for chapter in out["chapters"]]
        assert drawn, "the page drew no chapters; nothing checked"
        assert drawn == [key for key in declared if key in drawn], drawn

    def test_the_identity_chapter_closes_the_document(self):
        """`UX-285`'s outcome, now a property of the chapter order
        rather than of a pass that moved three sections."""
        out = _boot_chapters()
        assert out["chapters"][-1]["id"] == "run", out["chapters"][-1]
        # `UX-344`: and `document_shape`, which says how deep the
        # document itself turned out to be - a fact about the artifact,
        # like the producer stamp above it.
        assert out["chapters"][-1]["members"] == [
            "summary", "run_instance", "producer", "document_shape"]

    def test_the_blast_control_sits_with_the_table_it_answers(self):
        """`UX-285`'s other outcome. The chapter's declared order puts
        the control after `resource_blast`, not wherever `boot` happened
        to append it - document order would have left `whatif` between
        the shared-resource table and the query over it."""
        out = _boot_chapters(inventory=SHARED_MONOREPO)
        change = [c for c in out["chapters"] if c["id"] == "change"]
        assert change, "the run with an inventory drew no query chapter"
        members = change[0]["members"]
        assert "resource_blast" in members, members
        # `UX-348`: the export draws the same `blast` section the served
        # page does - with the published command instead of the search
        # box - so the key no longer says "offline".
        assert members.index("blast") == members.index(
            "resource_blast") + 1, members


@needs_node
class TestASectionTheTableDoesNotName:
    """The published `bga:rail` is the fallback, so a payload key added
    to the contract tomorrow is chaptered by what it already declares.

    Run against the grouping itself rather than the page, because the
    case is a section that does not exist yet - and a guard that waited
    for one would be a guard that never runs.
    """

    def test_an_unknown_section_lands_where_its_rail_says(self):
        out = _group([["findings", "decide"], ["newcomer", "prove"]])
        home = {member: box["chapter"]
                for box in out for member in box["members"]}
        assert home["newcomer"] == "believe", home

    def test_the_two_capacity_blocks_share_a_chapter(self):
        """`UX-275` published `capacity_recommendation`, which answers
        "what should the capacity be" beside `capacity_verdict`'s "was
        the capacity right".

        They would not meet on their published rails alone - `act` files
        one under "Where did the time go?" and `prove` files the other
        under "How much of this can I believe?" - so the pairing is a
        table entry, and this is what holds it. Checked here rather than
        on the booted export because the recommendation needs a Plane 2
        report the golden fixture does not carry.
        """
        out = _group([["capacity_verdict", "prove"],
                      ["capacity_recommendation", "act"]])
        home = {member: box["chapter"]
                for box in out for member in box["members"]}
        assert home["capacity_recommendation"] == home["capacity_verdict"], home
        assert home["capacity_verdict"] == "machine", home

    def test_an_unknown_section_with_no_rail_is_visible_not_lost(self):
        out = _group([["findings", "decide"], ["newcomer", None]])
        home = {member: box["chapter"]
                for box in out for member in box["members"]}
        assert home["newcomer"] == "more", home

    def test_a_block_built_later_joins_its_chapter(self):
        """`UX-278` builds an element block when its anchor is followed,
        which is long after `boot` grouped the document. Appended to the
        root it lands below the last chapter - past the identity block
        that closes the page (`UX-285`) - so it is filed instead."""
        out = _late()
        assert out["loose"] == [], f"{out['loose']} ended up outside a chapter"
        assert out["home"] == "elements", out
        assert out["last"] == "run", (
            "the identity chapter no longer closes the document")

    def test_grouping_twice_changes_nothing(self):
        """`UX-278` files an element block into its chapter long after
        `boot` grouped the document, which calls this again on a
        document that is already grouped."""
        sections = [["findings", "decide"], ["producer", "raw"],
                    ["element-a-bst", None]]
        once = _group(sections)
        assert [box["chapter"] for box in once] == ["decide", "elements", "run"]
        assert [box["members"] for box in once] == [
            ["findings"], ["element-a-bst"], ["producer"]]


# The same run-with-an-inventory `UX-285`'s order guard uses: four
# elements, one monorepo behind three of them, which is what makes
# `resource_blast` render at all.
SHARED_MONOREPO = {
    "schema": "sources/v1",
    "elements": {
        "lib.bst": [{"kind": "git", "identity": "example.com/org/mono",
                     "keying": "ref", "staged_at": "src/lib"}],
        "app.bst": [{"kind": "git", "identity": "example.com/org/mono",
                     "keying": "ref", "staged_at": "src/app"}],
        "extra.bst": [{"kind": "git", "identity": "example.com/org/mono",
                       "keying": "ref", "staged_at": "src/extra"}],
        "base.bst": [{"kind": "local", "identity": "files/base",
                      "keying": "content"}],
    },
    "unreadable": {},
}
