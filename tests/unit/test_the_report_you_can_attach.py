"""UX-195: the same page, as one file.

Direction 7's second delivery mode. `bga view --export report.html`
inlines the run's payloads into the static page and writes one
self-contained artifact — no port, no server, no network — for a CI
artifact, for "send me your report", and for the archive a pruned
snapshot leaves behind.

**The property under test is that it is the same page.** Not a second
renderer, not a simplified one: the identical `app.js`, reading its
payloads inline instead of over http, decided in one place. So the
guards below render the *exported file* through the same Node harness
`UX-193` renders the served payload with, and compare.

Measured, on the two runs the item names:

    1,202-element synthetic   report.json   816,573 B
    golden run                report.json    14,797 B
    the page itself (7 files)               39,119 B

At 1,202 elements the payload is 21x the page, which is Direction 7's
own test of whether the viewer stayed thin.
"""
import base64
import gzip
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

_WRAPPED = """[wrapper][2026-08-21 12:00:00,000] INFO: Executing command: bst build all.bst
[wrapper][2026-08-21 12:00:00,100] INFO: [00:00:00][aaaaaaaa][   build:work-a.bst] START Building
[wrapper][2026-08-21 12:00:03,100] INFO: [00:00:03][aaaaaaaa][   build:work-a.bst] SUCCESS Building
[wrapper][2026-08-21 12:00:03,200] INFO: Return code: 0
"""
_RAW = """START pid=101 ppid=1 ts=1000.000000 element=work-a.bst cmd=cc -c main.c
END pid=101 ppid=1 ts=1002.500000 element=work-a.bst cmd=cc -c main.c
"""


# UX-287: two bounds, because an export has two halves that grow for
# different reasons. Each is a measurement plus headroom, and each says
# which run it is a bound *for*.
#
#   the page      171,388 B on every run (modules 152,424 + css 17,135
#                 + 1,829 of scaffolding) - grows with source
#   golden   (4)  261,604 B   -> of which data 90,216
#   macro_micro (11) 299,695 B -> of which data 128,307
#
# The synthetic 1,202-element run exports at ~1.07 MB and is not
# committed (`UX-189`), so it is measured in the Outcome rather than
# guarded here.
#
# **The bounds moved once, and the split is what made that legible.**
# Round 39's viewer work (`UX-279`, `UX-280`, `UX-283`, `UX-284`,
# `UX-289`, `UX-292`) took the page 162,909 -> 171,388 B: modules
# +7,788, stylesheet +691. The data grew +2,653 in the same round, all
# of it schema descriptions the page shows as tooltips - which the
# companion guard below proves is documents rather than payload.
#
# That attribution is the difference between a bound that moves on a
# measurement and one that rises whenever it is exceeded, which is what
# `UX-287` was filed about. The page budget did *not* redden - it had
# 612 B left - and the totals did, which is the split working: source
# growth shows in every total and cannot hide behind content.
PAGE_BUDGET_B = 180_000
MACRO_MICRO = "tests/fixtures/macro_micro/run"
COMMITTED_EXPORTS = [
    # `UX-299` moved both of these by ~300 B: `run.json` now publishes
    # `trace_inline_max_bytes`, the one threshold that decides both
    # whether this file inlines the trace and whether the served page
    # copies it through itself. A number the page must not keep a second
    # copy of, so it travels in the payload.
    ("golden", GOLDEN, 276_000),                       #  274,917 B
    # `UX-297` moved this one by 385 B before that: the two-plane run
    # publishes `plane2_coverage.source`, which says which shape of
    # Plane 2 report served its numbers and what that costs to open. A
    # sentence a reader of a gigabyte capture needs, and the bound is
    # restated rather than the sentence trimmed to fit a number nobody
    # argued.
    # `UX-300` moved both again, by ~2.6 KB: the embedded
    # `store-aggregate/v1` now carries what the store weighs - a
    # `snapshot_bytes` distribution per host class and a document-level
    # total - which is the page telling a reader what their disk holds
    # without their having to go and ask a second command.
    ("macro_micro", MACRO_MICRO, 316_000),             #  314,096 B
]


def _embedded(path):
    """The bytes of documents the page carries, so the rest is the page."""
    text = pathlib.Path(path).read_text(encoding="utf-8")
    return sum(len(found) for found in re.findall(
        r'<script type="application/json"[^>]*>(.*?)</script>', text, re.S))


@pytest.fixture
def snapshot(tmp_path):
    snap = tmp_path / "20260821T120000Z"
    snap.mkdir()
    (snap / "build.log").write_text(_WRAPPED)
    shutil.copytree(GOLDEN, snap / "run")
    os.remove(snap / "run" / "expected_output.json")
    with gzip.open(snap / "plane2.log.gz", "wt") as handle:
        handle.write(_RAW)
    return snap


@pytest.fixture
def exported(snapshot, tmp_path):
    from tools.bga_view import export

    path = tmp_path / "report.html"
    result = export(str(snapshot / "run"), str(path))
    return path, result


class TestItNeedsNothingButItself:
    def test_no_reference_reaches_the_network_or_the_filesystem(self, exported):
        """An export opens from a download folder, a CI artifact viewer,
        or an email attachment. Anything it would have to fetch is
        simply not there."""
        text = exported[0].read_text()
        for url in re.findall(r'(?:src|href)="([^"]+)"', text):
            assert url.startswith(("#", "data:", "mailto:")) or \
                url.startswith("https://ui.perfetto.dev"), (
                    f"{url} would have to be fetched")

    def test_no_relative_module_import_survives(self, exported):
        """A browser refuses a relative `import` over `file://`, so the
        two modules are concatenated into one inline block."""
        text = exported[0].read_text()
        assert not re.search(r"""import\s.*from\s+["']\./""", text)
        assert "openInPerfetto" in text, "perfetto.js was not inlined"
        assert "renderFindings" in text, "app.js was not inlined"

    def test_every_payload_is_present_as_a_block(self, exported):
        found = set(re.findall(r'id="bga-([a-z]+)"', exported[0].read_text()))
        assert {"report", "schemas", "run"} <= found, found

    def test_the_blocks_are_named_the_way_the_loader_looks_them_up(
            self, exported):
        """The one that bit: `payloads()` keys by *url*
        (`report.json`), the loader looks up by *name* (`bga-report`).
        Getting it wrong is silent — the block is simply never found and
        the page falls through to `fetch`, which works when served and
        fails on `file://`, so the export looks fine everywhere except
        where it is used."""
        text = exported[0].read_text()
        assert 'id="bga-report"' in text
        assert 'id="bga-report.json"' not in text

    def test_a_payload_containing_a_script_tag_cannot_end_the_block(
            self, snapshot, tmp_path, monkeypatch):
        """An element named after an html file is not hypothetical, and
        a `</script>` anywhere in a payload would end the block early -
        everything after it becoming markup.

        Injected at the `payloads` seam. The first draft set `run_id` in
        `run-context.json` and asserted on the output; `run_id` is
        *computed*, so the string never reached the payload and the test
        passed without exercising the escape at all.
        """
        import tools.bga_view as view

        monkeypatch.setattr(view, "payloads", lambda run: {
            "report.json": {"schema": "analyze/v2", "section": None,
                            "run_id": "a</script><script>alert(1)</script>",
                            "total_duration_us": 1}})
        path = tmp_path / "r.html"
        view.export(str(snapshot / "run"), str(path))
        text = path.read_text()

        assert "alert(1)</script>" not in text, "the block was ended early"
        assert "<\\/script>" in text, "nothing was escaped"
        block = re.search(r'id="bga-report">(.*?)</script>', text)
        assert json.loads(block.group(1).replace("<\\/", "</"))["run_id"] == \
            "a</script><script>alert(1)</script>", "the payload was mangled"


@needs_node
class TestItRendersTheSameThing:
    """The exported file, parsed and rendered by the same harness the
    served payload goes through."""

    def _render_export(self, path):
        script = _EXPORT_HARNESS % json.dumps(str(path))
        result = subprocess.run([node, "--input-type=module", "-e", script],
                                capture_output=True, text=True,
                                cwd=os.getcwd(), timeout=90)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def test_it_renders_the_runs_findings_and_sections(self, exported):
        rendered = self._render_export(exported[0])
        assert "findings" in rendered["sections"], rendered["sections"]
        assert rendered["severities"], "no severity reached the page"

    def test_it_renders_what_the_served_page_renders(self, exported, snapshot):
        """Same payload, same schema, same renderer - so same output.
        A second renderer would show up here as a difference."""
        from tools.bga_view import payloads, schemas_payload

        run = str(snapshot / "run")
        payload = payloads(run)["report.json"]
        schema = schemas_payload()[payload["schema"]]

        served = subprocess.run(
            [node, "--input-type=module", "-e",
             _SERVED_HARNESS % (json.dumps(payload), json.dumps(schema))],
            capture_output=True, text=True, cwd=os.getcwd(), timeout=90)
        assert served.returncode == 0, served.stderr

        assert self._render_export(exported[0])["sections"] == \
            json.loads(served.stdout)["sections"]


class TestTheTimeline:
    def test_it_travels_inline_as_a_data_url(self, exported):
        """So the Perfetto button works from `file://`: `fetch` handles
        `data:` URLs, and the handshake never needed a server."""
        text = exported[0].read_text()
        block = re.search(r'id="bga-trace">"(data:application/gzip;base64,'
                          r'([A-Za-z0-9+/=]+))"', text)
        assert block, "no inline trace"
        # `UX-298`: a Perfetto trace, not a JSON array. `Trace` is
        # `repeated TracePacket packet = 1`, so the first byte of the
        # stream is that field's tag - `(1 << 3) | 2`.
        assert gzip.decompress(base64.b64decode(block.group(2)))[:1] == b"\x0a"
        assert exported[1]["has_timeline"] is True

    def test_a_run_without_one_says_so_rather_than_shipping_a_dead_button(
            self, tmp_path):
        from tools.bga_view import export

        run = tmp_path / "run"
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
        result = export(str(run), str(tmp_path / "r.html"))

        assert result["has_timeline"] is False
        assert result["omitted"] and "no raw Plane 2 log" in result["omitted"]
        run_block = re.search(r'id="bga-run">(.*?)</script>',
                              (tmp_path / "r.html").read_text())
        assert json.loads(run_block.group(1))["has_timeline"] is False

    def test_an_oversized_timeline_is_dropped_and_the_reason_recorded(
            self, snapshot, tmp_path, monkeypatch):
        """Recorded, not silent: the report is still worth having, and
        a user who wanted the timeline needs to know where it went."""
        import tools.bga_view as view

        monkeypatch.setattr(view, "TRACE_BUDGET_B", 8)
        result = view.export(str(snapshot / "run"), str(tmp_path / "r.html"))
        assert result["has_timeline"] is False
        assert "ceiling" in result["omitted"]
        assert 'id="bga-trace"' not in (tmp_path / "r.html").read_text()


class TestTheSizeDiscipline:
    """Direction 7's rule is a *ratio*: "the data, not the page, is what
    an export weighs". It was guarded by an absolute byte ceiling, and
    across rounds 23, 24 and 25 that ceiling was crossed three times by
    ordinary feature work - the decision panel, the rails, the table
    tools, the view state, the element object - and raised twice.

    A number that moves every time a feature lands is not measuring the
    feature; it is measuring the calendar. So the third time, what is
    measured changed instead of the number:

    1. **Composition** - the page *is* the checked-in modules plus the
       stylesheet and nothing else. This is the one that can tell 6 KB
       of new feature from 6 KB of vendored library, which is what the
       rule was always about.
    2. **The ratio, on a report big enough for it to mean something** -
       Direction 7's sentence as written.
    3. **A loose absolute backstop**, kept deliberately far above the
       current page so that crossing it means something structural
       happened rather than that a round landed.

    Measured today: eight modules at 85,579 B comment-stripped,
    `style.css` at 10,822 B, `index.html` at 1,433 B.
    """

    def test_the_page_is_a_backstop_away_from_where_it_is(self, exported):
        """The loose one, raised in round 26 and - deliberately - given
        the instrument it was standing in for.

        This number has now been crossed in rounds 23, 24, 25 and 26,
        and raised each time. UX-218 named that failure exactly: *a
        number that moves whenever a feature lands is measuring the
        calendar*. The reason it kept being raised is that its stated
        job - "crossing it means something structural happened rather
        than that a round landed" - was one it could not actually do. A
        byte count cannot tell a feature from a library.

        Measured when round 26 crossed it:

            page (data removed)   123,785 B
              modules             109,913 B
              style.css            12,552 B
              index.html            1,433 B
              accounted           123,898 B  = 100.1% of the page
            export total          184,934 B  = 2.20% of the 8 MiB budget

        Every byte is a checked-in module. Nothing crept in, the ratio
        guard still holds at 1,000 elements, and the export is a fortieth
        of what an attachment may weigh. So the backstop fired, someone
        looked, and the answer was "a round landed" - four times.

        Raised to 200,000 and joined by `test_no_module_looks_like_a
        _vendored_library` below, which checks the thing this number was
        a proxy for. If the absolute fires again it should be because
        that one is silent and something genuinely odd is happening.
        """
        html = open(exported[0], encoding="utf-8").read()
        # Every `<script type="application/json">` block and the trace
        # blob are *data*. What is left is the page.
        page = re.sub(r"<script[^>]*type=\"application/(json|octet-stream)\"[^>]*>"
                      r".*?</script>", "", html, flags=re.S)
        assert len(page) < 200_000, (
            f"the exported page is {len(page)} B with its data removed - "
            f"that is a structural change, not a feature. Check "
            f"`test_the_page_is_the_modules_and_nothing_else` and "
            f"`test_no_module_looks_like_a_vendored_library` first.")

    def test_no_module_looks_like_a_vendored_library(self):
        """What the byte ceiling was a proxy for, measured directly.

        Direction 7's rule is about what the page *is*, not how big it
        got. Hand-written modules are line-wrapped source with comments;
        vendored or minified code is not - it arrives as a small number
        of enormous lines and almost no comment. That difference is
        visible, and unlike a byte count it does not move when a feature
        lands.
        """
        import tools.bga_view as view

        offenders = []
        for name in view._module_order():
            source = open(os.path.join(view.ASSET_DIR, name),
                          encoding="utf-8").read()
            lines = source.splitlines() or [""]
            longest = max(len(line) for line in lines)
            commented = sum(1 for line in lines
                            if line.lstrip().startswith(("//", "/*", "*")))
            if longest > 400:
                offenders.append(f"{name}: a {longest}-character line")
            if len(source) > 4_000 and commented / len(lines) < 0.05:
                offenders.append(
                    f"{name}: {commented}/{len(lines)} commented lines")
        assert offenders == [], (
            f"these do not look like the hand-written modules this page is "
            f"supposed to be: {offenders}")

    def test_the_data_dwarfs_the_page_on_a_report_worth_measuring(
            self, tmp_path):
        """Direction 7's sentence, on a report the sentence is about.

        The small fixtures invert it and always did - on `examples/06`
        the data is 70,754 B against an 82,386 B page - which is a
        property of small reports, not of the viewer, and is why the
        absolute ceiling was the wrong instrument.

        Measured at the scale the rule names (1,000 elements, the
        figure Direction 7 quotes at 1,202): **691,401 B of data
        against a 97,488 B page, 7.1x**. The threshold is 4x rather
        than 7x so that ordinary growth does not trip it and a
        framework arriving does - a guard set at the measurement is a
        guard that fails on the next commit.
        """
        import tools.bga_view as view

        from tests.fixtures.topologies import linear_chain, write_run_dir

        run = write_run_dir(tmp_path, linear_chain(1000))
        out = tmp_path / "big.html"
        view.export(str(run), str(out))
        html = out.read_text(encoding="utf-8")
        page = re.sub(r"<script[^>]*type=\"application/(json|octet-stream)\"[^>]*>"
                      r".*?</script>", "", html, flags=re.S)
        data = len(html) - len(page)
        assert data > 4 * len(page), (
            f"{data} B of data against a {len(page)} B page - Direction 7's "
            f"rule is that the data is what an export weighs, and at this "
            f"scale it should not be close")

    def test_the_page_is_the_modules_and_nothing_else(self, exported):
        """What the ceiling is really guarding: that the page is the
        checked-in modules plus the stylesheet, and that nothing else
        crept into it. A ceiling alone cannot tell 4 KB of new feature
        from 4 KB of vendored library; this can.
        """
        import tools.bga_view as view

        html = open(exported[0], encoding="utf-8").read()
        page = re.sub(r"<script[^>]*type=\"application/(json|octet-stream)\"[^>]*>"
                      r".*?</script>", "", html, flags=re.S)
        accounted = sum(len(view._inline_module(name))
                        for name in view._module_order())
        accounted += len(view._uncommented_css(
            open(os.path.join(view.ASSET_DIR, "style.css"),
                 encoding="utf-8").read()))
        accounted += len(open(os.path.join(view.ASSET_DIR, "index.html"),
                              encoding="utf-8").read())
        # The export rewrites the page around those bytes, so an exact
        # equality would be asserting the glue. Anything the modules do
        # not account for is what this is looking for.
        assert len(page) - accounted < 4_000, (
            f"{len(page) - accounted} B of the page comes from neither "
            f"the modules nor the stylesheet")

    def test_the_page_itself_stays_within_its_budget(self, exported):
        """`UX-287`: the half of the size a run cannot change.

        The old backstop asserted a single constant against the golden
        export and had moved five times, always to accommodate the run
        it was measured against - a bound that rises whenever it is
        exceeded is a record, not a limit. Worse, it was measured on a
        **four-element** run, so it bounded the one quantity that barely
        varies while the quantity it was named for went unwatched.

        Measured across all three runs this repository can produce:

        ```text
        run             elements     bytes      data   modules     css   other
        golden                 4   261,604    90,216   152,424  17,135   1,829
        macro_micro           11   299,695   128,307   152,424  17,135   1,829
        ```

        The page is **171,388 B on every run**. That is the number a
        ceiling can honestly guard: it grows when *source* grows, and no
        amount of content can mask it. The totals below guard the other
        half, per fixture - so content can no longer hide behind the
        page, nor the page behind content.
        """
        page = exported[1]["bytes"] - _embedded(exported[0])
        assert page < PAGE_BUDGET_B, f"the page itself is {page} B"

    def test_the_page_costs_the_same_whatever_the_run(self, tmp_path):
        """What justifies splitting the bound in two. If the page's cost
        varied with the run, "the page" would not be a thing to bound
        separately and this whole structure would be wrong."""
        from tools.bga_view import export

        fixed = {}
        for label, run in (("golden", GOLDEN), ("macro_micro", MACRO_MICRO)):
            path = tmp_path / f"{label}.html"
            result = export(str(run), str(path))
            fixed[label] = result["bytes"] - _embedded(path)
        assert len(set(fixed.values())) == 1, (
            f"the page is not run-independent: {fixed}")

    @pytest.mark.parametrize("label,run,bound", COMMITTED_EXPORTS)
    def test_each_committed_run_exports_within_its_stated_bound(
            self, label, run, bound, tmp_path):
        """`UX-287`'s acceptance: the bound is asserted against a run
        whose size is representative, and it is stated *for that run*.

        **The decision the item asked for**, since the 11-element export
        is 288,404 B and the old ceiling was 260,000: the export is not
        too big. A self-contained HTML report at 288 KB - or at 1.04 MB
        for 1,202 elements - is well inside what a ticket or a mail
        client takes, and `tools/bga_view.py`'s own `EXPORT_BUDGET_B` of
        8 MiB is the limit that reflects the use. The old number was not
        a judgement about attachments; it was the size of a four-element
        run at the moment somebody wrote it down.
        """
        from tools.bga_view import export

        path = tmp_path / f"{label}.html"
        result = export(str(run), str(path))
        assert result["bytes"] < bound, (
            f"{label} exports {result['bytes']} B, over its stated {bound} B")
        assert result["over_budget"] is False

    def test_the_data_is_the_documents_and_the_schemas(self, exported):
        """The backstop's other half, and the one that actually
        discriminates: every byte of embedded data is a document the
        page renders. A ceiling cannot tell 10 KB of new contract from
        10 KB of embedded font; this can, and it is why raising the
        ceiling above is a measurement rather than an argument."""
        import json

        html = open(exported[0], encoding="utf-8").read()
        blocks = re.findall(
            r"<script[^>]*type=\"application/json\"[^>]*>(.*?)</script>",
            html, flags=re.S)
        assert blocks, "no data blocks - the export stopped embedding"
        for block in blocks:
            # Every one parses as JSON. A blob that is not a document
            # would land here as something else.
            json.loads(block)
        data = sum(len(block) for block in blocks)
        page = re.sub(r"<script[^>]*type=\"application/(json|octet-stream)\"[^>]*>"
                      r".*?</script>", "", html, flags=re.S)
        assert len(html) - len(page) - data < 4_000, (
            f"{len(html) - len(page) - data} B of embedded data is not one "
            f"of the JSON documents the page renders")

    def test_a_file_over_budget_is_reported_not_refused(
            self, snapshot, tmp_path, monkeypatch):
        import tools.bga_view as view

        monkeypatch.setattr(view, "EXPORT_BUDGET_B", 100)
        result = view.export(str(snapshot / "run"), str(tmp_path / "r.html"))
        assert result["over_budget"] is True
        assert os.path.exists(tmp_path / "r.html"), (
            "it refused to write a report the user asked for")


class TestTheCommandLine:
    def test_it_writes_the_file_and_says_where(self, snapshot, tmp_path):
        path = tmp_path / "out.html"
        result = subprocess.run(
            [sys.executable, "-c",
             "from bga.cli import main; raise SystemExit(main(%r))"
             % (["view", str(snapshot / "run"), "--export", str(path)],)],
            capture_output=True, text=True, cwd=os.getcwd(), timeout=120)
        assert result.returncode == 0, result.stderr
        assert path.exists()
        assert json.loads(result.stdout)["bytes"] == path.stat().st_size
        assert "needs no server" in result.stderr

    def test_it_never_starts_a_server(self, snapshot, tmp_path, monkeypatch):
        import tools.bga_view as view

        def refuse(*args, **kwargs):
            raise AssertionError("--export bound a port")

        monkeypatch.setattr(view.http.server, "ThreadingHTTPServer", refuse)
        monkeypatch.setattr(view.webbrowser, "open", refuse)
        assert view.main([str(snapshot / "run"), "--export",
                          str(tmp_path / "r.html")]) == 0


class TestTheCiWiring:
    def test_the_ci_docs_teach_attaching_it(self):
        text = open("docs/guides/ci-comment.md", encoding="utf-8").read()
        assert "--export" in text, (
            "the CI page posts the comment but never mentions the artifact")


_COMMON_SHIM = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;

function makeNode(tag) {
  const node = _makeNode(tag);
  return node;
}
function collect(root) {
  const sections = [], classes = new Set(), severities = new Set();
  let text = "";
  (function walk(node) {
    text += " " + node.text;
    if (node.className) String(node.className).split(/\\s+/).forEach(c => c && classes.add(c));
    if (node.attrs["data-section"]) sections.push(node.attrs["data-section"]);
    if (node.attrs["data-severity"]) severities.add(node.attrs["data-severity"]);
    node.children.forEach(walk);
  })(root);
  return { sections, classes: [...classes], severities: [...severities], text };
}
"""

# The export is run the way a browser runs it: its own inline module,
# its own inline JSON blocks, no filesystem beyond the one file.
_EXPORT_HARNESS = _COMMON_SHIM + """
import { readFileSync } from "node:fs";
const html = readFileSync(%s, "utf-8");

const blocks = {};
for (const m of html.matchAll(
    /<script type="application\\/json" id="bga-([a-z]+)">([\\s\\S]*?)<\\/script>/g)) {
  blocks[m[1]] = m[2].replace(/<\\\\\\//g, "</");
}
const nodes = {};
for (const name of Object.keys(blocks)) {
  const node = makeNode("script");
  node.textContent = blocks[name];
  nodes[`bga-${name}`] = node;
}
const root = makeNode("main");
nodes["report"] = root;

globalThis.document = {
  createElement: makeNode,
  getElementById: (id) => nodes[id] ?? makeNode("div"),
};
globalThis.fetch = () => { throw new Error("the export fetched something"); };

const source = html.match(
  /<script type="module">([\\s\\S]*?)<\\/script>/)[1];
const mod = await import(
  "data:text/javascript;base64," + Buffer.from(
    source + "\\nexport { render, inlined, load };").toString("base64"));

// Through `load`, not `inlined`: the first draft rendered
// `inlined("report")` directly, so deleting the inline-first branch
// from `load` entirely left every render guard green - the loading
// path was never on the wire. `fetch` above throws, so anything not
// answered inline fails here.
const payload = await mod.load("report");
const schemas = await mod.load("schemas");
mod.render(payload, schemas[payload.schema], root);
console.log(JSON.stringify(collect(root)));
"""

_SERVED_HARNESS = _COMMON_SHIM + """
const payload = %s, schema = %s;
globalThis.document = { createElement: makeNode, getElementById: () => makeNode("div") };
const mod = await import("./bga/viewer/app.js");
const root = makeNode("main");
mod.render(payload, schema, root);
console.log(JSON.stringify(collect(root)));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
