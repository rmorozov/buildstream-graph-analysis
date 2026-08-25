"""UX-279, UX-280, UX-284: the controls, named and within reach.

Three reports, one seam - the strip of controls above every table, and
the copy buttons scattered through the page.

**UX-279.** Reported: *"in sections there is button copy - its context
generally unclear - what will it copy."* Measured on the served report
when it was filed:

```text
"Copy link to this view"    1   (clear: the url)
"Copy"                     14   (decision x3, findings x11)
"Copy shown rows"          28   (one per table)

controls carrying a `title`        0 of 43
controls carrying an `aria-label`  0 of 43
```

The bare `Copy` was the sharper half: one function drew two different
controls - a finding's pasteable text and a question's SQL - and both
read `Copy`. And `Copy shown rows` is a promise; a number is a fact a
reader can check against the badge beside it.

**UX-280.** JSON pastes into a ticket as a code block somebody has to
read. Markdown pastes as a table. Same rows, same order, same `data-raw`
values - a second *rendering* of what `rowJson` already copies, so the
two can never disagree about which rows were shown.

**UX-284.** Reported: *"the search box is buried at the bottom of
sections."* Measured in Chromium, before and after, at two widths:

```text
                              before        after
  tools below their table       28 of 43     0 of 24
  tools with position: sticky    0 of 43    24 of 24
  jump box top (1440x900)          1236px      171px   (fold at 900)
```
"""
import json
import os
import pathlib
import shutil
import subprocess

import pytest

from bga import schemas

REPO = pathlib.Path(__file__).resolve().parents[2]
RUN = REPO / "tests/fixtures/macro_micro/run"
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

# What a copy control may say. The vocabulary is closed on purpose:
# `UX-279`'s third item is that two controls copying different things
# read differently, and an open vocabulary cannot be checked for that.
COPY_NOUNS = ("finding", "query", "command", "rows", "row",
              "link to this view")


@pytest.fixture(scope="module")
def payload():
    done = subprocess.run(
        ["python", "-m", "bga.cli", "analyze", str(RUN), "--format", "json"],
        capture_output=True, text=True, cwd=REPO, timeout=180)
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


_HARNESS = r"""
const shim = await import(process.env.BGA_DOM_SHIM);
globalThis._makeNode ??= shim.makeNode;
globalThis.Event ??= class { constructor(t, o = {}) { this.type = t; Object.assign(this, o); } };
shim.installDocument();
globalThis.window = { location: { hash: "", search: "" }, addEventListener() {},
                      matchMedia: () => ({ matches: false, addEventListener() {} }) };
const app = await import("%(app)s");
const { readFileSync } = await import("node:fs");
const root = shim.makeNode("div");
app.render(JSON.parse(readFileSync(%(payload)s, "utf8")),
           JSON.parse(readFileSync(%(schema)s, "utf8")), root);

const text = (n) => (n.textContent ?? "") + (n.children ?? []).map(text).join("");
const controls = root.querySelectorAll("button").filter(
  (b) => /^copy/i.test(text(b).trim()));

// Every table's tools, and whether they precede the table they belong
// to in document order. Geometry is the browser's job (a separate
// guard); this is the half a DOM can answer, and it is the half that
// decides reading order for a screen reader and the Tab key.
const strips = [];
for (const tools of root.querySelectorAll(".table-tools")) {
  const box = tools.parentNode;
  const kids = box?.children ?? [];
  const at = kids.indexOf(tools);
  const table = kids.findIndex((n) => n.tagName === "table"
    || (n.querySelectorAll?.("table") ?? []).length);
  strips.push({ tools_at: at, table_at: table });
}

console.log(JSON.stringify({
  controls: controls.map((b) => ({
    label: text(b).trim(),
    title: b.getAttribute("title"),
    copies: b.getAttribute("data-copies"),
    cls: b.attrs.class ?? "",
    // What it would actually put on the clipboard, where the control
    // carries it. This is what the label is a claim *about*.
    payload: (b.getAttribute("data-copy") ?? "").slice(0, 40),
  })),
  strips,
  markdown_boxes: root.querySelectorAll("input.copy-markdown").length,
  tables: root.querySelectorAll("table[data-table]").length,
}));
"""


def _page(payload):
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
            "payload": json.dumps(str(run)), "schema": json.dumps(str(doc))}
        done = subprocess.run([node, "--input-type=module", "-e", script],
                              capture_output=True, text=True, cwd=REPO,
                              timeout=120,
                              env={**os.environ, "BGA_DOM_SHIM":
                                   (REPO / "tests/dom_shim.mjs").as_uri()})
        assert done.returncode == 0, done.stderr[-3000:]
        return json.loads(done.stdout)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


@needs_node
class TestEveryCopyControlNamesItsNoun:
    def test_none_of_them_just_says_copy(self, payload):
        drawn = _page(payload)
        bare = [c for c in drawn["controls"] if c["label"] == "Copy"]
        assert bare == [], f"{len(bare)} control(s) still say only `Copy`"

    def test_every_one_of_them_names_something(self, payload):
        drawn = _page(payload)
        assert drawn["controls"], "the page draws no copy controls at all"
        unnamed = [c["label"] for c in drawn["controls"]
                   if not any(noun in c["label"].lower()
                              for noun in COPY_NOUNS)]
        assert unnamed == [], f"control(s) naming nothing: {unnamed}"

    def test_every_one_of_them_says_so_on_hover_too(self, payload):
        """`UX-279` item 1: in the control *or* on hover. Both, because
        a truncated label is the case the hover text is for."""
        drawn = _page(payload)
        bare = [c["label"] for c in drawn["controls"] if not c["title"]]
        assert bare == [], f"control(s) with no hover text: {bare}"

    def test_the_row_control_names_a_count_not_a_promise(self, payload):
        """`UX-279` item 2. "Copy shown rows" cannot be checked; `Copy 12
        rows` can, against the badge beside it."""
        drawn = _page(payload)
        rows = [c for c in drawn["controls"] if "row" in c["label"].lower()]
        assert rows, "no table offers a row copy"
        assert all(any(ch.isdigit() for ch in c["label"]) for c in rows), (
            [c["label"] for c in rows])
        assert not any("shown rows" == c["label"].lower().replace("copy ", "")
                       for c in rows)

    def test_the_label_matches_what_the_control_actually_copies(self, payload):
        """The rule with teeth. Grouping labels by a declared kind is
        satisfied by a control that declares the *wrong* kind - measured:
        reverting the finding button to the default noun left every other
        test here green, because it then agreed with itself. This checks
        the label against the payload the control carries.

        A finding's pasteable text is stamped (`UX-224`); anything so
        stamped must say `finding`, and nothing else may.
        """
        drawn = _page(payload)
        wrong = [c["label"] for c in drawn["controls"]
                 if c["payload"].startswith("BGA finding")
                 and "finding" not in c["label"].lower()]
        assert wrong == [], (
            f"control(s) copying a finding and saying {wrong}")
        stolen = [c["label"] for c in drawn["controls"]
                  if "finding" in c["label"].lower() and c["payload"]
                  and not c["payload"].startswith("BGA finding")]
        assert stolen == [], (
            f"control(s) saying `finding` and copying something else: {stolen}")

    def test_two_controls_that_copy_different_things_read_differently(
            self, payload):
        """`UX-279` item 3, the one that catches a regression rather than
        a wording choice: one label, one payload kind."""
        drawn = _page(payload)
        kinds = {}
        for control in drawn["controls"]:
            kind = control["copies"] or control["cls"]
            kinds.setdefault(control["label"], set()).add(kind)
        clashes = {label: sorted(seen) for label, seen in kinds.items()
                   if len(seen) > 1}
        assert clashes == {}, (
            f"label(s) covering two different payloads: {clashes}")


@needs_node
class TestTheRowCopyOffersMarkdown:
    def test_every_table_offers_the_choice(self, payload):
        drawn = _page(payload)
        assert drawn["markdown_boxes"] == drawn["tables"], (
            f"{drawn['markdown_boxes']} choices for {drawn['tables']} tables")

    def test_markdown_is_a_rendering_of_the_same_rows(self):
        """Not a second selection: the same `data-raw` values `rowJson`
        copies, in the same order, so the two can never disagree about
        what was shown."""
        script = """
const shim = await import(process.env.BGA_DOM_SHIM);
shim.installDocument();
const { rowsMarkdown, rowJson } = await import("%s");
const mk = shim.makeNode;
const row = (uid, dur) => {
  const tr = mk("tr");
  const a = mk("td"); a.setAttribute("data-column", "element");
  a.setAttribute("data-raw", uid);
  const b = mk("td"); b.setAttribute("data-column", "dur");
  b.setAttribute("data-raw", String(dur));
  tr.append(a, b);
  return tr;
};
const rows = [row("a|b.bst", 5), row("c.bst", 9)];
const specs = [{ key: "element", title: "Element" },
               { key: "dur", title: "Duration", numeric: true }];
console.log(JSON.stringify({
  markdown: rowsMarkdown(rows, specs),
  json: rows.map((tr) => rowJson(tr, ["element", "dur"])),
}));
""" % (REPO / "bga/viewer/tables.js").as_uri()
        done = subprocess.run([node, "--input-type=module", "-e", script],
                              capture_output=True, text=True, cwd=REPO,
                              timeout=60,
                              env={**os.environ, "BGA_DOM_SHIM":
                                   (REPO / "tests/dom_shim.mjs").as_uri()})
        assert done.returncode == 0, done.stderr[-2000:]
        out = json.loads(done.stdout)
        lines = out["markdown"].splitlines()
        assert lines[0] == "| Element | Duration |"
        assert lines[1] == "| --- | ---: |", "a numeric column is not aligned"
        assert len(lines) == 2 + len(out["json"]), (
            "the two renderings disagree about how many rows were shown")
        assert "a\\|b.bst" in out["markdown"], (
            "a `|` inside a value would end the cell and was not escaped")
        for line, raw in zip(lines[2:], out["json"]):
            for value in json.loads(raw).values():
                # The same value, in the one form the table shape needs:
                # a `|` inside a cell would end it, so it is escaped -
                # which the line above is what asserts.
                assert str(value).replace("|", "\\|") in line, (line, raw)


@needs_node
class TestTheToolsComeBeforeTheirTable:
    def test_in_document_order_everywhere(self, payload):
        """`UX-284` item 1, for every renderer that draws a table -
        including the nested ones inside cells. Reading order is what a
        screen reader and the Tab key follow, so it is checked here
        rather than only in the geometry guard."""
        drawn = _page(payload)
        assert drawn["strips"], "the page draws no table tools"
        after = [s for s in drawn["strips"]
                 if s["table_at"] >= 0 and s["tools_at"] > s["table_at"]]
        assert after == [], f"{len(after)} tool strip(s) come after the table"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
