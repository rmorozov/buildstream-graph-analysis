"""UX-598: Direction 11's percentile table against what publishes one.

The filing's measurement read `bga/schemas.py` as a proxy for "what
publishes a distribution" and found two of four. Re-measured round 84:

```text
$ git grep -n "_distribution(" bga/schemas.py
  1980 element_duration_distribution      1986 blast_radius_distribution
$ python3 -c "from bga.correlate import _scale_of; print(sorted(_scale_of(p, n)))"
['process_count_distribution', 'sandbox_tax_distribution']
```

Four of four publish; the other two live in `correlate/v2` and the
grep could not see them. What was true is that those two published
keys were declared by nothing, so their percentiles reached the reader
as bare numbers.

So the table is held against the decision, not against one module.
Each row names its `bga/analyzer.py` key; the `percentile?` cell is
derived from membership in `DISTRIBUTED_QUANTITIES`, and every `yes`
must reach both a published key and a `bga:distribution` declaration.
"""
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

DIRECTIONS = REPO / "docs/design/directions.md"
RUN = REPO / "tests/fixtures/macro_micro/run"
HEADER = "| quantity | key | percentile? | why |"

#: Where each `yes` quantity's distribution is published, and under
#: which contract. Read back off the tree below, never trusted.
PUBLISHED = {
    "blast_radius": ("analyze", "blast_radius_distribution"),
    "element_duration": ("analyze", "element_duration_distribution"),
    "sandbox_tax": ("correlate", "sandbox_tax_distribution"),
    "process_count": ("correlate", "process_count_distribution"),
}


def _table_rows():
    """Direction 11's table, as (keys, `yes`/`no`).

    The subject is the table; the prose above it argues for the rule and
    says "yes" in sentences, which is not a cell.
    """
    text = DIRECTIONS.read_text(encoding="utf-8")
    start = text.index(HEADER)
    table = text[start:text.index("\n\n", start)]
    rows = []
    for line in table.splitlines()[2:]:
        cells = [c.strip() for c in line.split("|")[1:-1]]
        verdict = re.match(r"\*\*(yes|no)\*\*", cells[2])
        assert verdict, ("a `percentile?` cell is neither **yes** nor "
                         "**no**", cells)
        rows.append((re.findall(r"`([a-z_0-9]+)`", cells[1]),
                     verdict.group(1)))
    return rows


def _the_decision():
    """`(distributed, undistributed)` - the split `UX-260` recorded."""
    from bga import analyzer

    return (dict(analyzer.DISTRIBUTED_QUANTITIES),
            dict(analyzer.UNDISTRIBUTED_QUANTITIES))


def _declared():
    """Every key in any published schema carrying `bga:distribution`."""
    from bga import schemas

    found = {}
    for name in schemas.names():
        document = schemas.schema(name)
        for key, node in document["properties"].items():
            if isinstance(node, dict) and schemas.DISTRIBUTION in node:
                found[key] = name
        for key, node in document["properties"].items():
            for nested, child in (node.get("properties") or {}).items():
                if isinstance(child, dict) and schemas.DISTRIBUTION in child:
                    found[nested] = name
    return found


class TestTheTableIsTheRecordedDecision:
    """A row whose cell disagrees with `bga/analyzer.py` is the drift
    `UX-581` dated instead of fixing."""

    def test_the_table_parses_to_rows_with_keys(self):
        rows = _table_rows()
        assert len(rows) >= 5 and all(keys for keys, _ in rows), (
            "Direction 11's table did not parse into keyed rows; every "
            "claim below would pass vacuously", rows)

    def test_every_cell_is_its_keys_membership(self):
        distributed, undistributed = _the_decision()
        wrong = []
        for keys, verdict in _table_rows():
            for key in keys:
                inside = key in distributed
                assert inside or key in undistributed, (
                    "Direction 11 names a quantity neither list in "
                    "bga/analyzer.py records", key)
                if inside != (verdict == "yes"):
                    wrong.append((key, verdict))
        assert not wrong, (
            "a `percentile?` cell disagrees with the split UX-260 "
            "recorded in bga/analyzer.py", wrong)

    def test_every_distributed_quantity_has_a_row(self):
        """The direction a fifth `yes` would take: added to the code,
        never to the table a reader trusts."""
        distributed, _ = _the_decision()
        named = {key for keys, _ in _table_rows() for key in keys}
        missing = sorted(set(distributed) - named)
        assert not missing, (
            "a quantity got a distribution and Direction 11's table does "
            "not have a row for it", missing)


class TestEveryYesReachesADistribution:
    """`UX-598`'s own finding. A `yes` is a promise about the payload,
    and two of them were kept only halfway."""

    def test_each_yes_publishes_a_distribution_shape(self):
        from bga import correlate
        from bga.analyzer import analyze_run

        distributed, _ = _the_decision()
        assert set(PUBLISHED) == set(distributed), (
            "the published-key map has drifted from DISTRIBUTED_QUANTITIES",
            sorted(PUBLISHED), sorted(distributed))
        payers = {"sandbox_tax": {"top_payers": [{"toll_us": i} for i in
                                                 range(1, 21)]}}
        native = {"per_element_parallelism":
                  [{"work_process_count": i} for i in range(1, 21)]}
        emitted = {
            "correlate": set(correlate._scale_of(payers, native)),
            "analyze": set(analyze_run(RUN).signals),
        }
        for key, (contract, published) in PUBLISHED.items():
            assert published in emitted[contract], (
                "a `yes` quantity's distribution is not in what "
                f"{contract} publishes", key, published,
                sorted(emitted[contract]))

    def test_each_yes_declares_bga_distribution(self):
        """The half that was missing: published and declared by nothing,
        so every percentile inside reached the reader as a bare number
        (`UX-343`)."""
        declared = _declared()
        assert len(declared) >= 4, (
            "almost nothing declares bga:distribution - the walk broke",
            sorted(declared))
        undeclared = sorted(
            published for _, (_, published) in PUBLISHED.items()
            if published not in declared)
        assert not undeclared, (
            "a quantity Direction 11 says yes to publishes a shape no "
            "schema declares", undeclared, sorted(declared))

    def test_no_quantity_answering_no_grew_one(self):
        """The direction that rots: a distribution appearing for a
        quantity the table argues against."""
        _, undistributed = _the_decision()
        declared = _declared()
        grew = sorted(key for key in undistributed
                      if f"{key}_distribution" in declared)
        assert not grew, (
            "a quantity Direction 11 argues against has grown a declared "
            "distribution; the row is now a lie", grew)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
