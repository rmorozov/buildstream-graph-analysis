"""UX-208 + UX-209: investigation one click away, and a rail.

Two items with one shape: **the schema says what a thing is, and the
page acts on the declaration.** UX-208 adds `bga:role` so a column can
say it holds element uids — which is what earns its rows a generic
Inspect, with no per-table code. UX-209 adds `bga:question` and
`bga:rail` so a section can say what it answers and which part of the
argument it belongs to, and the heading, the TOC and the text renderer
read the same field.

The alternative in both cases is a list of key names in the viewer,
which is precisely what `UX-193` built the schema dispatch to avoid.
"""
import contextlib
import io
import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile

import pytest

from bga import schemas

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"
REAL = "examples/06-macro-micro-optimization/.bga/runs/20260821T170127Z/run"
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _report(run=GOLDEN):
    from bga.cli import main

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        main(["analyze", run, "--format", "json"])
    return json.loads(buffer.getvalue())


def _node(script, timeout=120):
    result = subprocess.run([node, "--input-type=module", "-e", script],
                            capture_output=True, text=True, cwd=os.getcwd(),
                            timeout=timeout)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _render(payload, timeout=120):
    """Renders the *whole page* with the real schema, because that is
    where the hints have to arrive - a harness that passes `{}` proves
    only that the fallback works."""
    scratch = tempfile.mkdtemp()
    payload_path = os.path.join(scratch, "payload.json")
    schema_path = os.path.join(scratch, "schema.json")
    with open(payload_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    with open(schema_path, "w", encoding="utf-8") as handle:
        json.dump(schemas.schema(payload["schema"]), handle)
    try:
        return _node(_HARNESS % json.dumps([payload_path, schema_path]),
                     timeout=timeout)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


class TestTheSchemaCarriesTheVocabulary:
    def test_every_section_a_reader_meets_declares_its_question(self):
        declared = schemas.schema(schemas.ANALYZE)["properties"]
        asked = {k for k, v in declared.items() if v.get(schemas.QUESTION)}
        assert len(asked) >= 12, sorted(asked)
        assert "headline" in asked and "floors" in asked

    def test_a_question_is_a_question(self):
        """The validator rejects a `bga:question` that is not one -
        caught where it is written, because a heading that is not a
        question reads as a mislabelled section rather than a bug."""
        with pytest.raises(ValueError, match="is not a question"):
            schemas._check_hint("x/v1", "k", {schemas.QUESTION: "Floors"})

    def test_a_rail_outside_the_closed_set_is_rejected(self):
        """Open would mean a section could land in a group the TOC does
        not render - i.e. vanish."""
        with pytest.raises(ValueError, match="is not one of"):
            schemas._check_hint("x/v1", "k", {schemas.RAIL: "somewhere"})

    def test_every_declared_rail_is_one_the_toc_renders(self):
        declared = schemas.schema(schemas.ANALYZE)["properties"]
        rails = {v.get(schemas.RAIL) for v in declared.values()}
        rails.discard(None)
        assert rails <= set(schemas.RAILS), rails

    def test_the_viewer_and_the_schema_agree_on_the_rails(self):
        """Two lists that happen to match today is the state `UX-214`
        found elsewhere in this same round."""
        rails = _node('const n = await import("./bga/viewer/nav.js");'
                      "console.log(JSON.stringify(n.RAILS));")
        assert rails == list(schemas.RAILS)

    def test_a_column_can_say_it_holds_element_uids(self):
        columns = schemas.schema(schemas.BLAST)["properties"]["blast_tree"][
            "bga:columns"]
        roles = {c["key"]: c.get("role") for c in columns}
        assert roles["element_uid"] == "element"
        assert roles["depth"] is None, "only uid columns claim the role"

    def test_a_role_outside_the_closed_set_is_rejected(self):
        with pytest.raises(ValueError, match="role"):
            schemas._check_hint("x/v1", "k", {schemas.COLUMNS: [
                {"key": "a", "role": "mystery"}]})


@needs_node
class TestSectionsAreNamedAsQuestions:
    def test_a_declared_question_becomes_the_heading(self):
        out = _node(
            'const a = await import("./bga/viewer/app.js");'
            'console.log(JSON.stringify(a.heading("floors",'
            ' {"bga:question": "How much faster?", "bga:rail": "prove"})));')
        assert out["label"] == "How much faster?"
        assert out["subtitle"] == "floors", "the key stays visible as a subtitle"
        assert out["rail"] == "prove"

    def test_no_question_falls_back_to_the_key(self):
        """The mutation asserted both ways, as the acceptance asks."""
        out = _node(
            'const a = await import("./bga/viewer/app.js");'
            'console.log(JSON.stringify(a.heading("floors", {})));')
        assert out["label"] == "Floors"
        assert out["subtitle"] is None
        assert out["rail"] == "raw", "no rail means raw, never nowhere"

    def test_the_rendered_page_uses_the_declared_questions(self):
        out = _render(_report())
        headings = out["headings"]
        assert any(h["label"].endswith("?") for h in headings), headings
        for h in headings:
            if h["label"].endswith("?"):
                assert h["subtitle"], "a question heading keeps its key"


def _chapters():
    """The chapter table, read out of `chapters.js`.

    Read rather than restated: a copy here would pass while the page
    grouped by something else entirely, which is `UX-235`'s defect in a
    different file."""
    source = pathlib.Path("bga/viewer/chapters.js").read_text(encoding="utf-8")
    table = source.split("export const CHAPTERS = [", 1)[1].split("\n];", 1)[0]
    found = re.findall(r'id:\s*"([a-z]+)",\s*\n\s*title:\s*"([^"]+)"', table)
    assert len(found) >= 6, f"read {found} out of chapters.js"
    return found


def _chapter_titles():
    return [title for _, title in _chapters()] + ["Everything else"]


def _chapter_ids():
    return [key for key, _ in _chapters()] + ["more"]


@needs_node
class TestTheRailGroupsTheContents:
    def test_the_toc_renders_groups_in_chapter_order(self):
        """`UX-286` replaced the rail's five groups with the document's
        own chapters. The claim is unchanged - the contents is grouped,
        in a declared order - but it is now the *page's* grouping, so
        the list and the document cannot describe different reports."""
        out = _render(_report())
        rails = out["toc_rails"]
        assert rails, "the contents has no groups"
        titles = _chapter_titles()
        order = [title for title in titles if title in rails]
        assert rails == order, f"{rails} is not chapter order"

    def test_every_rendered_section_is_in_exactly_one_group(self):
        out = _render(_report())
        linked = [entry["key"] for entry in out["toc_links"]]
        assert len(linked) == len(set(linked)), "a section is in two groups"
        assert set(linked) == set(out["sections"]), (
            "the contents and the page disagree about what was rendered")

    def test_a_section_lands_in_a_chapter_and_never_nowhere(self):
        """Not nowhere - the acceptance names this case. `UX-286` keeps
        it and sharpens it: the fallback is no longer a bucket called
        `raw` but the chapter the section's published `bga:rail` names,
        and "Everything else" holds nothing on a real run."""
        out = _render(_report())
        ids = _chapter_ids()
        by_key = {e["key"]: e["rail"] for e in out["toc_links"]}
        for key, chapter in by_key.items():
            assert chapter in ids, (key, chapter)
            assert chapter != "more", (
                f"{key} is in no chapter; it fell through to Everything else")


@needs_node
class TestInvestigationIsOneClickAway:
    def test_a_path_box_popover_is_read_from_the_published_entry(self):
        """The acceptance's phrasing: a popover reading recomputed
        values has no fixture to pass, because every line is checked
        against the payload."""
        run = REAL if os.path.isdir(REAL) else GOLDEN
        payload = _report(run)
        out = _render(payload)
        detail = payload["signals"]["critical_path_detail"]
        by_uid = {e["element_uid"]: e for e in detail}
        assert out["popovers"], "no path box carried a popover"
        for box in out["popovers"]:
            entry = by_uid[box["element"]]
            assert box["text"].startswith(entry["element_uid"])
            share = f"{entry['share_of_path'] * 100:.1f}% of the path"
            assert share in box["text"], (share, box["text"])

    def test_a_declared_element_column_gives_every_row_an_inspect(self):
        """Per table, not in aggregate. A page-wide count is green as
        long as *one* declaration survives anywhere - measured: with
        `signals`' three declarations deleted, a whole-page count still
        passed on `headline.top_actions` alone. What the item promises
        is that a table which declares the role gets the affordance, so
        that is what is asserted, table by table.
        """
        out = _render(_report())
        declared = [t for t in out["tables"] if t["element_column"]]
        assert declared, "no rendered table declared an element column"
        for table in declared:
            assert table["inspect"] == table["rows"], table
        for table in out["tables"]:
            if not table["element_column"]:
                assert table["inspect"] == 0, table

    def test_the_element_tables_the_report_is_about_are_among_them(self):
        """`signals.critical_path_detail` is the list of elements the
        whole report argues about; before this item it rendered as a
        `<pre>` of raw JSON nested in a definition list, so nothing in
        it was sortable, filterable or one click from anywhere."""
        out = _render(_report())
        by_key = {t["key"]: t for t in out["tables"]}
        for key in ("critical_path_detail", "optimization_horizon",
                    "latent_heavies", "top_actions"):
            assert key in by_key, sorted(by_key)
            assert by_key[key]["element_column"] == "element_uid", by_key[key]
            assert by_key[key]["inspect"] == by_key[key]["rows"] > 0

    def test_removing_the_declaration_removes_the_buttons_quietly(self):
        """The acceptance's mutation: no declaration → no buttons, and
        nothing errors."""
        out = _node(
            'const a = await import("./bga/viewer/app.js");'
            'console.log(JSON.stringify({'
            '  declared: a.elementColumn([{key: "element_uid", role: "element"}]),'
            '  undeclared: a.elementColumn([{key: "element_uid"}]) }));')
        assert out["declared"] == "element_uid"
        assert out["undeclared"] is None

    def test_every_sql_block_carries_its_exact_text_to_copy(self):
        out = _node(
            'const q = await import("./bga/viewer/questions.js");'
            'const make = (t, a = {}, ...c) => ({ tagName: t, attrs: {...a},'
            '  children: [], textContent: c.join(""),'
            '  setAttribute(k, v) { this.attrs[k] = v; },'
            '  getAttribute(k) { return this.attrs[k] ?? null; },'
            '  addEventListener() {}, append(...x) {'
            '    for (const y of x) if (y) this.children.push(y); } });'
            'const found = [];'
            '(function walk(n) { if (!n) return;'
            '  if (n.attrs && n.attrs["data-copy"]) found.push(n.attrs["data-copy"]);'
            '  (n.children ?? []).forEach(walk); })(q.renderQuestions(make));'
            'console.log(JSON.stringify({ copies: found,'
            '  sql: q.QUESTIONS.map((x) => q.renderedSql(x)) }));')
        assert out["copies"], "no SQL block offered a copy"
        # Set-wise, because the page groups the blocks by category and
        # declaration order is not render order. Both directions: no
        # block without a copy, and no copy carrying anything but a
        # block's exact text.
        assert sorted(out["copies"]) == sorted(out["sql"]), (
            "the copy text is not the block's exact SQL")

    def test_the_top_n_preset_narrows_without_lying_about_the_total(self):
        out = _node(_TOP_N)
        assert out["shown"] == 10
        assert out["badge"] == "10 of 40", out["badge"]
        assert out["visible"] == 10

    def test_the_preset_offers_only_declared_quantity_columns(self):
        out = _node(
            'const t = await import("./bga/viewer/tables.js");'
            'console.log(JSON.stringify(t.presetColumns(['
            '  {key: "element_uid"}, {key: "duration_us", quantity: "duration_us"}'
            '])));')
        assert out == ["duration_us"]

    def test_blast_chips_come_from_the_published_ranking(self):
        out = _node(_CHIPS % json.dumps(["a.bst", "b.bst", "c.bst"]))
        assert out["chips"] == ["a.bst", "b.bst", "c.bst"]

    def test_an_empty_ranking_yields_no_chips(self):
        """The acceptance's mutation - not invented examples."""
        out = _node(_CHIPS % json.dumps([]))
        assert out["chips"] == []


@needs_node
class TestTheWallOfQuestionsFolds:
    def test_one_details_per_category_and_every_query_still_in_the_dom(self):
        """`UX-209` item 4, both halves. The fold is worth nothing if it
        costs the reader Ctrl-F, so the SQL text is asserted present -
        `<details>` hides pixels, not the DOM."""
        out = _node(
            'const q = await import("./bga/viewer/questions.js");'
            'const make = (t, a = {}, ...c) => ({ tagName: t, attrs: {...a},'
            '  children: [], textContent: c.join(""),'
            '  setAttribute(k, v) { this.attrs[k] = v; },'
            '  getAttribute(k) { return this.attrs[k] ?? null; },'
            '  addEventListener() {}, append(...x) {'
            '    for (const y of x) if (y) this.children.push(y); } });'
            'const root = q.renderQuestions(make);'
            'const all = (n, p, f = []) => { if (!n) return f;'
            '  if (p(n)) f.push(n); (n.children ?? []).forEach((c) => all(c, p, f));'
            '  return f; };'
            'const text = (n) => (n.textContent ?? "")'
            '  + (n.children ?? []).map(text).join("");'
            'console.log(JSON.stringify({'
            '  folds: all(root, (n) => n.tagName === "details").length,'
            '  open: all(root, (n) => n.tagName === "details")'
            '    .filter((n) => n.attrs.open).length,'
            '  categories: q.CATEGORIES.length,'
            '  text: text(root) }));')
        assert out["folds"] == out["categories"], out
        assert out["open"] == 0, "the fold opens itself"
        rendered = out["text"]
        sql = _node('const q = await import("./bga/viewer/questions.js");'
                    "console.log(JSON.stringify("
                    "q.QUESTIONS.map((x) => q.renderedSql(x))));")
        for query in sql:
            assert query in rendered, query[:60]


@needs_node
class TestTheLongExplanationsMoveBehindAFold:
    """`UX-209` item 5. Out of Scope says nothing may leave the page, so
    both halves are asserted on the *rendered* node - a source scrape
    reads the same words whichever branch produced them, which is how
    the first version of this guard stayed green while the caption was
    replaced by the paragraph it was meant to retire."""

    def test_the_trend_caption_is_the_declared_one_line_summary(self):
        out = _node(_SHIM + _TREND_PROBE)
        assert out["caption"] == ["3 snapshots · 2 not measurements"], out
        assert len(out["folded"]) == 1, out["folded"]
        assert "they are on disk, so they are on the chart" in out["folded"][0]
        assert "failed" in out["folded"][0] and "interrupted" in out["folded"][0]

    def test_the_band_caption_states_the_answer_and_folds_the_rest(self):
        out = _node(_SHIM + _BAND_PROBE)
        assert out["caption"], out
        assert out["caption"][0].endswith("so compare declines to call it."), (
            out["caption"])
        assert len(out["caption"][0]) < 160, "still a paragraph"
        assert len(out["folded"]) == 1, out["folded"]
        assert "Why this is not a regression" in out["folded"][0]
        assert "UX-170 calls this the disputed region" in out["folded"][0]


_SHIM = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;

function make(tag) {
  const node = _makeNode(tag);
  return node;
}
globalThis.document = { createElement: make, createElementNS: (_n, t) => make(t),
                        getElementById: () => null };
"""

_HARNESS = _SHIM + """
const app = await import("./bga/viewer/app.js");
const nav = await import("./bga/viewer/nav.js");
const { readFileSync } = await import("node:fs");
const [payloadPath, schemaPath] = %s;
const payload = JSON.parse(readFileSync(payloadPath, "utf8"));
const schema = JSON.parse(readFileSync(schemaPath, "utf8"));

const root = make("div");
app.render(payload, schema, root);

function all(node, pred) {
  const found = [];
  (function walk(n) { if (!n) return; if (pred(n)) found.push(n);
    (n.children ?? []).forEach(walk); })(node);
  return found;
}
const text = (n) => (n.textContent ?? "")
  + (n.children ?? []).map(text).join("");

const sections = all(root, (n) => n.attrs["data-section"])
  .map((n) => n.attrs["data-section"]);

const headings = all(root, (n) => n.tagName === "h2").map((n) => {
  const key = n.children.find((c) => c.className === "section-key muted");
  // The heading's *own* text, not the concatenation of its subtree: a
  // real DOM's `textContent` includes the `section-key` child, so
  // `label` used to read "Which capture is this?run_instance"
  // (`UX-264`).
  const own = n.children.filter((c) => c !== key)
    .map((c) => c.textContent).join("") || n._text;
  return { label: own, subtitle: key ? key.textContent : null };
});

const contents = nav.toc(root, { document: globalThis.document });
const tocRails = contents
  ? all(contents, (n) => n.className === "toc-rail").map((n) => n.textContent)
  : [];
const tocLinks = contents
  ? all(contents, (n) => n.attrs["data-toc"])
      .map((n) => ({ key: n.attrs["data-toc"], rail: n.attrs["data-rail"] }))
  : [];

const chain = (await import("./bga/viewer/views.js")).renderCriticalPath(payload);
const popovers = chain
  ? all(chain, (n) => n.attrs["data-popover"])
      .map((n) => ({ element: n.attrs["data-element"],
                     text: n.attrs["data-popover"] }))
  : [];

console.log(JSON.stringify({
  sections, headings, toc_rails: tocRails, toc_links: tocLinks, popovers,
  inspect_rows: all(root, (n) => n.className === "inspect").length,
  // This table's own body rows and its own Inspect anchors.
  //
  // `n.querySelectorAll("tbody tr")` counts one too many for a *nested*
  // table: CSS descendant matching is not scoped to the element the
  // query was called on, so the inner header row matches `tbody tr`
  // through the **outer** table's tbody. Measured in Chromium and in
  // the shim, which agree exactly - an inner table with 1 header row
  // and 3 body rows answers 4 to `inner.querySelectorAll("tbody tr")`
  // in both. `UX-283` is what surfaced it, by declaring an element
  // column on a nested table for the first time.
  tables: all(root, (n) => n.tagName === "table").map((n) => {
    const own = (child) => {
      let at = child.parentNode;
      while (at && at !== n) {
        if (at.tagName === "table") return false;
        at = at.parentNode;
      }
      return at === n;
    };
    return {
      key: n.attrs["data-table"],
      element_column: n.attrs["data-element-column"] ?? null,
      // A body row of *this* table: its parent is a `tbody` and that
      // tbody's parent is this table. The selector alone cannot say so.
      rows: n.querySelectorAll("tr").filter(
        (r) => r.parentNode?.tagName === "tbody"
               && r.parentNode.parentNode === n).length,
      inspect: all(n, (c) => c.className === "inspect").filter(own).length,
    };
  }),
}));
"""

_TOP_N = _SHIM + """
const app = await import("./bga/viewer/app.js");
const tables = await import("./bga/viewer/tables.js");
const rows = Array.from({length: 40}, (_, i) => ({
  element_uid: `e-${i}.bst`, duration_us: (i + 1) * 100000 }));
const hint = { "bga:columns": [
  { key: "element_uid", title: "Element", role: "element" },
  { key: "duration_us", title: "Duration", quantity: "duration_us" } ] };
const section = app.renderTable("elements", rows, hint);
const table = section.children.find((c) => c.tagName === "table");
const shown = tables.applyTopN(table, "duration_us", 10);
const visible = table.querySelectorAll("tbody tr").filter((tr) => !tr.hidden).length;
console.log(JSON.stringify({ shown, visible,
  badge: tables.badgeText(shown, rows.length) }));
"""

_CHIPS = """
const views = await import("./bga/viewer/views.js");
const make = (t, a = {}, ...c) => ({ tagName: t, attrs: {...a}, children: [],
  textContent: c.join(""), setAttribute(k, v) { this.attrs[k] = v; },
  getAttribute(k) { return this.attrs[k] ?? null; },
  addEventListener() {}, append(...x) {
    for (const y of x) if (y) this.children.push(y); } });
const node = views.blastChips(
  { signals: { top_blast_radius: %s } }, () => {}, make);
const chips = node
  ? node.children.filter((c) => c.attrs["data-element"])
      .map((c) => c.attrs["data-element"]) : [];
console.log(JSON.stringify({ chips }));
"""


_PROBE_TAIL = """
const all = (n, p, f = []) => { if (!n) return f; if (p(n)) f.push(n);
  (n.children ?? []).forEach((c) => all(c, p, f)); return f; };
const text = (n) => (n.textContent ?? "")
  + (n.children ?? []).map(text).join("");
console.log(JSON.stringify({
  caption: all(node, (n) => n.className === "muted" && n.tagName === "p")
    .map((n) => n.textContent),
  folded: all(node, (n) => n.tagName === "details").map(text),
}));
"""

_TREND_PROBE = """
const views = await import("./bga/viewer/views.js");
const rows = [
  { run_id: "a", total_duration_us: 100, incomplete_reason: null },
  { run_id: "b", total_duration_us: 120, incomplete_reason: "failed" },
  { run_id: "c", total_duration_us: 110, incomplete_reason: "interrupted" },
];
const node = views.renderTrend({ snapshots: rows });
""" + _PROBE_TAIL

# The disputed shape `UX-170` names: the set's own high edge sits
# outside the band its scatter produced, and the candidate lands in
# between.
_BAND_PROBE = """
const views = await import("./bga/viewer/views.js");
const node = views.renderBand({
  baseline_band: { low_us: 99, high_us: 101, median_us: 100,
                   observed_low_us: 100, observed_high_us: 200,
                   edges_outside_band: 1 },
  candidate: { total_duration_us: 150 },
});
""" + _PROBE_TAIL


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
