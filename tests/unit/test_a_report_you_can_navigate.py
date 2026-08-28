"""UX-199: getting around a report that had no signposts.

Field report: *"navigation in html report is quite poor at the moment if
explored through the browser."* Round 22's inventory agreed exactly: no
section ids, no table of contents, no collapse, fourteen sections in
payload key order on a real capture, Ctrl-F as the navigation.

**And a defect this item's export half uncovered, which nothing in the
filing predicted.** `bga view --export` inlined `perfetto.js` and
`app.js` and nothing else, while `app.js` had imported `views.js` since
`UX-196`. So every exported report called `renderBand`, `renderTrend`
and `renderBlastSearch` without defining any of them, threw a
`ReferenceError` inside `boot()`, and rendered its catch-all banner.
Measured under a DOM shim, before and after:

    before   top-level children: 1   sections: 0   "Could not load this run"
    after    top-level children: 14  sections: 14  no error banner

Every `--export` since `UX-196` produced a page that showed the reader
an error instead of their report. The module list is derived from the
entry point's own `import` lines now, because a hand-written list is a
thing to forget - which is exactly what happened.
"""
import json
import os
import re
import shutil
import subprocess

import pytest

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


@pytest.fixture
def run(tmp_path):
    target = tmp_path / "run"
    shutil.copytree(GOLDEN, target)
    os.remove(target / "expected_output.json")
    return str(target)


@pytest.fixture
def exported(run, tmp_path):
    from tools.bga_view import export

    path = tmp_path / "report.html"
    export(run, str(path))
    return path.read_text(encoding="utf-8")


def _inline(page):
    return re.search(r'<script type="module">(.*?)</script>', page, re.S).group(1)


def _boot(page, tmp_path, protocol="file:"):
    """Run the exported page's own module under a DOM shim."""
    module = tmp_path / "inline.mjs"
    module.write_text(_inline(page), encoding="utf-8")
    probe = tmp_path / "probe.mjs"
    probe.write_text(_PROBE, encoding="utf-8")
    result = subprocess.run(
        [node, str(probe)], capture_output=True, text=True, cwd=os.getcwd(),
        timeout=60, env=dict(os.environ, PAGE=str(tmp_path / "page.html"),
                             MOD=str(module), PROTOCOL=protocol))
    (tmp_path / "page.html").write_text(page, encoding="utf-8")
    result = subprocess.run(
        [node, str(probe)], capture_output=True, text=True, cwd=os.getcwd(),
        timeout=60, env=dict(os.environ, PAGE=str(tmp_path / "page.html"),
                             MOD=str(module), PROTOCOL=protocol))
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


class TestTheExportedPageActuallyRuns:
    """The regression that was live for a whole round."""

    def test_it_defines_every_function_it_calls(self, exported):
        body = _inline(exported)
        called = set(re.findall(r"\b(render[A-Z]\w+)\(", body))
        defined = set(re.findall(r"function\s+(render[A-Z]\w+)\b", body))
        missing = sorted(called - defined)
        assert not missing, (
            f"the exported page calls {missing} and defines none of them - "
            f"a ReferenceError in boot(), and the reader gets the catch-all "
            f"banner instead of their report")

    @needs_node
    def test_it_renders_sections_rather_than_an_error(self, exported, tmp_path):
        out = _boot(exported, tmp_path)
        assert out["error"] is None, out["error"]
        assert len(out["sections"]) >= 10, out["sections"]

    def test_the_module_list_is_derived_not_written_down(self):
        from tools.bga_view import _module_order

        order = _module_order()
        assert order[-1] == "app.js", "the entry point must come last"
        for name in ("views.js", "nav.js", "questions.js", "perfetto.js"):
            assert name in order, f"{name} would be missing from the export"
        # Dependencies before the module that imports them, or the
        # concatenation defines things after their first use.
        assert order.index("views.js") < order.index("app.js")

    def test_no_import_statement_survives_the_inlining(self):
        """A `file://` document cannot resolve `./views.js`, so one
        surviving `import` is `ERR_INVALID_URL` and an empty report.

        `UX-202` proved the old line-based strip was not enough: an
        `import { a, b }` list wrapped across two lines matched neither
        half of it, and every export died again - the same defect
        `UX-199` had just fixed, reintroduced by reformatting one line.
        This asserts the *property*, so the next reformat is caught by
        this rather than by a browser."""
        from tools.bga_view import _inline_module, _module_order

        blob = "\n".join(_inline_module(name) for name in _module_order())
        left = re.findall(r"^.*\bfrom\s+[\"']\./.*$", blob, re.M)
        assert not left, f"the export still tries to import: {left}"


class TestEverySectionCanBeLinkedTo:
    @needs_node
    def test_each_one_carries_its_key_as_an_id(self, exported, tmp_path):
        out = _boot(exported, tmp_path)
        for section in out["sections"]:
            assert section["id"] == section["key"], section

    @needs_node
    def test_the_contents_lists_exactly_what_was_rendered(self, exported, tmp_path):
        """Set equality, not order: `UX-209` groups the contents by
        rail - decide, act, prove, investigate, raw - so it no longer
        follows payload key order, deliberately. What must never drift
        is *which* sections it lists, which is the property this guard
        was written for; the rail order is asserted by
        `test_one_click_from_investigation.py`."""
        out = _boot(exported, tmp_path)
        rendered = [s["key"] for s in out["sections"]]
        assert sorted(out["toc"]) == sorted(rendered), (
            "the table of contents and the document disagree")
        assert len(out["toc"]) == len(set(out["toc"])), (
            "a section is listed twice")

    def test_the_contents_is_generated_from_the_render(self):
        """Not from a hardcoded list - so a section a schema addition
        brings into being appears in the contents with no edit, which is
        the property `UX-193` bought for the sections themselves."""
        source = open("bga/viewer/nav.js", encoding="utf-8").read()
        assert "querySelectorAll" in source
        assert "section[data-section]" in source


class TestCollapse:
    @needs_node
    def test_sections_start_open(self, exported, tmp_path):
        out = _boot(exported, tmp_path)
        assert all(s["collapsed"] != "true" for s in out["sections"]), (
            "a report that hides itself on load answers the navigation "
            "complaint by making the document harder to read")

    @needs_node
    def test_collapse_state_is_remembered_where_there_is_somewhere_to_put_it(
            self, exported, tmp_path):
        out = _boot(exported, tmp_path, protocol="http:")
        assert out["storageWrites"], (
            "nothing was written, so a reload forgets every choice")

    @needs_node
    def test_an_unavailable_localstorage_is_not_an_error(self, exported, tmp_path):
        """A private window, blocked site data, a thumbnail renderer."""
        out = _boot(exported, tmp_path, protocol="http:throwing")
        assert out["error"] is None, out["error"]
        assert out["sections"], "the report vanished because storage threw"


class TestTheExportKeepsItsFunctionality:
    def test_the_questions_module_is_the_single_source(self):
        """`sql.html` and the export must render the same list.

        This used to compare *titles* against a hand-written copy in
        `sql.html` - which would have passed while every query drifted.
        `UX-204` made the page render the module, so the assertion is
        now that there is nothing left to drift *from*."""
        result = subprocess.run(
            [node, "--input-type=module", "-e",
             'const { QUESTIONS } = await import("./bga/viewer/questions.js");'
             'console.log(JSON.stringify(QUESTIONS.map(q => q.title)));'],
            capture_output=True, text=True, cwd=os.getcwd(), timeout=60)
        assert result.returncode == 0, result.stderr
        titles = json.loads(result.stdout)
        assert len(titles) >= 4, titles
        page = open("bga/viewer/sql.html", encoding="utf-8").read()
        # `UX-266`: the script moved out of the page into a file,
        # because the server's own `default-src 'self'` refuses an
        # inline one. The property is unchanged; where it is written
        # is not, and a guard still reading the page would pass on
        # markup that no longer runs anything.
        script = open("bga/viewer/sql.js", encoding="utf-8").read()
        assert 'src="sql.js"' in page
        assert 'from "./questions.js"' in script
        page = page + script
        for title in titles:
            assert title not in page, (
                f"sql.html spells out {title!r} instead of rendering the "
                f"module - that is the copy this closed")

    @needs_node
    def test_the_export_carries_the_questions(self, exported, tmp_path):
        out = _boot(exported, tmp_path)
        keys = [s["key"] for s in out["sections"]]
        assert "perfetto-questions" in keys, (
            "the export used to strip the link to them and leave nothing")

    @needs_node
    def test_the_export_does_not_ship_a_search_box_that_cannot_work(
            self, exported, tmp_path):
        out = _boot(exported, tmp_path)
        blast = [s for s in out["sections"] if s["key"] == "blast"]
        # `UX-348`: what may not ship is the box, not the section. The
        # export draws `blast` with the command the pipeline published
        # for this run where the search box would be - dropping the
        # section left the reader with nothing to run instead.
        assert blast, "the export draws no blast section at all"
        assert blast[0]["inputs"] == 0, (
            f"the export ships {blast[0]['inputs']} control(s) whose fetch "
            f"can never succeed from file://")

    @needs_node
    def test_the_served_page_keeps_both(self, exported, tmp_path):
        out = _boot(exported, tmp_path, protocol="http:")
        keys = [s["key"] for s in out["sections"]]
        assert "blast" in keys, keys
        served = next(s for s in out["sections"] if s["key"] == "blast")
        assert served["inputs"] >= 1, (
            "served, the section is the search box - both shapes drawing "
            "the same thing would make the guard above vacuous")
        assert "perfetto-questions" not in keys, (
            "served, the questions have their own page to link to")


_PROBE = r"""
import fs from "node:fs";

const protocol = process.env.PROTOCOL;
const throwing = protocol.endsWith("throwing");
const writes = [];

globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;

function make(tag) {
  const node = _makeNode(tag);
  node.hidden = true;
  return node;
}

const page = fs.readFileSync(process.env.PAGE, "utf8");
const blocks = {};
for (const m of page.matchAll(
    /<script type="application\/json" id="bga-([^"]+)">([\s\S]*?)<\/script>/g)) {
  blocks[m[1]] = m[2];
}

const named = {};
const body = make("body");
globalThis.document = {
  createElement: make, createElementNS: (_n, t) => make(t), body, title: "",
  // UX-219: the shim was an incomplete model of the DOM, and the gap was
  // latent rather than new - `views.js` has called `createTextNode` since
  // UX-212, in paths a golden export never reaches (they need a compare
  // or a store payload). The horizon renders on every analyze report, so
  // it made the gap live: the exported page threw
  // `document.createTextNode is not a function` inside `boot()` and the
  // reader got the catch-all banner instead of their report - UX-199's
  // defect, by a different route.
  //
  // Fixed here rather than by avoiding a standard DOM method in the
  // viewer: every browser has it, two call sites already depended on it,
  // and leaving the model short would keep the trap set for whoever next
  // makes one of those paths run.
  createTextNode: (t) => ({ nodeType: 3, textContent: String(t),
                            attrs: {}, children: [] }),
  getElementById(id) {
    if (id.startsWith("bga-")) {
      const key = id.slice(4);
      return key in blocks ? { textContent: blocks[key] } : null;
    }
    return named[id] ??= make("div");
  },
  // UX-254: `document.querySelector` exists in every browser, and this
  // model did not have it at all - so `app.js` asking for `header`
  // threw, the boot fell into its own error path, and twelve order
  // guards reported "Could not load this run" rather than an order.
  //
  // Added for the reason the `createTextNode` note above records:
  // fixed here rather than by avoiding a standard DOM method in the
  // viewer, because leaving the model short keeps the trap set for
  // whoever next makes one of those paths run.
  //
  // It models what the page asks for and returns `null` otherwise -
  // which is a real browser's answer for a selector that matches
  // nothing, and is what makes the caller take its documented
  // fallback rather than crash.
  querySelector(sel) {
    if (sel === "header") {
      // Attached to `body`, because a real page's header is. Detached,
      // `heading.after(contents)` is a no-op - a real DOM's answer too -
      // and `app.js` quietly took its `insertBefore` fallback instead,
      // so this probe measured the path the page does not use
      // (`UX-264`).
      if (!named.__header) { named.__header = make("header"); body.append(named.__header); }
      return named.__header;
    }
    return body.querySelector?.(sel) ?? null;
  },
};
globalThis.location = { protocol: protocol.startsWith("http") ? "http:" : "file:",
                        href: "http://127.0.0.1:8000/index.html" };
globalThis.window = {
  get localStorage() {
    if (throwing) throw new Error("site data blocked");
    return { getItem: () => null, setItem: (k, v) => writes.push([k, v]) };
  },
};
globalThis.fetch = async () => { throw new Error("no network here"); };
globalThis.CSS = { escape: (s) => s };

let failure = null;
process.on("unhandledRejection", (e) => { failure = String(e?.message ?? e); });
await import(process.env.MOD);
await new Promise((r) => setTimeout(r, 250));

const report = named["report"] ?? make("div");

// State *before* any interaction - "sections start open" is a
// claim about what the reader first sees.
const sections = [];
// UX-348: a section can be present and still carry no live control, so
// the probe reports the controls as well as the key - "does the export
// ship a search box" is a question about the form, not the section.
const liveControls = (n) => {
  let found = 0;
  (function count(node) {
    for (const c of node.children ?? []) {
      const role = c.attrs["data-role"] ?? "";
      const tag = String(c.tagName ?? "").toLowerCase();
      if (tag === "input" || tag === "form" || role.endsWith("-form")
          || role.endsWith("-input")) found += 1;
      count(c);
    }
  })(n);
  return found;
};
(function walk(n) {
  for (const c of n.children ?? []) {
    if (c.attrs["data-section"]) {
      sections.push({ key: c.attrs["data-section"], id: c.attrs.id ?? null,
                      collapsed: c.attrs["data-collapsed"] ?? null,
                      inputs: liveControls(c) });
    }
    walk(c);
  }
})(report);

// UX-199: collapse writes on click, so the probe has to click - and the
// buttons live on the section headings inside the report, not in the
// nav. A harness that never fires the event would assert nothing was
// remembered and call that a pass.
for (const root of [report, body]) {
  const clicked = (function find(n) {
    for (const c of n.children ?? []) {
      if (c.attrs["data-collapse"]) { c.click(); return true; }
      if (find(c)) return true;
    }
    return false;
  })(root);
  if (clicked) break;
}

let toc = [];
(function findToc(n) {
  for (const c of n.children ?? []) {
    if (c.attrs["data-toc"]) toc.push(c.attrs["data-toc"]);
    findToc(c);
  }
})(body);

let error = failure;
(function findError(n) {
  for (const c of n.children ?? []) {
    if ((c.textContent || "").includes("Could not load")) error = c.textContent;
    findError(c);
  }
})(report);

console.log(JSON.stringify({ sections, toc, error, storageWrites: writes }));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
