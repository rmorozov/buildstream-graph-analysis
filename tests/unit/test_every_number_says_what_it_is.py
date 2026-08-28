"""UX-343: every number the report publishes says what unit it is in.

`UX-201`'s rule is *declared beats guessed*, and `quantityFor` still
guesses when the schema says nothing - name-sniffing `guessQuantity(key)`
and complaining to the console under `BGA_STRICT_HINTS`. What nobody had
measured was how often it was guessing, or how often it had nothing to
guess from either.

**Measured through the page's own resolution**, in Node against
`tests/viewer.mjs`, on both committed fixtures. That matters: two
earlier passes of this census re-implemented the resolution in Python
and were wrong twice, both times overstating the gap - once by missing
the `bga:columns` channel entirely, once by mis-inheriting it. And
`quantityFor` returns `declared ?? guessed`, so a guess counted as a
declaration until the two were read apart.

```text
                declared   guessed   neither
golden      29% -> 97%    20% -> 0%   51% ->  3%
macro_micro 32% -> 99%    21% -> 0%   48% ->  1%
```

**Why this guard walks a real payload and not the schema.** A schema
can declare a key no run emits, and a run can emit a key no schema
declares; only the payload says which numbers a reader actually meets.
The clause below therefore reads the emitted document and resolves each
numeric leaf the way the page will.
"""
import json
import os
import pathlib
import shutil
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = {"golden": REPO / "tests/fixtures/golden/mixed_task_kinds",
            "macro_micro": REPO / "tests/fixtures/macro_micro/run"}
node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")

# The numbers that genuinely cannot resolve a unit, and why. An
# allowlist with reasons rather than a count: a count says how many are
# missing, and a reason says whether that is acceptable.
UNDECLARABLE = {
    "findings.[].provenance.rule.threshold":
        "A rule whose `observed_path` is null compares against a quantity "
        "the finding computes rather than publishes, so no path names the "
        "unit. Rules that do have one carry `threshold_quantity`.",
    "findings.[].provenance.rule.threshold.[]":
        "The banded form of the same rule - two thresholds, same reason.",
    "headline.provenance.rule.threshold":
        "The diagnosis chain's own rule, same reason.",
}

_CENSUS = r"""
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis.document = { createElement: _makeNode,
                        createElementNS: (_n, t) => _makeNode(t),
                        getElementById: () => null, querySelector: () => null,
                        querySelectorAll: () => [], addEventListener: () => {} };
// UX-343: the complaint `quantityFor` makes when it had to guess is the
// signal this item empties. Captured rather than silenced.
const warnings = [];
console.warn = (text) => warnings.push(String(text));
globalThis.BGA_STRICT_HINTS = true;

const v = await import(process.env.BGA_VIEWER);
const fs = await import("node:fs");
const payload = JSON.parse(fs.readFileSync(process.env.BGA_PAYLOAD, "utf8"));
const schemas = JSON.parse(fs.readFileSync(process.env.BGA_SCHEMAS, "utf8"));

const declared = [], guessed = [], neither = [];

function columnsOf(node) {
  const out = new Map();
  for (const spec of v.hintsOf(node)["bga:columns"] ?? []) {
    if (spec && typeof spec === "object" && spec.key) out.set(spec.key, spec.quantity);
  }
  return out;
}

function walk(value, node, path, columns, rowQuantity) {
  if (value && typeof value === "object" && !Array.isArray(value)) {
    rowQuantity = value.quantity ?? rowQuantity;
    const here = columnsOf(node);
    for (const [k, sub] of Object.entries(value)) {
      walk(sub, v.childNode(node, k), path.concat(k),
           here.size ? here : columns, rowQuantity);
    }
  } else if (Array.isArray(value)) {
    const here = columnsOf(node);
    const items = v.childNode(node, "__item__");
    for (const sub of value) {
      walk(sub, items, path.concat("[]"), here.size ? here : columns, rowQuantity);
    }
  } else if (typeof value === "number" && Number.isFinite(value)) {
    const key = path[path.length - 1];
    // `quantityFor` returns `declared ?? guessed`; the two are read
    // apart here because a guess is what this item is emptying.
    const stated = v.hintsOf(node)["bga:quantity"]
      ?? (columns && columns.get(key))
      ?? (key === "value" && rowQuantity);
    const bag = stated ? declared : (v.guessQuantity(key) ? guessed : neither);
    bag.push(path.join("."));
  }
}

walk(payload, schemas[payload.schema], [], null, null);
console.log(JSON.stringify({
  declared: declared.length,
  guessed: [...new Set(guessed)].sort(),
  neither: [...new Set(neither)].sort(),
  warnings: [...new Set(warnings)].sort(),
}));
"""


def _census(label):
    from bga import schemas
    from tools.bga_view import payloads

    import tempfile

    scratch = pathlib.Path(tempfile.mkdtemp())
    (scratch / "payload.json").write_text(
        json.dumps(payloads(str(FIXTURES[label]))["report.json"]))
    (scratch / "schemas.json").write_text(
        json.dumps({name: schemas.schema(name) for name in schemas.names()}))
    done = subprocess.run(
        [node, "--input-type=module", "-e", _CENSUS],
        capture_output=True, text=True, cwd=REPO, timeout=120,
        env={**os.environ,
             "BGA_DOM_SHIM": (REPO / "tests/dom_shim.mjs").as_uri(),
             "BGA_VIEWER": (REPO / "tests/viewer.mjs").as_uri(),
             "BGA_PAYLOAD": str(scratch / "payload.json"),
             "BGA_SCHEMAS": str(scratch / "schemas.json")})
    assert done.returncode == 0, done.stderr
    return json.loads(done.stdout)


@needs_node
@pytest.mark.parametrize("label", sorted(FIXTURES))
class TestEveryNumberResolvesToAUnit:

    def test_nothing_renders_from_a_guess(self, label):
        """`guessQuantity` is the fallback `UX-201` kept as a
        *complaint*. This item empties its input, so the complaint
        should never fire - and it is read from the console rather than
        inferred, because the console is where a reader would meet it.
        """
        census = _census(label)
        assert census["guessed"] == [], (
            f"{label}: {len(census['guessed'])} numeric leaves render from "
            f"a name-sniffed guess: {census['guessed'][:8]}")
        assert census["warnings"] == [], (
            f"{label}: BGA_STRICT_HINTS complained: {census['warnings'][:5]}")

    def test_what_cannot_resolve_is_named_with_a_reason(self, label):
        """An allowlist with reasons, not a count.

        A count says how many are missing; a reason says whether that
        is acceptable, and makes a new one somebody's decision rather
        than a number quietly going up.
        """
        census = _census(label)
        unexpected = sorted(set(census["neither"]) - set(UNDECLARABLE))
        assert unexpected == [], (
            f"{label}: numeric leaves with no unit at all and no entry "
            f"saying why: {unexpected}")

    def test_the_walk_reached_the_document(self, label):
        """A census that resolved nothing would pass every clause above
        by finding no numbers to complain about."""
        census = _census(label)
        assert census["declared"] > 150, (
            f"{label}: only {census['declared']} declared leaves found - the "
            f"walk is not reaching the document")


@needs_node
class TestTheAllowlistIsNotAGraveyard:
    """Read on the wider fixture only, deliberately.

    An entry excusing something that now resolves is a note about
    history the next reader would trust, so it has to redden - but
    `golden` is a four-element run and does not emit every shape, so
    asserting on it would call an entry dead because that fixture never
    reaches it.
    """

    def test_every_entry_still_has_something_to_excuse(self):
        census = _census("macro_micro")
        dead = sorted(set(UNDECLARABLE) - set(census["neither"]))
        assert dead == [], (
            f"these resolve now and the allowlist still excuses them: {dead}")


@needs_node
class TestTheProducerMatchesItsOwnColumns:
    """`UX-290` declared these three as rows with named columns; the
    producer published positional tuples until `UX-343`. A contract and
    a payload that disagree are worse than either being wrong alone -
    a consumer reads the contract and gets the payload.
    """

    @pytest.mark.parametrize("where,key,columns", [
        ("structural.bottleneck", "high_fanin_elements",
         {"element_uid", "fan_in"}),
        ("structural.bottleneck", "high_fanout_elements",
         {"element_uid", "fan_out"}),
        ("structural.sensitivity", "top_opportunities",
         {"element_uid", "sensitivity", "saving_us"}),
    ])
    def test_the_rows_carry_the_declared_keys(self, where, key, columns):
        from tools.bga_view import payloads

        payload = payloads(str(FIXTURES["macro_micro"]))["report.json"]
        node = payload
        for step in where.split("."):
            node = node[step]
        rows = node[key]
        assert rows, f"{where}.{key} publishes nothing on this fixture"
        for row in rows:
            assert isinstance(row, dict), (
                f"{where}.{key} still publishes a positional tuple: {row!r}")
            assert columns <= set(row), (
                f"{where}.{key} row is missing declared columns: "
                f"{sorted(columns - set(row))}")

    def test_the_declared_columns_are_the_published_keys(self):
        """Derived from the schema rather than restated, so the two
        cannot drift the way they did for four rounds."""
        from bga import schemas
        from tools.bga_view import payloads

        payload = payloads(str(FIXTURES["macro_micro"]))["report.json"]
        structural = schemas.schema(schemas.ANALYZE)[
            "properties"]["structural"]["properties"]
        for block, key in (("bottleneck", "high_fanin_elements"),
                           ("bottleneck", "high_fanout_elements"),
                           ("sensitivity", "top_opportunities")):
            declared = {spec["key"] for spec
                        in structural[block]["properties"][key]["bga:columns"]
                        if isinstance(spec, dict) and spec.get("key")}
            published = set(payload["structural"][block][key][0])
            assert declared == published, (
                f"structural.{block}.{key}: the schema declares "
                f"{sorted(declared)} and the payload publishes "
                f"{sorted(published)}")
