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

**`UX-404`: and every contract, not only the one it grew up on.** The
census walked `report.json` and nothing else, so `schemas.py` validated
that a declared quantity was *valid* while nobody checked that one was
*present* on the other emitters. Round 64 proved the hole by mutation:
removing `bga:quantity` from a `whatif/v1` hint left all three unit
guards green. Measured when the second half of this file was written:

```text
                    declared  guessed  neither
compare/v2                64       13       26
correlate/v2             314        5        5
sweep/v1                  22        0        4
store-aggregate/v1        12        0       26
```

Seventy-nine numeric leaves outside the analyze door with no unit or a
sniffed one - the exact class `UX-343` closed inside it.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

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
    # `UX-344`: one list at the top level rather than a copy inside every
    # claim, so there is one path here where there were three.
    "provenance.[].rule.threshold":
        "A rule whose `observed_path` is null compares against a quantity "
        "the finding computes rather than publishes, so no path names the "
        "unit. Rules that do have one carry `threshold_quantity`.",
    "provenance.[].rule.threshold.[]":
        "The banded form of the same rule - two thresholds, same reason.",
}

_CENSUS = r"""
globalThis._makeNode ??= (await import(process.env.BGA_DOM_SHIM)).makeNode;
globalThis._installDocument ??= (await import(process.env.BGA_DOM_SHIM)).installDocument;
_installDocument();
// UX-343: this census reads `hintsOf`/`guessQuantity` directly rather
// than calling `quantityFor`, because the two channels a declaration
// can arrive through have to be read *apart* and `quantityFor` folds
// them together. So the `BGA_STRICT_HINTS` complaint never fires here
// - a first cut of this file asserted on it anyway, against a variable
// nothing could ever write to. The strict-hints reading lives where it
// belongs, on a real boot, in
// `test_the_console_stays_clean.py::test_no_number_renders_from_a_guess`.

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
}));
"""


def _census(label):
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
class TestEveryNumberResolvesToAUnit:

    def test_nothing_renders_from_a_guess(self, label):
        """`guessQuantity` is the fallback `UX-201` kept as a
        *complaint*. This item empties its input: no numeric leaf in
        either fixture's payload should reach the page with nothing but
        a name to sniff. What the complaint itself sounds like on a
        real boot is read by the console guard, not here.
        """
        census = _census(label)
        assert census["guessed"] == [], (
            f"{label}: {len(census['guessed'])} numeric leaves render from "
            f"a name-sniffed guess: {census['guessed'][:8]}")

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


#: Every document `bga` emits, and the argv or builder that produces
#: one. Derived from the emitter inventory
#: `test_every_emitted_contract_is_answerable.py` already keeps
#: structurally - a second list of commands here is exactly what fell
#: behind on the way to `UX-328`.
#:
#: `store/v1` and `store-aggregate/v1` have no command: `bga view`
#: builds them from a run store, which is what the two entries below
#: with no argv are.
CONTRACT_RUNS = {
    "analyze/v6": ["analyze", str(FIXTURES["macro_micro"]), "--format",
                   "json"],
    "compare/v2": ["compare", str(FIXTURES["golden"]),
                   str(FIXTURES["golden"]), "--format", "json"],
    "correlate/v2": ["correlate", str(FIXTURES["macro_micro"]),
                     str(REPO / "tests/fixtures/macro_micro/plane2.json"),
                     "--format", "json"],
    "blast/v2": ["blast", "toolchain.bst", str(FIXTURES["golden"]),
                 "--format", "json"],
    "whatif/v1": ["whatif", str(FIXTURES["macro_micro"]), "--format",
                  "json"],
    "sweep/v1": ["sweep", str(FIXTURES["macro_micro"]), "--format", "json"],
    "store/v1": None,
    "store-aggregate/v1": None,
    # `UX-613`: the model over that same store. No argv either - it
    # needs a store of finished runs, and `_store_document` below is
    # where one gets built.
    "capacity-model/v1": None,
}

#: What the `neither` bag is allowed to hold outside `analyze/v6`, and
#: why. Both entries are `UNDECLARABLE`'s own case reached by a path a
#: comparison publishes it under - a rule object whose `observed_path`
#: is null.
UNDECLARABLE_ELSEWHERE = {
    "compare/v2": {
        "candidate_diagnosis.provenance.rule.threshold":
            "`UNDECLARABLE`'s first entry, one document over: a rule "
            "whose `observed_path` is null compares against a quantity "
            "the finding computes rather than publishes.",
        # `UX-610`: the same case for the *verdict*'s rule. Its two
        # thresholds are scaled-MAD units and a percentage of the
        # baseline, and no published field is in either - so
        # `observed_path` is null rather than pointed at a duration it
        # is not.
        "verdict_provenance.rule.threshold":
            "The verdict's own rule: neither threshold is in the unit "
            "of any published field, so the path is null and the "
            "number is not a quantity this document carries.",
    },
}


def _emitted(contract):
    """The document one contract's emitter really writes."""
    argv = CONTRACT_RUNS[contract]
    if argv is None:
        return _store_document(contract)
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", *argv],
        capture_output=True, text=True, cwd=REPO, timeout=300,
        env={**os.environ, "PYTHONPATH": str(REPO)})
    assert done.returncode == 0, f"{contract}: {done.stderr[-2000:]}"
    document = json.loads(done.stdout)
    assert document.get("schema") == contract, (
        f"{' '.join(argv)} emitted {document.get('schema')!r}, not "
        f"{contract!r} - the inventory and the emitter disagree")
    return document


def _store_document(contract):
    """`store/v1`, its aggregate and the model, from one store.

    `bga view` builds the first two; no command prints either, which is
    the one legitimate reason for a contract to have no argv above and
    is the same distinction `UX-328`'s guard draws for file-written
    ids. `UX-613`'s model *does* have a command, but it needs a store
    on disk rather than a fixture run directory, so it is built beside
    them from the same snapshots.
    """
    import shutil
    import tempfile

    from tools.bga_view import store_aggregate_payload, store_payload

    into = pathlib.Path(tempfile.mkdtemp())
    (into / "project.conf").write_text("name: p\nmin-version: 2.0\n")
    runs = []
    # `UX-613`: five, not three - a service time needs `MIN_BASELINE_RUNS`
    # finished runs before the model computes one, and a store of three
    # would census a document whose only content is a shortfall.
    for nth in (1, 2, 3, 4, 5):
        run = into / ".bga" / "runs" / f"2026010{nth}T000000Z" / "run"
        run.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(FIXTURES["golden"], run)
        os.remove(run / "expected_output.json")
        runs.append(str(run))
    if contract == "capacity-model/v1":
        from bga import capacity_model

        document = capacity_model.read(str(into), 4, 400)
        assert document["host_classes"][0]["answers"], (
            "the store fixture produced a model with no figures in it")
        return document
    store = store_payload(runs[-1])
    assert store, "the store fixture produced no store/v1 document"
    if contract == "store/v1":
        return store
    aggregate = store_aggregate_payload(store)
    assert aggregate, "the store fixture produced no aggregate"
    return aggregate


def _census_document(document):
    import tempfile

    from bga import schemas

    scratch = pathlib.Path(tempfile.mkdtemp())
    (scratch / "payload.json").write_text(json.dumps(document))
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
class TestTheCensusReachesEveryContract:
    """`UX-404`: the same three questions, one document at a time."""

    def test_the_inventory_is_the_contract_list(self):
        """Neither side may grow without the other.

        A contract missing here would be censused by nothing, which is
        the state `whatif/v1`, `store/v1`, `store-aggregate/v1` and the
        sweep were all in.
        """
        from bga import schemas

        assert sorted(CONTRACT_RUNS) == sorted(schemas.names()), (
            f"censused: {sorted(CONTRACT_RUNS)}; emitted: "
            f"{sorted(schemas.names())}")

    @pytest.mark.parametrize("contract", sorted(CONTRACT_RUNS))
    def test_nothing_renders_from_a_guess(self, contract):
        census = _census_document(_emitted(contract))
        assert census["guessed"] == [], (
            f"{contract}: {len(census['guessed'])} numeric leaves resolve "
            f"only by name-sniffing: {census['guessed']}")

    @pytest.mark.parametrize("contract", sorted(CONTRACT_RUNS))
    def test_what_cannot_resolve_is_named_with_a_reason(self, contract):
        census = _census_document(_emitted(contract))
        excused = dict(UNDECLARABLE_ELSEWHERE.get(contract, {}))
        if contract == "analyze/v6":
            excused.update(UNDECLARABLE)
        unexpected = sorted(set(census["neither"]) - set(excused))
        assert unexpected == [], (
            f"{contract}: numeric leaves with no unit at all and no entry "
            f"saying why: {unexpected}")

    @pytest.mark.parametrize("contract", sorted(CONTRACT_RUNS))
    def test_the_walk_reached_the_document(self, contract):
        """A contract whose emitter produced an empty document would
        pass both clauses above by having nothing to complain about."""
        census = _census_document(_emitted(contract))
        assert census["declared"] > 0, (
            f"{contract}: the walk found no declared numeric leaf at all")

    def test_no_excuse_outlives_what_it_excused(self):
        """`TestTheAllowlistIsNotAGraveyard`'s rule, for the second
        allowlist: an entry excusing something that now resolves is a
        note about history the next reader would trust."""
        dead = []
        for contract, entries in UNDECLARABLE_ELSEWHERE.items():
            census = _census_document(_emitted(contract))
            dead += [f"{contract}: {path}" for path in entries
                     if path not in census["neither"]]
        assert dead == [], dead


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


class TestAPathResolvesToItsUnit:
    """`quantity_for_path` is what lets a provenance row carry a unit
    its own key could never declare. The cases below are the ones the
    fixtures do not happen to exercise - a subscript holding an element
    uid, which contains a dot.

    Splitting the path on `.` before reading its subscripts turns
    `elements.element_durations[app.bst]` into two nonsense segments that
    resolve to nothing, and no payload in this repository publishes a
    provenance path in that form today. So the resolver would be wrong
    and every other clause would stay green.
    """

    @pytest.mark.parametrize("path,expected", [
        ("total_duration_us", "duration_us"),
        ("floors.lb", "duration_us"),
        ("headline.chain_share", "share"),
        # A list of records, subscripted by index.
        ("critical_path_detail[0].duration_us", "duration_us"),
        # A table that declares columns instead of `items`.
        ("element_join[0].peak_rss_bytes", "bytes"),
        # A map keyed by an element uid - the dot inside the subscript
        # is the case a split-first walk loses.
        ("elements.element_durations[app.bst]", "duration_us"),
        ("elements.blast_radius[app.bst].risk_score", "ratio"),
        ("elements.criticality_probability[lib.bst].probability", "share"),
        # The selector form the provenance grammar also allows.
        ("findings[id=x].evidence.share", "share"),
        # A path the schema does not describe resolves to nothing rather
        # than to a guess.
        ("nonsense.path", None),
    ])
    def test_it_reads_the_unit_the_page_would(self, path, expected):
        from bga import schemas

        assert schemas.quantity_for_path(path) == expected, path


@needs_node
class TestTheProducerMatchesItsOwnColumns:
    """`UX-290` declared these three as rows with named columns; the
    producer published positional tuples until `UX-343`. A contract and
    a payload that disagree are worse than either being wrong alone -
    a consumer reads the contract and gets the payload.
    """

    @pytest.mark.parametrize("where,key,columns", [
        ("bottleneck", "high_fanin_elements",
         {"element_uid", "fan_in"}),
        ("bottleneck", "high_fanout_elements",
         {"element_uid", "fan_out"}),
        ("sensitivity", "top_opportunities",
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
        # `UX-344`: the two blocks are keys of the document; the columns
        # are declared where they always were, one level up.
        properties = schemas.schema(schemas.ANALYZE)["properties"]
        for block, key in (("bottleneck", "high_fanin_elements"),
                           ("bottleneck", "high_fanout_elements"),
                           ("sensitivity", "top_opportunities")):
            declared = {spec["key"] for spec
                        in properties[block]["properties"][key]["bga:columns"]
                        if isinstance(spec, dict) and spec.get("key")}
            published = set(payload[block][key][0])
            assert declared == published, (
                f"{block}.{key}: the schema declares "
                f"{sorted(declared)} and the payload publishes "
                f"{sorted(published)}")
