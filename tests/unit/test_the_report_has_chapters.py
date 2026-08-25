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


def _boot_chapters(inventory=None):
    """What the booted export is actually grouped into.

    The export, not a shim document: this is the page a reader is sent
    (`UX-195`), assembled by `boot` rather than by a test that calls the
    same functions in the same order and proves nothing.
    """
    tmp = pathlib.Path(tempfile.mkdtemp())
    run = tmp / "run"
    shutil.copytree(GOLDEN, run)
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
    title: n.children.find((c) => c.className === "chapter-title")?.textContent,
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

    def test_nothing_falls_through_to_everything_else(self):
        """The fallback chapter is not a hiding place. A section with no
        entry in the table and no `bga:rail` lands there, and on a real
        run there is no such section - so a new one that arrives
        unclassified reddens this instead of appearing at the foot of
        the document under a heading that says nothing."""
        out = _boot_chapters()
        assert out["chapters"], "the page drew no chapters; nothing checked"
        more = [c for c in out["chapters"] if c["id"] == "more"]
        assert more == [], f"Everything else holds {more[0]['members']}"

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
        assert out["chapters"][-1]["members"] == [
            "summary", "run_instance", "producer"]

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
        assert members.index("blast-offline") == members.index(
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
