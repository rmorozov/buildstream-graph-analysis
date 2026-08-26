"""UX-217: findings carry the evidence they were drawn from.

Every finding has carried a structured `evidence` dict since findings
became data. Measured on `examples/06`:

```text
cache-hit-ratio     hit_ratio, built_elements, cached_elements, run_mode
confidence          primary, band, violation_count
wait-category       category, category_us, share, hint
time-concentration  path_us, share_of_path, chain_bound, rows
```

`renderFindings` read `id`, `severity`, `title`, `detail` and
`elements` — and dropped `evidence` on the floor. So the page showed
the *conclusion* and hid the numbers the conclusion rests on, in a tool
whose whole proposition is that its conclusions are measured rather
than guessed.

The units are the substance here. `primary` is `0.875` and a share;
`category_us` is `2000` and microseconds; `cores_busy` is `1.60` and a
ratio. Rendering any of them raw, or guessing from the key's name, is
the class of error `UX-201` exists to stop — so the vocabulary is
declared in the schema and asserted against values that were *measured
from a rendered payload*, not inferred from a suffix.
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import tempfile

import pytest

from bga import schemas

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN = os.path.join(REPO, "tests", "fixtures", "golden", "mixed_task_kinds")
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")


def _report(run=GOLDEN):
    from bga.cli import main

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        main(["analyze", run, "--format", "json"])
    return json.loads(buffer.getvalue())


def _parse(raw):
    """A `data-raw` string back to the value it was written from."""
    if raw in ("true", "false"):
        return raw == "true"
    try:
        return float(raw)
    except ValueError:
        return raw


def _render(payload):
    scratch = tempfile.mkdtemp()
    try:
        payload_path = os.path.join(scratch, "payload.json")
        schema_path = os.path.join(scratch, "schema.json")
        with open(payload_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle)
        with open(schema_path, "w", encoding="utf-8") as handle:
            json.dump(schemas.schema(payload["schema"]), handle)
        result = subprocess.run(
            [node, "--input-type=module",
             "-e", _HARNESS % json.dumps([payload_path, schema_path])],
            capture_output=True, text=True, cwd=REPO, timeout=120)
        assert result.returncode == 0, result.stderr
        return json.loads(result.stdout)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


class TestTheVocabularyIsDeclared:
    def test_the_schema_says_what_unit_each_measurement_is_in(self):
        declared = schemas.schema(schemas.ANALYZE)["properties"]["findings"][
            "items"]["properties"]["evidence"]["properties"]
        # Checked against rendered values, not guessed from suffixes.
        assert declared["primary"][schemas.QUANTITY] == "share"
        assert declared["category_us"][schemas.QUANTITY] == "duration_us"
        assert declared["cores_busy"][schemas.QUANTITY] == "ratio"
        assert declared["envelope_mb"][schemas.QUANTITY] == "megabytes"
        assert declared["host_cpu_count"][schemas.QUANTITY] == "count"

    def test_every_declared_unit_is_one_the_renderer_knows(self):
        declared = schemas.schema(schemas.ANALYZE)["properties"]["findings"][
            "items"]["properties"]["evidence"]["properties"]
        for key, hint in declared.items():
            assert hint[schemas.QUANTITY] in schemas.QUANTITIES, key

    def test_no_declaration_names_a_key_no_finding_emits(self):
        """A hint for a key nothing produces is dead weight in the
        contract, and the kind of thing that rots silently."""
        import re

        source = open(os.path.join(REPO, "bga/findings.py"),
                      encoding="utf-8").read()
        emitted = set(re.findall(r"'([a-z0-9_]+)':", source))
        declared = set(schemas.schema(schemas.ANALYZE)["properties"]["findings"]
                       ["items"]["properties"]["evidence"]["properties"])
        assert declared <= emitted, sorted(declared - emitted)


@needs_node
class TestThePageShowsTheNumbers:
    def test_a_finding_renders_its_measurements(self):
        payload = _report()
        with_evidence = [f for f in payload["findings"] if f.get("evidence")]
        assert with_evidence, "this fixture's findings carry no evidence"
        out = _render(payload)
        assert out["evidence_fields"], (
            "the page rendered no evidence at all - which was the defect")

    def test_each_value_is_the_published_one(self):
        """`data-raw` is the payload's value, so nothing here can pass
        by rendering a plausible number."""
        payload = _report()
        def spelling(value):
            """One spelling for both languages: `True`/`true` and
            `1.0`/`1` are the same published value, and comparing their
            reprs would be asserting the language rather than the
            number."""
            if isinstance(value, bool):
                return "true" if value else "false"
            if isinstance(value, (int, float)):
                return repr(float(value))
            return str(value)

        published = {}
        for finding in payload["findings"]:
            for key, value in (finding.get("evidence") or {}).items():
                if value is None or not isinstance(value, (dict, list)):
                    published.setdefault(key, spelling(value))
        out = _render(payload)
        assert out["evidence_fields"], "nothing to compare"
        for key, raw in out["evidence_fields"].items():
            assert key in published, f"{key} is not in any finding's evidence"
            assert spelling(_parse(raw)) == published[key], (
                key, raw, published[key])

    def test_a_share_renders_as_a_percentage_not_a_bare_number(self):
        """The unit is the point. `primary: 0.875` reading as "0.875"
        is the papercut, and reading as "87.5%" is the fix."""
        out = _render(_report())
        assert out["formatted"].get("primary") == "87.5%", out["formatted"]

    def test_a_duration_renders_as_a_duration(self):
        out = _render(_report())
        assert out["formatted"].get("category_us") == "2 ms", out["formatted"]

    def test_a_key_with_no_declared_unit_renders_raw_and_does_not_error(self):
        """`band` is a word and `chain_bound` is a boolean. Neither has
        a unit, and inventing one would be worse than saying nothing."""
        out = _render(_report())
        assert out["formatted"].get("band") == "high", out["formatted"]

    def test_the_arrays_are_left_to_the_sections_that_draw_them(self):
        """`rows`, `steps` and `constraints` are tables in their own
        right - a finding builds its sentence from them, and the report
        already draws them elsewhere. Flattening them into a definition
        list would be a worse rendering, not a more complete one."""
        payload = _report()
        arrays = {key for finding in payload["findings"]
                  for key, value in (finding.get("evidence") or {}).items()
                  if isinstance(value, (dict, list))}
        if not arrays:
            pytest.skip("this fixture's evidence carries no structured value")
        out = _render(payload)
        assert not (arrays & set(out["evidence_fields"])), (
            arrays & set(out["evidence_fields"]))

    def test_a_finding_with_no_evidence_renders_as_it_always_did(self):
        out = _render({
            "schema": schemas.ANALYZE, "run_id": "r", "section": None,
            "total_duration_us": 1,
            "findings": [{"id": "bare", "severity": "info", "title": "Bare"}],
        })
        assert out["evidence_fields"] == {}
        assert out["findings"] == 1, "the finding itself must still render"

    def test_a_long_evidence_block_folds(self):
        """`UX-209`'s rule: the evidence is the point, and eight rows of
        it above the next finding is a wall."""
        import importlib

        many = {f"k{i}": i for i in range(10)}
        out = _render({
            "schema": schemas.ANALYZE, "run_id": "r", "section": None,
            "total_duration_us": 1,
            "findings": [{"id": "many", "severity": "info", "title": "Many",
                          "evidence": many}],
        })
        assert out["folds"] == 1, "ten measurements did not fold"
        assert len(out["evidence_fields"]) == 10, (
            "the fold hid the values from Ctrl-F as well as from the eye")
        del importlib


_HARNESS = """
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;

function make(tag) {
  const node = _makeNode(tag);
  node.open = false;
  return node;
}
globalThis.document = { createElement: make, createElementNS: (_n, t) => make(t),
                        createTextNode: (t) => ({ nodeType: 3, textContent: t,
                                                  attrs: {}, children: [] }),
                        getElementById: () => null };
const app = await import("./bga/viewer/app.js");
const { readFileSync } = await import("node:fs");
const [payloadPath, schemaPath] = %s;
const payload = JSON.parse(readFileSync(payloadPath, "utf8"));
const schema = JSON.parse(readFileSync(schemaPath, "utf8"));
const root = make("div");
app.render(payload, schema, root);
const all = (n, p, f = []) => { if (!n) return f; if (p(n)) f.push(n);
  (n.children ?? []).forEach((c) => all(c, p, f)); return f; };
// Only the definition lists this item added, so a `data-field` some
// other view draws cannot be mistaken for evidence.
const lists = all(root, (n) => String(n.className ?? "").includes("evidence"));
const cells = lists.flatMap((l) => all(l, (n) => n.attrs["data-field"]));
console.log(JSON.stringify({
  evidence_fields: Object.fromEntries(
    cells.map((c) => [c.attrs["data-field"], c.attrs["data-raw"]])),
  // `UX-317`: the cell's **value**, not everything inside it. A
  // described value's `<dd>` now holds the number and, beside it, the
  // schema's own sentence about the number - so "what this cell reads
  // as" is the cell minus its description. `data-raw` is unaffected and
  // is still the machine value, which is what every other consumer
  // reads.
  formatted: Object.fromEntries(
    cells.map((c) => [c.attrs["data-field"],
      (c.children ?? []).filter(
        (n) => n.attrs?.["data-role"] === "description")
        .reduce((text, n) => text.replace(n.textContent, ""),
                c.textContent)])),
  folds: all(root, (n) => n.attrs["data-fold"] === "evidence").length,
  findings: all(root, (n) => n.attrs["data-finding-id"]).length,
}));
"""


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
