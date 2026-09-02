"""UX-201: the schema decides, all the way down.

The external review's P0, verified line by line in round 22 and
reproduced here before anything was changed. The viewer's rule — *the
schema determines what a field is* — held only at the **top level**.
Every nested value fell to `guessQuantity(key)` name-sniffing, and the
two systems demonstrably disagreed:

    peak_rss_bytes: 512   rendered "512 B"      (`_mb` guessed as bytes)
    cpu_pct: 42        rendered "4200.0%"    (`_pct` guessed as a 0..1 share)

Both measured against the shipped renderer. Same class, adjacent:
`renderFindings` hard-coded five field names against a `findings` the
schema declared as a bare array; `renderTable` decided numeric-ness by
sampling row values; and `verdictClass` string-matched the verdict
*sentence*, so rewording it would have silently restyled the banner.

**UX-220 moved these fixtures, and the reason matters.** The two
wrongnesses above were reproduced against `utilisation.peak_rss_bytes` and
`utilisation.cpu_pct` — and no code path has ever put either name in
that object. The renderer bug was real and these guards did catch it,
but they caught it on a shape the tool does not publish, which is why
`utilisation`'s twelve real members went unhinted for four rounds
without anything noticing. Same assertions now, against fields a run
actually emits: `correlate/v1`'s `memory_envelope.host_memory_bytes`
for the memory case and `utilisation.useful_share` for the fraction
case (`UX-341` retired the `megabytes` and `percent` spellings; the
name-sniffing reproduction below still uses the old names, because that
is what it is about).
The name-sniffing reproduction below keeps the original two names
deliberately — it asserts what `guessQuantity` does with a *name*, and
needs no schema node at all.
"""
import json
import os
import shutil
import subprocess

import pytest

from bga import schemas

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _js(script):
    result = subprocess.run([node, "--input-type=module", "-e", script],
                            capture_output=True, text=True, cwd=os.getcwd(),
                            timeout=60)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@needs_node
class TestTheTwoLiveWrongnesses:
    """Fixtures now, per the acceptance."""

    def test_a_nested_byte_count_renders_as_one(self):
        out = _js('''
          const { quantity, quantityFor, childNode } =
            await import("./tests/viewer.mjs");
          const envelope = %s;
          console.log(JSON.stringify(
            quantity(512 * 1024 * 1024, quantityFor(
              childNode(envelope, "host_memory_bytes"), "host_memory_bytes"))));
        ''' % json.dumps(
            schemas.schema(schemas.CORRELATE)["properties"]["memory_envelope"]))
        assert out == "512.0 MiB", out

    def test_a_declared_share_is_shown_as_a_percentage(self):
        """`UX-341` retired `percent`: the payload carries 0..1 and the
        renderer is what turns it into a percentage. The wrongness this
        clause was written for - a 0..100 value multiplied by 100 again
        - is now unreachable by construction, because there is no
        0..100 member left to declare."""
        out = _js('''
          const { quantity, quantityFor, childNode } =
            await import("./tests/viewer.mjs");
          const util = %s;
          console.log(JSON.stringify(quantity(0.42, quantityFor(
            childNode(util, "useful_share"), "useful_share"))));
        ''' % json.dumps(
            schemas.schema(schemas.ANALYZE)["properties"]["utilisation"]))
        assert out == "42.0%", out

    def test_without_the_schema_node_the_guess_is_still_wrong(self):
        """The reproduction, kept verbatim: this is what every nested
        value got before the recursive walk, and it is why the walk
        exists. It asserts on *names*, so it needs no schema node and
        was untouched when UX-220 moved the fixtures above."""
        out = _js('''
          const { quantity, guessQuantity } = await import("./tests/viewer.mjs");
          console.log(JSON.stringify([
            quantity(512, guessQuantity("peak_rss_bytes")),
            quantity(42, guessQuantity("cpu_pct")),
          ]));
        ''')
        assert out == ["512 B", "4200.0%"]

    def test_a_fractional_count_is_a_measurement_not_a_float_dump(self):
        """`UX-275` published the first one. `cores_busy` is an average
        over the run, and it arrived on the page as
        "1.603977885512677" - fifteen digits of a number measured to
        two. Whole counts, which are all the others, are untouched."""
        out = _js('''
          const { quantity, quantityFor, childNode } =
            await import("./tests/viewer.mjs");
          const block = %s;
          console.log(JSON.stringify([
            quantity(1.603977885512677,
                     quantityFor(childNode(block, "cores_busy"),
                                 "cores_busy")),
            quantity(4, quantityFor(childNode(block, "builders"),
                                    "builders")),
          ]));
        ''' % json.dumps(
            schemas.schema(schemas.ANALYZE)["properties"]
            ["capacity_recommendation"]))
        # `UX-341`: `cores_busy` is one measurement with one unit now.
        # `capacity_recommendation` declared it `count` while the four
        # element-level copies of the same figure declared `ratio`.
        assert out == ["1.60\u00d7", "4"], out

    def test_declared_beats_guessed(self):
        out = _js('''
          const { quantityFor } = await import("./tests/viewer.mjs");
          console.log(JSON.stringify([
            quantityFor({"bga:quantity": "megabytes"}, "peak_rss_bytes"),
            quantityFor(undefined, "peak_rss_bytes"),
          ]));
        ''')
        assert out == ["megabytes", "bytes"]


class TestTheSchemasCarryTheNestedSemantics:
    def test_utilisation_declares_the_two(self):
        util = schemas.schema(schemas.ANALYZE)["properties"]["utilisation"]
        assert util["properties"]["useful_share"][schemas.QUANTITY] == "share"
        envelope = schemas.schema(schemas.CORRELATE)["properties"]["memory_envelope"]
        assert envelope["properties"]["host_memory_bytes"][schemas.QUANTITY] \
            == "bytes"

    def test_the_declared_shapes_are_ones_a_run_publishes(self):
        """UX-220: the failure this file was pinned to for four rounds.

        A quantity declared on a name nothing emits is a hint aimed at
        nothing - it renders no value correctly, and it hides that the
        object's real members were never hinted at all.
        """
        util = schemas.schema(schemas.ANALYZE)["properties"]["utilisation"]
        for phantom in ("peak_rss_bytes", "cpu_pct", "cpu_seconds"):
            assert phantom not in util["properties"], phantom

    def test_the_deltas_members_say_what_they_are(self):
        deltas = schemas.schema(schemas.COMPARE)["properties"]["deltas"]
        assert deltas["properties"]["total_duration_us"][schemas.QUANTITY] \
            == "duration_us"
        assert deltas[schemas.DIRECTION] == "lower_is_better"

    def test_a_nested_typo_is_refused(self):
        with pytest.raises(ValueError, match="furlongs"):
            schemas._document("x/v1", "x", {"a": "object"}, "d",
                              hints={"a": {"properties": {
                                  "b": {schemas.QUANTITY: "furlongs"}}}})

    def test_the_findings_item_shape_is_declared(self):
        findings = schemas.schema(schemas.ANALYZE)["properties"]["findings"]
        item = findings["items"]
        assert set(item["required"]) == {"id", "severity", "title"}
        assert item["properties"]["severity"]["enum"] == list(schemas.SEVERITIES)


class TestColumnsAreObjects:
    def test_a_column_entry_may_declare_itself(self):
        columns = schemas.schema(schemas.COMPARE)["properties"]["mismatches"][
            schemas.COLUMNS]
        assert any(isinstance(c, dict) and c.get("sortable") is False
                   for c in columns)

    def test_a_bad_quantity_in_a_column_is_refused(self):
        with pytest.raises(ValueError, match="furlongs"):
            schemas._document("x/v1", "x", {"a": "array"}, "d",
                              hints={"a": {schemas.COLUMNS: [
                                  {"key": "b", "quantity": "furlongs"}]}})

    def test_a_column_object_without_a_key_is_refused(self):
        with pytest.raises(ValueError, match="key"):
            schemas._document("x/v1", "x", {"a": "array"}, "d",
                              hints={"a": {schemas.COLUMNS: [{"title": "B"}]}})

    def test_plain_names_still_parse(self):
        document = schemas._document(
            "x/v1", "x", {"a": "array"}, "d",
            hints={"a": {schemas.COLUMNS: ["b", "c"]}})
        assert document["properties"]["a"][schemas.COLUMNS] == ["b", "c"]

    @needs_node
    def test_a_column_declared_unsortable_renders_unsortable(self):
        out = _js('''
          const { columnSpecs } = await import("./tests/viewer.mjs");
          const rows = [{ field: "trace_spine", baseline: "1", candidate: "2" }];
          const hint = { "bga:columns": [
            { key: "field", sortable: true },
            { key: "baseline", sortable: false },
          ]};
          console.log(JSON.stringify(
            columnSpecs(hint, rows, undefined).map((s) => [s.key, s.sortable])));
        ''')
        assert out == [["field", True], ["baseline", False]]

    @needs_node
    def test_numeric_ness_is_declared_rather_than_sampled(self):
        """A column of numeric-looking *strings* must not become a
        number column because the sample happened to look like one."""
        out = _js('''
          const { columnSpecs } = await import("./tests/viewer.mjs");
          const rows = [{ ref: "12345", seconds: 3 }];
          const hint = { "bga:columns": [
            { key: "ref" },
            { key: "seconds", quantity: "seconds" },
          ]};
          console.log(JSON.stringify(
            columnSpecs(hint, rows, undefined).map((s) => [s.key, s.numeric])));
        ''')
        assert out == [["ref", False], ["seconds", True]]


class TestTheVerdictIsAValue:
    def test_compare_declares_it(self):
        assert "verdict_kind" in schemas.schema(schemas.COMPARE)["properties"]

    def test_it_is_emitted_from_the_same_branch_as_the_sentence(self, tmp_path):
        import io
        import contextlib

        from bga.cli import main

        runs = []
        for name in ("a", "b"):
            run = tmp_path / name
            shutil.copytree("tests/fixtures/golden/mixed_task_kinds", run)
            os.remove(run / "expected_output.json")
            runs.append(str(run))
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            try:
                main(["compare", *runs, "--format", "json"])
            except SystemExit:
                pass
        payload = json.loads(buffer.getvalue())
        assert payload["verdict_kind"] in schemas.VERDICT_KINDS
        # The sentence and the enum must agree about which branch ran.
        assert payload["verdict"].replace(" ", "_") == payload["verdict_kind"] \
            or payload["verdict_kind"] == "no_significant_change"

    def test_absence_is_not_read_as_not_comparable(self):
        """A `ComparisonResult` built by something other than the
        significance chain records nothing rather than claiming the
        strongest refusal."""
        from bga.compare import ComparisonResult
        import dataclasses

        field = {f.name: f for f in dataclasses.fields(ComparisonResult)}
        assert field["verdict_kind"].default is None

    @needs_node
    def test_the_banner_styles_from_the_enum_not_the_prose(self):
        out = _js('''
          const { verdictClass } = await import("./tests/viewer.mjs");
          console.log(JSON.stringify([
            verdictClass("THE BUILD GOT WORSE, MATE", "regressed"),
            verdictClass("improved", "regressed"),
            verdictClass("improved", undefined),
          ]));
        ''')
        assert out == ["refused", "refused", "good"], out


class TestDescriptionsAreThePopovers:
    @needs_node
    def test_a_described_field_carries_its_schema_text(self):
        overhead = schemas.schema(schemas.ANALYZE)["properties"][
            "pipeline_overhead"]
        description = overhead["properties"]["total_us"]["description"]
        out = _js('''
          const { renderPairs } = await import("./tests/viewer.mjs");
          globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;

function make(tag) {
  const node = _makeNode(tag);
  return node;
}
          _installDocument();
          const node = %s;
          const out = renderPairs("pipeline_overhead", { total_us: 1441000 }, {}, node);
          // `el()` assigns non-data attributes as *properties*
          // (node.title = ...), which a browser reflects onto the
          // attribute. The shim has to look in both places; checking
          // only `attrs` reported an empty list against a working
          // popover.
          const titles = [];
          (function walk(n) {
            const t = (n.attrs && n.attrs.title) || n.title;
            if (t) titles.push(t);
            (n.children ?? []).forEach(walk);
          })(out);
          console.log(JSON.stringify(titles));
        ''' % json.dumps(overhead))
        assert description in out, out

    def test_every_description_is_a_sentence_worth_showing(self):
        """A popover of three words is noise; the point is the "why does
        this matter" answer the spec already carries."""
        for name in schemas.names():
            document = schemas.schema(name)
            for key, sub in document["properties"].items():
                for nested_key, nested in (sub.get("properties") or {}).items():
                    text = nested.get("description")
                    if text is not None:
                        assert len(text) > 30, f"{name}.{key}.{nested_key}"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
