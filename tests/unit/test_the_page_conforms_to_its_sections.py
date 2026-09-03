"""UX-320: the page, audited against the sections round 44 earned.

The `UX-305` precedent: an extension to the visual contract is not real
until the *existing* page is audited against it and the audit is a
guard. Round 44 added four sections — §2a drawing grades, §2b apparatus
placement, §3a the depth budget, §3b the click budget — and `UX-316`,
`UX-317`, `UX-318` and `UX-319` built the mechanisms. This file is the
pass over everything they did not each touch.

**What the pass found.** Three things, and only one of them was a
defect:

```text
every <svg> in main            graded, box from the scale          ok
every value fold               levels + rows                        ok
`evidence-detail`              "The numbers behind that", no count  FIXED
`question-group`               "scheduling (3)" - counted already   ok
`provenance` / `why-ranked`    one prose block each                 declared
`long-text`                    the rest of a string, shown          declared
```

`evidence-detail` is the one that mattered: it folds **published
values** — the numbers behind the verdict — and was built by hand in
`views.js`, outside the renderer `UX-318` taught to count. It says
"1 level, N rows" now.

The other two are the line this pass draws, and drawing it is the other
half of the job. §3a.1's subject is "a cell that folds deeper content":
a fold over one prose block has no depth to announce, and a truncation
shows what it truncated. They are **declared** here with their reasons
rather than exempted silently, so a fold that joins them has to argue
its way in.

**The four walks.** Each item's own guard drives the mechanism it
built; these drive the *page*, over everything on it, so a surface none
of them enumerated is still held to the rule.

holds: rules.md#touching-the-page-run-the-styleguides-seven-questions
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))
from pages import snapshot_copy    # noqa: E402
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")
VIEWER = REPO / "bga" / "viewer"
SHIM = str(REPO / "tests" / "dom_shim.mjs")
GOLDEN = REPO / "tests" / "fixtures" / "golden" / "mixed_task_kinds"
MACRO = REPO / "tests" / "fixtures" / "macro_micro" / "run"

#: §3a.1's subject is "a cell that folds deeper content". These fold
#: something else, and each says what instead - declared, so a fold that
#: joins them has to argue rather than arrive.
LAYOUT_FOLDS = {
    "provenance": "one prose block: why this verdict. No depth to announce",
    "why-ranked": "one ranked reason, one block each - same",
    "long-text": "`UX-269`'s truncation: it shows the string it cut, and "
                 "the rest is the same string",
    "question-group": "counted already, in its own summary - "
                      "`scheduling (3)`",
}

#: The boxes `drawings.js` declares. A drawing outside them is a
#: per-drawing constant by another name (§2a).
def _scale():
    source = (VIEWER / "drawings.js").read_text(encoding="utf-8")
    found = {}
    for grade in ("GRADE_ANNOTATION", "GRADE_EXHIBIT"):
        block = re.search(
            r"\[%s\]: Object\.freeze\(\{([^}]*)\}\)" % grade, source, re.S)
        assert block, grade
        found[grade] = {name: int(value) for name, value in
                        re.findall(r"(\w+):\s*(\d+)", block.group(1))}
    return found


def _boxes():
    scale = _scale()
    out = set()
    for grade in scale.values():
        width = grade["width"]
        for name, height in grade.items():
            if name != "width":
                out.add(f"0 0 {width} {height}")
    return out


def _probe_source():
    source = (REPO / "tests/unit/test_a_report_you_can_navigate.py").read_text()
    return source.split('_PROBE = r"""', 1)[1].rsplit('"""', 1)[0]


_TAIL = r"""
const all = (n, pred, out = []) => {
  if (pred(n)) out.push(n);
  for (const c of n.children ?? []) all(c, pred, out);
  return out;
};
const text = (n) => !n ? "" : ((n.children ?? []).length
  ? (n._text ?? "") + n.children.map(text).join("") : (n._text ?? ""));
const root = named["report"] ?? body;
const gradeOf = (n) => {
  let at = n;
  while (at) {
    if (at.attrs?.["data-grade"]) return at.attrs["data-grade"];
    at = at._parent;
  }
  return null;
};
console.log(JSON.stringify({
  // §2a: every drawing on the page, graded, with the box it drew at.
  drawings: all(root, (n) => n.tagName === "svg").map((n) => ({
    cls: String(n.className || n.attrs.class || ""),
    viewBox: n.attrs.viewBox ?? null, grade: gradeOf(n) })),
  // §3a.1: every fold, with what it says about its depth.
  folds: all(root, (n) => n.tagName === "details").map((n) => ({
    cls: String(n.className || "").split(" ")[0],
    levels: n.attrs["data-levels"] ?? null,
    rows: n.attrs["data-rows"] ?? null,
    summary: text(n.children[0]).trim() })),
  // §3a.3: the scroll chain, as `UX-318`'s walk counts it.
  scrolls: (() => {
    const depths = [];
    const scrolls = (n) => {
      if (String(n.className || n.attrs?.class || "").split(" ")
          .includes("map-table")) return false;   // no scroll since UX-318
      if (n.tagName !== "table") return false;
      let at = n._parent;
      while (at) { if (at.tagName === "table") return false; at = at._parent; }
      return true;
    };
    (function walk(n, above) {
      const here = scrolls(n) ? above + 1 : above;
      if (scrolls(n)) depths.push(here);
      for (const c of n.children ?? []) walk(c, here);
    })(root, 0);
    return depths;
  })(),
  // §3b: every section, and whether the rail lists it.
  sections: (() => {
    const nav = all(body, (n) => n.tagName === "nav"
      && String(n.className ?? "").includes("toc"))[0] ?? null;
    const linked = new Set((nav ? all(nav, (n) => n.attrs?.["data-toc"]) : [])
      .map((n) => n.attrs["data-toc"]));
    return all(root, (n) => n.attrs?.["data-section"]).map((s) => ({
      key: s.attrs["data-section"],
      linked: linked.has(s.attrs["data-section"]),
      collapsed: s.attrs["data-collapsed"] === "true" }));
  })(),
  error: failure,
}));
"""


def _boot(run_dir, tmp):
    run = snapshot_copy(run_dir, tmp)

    import tools.bga_view as view

    page = tmp / "report.html"
    view.export(str(run), str(page))
    html = page.read_text(encoding="utf-8")
    module = tmp / "inline.mjs"
    module.write_text(
        re.search(r'<script type="module">(.*?)</script>', html, re.S).group(1),
        encoding="utf-8")
    probe = tmp / "probe.mjs"
    probe.write_text(_probe_source().split("const report =", 1)[0] + _TAIL,
                     encoding="utf-8")
    result = subprocess.run(
        [node, str(probe)], capture_output=True, text=True, cwd=REPO,
        timeout=180,
        env=dict(os.environ, PAGE=str(page), MOD=str(module),
                 PROTOCOL="file:", BGA_DOM_SHIM=SHIM))
    assert result.returncode == 0, result.stderr[-4000:]
    out = json.loads(result.stdout)
    assert out["error"] is None, out["error"]
    return out


@pytest.fixture(scope="module")
def pages(tmp_path_factory):
    return {name: _boot(run, tmp_path_factory.mktemp(name))
            for name, run in (("golden", GOLDEN), ("macro_micro", MACRO))}


@pytest.fixture(scope="module")
def exports(tmp_path_factory):
    """The exported files themselves, for the claims that are about
    markup rather than about a booted document."""
    import tools.bga_view as view

    out = {}
    for name, source in (("golden", GOLDEN), ("macro_micro", MACRO)):
        tmp = tmp_path_factory.mktemp(f"{name}-export")
        run = snapshot_copy(source, tmp)
        page = tmp / "report.html"
        view.export(str(run), str(page))
        out[name] = page
    return out


@needs_node
@pytest.mark.medium
class TestTheGradeWalk:
    """§2a, over every drawing on the page - not the four the item
    named. A fifth drawing added anywhere is held to the same rule."""

    def test_every_drawing_declares_a_grade(self, pages):
        for name, page in pages.items():
            assert page["drawings"], f"{name} drew nothing"
            for drawing in page["drawings"]:
                assert drawing["grade"] in ("annotation", "exhibit"), (
                    name, drawing)

    def test_no_module_writes_a_box_the_scale_does_not_name(self):
        """The other half, and the one the booted pages cannot give: a
        drawing that renders only on a payload the committed fixtures do
        not carry - the store diagram needs two snapshots - is on
        neither page, so the walk below never sees it. Held statically
        instead, which is why the walk below is not the whole check.
        """
        loose = []
        for path in sorted(VIEWER.glob("*.js")):
            for line, body in enumerate(
                    path.read_text(encoding="utf-8").splitlines(), 1):
                if re.match(r"\s*(//|\*|/\*)", body):
                    continue
                for match in re.finditer(r"viewBox:\s*(.+?)(?:,\s*$|,\s)", body):
                    expr = match.group(1).strip()
                    if not any(token in expr for token in
                               ("size.", "SCALE[", "${H}", "${W}")):
                        loose.append((path.name, line, expr))
        assert loose == [], (
            f"a drawing's box is written out rather than read from the "
            f"scale: {loose}")

    def test_every_local_height_is_read_from_the_scale(self):
        """And the variables those `${H}` boxes interpolate - or the
        clause above has a hole shaped like a local constant, which is
        how the store diagram's `const H = 40` would have survived."""
        source = (VIEWER / "views.js").read_text(encoding="utf-8")
        assigns = re.findall(r"const (?:W = [^,;]+, )?H = ([^;]+);", source)
        assert assigns, "no figure height assigned in views.js"
        for expr in assigns:
            assert "SCALE[" in expr, (
                f"a figure's height is a local constant: {expr}")

    def test_every_box_comes_from_the_scale(self, pages):
        boxes = _boxes()
        for name, page in pages.items():
            for drawing in page["drawings"]:
                assert drawing["viewBox"] in boxes, (
                    f"{name}: {drawing['cls']} draws at {drawing['viewBox']}, "
                    f"which is not one of the scale's boxes {sorted(boxes)}")


class TestTheApparatusWalk:
    """§2b, on the **exported file** rather than on `index.html`.

    A first draft read the header off the booted DOM and passed a
    mutation that put a control straight back into it. The reason is
    worth writing down: the shim's `querySelector("header")` returns a
    *synthetic* node the probe makes for `app.js` to insert the rail
    after, so the walk was measuring a header nobody renders. `UX-317`
    measures the real one in a browser and scans `index.html`; this
    reads the export's own markup, which is the third surface and the
    one an attachment carries.

    Note what the export does to a link: `bga_view` strips anchors to
    satellite pages it does not carry, so a header `<a>` never reaches
    the file. A `<button>` does, which is what this catches.
    """

    def _header(self, path):
        html = Path(path).read_text(encoding="utf-8")
        found = re.search(r"<header>(.*?)</header>", html, re.S)
        assert found, f"{path} has no header"
        return re.sub(r"<!--.*?-->", "", found.group(1), flags=re.S)

    def test_the_header_holds_no_control(self, exports):
        for name, path in exports.items():
            body = self._header(path)
            for tag in ("<button", "<select", "<input", "<a "):
                assert tag not in body, (
                    f"{name}'s exported header holds a {tag.strip('< ')}: "
                    f"§2b.2 says actions live in the actions group")

    def test_the_header_stays_within_its_line_budget(self, exports):
        # `UX-317` owns the number; this pass holds the export to it
        # rather than keeping a second copy.
        sys.path.insert(0, str(REPO / "tests" / "unit"))
        from test_apparatus_in_its_place import HEADER_LINE_BUDGET

        for name, path in exports.items():
            blocks = re.findall(r"<(h1|p|div|ul|ol|table|section)\b",
                                self._header(path))
            assert len(blocks) <= HEADER_LINE_BUDGET, (name, blocks)


@needs_node
@pytest.mark.medium
class TestTheDepthWalk:
    """§3a, over every `<details>` - which is where this pass earned its
    keep: `evidence-detail` folds published values, is built by hand in
    `views.js`, and `UX-318`'s renderer never saw it."""

    def test_every_fold_either_counts_or_is_a_declared_layout_fold(self, pages):
        stray = {}
        for name, page in pages.items():
            for fold in page["folds"]:
                if fold["levels"] and fold["rows"]:
                    continue
                if fold["cls"] in LAYOUT_FOLDS:
                    continue
                stray.setdefault(name, []).append(
                    (fold["cls"], fold["summary"][:60]))
        assert stray == {}, (
            f"fold(s) that announce no depth and are not declared layout "
            f"folds: {stray}. Either count them (§3a.1) or add them to "
            f"LAYOUT_FOLDS with the reason.")

    def test_a_counting_fold_says_in_prose_what_it_says_in_attributes(
            self, pages):
        for name, page in pages.items():
            for fold in page["folds"]:
                if not fold["levels"]:
                    continue
                levels, rows = int(fold["levels"]), int(fold["rows"])
                want = (f"{levels} level{'' if levels == 1 else 's'}, "
                        f"{rows} row{'' if rows == 1 else 's'}")
                assert want in fold["summary"], (name, want, fold["summary"])

    def test_the_evidence_fold_is_one_of_the_counting_ones(self, pages):
        """Named, because it is what the pass found. A regression here
        is a fold going quiet again, not a class disappearing."""
        for name, page in pages.items():
            evidence = [f for f in page["folds"] if f["cls"] == "evidence-detail"]
            assert evidence, f"{name} has no evidence fold at all"
            for fold in evidence:
                assert fold["levels"] and int(fold["rows"]) > 0, (name, fold)

    def test_no_declared_layout_fold_is_unused(self):
        """The other direction: an exemption whose fold is gone is an
        exemption that quietly covers the next thing to use the name."""
        source = "".join(path.read_text(encoding="utf-8")
                         for path in sorted(VIEWER.glob("*.js")))
        for name in LAYOUT_FOLDS:
            assert f'"{name}"' in source, (
                f"`{name}` is exempted from the depth rule and no module "
                f"builds it")

    def test_no_scroll_container_sits_inside_another(self, pages):
        for name, page in pages.items():
            assert page["scrolls"], f"{name} found no scroll container"
            assert max(page["scrolls"]) <= 1, (name, page["scrolls"])


@needs_node
@pytest.mark.medium
class TestTheClickWalk:
    """§3b, over every section on the page. `UX-319`'s file measures the
    worst path and records the numbers; this asserts the property that
    makes the measurement meaningful - every section is *in* the rail,
    and none opens collapsed, so the budget is spent on navigation
    rather than on undoing a default."""

    def test_every_section_is_in_the_rail(self, pages):
        for name, page in pages.items():
            missing = [s["key"] for s in page["sections"] if not s["linked"]]
            assert missing == [], (name, missing)

    def test_no_section_opens_collapsed(self, pages):
        """A collapsed default costs a click on every path into it, and
        at 390px - where the rail is folded too - that is the third one
        (`UX-319`)."""
        for name, page in pages.items():
            shut = [s["key"] for s in page["sections"] if s["collapsed"]]
            assert shut == [], (name, shut)


class TestTheChecklistNamesTheNewSections:
    """`UX-320`'s last clause: the fixing guide's conformance checklist
    is what a contributor reads before committing, and an extension
    nobody is told to check is an extension that decays."""

    def _checklist(self):
        text = (REPO / "docs/contributing/fixing-guide.md").read_text(
            encoding="utf-8")
        line = [one for one in text.splitlines()
                if "conformance checklist" in one]
        assert line, "the fixing guide has no conformance checklist line"
        return line[0]

    @pytest.mark.parametrize("section", ["§2a", "§2b", "§3a", "§3b"])
    def test_the_line_names_the_section(self, section):
        assert section in self._checklist(), (
            f"the checklist does not mention {section}, so nobody is asked "
            f"to check it before committing")

    @pytest.mark.parametrize("guard", [
        "test_a_drawing_is_graded.py",
        "test_apparatus_in_its_place.py",
        "test_the_fold_says_how_deep_it_goes.py",
        "test_the_chain_folds_and_clicks_are_counted.py",
        "test_the_page_conforms_to_its_sections.py",
    ])
    def test_the_line_names_the_guard_that_answers(self, guard):
        assert guard in self._checklist(), (
            f"{guard} is not named, so a reader who fails the check does not "
            f"know which guard will say so")
