"""UX-345: a declaration is a claim about the value, and the value can answer.

`UX-341` made the vocabulary one member per dimension and guarded that
property. `UX-343` made every numeric leaf carry a declaration and
guarded that one. Neither can see the case this file is for: a leaf that
declares a *valid* member and holds a value that member cannot be.

The case it was filed on, printed on the page for anyone to read:

```text
Critical path length   43200000   How many elements the chain runs
                                  through. A count of elements, not a
                                  duration - `floors.t_infinity_observed`
                                  is the time.
```

Ten elements. `43200000` is `floors.t_infinity_observed` in
microseconds - the very field the sentence points at as the other thing
- and `graph_metrics.critical_path_length` held the real count, 10.
One name, two quantities, both declared `count`.

**The two cheap checks, and why only two.** A `count` is a whole number
and a `share` is in 0..1; both are decidable from the value alone. A
third was tried and rejected: *two leaves of one name may not differ in
magnitude by more than N*. Measured on the fixtures, legitimate spread
inside one `(name, quantity)` reaches **4,739x** (`total_duration_us`
across six sites) and 1,023x (`elapsed_us`), so any N that admitted
those would also admit the 4.3-million-fold error this file is named
for. A bound that cannot separate the defect from the data is not a
bound; the two below can, and did.

**What the second check caught on its first run**, which is the reason
it is here rather than in a later round: `signals.wall_clock_share` was
declared `share` and held `20433333.33` - microseconds. The producer's
own field is called `wall_clock_share_us`. It is `wall_clock_share_us`
in the payload now.

**And on its second run**, a smaller one of the same kind:
`confidence.duration_coverage` published `1.0001793150166365`.
Quantization (Part 3.2) rounds a span's start and its finish onto the
50 ms grid independently, so a normalized task can come out up to one
epsilon longer than the span it was made from; across the eleven spans
of `macro_micro` that lifts the accounted sum 9 ms above the 50.191 s
declared. The number was not a unit error - it was a share reporting
100.018% coverage. `compute_confidence` now reads a coverage the grid
pushed over one as complete, 1.0, and leaves an excess the grid cannot
explain visible, so a duplicated task stream still shows. Its
description said "the share of elements whose duration was actually
recorded", which the field has never been; it says what it computes
now. `SHARE_SLACK` stayed at 1e-6 - widening it to admit 1.8e-4 would
have bought nothing this fix does not, and every other share in both
fixtures lands inside 0..1 exactly.
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

#: A share may sit a hair outside 0..1 through floating-point division
#: without being a defect. Wide enough to admit rounding, far too narrow
#: to admit a microsecond count.
SHARE_SLACK = 1e-6

#: Declared `count` leaves that are legitimately fractional, with the
#: reason. An average over a population is a count of things per thing,
#: and rounding it would be the lie.
FRACTIONAL_COUNTS = {
    "graph_metrics.avg_fanin":
        "Edges per element, averaged over the graph - a mean of counts.",
    "graph_metrics.avg_fanout":
        "The same, the other way round.",
}

_CENSUS = r"""
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis.document = { createElement: _makeNode,
                        createElementNS: (_n, t) => _makeNode(t),
                        getElementById: () => null, querySelector: () => null,
                        querySelectorAll: () => [], addEventListener: () => {} };
const v = await import(process.env.BGA_VIEWER);
const fs = await import("node:fs");
const payload = JSON.parse(fs.readFileSync(process.env.BGA_PAYLOAD, "utf8"));
const schemas = JSON.parse(fs.readFileSync(process.env.BGA_SCHEMAS, "utf8"));

// The same resolution `UX-343`'s census walks - both declaration
// channels, read through the page's own helpers - carrying the value
// this time, because the value is what is on trial.
const found = [];
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
    const stated = v.hintsOf(node)["bga:quantity"]
      ?? (columns && columns.get(key))
      ?? (key === "value" && rowQuantity);
    if (stated) found.push([path.join("."), stated, value]);
  }
}
walk(payload, schemas[payload.schema], [], null, null);
console.log(JSON.stringify(found));
"""


def _declared_values(label):
    """`[(path, quantity, value)]` for every declared numeric leaf."""
    import tempfile

    from bga import schemas
    from tools.bga_view import payloads

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
class TestAValueCanBeWhatItSaysItIs:
    def test_every_count_is_a_whole_number(self, label):
        """`43200000` passed this one; it is the *pair* of checks that
        locates a duration wearing a count's declaration, and this is
        the half that catches the fractional case."""
        bad = [(path, value) for path, quantity, value in _declared_values(label)
               if quantity == "count" and float(value) != int(float(value))
               and path not in FRACTIONAL_COUNTS]
        assert bad == [], (
            f"{label}: leaves declared `count` holding a fraction: {bad[:6]}")

    def test_every_share_is_between_zero_and_one(self, label):
        """The half that found `signals.wall_clock_share` holding
        20,433,333 microseconds under a `share`."""
        bad = [(path, value) for path, quantity, value in _declared_values(label)
               if quantity == "share"
               and not (-SHARE_SLACK <= float(value) <= 1 + SHARE_SLACK)]
        assert bad == [], (
            f"{label}: leaves declared `share` outside 0..1: {bad[:6]}")

    def test_the_summary_quotes_no_metric_at_all(self, label):
        """`UX-535` replaces the agreement this asserted. `graph_summary`
        held three numbers assigned from the same `StructuralMetrics`
        object `graph_metrics` publishes - two of them under a second
        spelling - so a `+ 1` at the summary's own site changed a
        published count and reddened nothing, and checking the two
        copies agreed only caught the drift after both were written.
        `analyze/v5` publishes each once, so the drift has nowhere to
        happen; this asserts the absence rather than the agreement."""
        from tools.bga_view import payloads

        document = payloads(str(FIXTURES[label]))["report.json"]
        metrics = document.get("graph_metrics") or {}
        summary = document.get("graph_summary") or {}
        assert metrics and summary, (label, sorted(document))
        for quoted, source in (("total_elements", "num_elements"),
                               ("critical_path_length", "critical_path_length"),
                               ("max_parallelism", "max_parallelism")):
            assert quoted not in summary, (
                f"{label}: graph_summary.{quoted} is back, republishing "
                f"graph_metrics.{source} ({metrics.get(source)!r})")

    def test_the_walk_reached_the_document(self, label):
        """A census that resolved nothing would pass both clauses above
        by finding no values to judge."""
        found = _declared_values(label)
        assert len(found) > 150, (
            f"{label}: only {len(found)} declared values found - the walk is "
            f"not reaching the document")


@needs_node
class TestTheOneThisWasFiledFor:
    def test_the_chains_length_is_not_published_as_a_count(self):
        """`signals.critical_path_length` held the weighted longest
        path in microseconds. `floors.t_infinity_observed` and
        `sensitivity.critical_path_us` are the same number
        under names that are true, so it is gone rather than renamed -
        `UX-288`'s rule is that a population is published once."""
        from tools.bga_view import payloads

        for label, run in FIXTURES.items():
            payload = payloads(str(run))["report.json"]
            # `UX-344` lifted the namespace; the removed key would come
            # back as a key of the document or as a member of `elements`.
            for where in (payload, payload.get("elements") or {}):
                assert "critical_path_length" not in where, (
                    f"{label}: critical_path_length is back, holding "
                    f"{where['critical_path_length']}")
            # The two that remain say the same thing, truthfully.
            floors = (payload.get("floors") or {}).get("t_infinity_observed")
            sensitivity = (payload.get("sensitivity") or {}).get(
                "critical_path_us")
            assert floors == sensitivity, (label, floors, sensitivity)

    def test_the_count_of_elements_on_the_chain_still_reads_as_one(self):
        """The number the removed key's own description described is
        published, and is the length of the path beside it."""
        from tools.bga_view import payloads

        for label, run in FIXTURES.items():
            payload = payloads(str(run))["report.json"]
            metrics = payload.get("graph_metrics") or {}
            detail = payload.get("critical_path_detail")
            assert metrics.get("critical_path_length") == len(detail or []), (
                label, metrics.get("critical_path_length"), len(detail or []))
