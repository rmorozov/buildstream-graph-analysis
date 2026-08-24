"""UX-226: what happened to this element since last time.

The loop ends on a question the tool could not answer:

    I spent an afternoon on core.bst. Did it work?

Everything needed was on disk — the store holds every snapshot,
`bga compare` judges a pair, the trend draws the set — and all three
answer for the **whole run**. Measured before this: `store/v1`'s rows
carried `total_duration_us`, `cache_hit_rate`, `bytes` and
`verdict_kind`, and nothing per element. The trend was a whole-run trend
because that was all the store published.

Two decisions these guards exist to hold:

* **the slice is written at capture time, not derived at read time.**
  `UX-203` established that the store is rebuilt on *every* `bga view`,
  for every snapshot; a row that needed an analysis would put N full
  analyses in front of a page load.
* **absence is stated, never drawn.** A snapshot from before this has
  `elements: null`; a snapshot where the element was not worth watching
  has it missing from a list that exists. Those are different facts and
  the reader is told which.
"""
import json
import os
import shutil
import subprocess

import pytest

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN = os.path.join(REPO, "tests", "fixtures", "golden", "mixed_task_kinds")

_SHIM = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;

function make(tag) {
  const node = _makeNode(tag);
  return node;
}
globalThis.document = { createElement: make, createElementNS: (_n, t) => make(t),
                        createTextNode: (t) => ({ nodeType: 3, textContent: String(t),
                                                  attrs: {}, children: [] }),
                        getElementById: () => null };
const all = (n, p, f = []) => { if (!n) return f; if (p(n)) f.push(n);
  (n.children ?? []).forEach((c) => all(c, p, f)); return f; };
const text = (n) => (n.children ?? []).reduce(
  (acc, c) => acc + text(c), n.textContent ?? "");
"""


def _js(body):
    result = subprocess.run([node, "--input-type=module", "-e", _SHIM + body],
                            capture_output=True, text=True, cwd=REPO, timeout=60)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _store(*rows):
    return {"schema": "store/v1", "snapshots": list(rows)}


def _snapshot(stamp, elements, verdict="improved"):
    return {"stamp": stamp, "verdict_kind": verdict, "elements": elements}


def _element(uid, duration, on_path=True):
    return {"element_uid": uid, "duration_us": duration,
            "share_of_path": 0.5 if on_path else None,
            "on_critical_path": on_path}


class TestTheSliceIsWrittenAtCaptureTime:

    @pytest.fixture
    def written(self, tmp_path):
        from tools.bga_snapshot import read_element_slice, write_element_slice

        snapshot = tmp_path / "20260101T000000Z"
        snapshot.mkdir()
        shutil.copytree(GOLDEN, snapshot / "run")
        os.remove(snapshot / "run" / "expected_output.json")
        written = write_element_slice(str(snapshot), str(snapshot / "run"))
        return written, read_element_slice(str(snapshot))

    def test_it_lands_on_disk_and_reads_back(self, written):
        write, read = written
        assert write is not None
        assert read == write

    def test_it_carries_the_runs_critical_path(self, written):
        write, _ = written
        uids = [row["element_uid"] for row in write["elements"]]
        assert uids == ["base.bst", "lib.bst", "app.bst"]

    def test_each_row_has_a_published_duration_and_share(self, written):
        write, _ = written
        for row in write["elements"]:
            assert isinstance(row["duration_us"], int)
            assert row["on_critical_path"] is True
            assert 0 < row["share_of_path"] <= 1

    def test_the_bound_is_stated_in_the_slice(self, written):
        from tools.bga_snapshot import SLICE_ELEMENTS_MAX
        write, _ = written
        assert write["bounded_at"] == SLICE_ELEMENTS_MAX
        assert len(write["elements"]) <= SLICE_ELEMENTS_MAX

    def test_a_run_that_cannot_be_analyzed_yields_no_slice(self, tmp_path):
        """A slice sits on top of a capture that already succeeded, and
        must never be the thing that fails a snapshot."""
        from tools.bga_snapshot import read_element_slice, write_element_slice

        snapshot = tmp_path / "broken"
        (snapshot / "run").mkdir(parents=True)
        (snapshot / "run" / "graph.json").write_text("{ not json")
        assert write_element_slice(str(snapshot), str(snapshot / "run")) is None
        assert read_element_slice(str(snapshot)) is None

    def test_reading_is_one_small_file_and_not_an_analysis(self):
        """The `UX-203` constraint, asserted against the source: the
        store is rebuilt on every page load, for every snapshot."""
        source = open(os.path.join(REPO, "tools", "bga_snapshot.py"),
                      encoding="utf-8").read()
        body = source.split("def read_element_slice", 1)[1].split("\ndef ", 1)[0]
        for banned in ("analyze(", "BuildEfficiencyAnalyzer"):
            assert banned not in body, (
                f"read_element_slice must not {banned} - it runs once per "
                f"snapshot on every bga view")


@needs_node
class TestTheHistoryIsDrawnFromPublishedValues:

    def test_a_falling_series_draws_its_points(self):
        store = _store(
            _snapshot("a", [_element("core.bst", 12100000)]),
            _snapshot("b", [_element("core.bst", 10500000)]),
            _snapshot("c", [_element("core.bst", 9400000)]),
        )
        out = _js('''
          const { renderElementHistory } = await import("./bga/viewer/views.js");
          const block = renderElementHistory(%s, "core.bst");
          const spark = all(block, (n) => n.attrs["data-role"] === "sparkline")[0];
          console.log(JSON.stringify({
            history: block.attrs["data-history"],
            points: block.attrs["data-points"],
            values: spark ? spark.attrs["data-values"] : null,
            sentence: text(all(block,
              (n) => n.attrs["data-role"] === "history-sentence")[0]),
          }));
        ''' % json.dumps(store))
        assert out["history"] == "present"
        assert out["points"] == "3"
        assert out["values"] == "12100000,10500000,9400000"
        assert out["sentence"] == "12.1 s → 9.4 s over 3 runs."

    def test_the_points_are_the_payloads_and_not_one_value_repeated(self):
        """The mutation this task names: derive the sparkline from the
        current run's value repeated, and the falling fixture flattens."""
        store = _store(
            _snapshot("a", [_element("core.bst", 12100000)]),
            _snapshot("b", [_element("core.bst", 9400000)]),
        )
        out = _js('''
          const { elementHistory } = await import("./bga/viewer/views.js");
          console.log(JSON.stringify(
            elementHistory(%s, "core.bst").series.map((p) => p.duration_us)));
        ''' % json.dumps(store))
        assert out == [12100000, 9400000]
        assert len(set(out)) > 1, "the fixture must actually fall"

    def test_one_run_is_stated_as_one_run(self):
        store = _store(_snapshot("a", [_element("core.bst", 5000000)]))
        out = _js('''
          const { renderElementHistory } = await import("./bga/viewer/views.js");
          const block = renderElementHistory(%s, "core.bst");
          console.log(JSON.stringify(text(all(block,
            (n) => n.attrs["data-role"] === "history-sentence")[0])));
        ''' % json.dumps(store))
        assert out == "5.0 s in one recorded run."

    def test_leaving_the_critical_path_is_named(self):
        store = _store(
            _snapshot("first", [_element("core.bst", 12000000, on_path=True)]),
            _snapshot("second", [_element("core.bst", 3000000, on_path=False)]),
        )
        out = _js('''
          const { renderElementHistory } = await import("./bga/viewer/views.js");
          const block = renderElementHistory(%s, "core.bst");
          console.log(JSON.stringify(text(all(block,
            (n) => n.attrs["data-role"] === "history-sentence")[0])));
        ''' % json.dumps(store))
        assert "Off the critical path since second." in out

    def test_each_point_carries_the_verdict_shape_from_the_schema(self):
        """UX-212's rule, and the first draft of this broke it.

        The shape must come from the *schema*, not from a second map in
        JavaScript - `UX-214` is the standing reason a vocabulary kept
        twice is a vocabulary waiting to diverge. Passed the real
        `store/v1` schema here, so the assertion is against the contract
        rather than against a literal.
        """
        from bga import schemas

        store = _store(
            _snapshot("a", [_element("core.bst", 10)], verdict="regressed"),
            _snapshot("b", [_element("core.bst", 8)], verdict="improved"),
        )
        out = _js('''
          const { renderElementHistory } = await import("./bga/viewer/views.js");
          const block = renderElementHistory(%s, "core.bst", %s);
          console.log(JSON.stringify(all(block,
            (n) => n.attrs["data-marker"]).map((n) => n.attrs["data-marker"])));
        ''' % (json.dumps(store), json.dumps(schemas.schema(schemas.STORE))))
        assert out == [schemas.VERDICT_MARKERS["regressed"],
                       schemas.VERDICT_MARKERS["improved"]]

    def test_without_a_schema_every_point_is_a_plain_circle(self):
        """Not a guessed shape: a page with no contract to read draws
        the neutral one rather than inventing a vocabulary."""
        store = _store(_snapshot("a", [_element("core.bst", 10)],
                                 verdict="regressed"))
        out = _js('''
          const { renderElementHistory } = await import("./bga/viewer/views.js");
          const block = renderElementHistory(%s, "core.bst");
          console.log(JSON.stringify(all(block,
            (n) => n.attrs["data-marker"]).map((n) => n.attrs["data-marker"])));
        ''' % json.dumps(store))
        assert out == ["circle"]


@needs_node
class TestAbsenceIsStatedNeverDrawn:

    def test_an_element_with_no_history_says_so(self):
        store = _store(_snapshot("a", [_element("other.bst", 100)]))
        out = _js('''
          const { renderElementHistory } = await import("./bga/viewer/views.js");
          const block = renderElementHistory(%s, "core.bst");
          console.log(JSON.stringify({
            history: block.attrs["data-history"],
            points: block.attrs["data-points"],
            spark: all(block, (n) => n.attrs["data-role"] === "sparkline").length,
            text: text(block),
          }));
        ''' % json.dumps(store))
        assert out["history"] == "none"
        assert out["points"] == "0"
        assert out["spark"] == 0, "a point at zero is not an absence"
        assert "No history for this element" in out["text"]

    def test_a_store_written_before_this_says_which_absence_it_is(self):
        """`elements: null` and `elements: []` are different facts."""
        old = _store({"stamp": "a", "verdict_kind": "improved", "elements": None})
        analyzed = _store(_snapshot("a", []))
        out = _js('''
          const { renderElementHistory } = await import("./bga/viewer/views.js");
          console.log(JSON.stringify({
            old: text(renderElementHistory(%s, "core.bst")),
            analyzed: text(renderElementHistory(%s, "core.bst")),
          }));
        ''' % (json.dumps(old), json.dumps(analyzed)))
        assert "captured before per-element history was recorded" in out["old"]
        assert "has not been on the critical path" in out["analyzed"]
        assert out["old"] != out["analyzed"]

    def test_a_pre_existing_store_renders_without_an_error(self):
        """The acceptance's last clause."""
        out = _js('''
          const { renderElementHistory } = await import("./bga/viewer/views.js");
          const block = renderElementHistory(
            { schema: "store/v1", snapshots: [
              { stamp: "a", total_duration_us: 1, bytes: 2 },
              { stamp: "b", total_duration_us: 2, bytes: 3 }] }, "core.bst");
          console.log(JSON.stringify({ history: block.attrs["data-history"],
                                       text: text(block) }));
        ''')
        assert out["history"] == "none"
        assert "captured before per-element history" in out["text"]

    def test_no_store_at_all_is_not_an_error(self):
        out = _js('''
          const { renderElementHistory } = await import("./bga/viewer/views.js");
          console.log(JSON.stringify(
            renderElementHistory(null, "core.bst").attrs["data-history"]));
        ''')
        assert out == "none"


class TestTheStoreDeclaresIt:

    def test_the_snapshot_rows_declare_elements(self):
        from bga import schemas
        items = (schemas.schema(schemas.STORE)["properties"]["snapshots"]
                 ["items"]["properties"])
        assert "elements" in items, sorted(items)
        assert set(items) >= {"total_duration_us", "cache_hit_rate", "bytes"}

    def test_the_slice_declares_an_element_column(self):
        from bga import schemas
        elements = (schemas.schema(schemas.STORE)["properties"]["snapshots"]
                    ["items"]["properties"]["elements"])
        roles = [column.get("role") for column in elements[schemas.COLUMNS]]
        assert "element" in roles

    def test_the_share_says_why_it_can_be_absent(self):
        """Zero would read as "on the path and costing nothing"."""
        from bga import schemas
        sentence = schemas.description(
            schemas.STORE, "snapshots[].elements[].share_of_path")
        assert "not on it" in sentence, sentence

    def test_null_and_empty_are_documented_as_different(self):
        """The two absences the drawing keeps apart."""
        from bga import schemas
        sentence = schemas.description(schemas.STORE, "snapshots[].elements")
        assert "null" in sentence and "empty list" in sentence, sentence
