"""UX-344: the payload was six deep, and two of them were namespaces.

Measured on the emitted `analyze/v3`, counting a container step per
level:

```text
golden       489 leaves   1:5 2:79  3:124 4:151 5:76  6:54
                          deeper than three: 281 (57%)
                          deepest: findings.[].provenance.rule.threshold.[]
macro_micro 1442 leaves   1:5 2:117 3:353 4:533 5:286 6:147 7:1
                          deeper than three: 967 (67%)
                          deepest: findings.[].evidence.steps.[].entering.[]
```

Three shapes carried most of it, and this file is one clause per shape:

* **two namespaces.** `signals` was a map of named tables and
  `structural` was another; neither held a value of its own, and both
  cost every table below them a level. Each table is a key of the
  document now.
* **provenance nested inside every claim it explains.** The deepest
  shape in the report sat inside the record it was about, three times
  over - once per finding, once on the headline, and once more as a
  `see` path from each top action into the finding's copy. It is one
  list keyed by claim.
* **a map keyed by data whose values nothing declared.**
  `findings[].evidence.blast_radius` was a slice of a population
  published in full beside it (`UX-288`'s rule), and
  `leaf_analysis.leaves_detail` - found by the clause below, not by
  reading the schema - was an element-keyed map with no
  `additionalProperties` at all.

**What is *not* claimed.** Three deep everywhere is not reachable and
the item said so: `findings[].evidence.steps[].entering[]` is four real
relations and stays at seven on `macro_micro`. The bounds below are the
measured shape with room to move, so a level that comes back reddens.
"""
import pathlib

import pytest

from bga import schemas
from bga.report.json import _measure_shape

REPO = pathlib.Path(__file__).resolve().parents[2]
FIXTURES = {"golden": REPO / "tests/fixtures/golden/mixed_task_kinds",
            "macro_micro": REPO / "tests/fixtures/macro_micro/run"}

#: What the shape was when this item was filed, and the bound each
#: fixture is held to now. Measured after the lift: 0.398 and 0.533.
DEEPER_THAN_THREE = {"golden": (0.574, 0.45), "macro_micro": (0.671, 0.58)}

#: `macro_micro` keeps a seventh level, argued in the item: a step's
#: `entering` list is four real relations, not a namespace.
DEEPEST = {"golden": 5, "macro_micro": 7}


def _document(label):
    from tools.bga_view import payloads

    return payloads(str(FIXTURES[label]))["report.json"]


def _walk(value, node, path, visit):
    """Every object in the document, with the schema node that
    describes it - the same two-channel resolution the page uses."""
    if isinstance(value, dict):
        visit(value, node, path)
        for key, sub in value.items():
            visit_node = schemas._descend(node, key) if node else None
            _walk(sub, visit_node, path + [key], visit)
    elif isinstance(value, list):
        item = schemas._descend(node, None) if node else None
        for sub in value:
            _walk(sub, item, path + ["[]"], visit)


@pytest.mark.parametrize("label", sorted(FIXTURES))
class TestTheNamespacesAreGone:
    def test_neither_namespace_is_a_key(self, label):
        document = _document(label)
        assert "signals" not in document and "structural" not in document, (
            f"{label}: {sorted(set(document) & {'signals', 'structural'})} is "
            f"back - a level that holds only other levels")

    def test_every_table_they_held_is_still_published(self, label):
        """Lifting is not dropping. Every table either stands on its own
        or is a member of `elements`, the one population it belongs to."""
        document = _document(label)
        elements = document.get("elements") or {}
        renamed = {"metrics": "graph_metrics", "summary": "graph_summary"}
        missing = []
        for table in list(schemas._SIGNALS_TABLES) + list(schemas._STRUCTURAL_TABLES):
            name = renamed.get(table, table)
            if name in document or name in elements:
                continue
            missing.append(name)
        # A table the run has nothing to say about is absent by design -
        # the run-dependent list is where that is declared.
        unexplained = sorted(set(missing) - set(schemas.ANALYZE_RUN_DEPENDENT_KEYS))
        assert not unexplained, (
            f"{label}: {unexplained} was published under a namespace and is "
            f"published nowhere now")


@pytest.mark.parametrize("label", sorted(FIXTURES))
class TestNoMapIsKeyedByDataItCannotDescribe:
    def test_every_map_keyed_by_a_uid_declares_its_values(self, label):
        """A map whose *keys* are values cannot name them in
        `properties` - so it says what a value is once, under
        `additionalProperties`, and every key resolves to that.

        Found `leaf_analysis.leaves_detail` on its first run: an
        element-keyed map of four-field records, declaring nothing.
        """
        document = _document(label)
        uids = set((document.get("elements") or {}).get("element_durations") or {})
        uids |= set(document.get("wall_clock_share_us") or {})
        assert uids, f"{label}: no element population to test against"
        undeclared = []

        def visit(value, node, path):
            if not value or not (set(value) & uids):
                return
            if not isinstance((node or {}).get("additionalProperties"), dict):
                undeclared.append(".".join(path) or "<root>")

        _walk(document, schemas.schema(document["schema"]), [], visit)
        assert not sorted(set(undeclared)), (
            f"{label}: map(s) keyed by a uid the schema cannot name, with no "
            f"`additionalProperties` to say what a value is: "
            f"{sorted(set(undeclared))}")

    def test_no_finding_republishes_the_element_population(self, label):
        """`findings[].evidence.blast_radius` was `elements.blast_radius`
        keyed by the same uids, written again inside the finding that
        names those elements - `UX-288`'s rule, and the deepest shape in
        the golden report for the sake of it."""
        document = _document(label)
        uids = set((document.get("elements") or {}).get("element_durations") or {})
        repeated = [key for finding in document.get("findings") or []
                    for key, value in (finding.get("evidence") or {}).items()
                    if isinstance(value, dict) and set(value) & uids]
        assert not repeated, (
            f"{label}: findings[].evidence.{repeated} is keyed by element "
            f"uid - the population is published once, in `elements`")


@pytest.mark.parametrize("label", sorted(FIXTURES))
class TestTheDocumentKnowsItsOwnShape:
    def test_the_published_shape_is_the_measured_shape(self, label):
        """The block counts itself, so a consumer that re-measures gets
        these numbers back. This is that consumer."""
        document = _document(label)
        published = document["document_shape"]
        leaves, depth, path, deeper = _measure_shape(document)
        assert (published["leaves"], published["deepest_depth"],
                published["deeper_than_three"]) == (leaves, depth, deeper), (
            f"{label}: the document says {published} and measures "
            f"{{'leaves': {leaves}, 'deepest_depth': {depth}, "
            f"'deeper_than_three': {deeper}}}")
        assert published["deepest_path"] == path, (
            f"{label}: deepest published {published['deepest_path']!r}, "
            f"measured {path!r}")

    def test_the_deepest_leaf_is_where_the_item_left_it(self, label):
        document = _document(label)
        assert document["document_shape"]["deepest_depth"] <= DEEPEST[label], (
            f"{label}: {document['document_shape']['deepest_path']} is "
            f"{document['document_shape']['deepest_depth']} levels down, "
            f"against {DEEPEST[label]}")

    def test_fewer_leaves_are_deeper_than_three(self, label):
        was, bound = DEEPER_THAN_THREE[label]
        share = _document(label)["document_shape"]["deeper_than_three_share"]
        assert share <= bound, (
            f"{label}: {share:.3f} of leaves are deeper than three levels, "
            f"against a bound of {bound} (it was {was} when UX-344 was filed)")


@pytest.mark.parametrize("label", sorted(FIXTURES))
class TestOneRecordPerClaim:
    def test_the_chain_is_published_once_per_claim(self, label):
        document = _document(label)
        claims = [entry.get("claim") for entry in document["provenance"]]
        assert len(claims) == len(set(claims)), f"{label}: repeated {claims}"
        expected = {finding["id"] for finding in document.get("findings") or []}
        expected.add("diagnosis")
        assert set(claims) == expected, (
            f"{label}: published {sorted(set(claims))}, claims made "
            f"{sorted(expected)}")

    def test_no_claim_carries_a_copy_of_its_chain(self, label):
        """The three copies this item removed: every finding, the
        headline, and a `see` path on every top action."""
        document = _document(label)
        found = []

        def visit(value, _node, path):
            if "provenance" in value and path:
                found.append(".".join(path))

        _walk(document, None, [], visit)
        assert not found, (
            f"{label}: a nested `provenance` is back on {found[:4]}")

    def test_every_id_a_claim_carries_resolves_into_it(self, label):
        from bga import provenance

        assert provenance.unresolved_references(_document(label)) == []
