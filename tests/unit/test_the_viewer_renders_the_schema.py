"""UX-193: `bga view` renders the schema, not the report.

Field feedback, round 21: *"we are on the verge of necessity for making
a viewer."*

Direction 7's rule is what these guards are about: **the published JSON
is the entire interface**. Two properties follow, and both are tested
here rather than asserted in prose:

1. Anything the viewer shows must first exist in the published schema -
   so the text renderer, CI and every external consumer get it too.
2. The page renders the *schema*, so a new field appears with **zero
   viewer changes**. That is the discriminating test: a synthetic field
   with hints is added to a payload and must render, with `app.js`
   untouched and asserted untouched.

The JavaScript is exercised through Node where it is available and
through its own structure where it is not, so CI needs no browser.
"""
import json
import os
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.request

import pytest

from bga import schemas

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"
APP_JS = "bga/viewer/app.js"

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")



def _package_data_for(package):
    """`[tool.setuptools.package-data]`'s entry for `package`.

    `tomllib` is stdlib only from **3.11**, and this project supports
    3.9 (`requires-python = ">=3.9"`, and CI's matrix runs 3.9-3.12).
    The first version of this guard imported it unconditionally, which
    would have failed two of the four matrix jobs - reproduced against
    the real `python3.10` on this machine, not inferred:

        $ python3.10 -c "import tomllib"
        ModuleNotFoundError: No module named 'tomllib'

    Not `importorskip`: skipping on 3.9 and 3.10 would make a packaging
    guard silent on two thirds of the interpreters, which is `UX-197`
    seam 6 written again. The fallback reads the one line this asserts
    on, so the guard runs everywhere.
    """
    text = open("pyproject.toml", encoding="utf-8").read()
    try:
        import tomllib
    except ImportError:                       # pragma: no cover - <3.11
        import ast
        import re

        match = re.search(rf'^"{package}"\s*=\s*(\[[^\]]*\])',
                          text, re.M)
        return ast.literal_eval(match.group(1)) if match else []
    data = tomllib.loads(text)
    return data["tool"]["setuptools"]["package-data"].get(package, [])

@pytest.fixture
def served():
    """A started server, torn down whatever the test does."""
    from tools.bga_view import serve

    made = []

    def start(run=GOLDEN, **kwargs):
        httpd, url = serve(run, **kwargs)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        made.append(httpd)
        return url

    yield start
    for httpd in made:
        httpd.shutdown()
        httpd.server_close()


def _get(url):
    with urllib.request.urlopen(url, timeout=10) as response:
        return response.status, response.headers, response.read()


class TestItServesTheSameJsonTheCliPrints:
    """The viewer and the terminal cannot be allowed to disagree about
    what a run says, which is why the payload comes through `main()`
    rather than from a second code path."""

    def test_the_report_is_the_cli_payload_field_for_field(self, served):
        url = served()
        _, _, body = _get(url + "report.json")
        served_payload = json.loads(body)

        printed = subprocess.run(
            [sys.executable, "-c",
             "from bga.cli import main; raise SystemExit(main("
             "['analyze', %r, '--format', 'json']))" % GOLDEN],
            capture_output=True, text=True, cwd=os.getcwd())
        assert served_payload == json.loads(printed.stdout)

    def test_the_schemas_are_served_too(self, served):
        _, _, body = _get(served() + "schemas.json")
        document = json.loads(body)
        assert set(document) == set(schemas.names())
        assert document[schemas.ANALYZE]["properties"]["schema"]["const"] == \
            schemas.ANALYZE


class TestTheServerIsLocalAndNarrow:
    def test_it_binds_loopback_only(self):
        from tools.bga_view import serve

        httpd, _ = serve(GOLDEN)
        try:
            assert httpd.server_address[0] == "127.0.0.1", (
                f"bound to {httpd.server_address[0]} - reachable off this "
                f"machine")
        finally:
            httpd.server_close()

    @pytest.mark.parametrize("path", [
        "../../../etc/passwd",
        "run/trace.json",          # a real file in the run, not in the table
        "run-context.json",
        "",                        # handled: index.html
    ])
    def test_only_the_table_is_reachable(self, served, path):
        url = served()
        try:
            status, _, _ = _get(url + path)
        except urllib.error.HTTPError as error:
            assert error.code == 404, error.code
            return
        assert path == "", f"{path!r} was served with {status}"

    def test_there_is_no_directory_listing(self, served):
        with pytest.raises(urllib.error.HTTPError) as caught:
            _get(served() + "run/")
        assert caught.value.code == 404

    def test_it_answers_no_write_method(self, served):
        url = served()
        request = urllib.request.Request(url + "report.json", method="POST",
                                         data=b"{}")
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=10)
        assert caught.value.code in (404, 501), caught.value.code

    def test_the_assets_carry_a_content_security_policy(self, served):
        _, headers, _ = _get(served() + "index.html")
        assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
        assert headers["X-Content-Type-Options"] == "nosniff"


class TestTheViewHints:
    """View-hints v1: the schema says what a number *is*, so a renderer
    - this one or someone else's - does not have to guess."""

    def test_every_hint_names_a_key_the_document_declares(self):
        for name in schemas.names():
            document = schemas.schema(name)
            for key, sub in document["properties"].items():
                for hint in (schemas.QUANTITY, schemas.SEVERITY,
                             schemas.COLUMNS, schemas.DIRECTION):
                    if hint in sub:
                        assert key in document["properties"], key

    def test_quantities_come_from_the_closed_set(self):
        for name in schemas.names():
            for key, sub in schemas.schema(name)["properties"].items():
                if schemas.QUANTITY in sub:
                    assert sub[schemas.QUANTITY] in schemas.QUANTITIES, \
                        f"{name}.{key}"

    def test_a_typo_in_a_quantity_is_refused(self):
        with pytest.raises(ValueError, match="furlongs"):
            schemas._document("x/v1", "x", {"a": "number"}, "d",
                              hints={"a": {schemas.QUANTITY: "furlongs"}})

    def test_a_hint_on_a_key_that_does_not_exist_is_refused(self):
        """Silent otherwise: the renderer would simply never see it."""
        with pytest.raises(KeyError, match="nosuchkey"):
            schemas._document("x/v1", "x", {"a": "number"}, "d",
                              hints={"nosuchkey": {schemas.QUANTITY: "bytes"}})

    def test_the_findings_array_is_marked_as_findings(self):
        analyze = schemas.schema(schemas.ANALYZE)["properties"]
        assert analyze["findings"][schemas.SEVERITY] == "severity"

    def test_the_deltas_say_which_way_is_better(self):
        compare = schemas.schema(schemas.COMPARE)["properties"]
        assert compare["deltas"][schemas.DIRECTION] == "lower_is_better"

    def test_hints_do_not_change_what_validates(self):
        """`UX-190`'s guard must be unaffected: JSON Schema ignores
        keywords it does not know, and these are annotations."""
        jsonschema = pytest.importorskip("jsonschema")

        printed = subprocess.run(
            [sys.executable, "-c",
             "from bga.cli import main; raise SystemExit(main("
             "['analyze', %r, '--format', 'json']))" % GOLDEN],
            capture_output=True, text=True, cwd=os.getcwd())
        jsonschema.validate(json.loads(printed.stdout),
                            schemas.schema(schemas.ANALYZE))


@needs_node
class TestThePageRendersFromTheSchema:
    """Driven through Node against the real `app.js`, so what is
    asserted is the shipped renderer rather than a description of it."""

    def _render(self, payload, schema):
        script = _RENDER_HARNESS % (json.dumps(payload), json.dumps(schema))
        result = subprocess.run([node, "--input-type=module", "-e", script],
                                capture_output=True, text=True,
                                cwd=os.getcwd(), timeout=60)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def test_a_findings_array_renders_as_findings_with_severity(self):
        rendered = self._render(
            {"schema": schemas.ANALYZE, "run_id": "r",
             "total_duration_us": 1_500_000, "section": None,
             "findings": [{"id": "x", "severity": "critical",
                           "title": "The build is serialised",
                           "detail": ["one"], "elements": ["a.bst"]}]},
            schemas.schema(schemas.ANALYZE))
        assert "critical" in rendered["severities"]
        assert "The build is serialised" in rendered["text"]

    def test_a_duration_hint_makes_the_number_human(self):
        rendered = self._render(
            {"schema": schemas.ANALYZE, "run_id": "r", "section": None,
             "total_duration_us": 5_400_000_000},
            schemas.schema(schemas.ANALYZE))
        assert "1.5 h" in rendered["text"], rendered["text"]

    def test_a_delta_is_coloured_by_the_direction_hint(self):
        rendered = self._render(
            {"schema": schemas.COMPARE, "deltas": {"total_duration_us": -900000,
                                                   "contention_us": 400000}},
            schemas.schema(schemas.COMPARE))
        assert "better" in rendered["classes"], rendered["classes"]
        assert "worse" in rendered["classes"]

    def test_a_refusal_gets_visual_weight(self):
        rendered = self._render(
            {"schema": schemas.COMPARE,
             "verdict": "not comparable (trace_spine differs)"},
            schemas.schema(schemas.COMPARE))
        assert "refused" in rendered["classes"]
        assert "not comparable" in rendered["text"]

    def test_a_new_field_renders_with_no_viewer_change(self):
        """**The discriminating test.** A field that did not exist when
        `app.js` was written, carrying nothing but its hints, has to
        render - otherwise "the page renders the schema" is a slogan.

        `app.js` is hashed before and after to make the claim literal.
        """
        before = open(APP_JS, "rb").read()

        schema = schemas.schema(schemas.ANALYZE)
        schema["properties"]["cache_efficiency"] = {
            "type": ["object", "null"], schemas.QUANTITY: "share"}
        schema["properties"]["hotspots"] = {
            "type": ["array", "null"],
            # Deliberately neither key order nor alphabetical order.
            # The first draft used ["element", "seconds"], which is
            # both - so ignoring the hint entirely left this green.
            schemas.COLUMNS: ["seconds", "element"]}

        rendered = self._render(
            {"schema": schemas.ANALYZE, "run_id": "r", "section": None,
             "total_duration_us": 10,
             "cache_efficiency": {"pull_share": 0.42},
             "hotspots": [{"element": "slow.bst", "seconds": 61.0}]},
            schema)

        assert "cache_efficiency" in rendered["sections"], rendered["sections"]
        assert "hotspots" in rendered["sections"]
        assert "42.0%" in rendered["text"], rendered["text"]
        assert "slow.bst" in rendered["text"]
        # Column order came from the hint - not from key order
        # (element, seconds) and not from sorting (element, seconds).
        assert rendered["columns"]["hotspots"] == ["seconds", "element"]

        assert open(APP_JS, "rb").read() == before, (
            "the renderer was edited to make this pass, which is the "
            "opposite of what it asserts")

    def test_an_unhinted_field_still_renders(self):
        """The other half: the schemas deliberately do not describe
        every nested shape, so absence of a hint must degrade, not
        erase."""
        rendered = self._render(
            {"schema": schemas.ANALYZE, "run_id": "r", "section": None,
             "total_duration_us": 1, "mystery": {"alpha": 3}},
            schemas.schema(schemas.ANALYZE))
        assert "mystery" in rendered["sections"]
        assert "Alpha" in rendered["text"]



class TestTheSchemaDescribesWhatRealRunsEmit:
    """`UX-193` found `pipeline_overhead` and `timestamp_agreement`
    undeclared, by serving a **real** capture of `examples/06`.

    Both are present on every run with Plane 1 wrapper data and absent
    from `tests/fixtures/golden/`, so `UX-190`'s round-trip guard - which
    validates the golden fixture - had never seen either. That is
    `UX-179`'s shape once more: a guard that passes on the fixture it was
    built for.

    So this guard does not list the two keys. It asserts the general
    property, by enriching a run until it emits the wrapper-derived
    sections and then checking that *every* key the analyzer produced is
    a key the schema declares. The next undeclared field fails here
    rather than reaching a consumer.
    """

    @staticmethod
    def _enriched_run(tmp_path):
        """The golden run plus the run-context fields a real capture has."""
        run = tmp_path / "run"
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
        context_path = run / "run-context.json"
        context = json.loads(context_path.read_text())
        context["pipeline_overhead"] = [
            {"phase": "Loading elements", "elapsed_us": 3000},
            {"phase": "Resolving elements", "elapsed_us": 1023000},
        ]
        context_path.write_text(json.dumps(context))
        return str(run)

    def _analyze(self, run):
        result = subprocess.run(
            [sys.executable, "-c",
             "from bga.cli import main; raise SystemExit(main("
             "['analyze', %r, '--format', 'json']))" % run],
            capture_output=True, text=True, cwd=os.getcwd())
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def test_the_enriched_run_really_does_emit_more(self, tmp_path):
        """The precondition: without this the check below is vacuous,
        which is exactly how the gap survived in the first place."""
        plain = set(self._analyze(GOLDEN))
        enriched = set(self._analyze(self._enriched_run(tmp_path)))
        assert enriched - plain, (
            "the enriched run emits nothing the golden one does not - "
            "this fixture no longer exercises the wrapper-derived keys")

    def test_every_key_a_real_run_emits_is_declared(self, tmp_path):
        declared = set(schemas.schema(schemas.ANALYZE)["properties"])
        emitted = set(self._analyze(self._enriched_run(tmp_path)))
        undeclared = sorted(emitted - declared)
        assert not undeclared, (
            f"the analyzer emits {undeclared}, which the schema does not "
            f"declare - a consumer reading the schema would not know they "
            f"exist, and a rename would be silent")

class TestTheViewerShipsNoToolchain:
    """Direction 7's rule, made checkable."""

    def test_every_file_is_plain_checked_in_source(self):
        """The first draft pinned the literal list `["app.js",
        "index.html", "style.css"]`, which `UX-194` immediately broke by
        adding three more legitimate files. The property that matters is
        not the count - it is that nothing here is generated, minified,
        or fetched at build time."""
        files = sorted(os.listdir("bga/viewer"))
        assert files, "the viewer has no files"
        for name in files:
            assert os.path.splitext(name)[1] in (".html", ".js", ".css"), name
            assert not name.endswith((".min.js", ".min.css", ".map")), (
                f"{name} looks generated; every file here is source a "
                f"human edits")
            text = open(os.path.join("bga/viewer", name), encoding="utf-8").read()
            longest = max((len(line) for line in text.splitlines()), default=0)
            assert longest < 400, (
                f"{name} has a {longest}-character line - that is what "
                f"bundled output looks like")

    def test_nothing_is_fetched_from_a_cdn(self):
        # `http://www.w3.org/2000/svg` is an XML *namespace identifier*,
        # required by `createElementNS` and never dereferenced by
        # anything. `UX-196` added the first SVG and this guard flagged
        # it - correct instinct, wrong rule.
        inert = ("http://127.0.0.1", "http://www.w3.org/2000/svg")
        for name in os.listdir("bga/viewer"):
            text = open(os.path.join("bga/viewer", name), encoding="utf-8").read()
            for allowed in inert:
                text = text.replace(allowed, "")
            assert "http://" not in text, name
            assert "cdn." not in text, name
            assert "unpkg" not in text and "jsdelivr" not in text, name

    def test_there_is_no_package_json_anywhere_near_it(self):
        assert not os.path.exists("bga/viewer/package.json")
        assert not os.path.exists("package.json")


    def test_the_assets_are_found_through_the_package_not_the_checkout(self):
        """`ASSET_DIR` must be right in both install shapes.

        Measured, not argued: `UX-193` computed it as "two directories
        up, then `bga/viewer`", which is correct from a checkout and
        wrong from a wheel - `UX-94` installs this directory as
        `bga._tools`, so two up is `site-packages` and the answer became
        `site-packages/bga/bga/viewer`. Every asset 404'd, and no test
        that runs from a checkout could have noticed.
        """
        import bga
        import tools.bga_view as view

        expected = os.path.join(os.path.dirname(os.path.abspath(bga.__file__)),
                                "viewer")
        assert view.ASSET_DIR == expected
        for name in view.ASSETS:
            assert os.path.exists(os.path.join(view.ASSET_DIR, name)), name

        # The value alone cannot catch this - falsifying showed the
        # broken derivation gives the *same answer from a checkout*,
        # which is exactly why it shipped. So the derivation is what is
        # asserted: the path must come from the `bga` package's own
        # location, not from walking up from this file.
        source = open("tools/bga_view.py", encoding="utf-8").read()
        derivation = source.split("ASSET_DIR")[0].rsplit("def _asset_dir", 1)
        assert len(derivation) == 2, "ASSET_DIR is no longer derived in one place"
        assert "bga.__file__" in derivation[1], (
            "ASSET_DIR is not derived from the bga package's location - "
            "packaged as bga._tools, walking up from this file lands in "
            "site-packages and every asset 404s")
        assert "dirname(os.path.dirname" not in derivation[1].replace(" ", ""), (
            "walking up from __file__ is the derivation that broke")

    def test_the_viewer_ships_in_the_wheel(self):
        """The other half: the files have to be *in* the package.

        They are html, css and ES modules, so setuptools skips them
        unless `package-data` names them - and it did not, so an
        installed `bga view` served a 404 for every asset.
        """
        patterns = _package_data_for("bga")
        for name in sorted(os.listdir("bga/viewer")):
            suffix = os.path.splitext(name)[1]
            assert any(pattern.endswith(f"*{suffix}") for pattern in patterns), (
                f"{name} is not covered by package-data {patterns} - it would "
                f"not ship, and `bga view` would 404 on it")

    def test_the_tool_modules_import_each_other_relatively(self):
        """`UX-94`'s rule, which this round broke twice: packaged, this
        directory is `bga._tools` and a top-level `tools` does not
        exist, so `from tools.x import y` is an ImportError in every
        installed shape."""
        import re

        source = open("tools/bga_view.py", encoding="utf-8").read()
        offenders = [line.strip() for line in source.splitlines()
                     if re.match(r"\s*(from|import)\s+tools\.", line)]
        assert not offenders, offenders

class TestTheCommandLine:
    def test_no_browser_prints_the_url_and_opens_nothing(self, tmp_path):
        """Asserted by patching `webbrowser.open` in-process: a test
        that actually launched a browser would be a test nobody can run
        twice."""
        import tools.bga_view as view

        opened = []
        real = view.webbrowser.open
        view.webbrowser.open = lambda url: opened.append(url)
        try:
            httpd, url = view.serve(GOLDEN)
            httpd.server_close()
            assert url.startswith("http://127.0.0.1:")
            assert opened == []
        finally:
            view.webbrowser.open = real

    def test_a_bad_run_is_an_error_not_a_traceback(self, tmp_path):
        result = subprocess.run(
            [sys.executable, "-c",
             "from bga.cli import main; raise SystemExit(main("
             "['view', %r, '--no-browser']))" % str(tmp_path / "nope")],
            capture_output=True, text=True, cwd=os.getcwd(), timeout=60)
        assert result.returncode == 2, result.stdout
        assert "Traceback" not in result.stderr
        assert "Error:" in result.stderr

    def test_the_help_is_under_the_cap(self):
        result = subprocess.run(
            [sys.executable, "-c",
             "from bga.cli import main; raise SystemExit(main(['view','--help']))"],
            capture_output=True, text=True, cwd=os.getcwd())
        assert len(result.stdout.splitlines()) <= 45, result.stdout


# A DOM shim rather than a browser: `app.js` uses `document.createElement`
# and nothing else, so ~40 lines of stand-in run the real renderer under
# plain Node. CI gets no browser dependency and the assertions are still
# about the shipped file.
_RENDER_HARNESS = """
const payload = %s, schema = %s;

function makeNode(tag) {
  const node = {
    // `nodeType` is what `app.js`'s `el()` checks to tell a node from a
    // string. Without it every child stringified to "[object Object]" -
    // a shim defect, and worth keeping in mind when reading a failure
    // here: the renderer is the shipped file, the DOM is not.
    nodeType: 1,
    tagName: tag, className: "", children: [], attrs: {}, text: "",
    style: {}, dataset: {},
    setAttribute(k, v) { this.attrs[k] = String(v); },
    removeAttribute(k) { delete this.attrs[k]; },
    getAttribute(k) { return this.attrs[k] ?? null; },
    addEventListener() {},
    append(...items) {
      for (const item of items) {
        if (item === null || item === undefined) continue;
        if (typeof item === "string") this.text += item;
        else this.children.push(item);
      }
    },
    replaceChildren(...items) { this.children = []; this.text = ""; this.append(...items); },
    querySelector() { return makeNode("tbody"); },
    querySelectorAll() { return []; },
  };
  return node;
}
globalThis.document = {
  createElement: makeNode,
  getElementById: () => makeNode("div"),
};

const mod = await import("./bga/viewer/app.js");
const root = makeNode("main");
mod.render(payload, schema, root);

const sections = [], classes = new Set(), severities = new Set();
const columns = {};
let text = "";
(function walk(node) {
  text += " " + node.text;
  if (node.className) String(node.className).split(/\\s+/).forEach(c => c && classes.add(c));
  if (node.attrs["data-section"]) sections.push(node.attrs["data-section"]);
  if (node.attrs["data-severity"]) severities.add(node.attrs["data-severity"]);
  if (node.attrs["data-table"]) {
    columns[node.attrs["data-table"]] = [];
    (function heads(n) {
      if (n.tagName === "th" && n.attrs["data-column"])
        columns[node.attrs["data-table"]].push(n.attrs["data-column"]);
      n.children.forEach(heads);
    })(node);
  }
  node.children.forEach(walk);
})(root);

console.log(JSON.stringify({
  sections, classes: [...classes], severities: [...severities], columns, text,
}));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
