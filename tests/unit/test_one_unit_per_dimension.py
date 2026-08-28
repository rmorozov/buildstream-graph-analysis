"""UX-341: the payload measures each dimension one way.

`QUANTITIES` had nine members and three of the dimensions it covered
were spelled more than one way. Counted over all eight published
schemas, reading **both** declaration channels (`bga:quantity` on a
node, and `quantity` inside a `bga:columns` entry):

```text
before                          after
count          153              count        152
duration_us    122              duration_us  145
share           61              share         70
ratio           22              ratio         22
seconds         20
kilobytes        6
bytes            6              bytes         17
megabytes        5
percent          5
                                (+6: `attribution_deltas`, which was
                                 the last block in `compare` with no
                                 declaration at all, three of whose
                                 members were 0..100)
```

Every tail was derived from its own head, and usually by a lossy
division of a value the tool already held as an integer -
`micros / 1e6` for `measured_seconds`, `peak_rss_kb / 1024` for
`peak_rss_mb`. The conversions that remain are at the two input
boundaries (`bga/units.py`): `run-context.json` records the host's RAM
in MB and Plane 2's record reports `ru_maxrss` in KiB. Neither is one
of this tool's documents, and neither is rewritten by this item.

**The property, not the list.** The clauses below assert that no two
members of the vocabulary measure one dimension, and that no leaf name
carries two different quantities - rather than naming the four
spellings that were removed, which a later round could re-add without
failing anything.
"""
import collections
import re

import pytest

from bga import schemas

QUANTITY = schemas.QUANTITY
COLUMNS = schemas.COLUMNS

#: Generic members of a published distribution. Their dimension is the
#: parent's, not their own, so `element_duration_distribution.max` and
#: `blast_radius_distribution.max` legitimately differ - the name `max`
#: says which statistic, and the block above it says of what.
_STATISTIC = re.compile(r"^(n|samples|min|max|median|mad|p\d{1,2})$")

#: Suffixes that promise a unit, and the one they promise. A key whose
#: name ends in `_us` and is declared `share` is a payload a consumer
#: reads twice: once from the name, once from the contract.
SUFFIXES = {"_us": "duration_us", "_bytes": "bytes",
            "_share": "share", "_ratio": "ratio"}


def _declarations():
    """`{leaf name: {quantity: [where]}}` over both channels."""
    found = collections.defaultdict(lambda: collections.defaultdict(list))

    def walk(node, doc, path):
        if isinstance(node, dict):
            if node.get(QUANTITY):
                leaf = path.split(".")[-1] if path else "?"
                found[leaf][node[QUANTITY]].append(f"{doc} {path}")
            for spec in node.get(COLUMNS, []) or []:
                if isinstance(spec, dict) and spec.get("quantity"):
                    found[spec["key"]][spec["quantity"]].append(
                        f"{doc} {path}[].{spec['key']}")
            for key, value in node.items():
                if key == COLUMNS:
                    continue
                if key in ("properties", "additionalProperties", "items"):
                    walk(value, doc, path)
                elif isinstance(value, (dict, list)):
                    walk(value, doc, f"{path}.{key}" if path else key)
        elif isinstance(node, list):
            for value in node:
                walk(value, doc, path)

    for name in schemas.names():
        walk(schemas.schema(name), name, "")
    return found


class TestTheVocabularyHasOneMemberPerDimension:
    def test_no_two_quantities_measure_one_thing(self):
        """The property this item is about, asserted on the vocabulary
        rather than on a list of removed names."""
        by_dimension = collections.defaultdict(list)
        for quantity, dimension in schemas.DIMENSIONS.items():
            by_dimension[dimension].append(quantity)
        doubled = {d: sorted(q) for d, q in by_dimension.items() if len(q) > 1}
        assert doubled == {}, (
            f"these dimensions have more than one spelling: {doubled}")

    def test_every_member_declares_its_dimension(self):
        """A vocabulary member with no dimension cannot be checked by
        the clause above, which is how a fifth spelling of time would
        get in."""
        assert set(schemas.DIMENSIONS) == set(schemas.QUANTITIES), (
            f"QUANTITIES and DIMENSIONS disagree: "
            f"{sorted(set(schemas.QUANTITIES) ^ set(schemas.DIMENSIONS))}")


class TestEveryDeclarationIsInTheVocabulary:
    def test_both_channels_declare_only_known_quantities(self):
        unknown = {}
        for leaf, quantities in _declarations().items():
            for quantity, where in quantities.items():
                if quantity not in schemas.QUANTITIES:
                    unknown[f"{leaf} ({quantity})"] = where[:3]
        assert unknown == {}, unknown


class TestOneNameMeansOneThing:
    def test_no_leaf_carries_two_quantities(self):
        """`cores_busy` was a `count` in one block and a `ratio` in four
        others; `efficiency_score` was a `ratio` on the floor and a
        `share` in the finding that quotes it; `change` was a count of
        builders and a share of a baseline."""
        doubled = {}
        for leaf, quantities in _declarations().items():
            if _STATISTIC.match(leaf) or len(quantities) < 2:
                continue
            doubled[leaf] = {q: w[:2] for q, w in quantities.items()}
        assert doubled == {}, doubled

    def test_no_name_promises_a_unit_it_does_not_carry(self):
        """Five keys ended `_ratio` and were declared `share`. The name
        is what a consumer grepping the payload sees first."""
        lying = {}
        for leaf, quantities in _declarations().items():
            for suffix, promised in SUFFIXES.items():
                if not leaf.endswith(suffix):
                    continue
                wrong = sorted(q for q in quantities if q != promised)
                if wrong:
                    lying[leaf] = (promised, wrong)
        assert lying == {}, lying


@pytest.mark.parametrize("fixture", ["golden/mixed_task_kinds",
                                     "macro_micro/run"])
class TestThePayloadIsInTheNewUnitsAndTheSameNumbers:
    """A rename that changed a value would be a silent regression in
    every figure the report prints. The conversions are exact - µs and
    bytes are both integer multiples of what they replaced - so this
    asserts equality rather than closeness."""

    def test_a_duration_figure_is_an_integer_count_of_microseconds(self, fixture):
        import pathlib

        from tools.bga_view import payloads

        root = pathlib.Path(__file__).resolve().parents[2]
        payload = payloads(str(root / "tests/fixtures" / fixture))["report.json"]
        agreement = payload.get("timestamp_agreement") or {}
        if agreement.get("resolution_us") is None:
            pytest.skip(f"{fixture} carries no timestamp agreement")
        assert isinstance(agreement["resolution_us"], int), (
            "a µs figure converted from seconds is an integer count, "
            "not a float of seconds under a new name")

    def test_every_memory_figure_is_the_records_own_number(self, fixture):
        """The rename must not have changed a value. `ru_maxrss` is KiB
        and the payload is bytes, so the published figure is the
        record's own times 1024 - exactly, not rounded through
        megabytes, which is what the float it replaced did."""
        import json
        import pathlib

        from tools.bga_view import payloads

        root = pathlib.Path(__file__).resolve().parents[2]
        run = root / "tests/fixtures" / fixture
        report = run.parent / "plane2.json"
        if not report.exists():
            pytest.skip(f"{fixture} has no Plane 2 record beside it")
        record = json.loads(report.read_text())
        peaks = ((record.get("peak_memory") or {}).get("per_element")) or {}
        payload = payloads(str(run))["report.json"]
        checked = 0
        for row in payload.get("element_join") or []:
            measured = (peaks.get(row.get("element")) or {}).get("peak_rss_kb")
            if measured is None or row.get("peak_rss_bytes") is None:
                continue
            assert row["peak_rss_bytes"] == measured * 1024, row["element"]
            checked += 1
        assert checked, (
            "no element carried a peak this could compare - the clause "
            "would pass on a payload that published nothing")
