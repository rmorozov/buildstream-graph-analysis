"""UX-196: three views where a drawing says what sentences strain to.

Direction 7's second wave, on `UX-193`'s shell. The discipline is
unchanged: these render **published** payloads and draw only where the
generic table genuinely cannot say it — exactly two SVGs, no library
behind either, and nothing recomputed in the browser.

The view worth the drawing is the first one. `UX-170`'s **disputed
region** — a candidate outside the noise band but inside the range the
baseline runs themselves spanned — took a paragraph in prose and still
read like a paradox. Drawn, the marker lands *between* the strip's edge
and the dots' extent. The geometry assertion below is that sentence,
made checkable.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request

import pytest

from bga import schemas

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"
# `UX-337`: the sections used to be one file. They are three - the
# chapters `views.js` grew too long to hold moved to `element.js`
# and `decision.js` unchanged - and these clauses are about the
# *sections*, not about a filename, so they read all three. Reading
# only `views.js` would have quietly stopped seeing
# `renderElementHistory`, which is exactly the drawing the set
# below argues for.
SECTION_MODULES = ("views.js", "element.js", "decision.js")


def _sections_source():
    return "\n".join(
        open("bga/viewer/" + name, encoding="utf-8").read()
        for name in SECTION_MODULES)
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _store(tmp_path, stamps=("20260101T000000Z", "20260102T000000Z",
                             "20260103T000000Z")):
    (tmp_path / "project.conf").write_text("name: p\nmin-version: 2.0\n")
    for stamp in stamps:
        run = tmp_path / ".bga" / "runs" / stamp / "run"
        run.parent.mkdir(parents=True)
        shutil.copytree(GOLDEN, run)
        os.remove(run / "expected_output.json")
    return tmp_path


class TestStoreV1:
    """The one payload the views needed that did not exist."""

    def test_it_declares_itself_and_validates(self, tmp_path):
        jsonschema = pytest.importorskip("jsonschema")
        from tools.bga_snapshot import store_listing

        listing = store_listing(str(_store(tmp_path)))
        assert listing["schema"] == schemas.STORE
        jsonschema.validate(listing, schemas.schema(schemas.STORE))

    def test_it_carries_the_rows_the_trend_draws(self, tmp_path):
        from tools.bga_snapshot import store_listing

        listing = store_listing(str(_store(tmp_path)))
        assert listing["count"] == 3
        assert listing["total_bytes"] == sum(
            row["bytes"] for row in listing["snapshots"])
        aliases = [row["alias"] for row in listing["snapshots"]]
        assert aliases[-1] == "@last" and aliases[-2] == "@prev"
        assert aliases[0] is None

    def test_the_text_listing_derives_from_the_same_rows(self, tmp_path):
        """Not "looks similar" - the same function. A second walk of the
        store would be a second answer to what is on disk."""
        import tools.bga_snapshot as snapshot

        project = str(_store(tmp_path))
        listing = snapshot.store_listing(project)

        seen = {}
        real = snapshot.store_listing
        snapshot.store_listing = lambda p: seen.setdefault("called", real(p))
        try:
            buffer = io.StringIO()
            import contextlib
            with contextlib.redirect_stdout(buffer):
                snapshot._list(project)
        finally:
            snapshot.store_listing = real

        assert "called" in seen, "_list did not go through store_listing"
        for row in listing["snapshots"]:
            assert row["stamp"] in buffer.getvalue()

    def test_an_incomplete_snapshot_is_listed_not_hidden(self, tmp_path):
        """It occupies the disk the size warning is about."""
        from tools.bga_snapshot import store_listing

        project = _store(tmp_path, stamps=("20260101T000000Z",))
        context = (project / ".bga" / "runs" / "20260101T000000Z" / "run"
                   / "run-context.json")
        loaded = json.loads(context.read_text())
        loaded["build_outcome"] = {"interrupted": True}
        context.write_text(json.dumps(loaded))

        row = store_listing(str(project))["snapshots"][0]
        assert row["incomplete_reason"] == "interrupted"

    def test_the_cli_emits_it(self, tmp_path):
        result = subprocess.run(
            [sys.executable, "-c",
             "import os, sys; os.chdir(sys.argv[1])\n"
             "from bga.cli import main\n"
             "raise SystemExit(main(['snapshot', '--list', '--format', 'json']))",
             str(_store(tmp_path))],
            capture_output=True, text=True, cwd=os.getcwd())
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["schema"] == schemas.STORE


@needs_node
class TestTheBandDrawn:
    """The geometry, asserted from the data attributes the SVG carries."""

    def _geometry(self, compare):
        script = _HARNESS % ("bandGeometry", json.dumps(compare))
        result = subprocess.run([node, "--input-type=module", "-e", script],
                                capture_output=True, text=True,
                                cwd=os.getcwd(), timeout=60)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def test_the_disputed_region_puts_the_marker_between_edge_and_extent(self):
        """`UX-170`'s case, and the reason this drawing exists.

        Band 100-110s; the baseline runs actually ranged 95-118s; the
        candidate at 114s is **outside the band** and **inside the
        observed range**. The marker must sit past the strip's right
        edge and short of the observed extent's — which is the paradox,
        drawn.
        """
        geometry = self._geometry({
            "schema": schemas.COMPARE,
            "candidate": {"total_duration_us": 114_000_000},
            "baseline_band": {
                "band_low_us": 100_000_000, "band_high_us": 110_000_000,
                "observed_low_us": 95_000_000, "observed_high_us": 118_000_000,
                "runs": [95_000_000, 104_000_000, 118_000_000],
            },
        })
        assert geometry["disputed"] is True
        assert geometry["where"] == "outside the band, inside the observed range"

        band_right = geometry["band"]["x"] + geometry["band"]["width"]
        observed_right = geometry["observed"]["x"] + geometry["observed"]["width"]
        assert band_right < geometry["candidate"]["x"] < observed_right, (
            f"candidate at {geometry['candidate']['x']} is not between the "
            f"band edge {band_right} and the observed extent {observed_right}")

        # ...and everything drawn is actually on the canvas. Falsifying
        # showed the ordering above holds however the axis is chosen -
        # narrowing it to the band alone left the assertion green while
        # pushing the marker past the viewBox's right edge, which is a
        # drawing nobody can read.
        for name, value in (("candidate", geometry["candidate"]["x"]),
                            ("band left", geometry["band"]["x"]),
                            ("band right", band_right),
                            ("observed left", geometry["observed"]["x"]),
                            ("observed right", observed_right)):
            assert 0 <= value <= 100, f"{name} at {value} is off the canvas"

    def test_a_candidate_inside_the_band_is_not_disputed(self):
        geometry = self._geometry({
            "schema": schemas.COMPARE,
            "candidate": {"total_duration_us": 105_000_000},
            "baseline_band": {"band_low_us": 100_000_000,
                              "band_high_us": 110_000_000,
                              "observed_low_us": 95_000_000,
                              "observed_high_us": 118_000_000, "runs": []},
        })
        assert geometry["disputed"] is False
        assert geometry["where"] == "inside the band"
        band_right = geometry["band"]["x"] + geometry["band"]["width"]
        assert geometry["band"]["x"] <= geometry["candidate"]["x"] <= band_right

    def test_a_candidate_outside_both_says_so(self):
        geometry = self._geometry({
            "schema": schemas.COMPARE,
            "candidate": {"total_duration_us": 140_000_000},
            "baseline_band": {"band_low_us": 100_000_000,
                              "band_high_us": 110_000_000,
                              "observed_low_us": 95_000_000,
                              "observed_high_us": 118_000_000, "runs": []},
        })
        assert geometry["where"] == "outside both"
        assert geometry["disputed"] is False

    def test_a_compare_with_no_band_draws_nothing(self):
        """Half the compares in the world have no baseline set."""
        assert self._geometry({"schema": schemas.COMPARE,
                               "candidate": {"total_duration_us": 1}}) is None


@needs_node
class TestTheStoreTrend:
    def _render(self, store):
        script = _RENDER_HARNESS % ("renderTrend", json.dumps(store))
        result = subprocess.run([node, "--input-type=module", "-e", script],
                                capture_output=True, text=True,
                                cwd=os.getcwd(), timeout=60)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)

    def _store_doc(self, rows):
        return {"schema": schemas.STORE, "project": "/p", "count": len(rows),
                "total_bytes": sum(r["bytes"] for r in rows),
                "snapshots": rows}

    def test_failed_and_interrupted_snapshots_are_marked_distinctly(self):
        """Marked, not hidden: they are on the disk, so they are on the
        chart. A trend that quietly dropped them would answer the drift
        question with a curated subset."""
        rendered = self._render(self._store_doc([
            {"stamp": "a", "bytes": 100, "alias": None, "has_run": True,
             "incomplete_reason": None},
            {"stamp": "b", "bytes": 200, "alias": None, "has_run": True,
             "incomplete_reason": "failed"},
            {"stamp": "c", "bytes": 150, "alias": "@prev", "has_run": True,
             "incomplete_reason": "interrupted"},
            {"stamp": "d", "bytes": 300, "alias": "@last", "has_run": True,
             "incomplete_reason": None},
        ]))
        assert rendered["points"] == 4, "a snapshot was dropped from the chart"
        assert rendered["incomplete"] == {"b": "failed", "c": "interrupted"}
        assert "rect" in rendered["shapes"] and "circle" in rendered["shapes"], (
            "complete and incomplete snapshots draw the same shape")
        assert "The store (4 snapshots)" in rendered["text"]
        assert "failed" in rendered["text"] and "interrupted" in rendered["text"]

    def test_one_snapshot_is_not_a_trend(self):
        assert self._render(self._store_doc(
            [{"stamp": "a", "bytes": 1, "alias": "@last", "has_run": True,
              "incomplete_reason": None}])) == {"empty": True}


class TestTheBlastEndpoint:
    """Item 3, and the rule it is bound by: no viewer-side semantics."""

    @pytest.fixture
    def served(self, tmp_path):
        from tools.bga_view import serve

        project = _store(tmp_path, stamps=("20260101T000000Z",))
        run = project / ".bga" / "runs" / "20260101T000000Z" / "run"
        httpd, url = serve(str(run))
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        yield url, str(run)
        httpd.shutdown()
        httpd.server_close()

    def test_it_answers_what_the_cli_answers(self, served):
        """Digest-compared. A resolver of its own would be a second
        answer to which elements a change touches."""
        url, run = served
        target = "work-a.bst"
        served_answer = json.loads(urllib.request.urlopen(
            f"{url}blast.json?target={urllib.parse.quote(target)}").read())

        printed = subprocess.run(
            [sys.executable, "-c",
             "from bga.cli import main; raise SystemExit(main(%r))"
             % (["blast", target, run, "--no-cost", "-f", "json"],)],
            capture_output=True, text=True, cwd=os.getcwd())
        assert printed.returncode == 0, printed.stderr
        assert served_answer == json.loads(printed.stdout)

    def test_a_missing_target_is_a_refusal_not_a_traceback(self, served):
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(served[0] + "blast.json")
        assert caught.value.code == 400

    def test_an_absurd_target_is_bounded(self, served):
        with pytest.raises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(
                served[0] + "blast.json?target=" + "a" * 900)
        assert caught.value.code == 400

    def test_an_unresolvable_target_answers_rather_than_crashing(self, served):
        """`bga blast` is a question, not a gate - it always exits 0 and
        says what reading it used. The endpoint keeps that."""
        answer = json.loads(urllib.request.urlopen(
            served[0] + "blast.json?target=nothing-like-this").read())
        assert answer["schema"] == schemas.BLAST
        assert answer["element_exists"] is False


class TestTheViewsStayThin:
    # Direction 7's rule is "draw only where the generic table cannot
    # say it", and this guard used to hold a *count* of two. UX-226
    # added a third - a per-element sparkline - and a count can only be
    # bumped, which teaches nothing and is the same failure UX-218 found
    # in the page-size ceiling: a number that moves when a feature lands
    # is measuring the calendar.
    #
    # So the guard holds the **set**, by the function each drawing lives
    # in, with the reason beside it. A fourth still fails; adding one
    # means naming it here and saying what the table could not have said.
    DRAWINGS = {
        # A candidate's position between a noise band and the range the
        # baselines actually spanned. In prose this took a paragraph and
        # still read like a paradox (UX-170's disputed region).
        "renderBand",
        # A series of runs with a verdict shape per point. A table of
        # the same rows cannot show the shape of a drift.
        "renderTrend",
        # UX-226: one element's duration across the snapshots, beside
        # its sentence. Three rows of a table per element section, in a
        # report with hundreds of them, is not a thing anyone reads.
        "renderElementHistory",
    }

    def test_the_custom_drawings_are_the_ones_that_were_argued_for(self):
        """Direction 7's rule: draw only where the generic table cannot
        say it - held as a named set, not a count."""
        import re

        source = _sections_source()
        drawing_at = [m.start() for m in re.finditer(r'svg\("svg"', source)]
        functions = [(m.start(), m.group(1)) for m in
                     re.finditer(r"function\s+(\w+)", source)]
        found = set()
        for position in drawing_at:
            enclosing = [name for start, name in functions if start < position]
            assert enclosing, "a drawing outside any function"
            found.add(enclosing[-1])
        assert found == self.DRAWINGS, (
            f"the set of custom drawings changed: {found ^ self.DRAWINGS}. "
            f"Direction 7 allows a drawing where the generic table cannot "
            f"say it - name the new one in DRAWINGS above with the reason, "
            f"or use a table.")

    def test_no_library_and_no_arithmetic_beyond_layout(self):
        import re

        source = _sections_source()
        code = [line for line in source.splitlines()
                if not line.lstrip().startswith("//")]
        # No **library**: a bare specifier reaches outside this
        # repository, and a `../` one reaches outside the viewer. A
        # sibling module is neither - `UX-316` made this file import
        # `drawings.js` for the size scale, and the alternative was a
        # second copy of the scale in the file that had already written
        # `viewBox: "0 0 100 20"` out by hand, which is the defect §2a
        # exists to end. `drawings.js` imports nothing, so nothing
        # arrives behind it.
        imports = [line.strip() for line in code
                   if line.lstrip().startswith("import")]
        for line in imports:
            source_of = re.search(r'from\s+"([^"]+)"', line + " ".join(
                source.split(line, 1)[1].splitlines()[:3]))
            assert source_of, f"cannot read what this import names: {line}"
            named = source_of.group(1)
            assert named.startswith("./") and "/" not in named[2:], (
                f"views.js reached outside the viewer directory: {named}")
        # Strings and comments stripped first: the band's caption
        # legitimately contains the word "regression" (it is quoting what
        # compare declines to call the result), and the first draft of
        # this guard flagged its own explanation.
        bare = re.sub(r'"[^"\n]*"|\'[^\'\n]*\'|`[^`]*`|//[^\n]*', "", source)
        for word in ("percentile", "stddev", "regress", "quantile", "Math.sqrt"):
            assert word.lower() not in bare.lower(), (
                f"{word} in code suggests the page is recomputing the "
                f"analysis rather than rendering it")


_HARNESS = """
const mod = await import("./tests/viewer.mjs");
console.log(JSON.stringify(mod.%s(%s) ?? null));
"""

_RENDER_HARNESS = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;

function makeNode(tag, ns) {
  const node = _makeNode(tag);
  node.ns = ns ?? null;
  return node;
}
globalThis.document = {
  createElement: (t) => makeNode(t),
  createElementNS: (ns, t) => makeNode(t, ns),
  getElementById: () => makeNode("div"),
};
const mod = await import("./tests/viewer.mjs");
const out = mod.%s(%s);
if (!out) { console.log(JSON.stringify({ empty: true })); }
else {
  const shapes = new Set(), incomplete = {};
  let points = 0, text = "";
  (function walk(node) {
    text += " " + (node.text ?? "") + " " + (node.textContent ?? "");
    if (String(node.className).includes("trend-point")
        || String(node.attrs.class ?? "").includes("trend-point")) {
      points += 1;
      shapes.add(node.tagName);
      if (node.attrs["data-incomplete"])
        incomplete[node.attrs["data-stamp"]] = node.attrs["data-incomplete"];
    }
    (node.children ?? []).forEach(walk);
  })(out);
  console.log(JSON.stringify({ points, shapes: [...shapes], incomplete, text }));
}
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
