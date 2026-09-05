"""UX-383: Plane 2's last three per-element blocks reach the page.

`UX-370` moved `by_binary`, `binary_cost` and `configure_phase` into
`analyze/v5` so the page could render what Plane 2 measured. Three
blocks were left where they were and a fourth joined them. Measured on
`tests/fixtures/macro_micro/plane2.json` when this was filed:

```text
plane2 block        rendered in the terminal   in ANALYZE_PLANE2_KEYS
binary_cost                    yes                      yes
configure_phase                yes                      yes
cpu_time                       yes                       no    2,152 B
peak_memory                    yes                       no      973 B
resource_pressure              yes                       no   (UX-379)
```

So "was this element CPU-bound", "how much memory did its largest
process need" and "did it read from disk or get preempted" were
answerable at a terminal and not in the report a reader opens in a
browser - the split `UX-329` closed for coverage and `UX-370` for cost.

**The per-element halves go on the join row, not into tables of their
own.** That is `UX-382`'s placement rule - an attribute that needs
Plane 2 to exist is a field on an `element_join` row - and the first
draft here ignored it, wrote three per-element tables, and was caught
by `UX-288`'s: `element_cpu_time`, `element_peak_memory` and
`binary_cost` drawing the same nine elements. What is genuinely
run-level stays run-level, with each block's own `note`.

**The rule the rendering must not lose.** `peak_rss_bytes` is a
per-process maximum that must never be summed; the pressure counters
beside it are sums that may be. Both say which they are in their own
schema sentence, which is `UX-346`'s door and the place a reader about
to add two numbers actually looks.
"""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

from bga import schemas

FIXTURE = REPO / "tests/fixtures/macro_micro"

#: The three blocks, and the per-element fields each one now lands on
#: an `element_join` row.
FROM_EACH_BLOCK = {
    "cpu_time": ("cores_busy", "cpu_coverage", "cpu_us"),
    "peak_memory": ("peak_rss_bytes",),
    "resource_pressure": ("read_bytes", "written_bytes", "major_faults",
                          "involuntary_switches"),
}


@pytest.fixture(scope="module")
def payload():
    """`macro_micro`'s report, once - the one committed fixture with a
    Plane 2 report beside its run."""
    import pages

    from tools.bga_view import payloads
    return payloads(str(pages.FIXTURES["macro_micro"]))["report.json"]


class TestTheBlocksAreInTheContract:
    @pytest.mark.parametrize("key", sorted(FROM_EACH_BLOCK))
    def test_the_run_level_half_is_pinned(self, key):
        """`ANALYZE_PLANE2_KEYS` is what the pin asserts a full
        two-plane report carries. It named neither of these three."""
        assert key in schemas.ANALYZE_PLANE2_KEYS

    @pytest.mark.parametrize("key", sorted(FROM_EACH_BLOCK))
    def test_it_is_typed_at_the_top_level(self, key):
        """A key the document publishes and the schema does not type is
        a value `--schema` cannot answer for (`UX-328`)."""
        document = schemas.schema(schemas.ANALYZE)
        assert key in document["properties"], key

    @pytest.mark.parametrize("field", sorted(
        f for fields in FROM_EACH_BLOCK.values() for f in fields))
    def test_every_per_element_field_has_a_sentence(self, field):
        """`UX-201`/`UX-346`: the schema's own sentence is the `?` door,
        so a field with no description is a number with no unit and no
        meaning in front of the person reading it."""
        described = schemas._JOIN_ITEM_PROPERTIES.get(field) or {}
        assert described.get("description"), field
        assert len(described["description"]) > 40, field


class TestTheBlocksArriveInThePayload:
    def test_the_run_level_scalars_land(self, payload):
        """`cpu_time` is the one this fixture can show whole."""
        block = payload.get("cpu_time")
        assert block, "the run's own CPU total does not reach the page"
        assert block["total_cpu_us"] > 0
        assert block["note"], "the block arrives without its door"

    def test_the_per_element_halves_land_on_the_join_row(self, payload):
        rows = payload.get("element_join") or []
        assert rows, "the fixture has no join to carry them"
        row = rows[0]
        for field in ("cores_busy", "cpu_coverage", "cpu_us",
                      "peak_rss_bytes"):
            assert field in row, (field, sorted(row))

    def test_the_cpu_quantity_is_not_just_the_ratio(self, payload):
        """The gap this half closes. `cores_busy` said an element was
        CPU-bound and nothing said what that cost."""
        rows = payload.get("element_join") or []
        burned = [row["cpu_us"] for row in rows
                  if row.get("cpu_us") is not None]
        assert burned, "no element publishes the CPU it burned"
        assert max(burned) > 0

    def test_a_block_the_capture_lacks_is_absent_rather_than_empty(
            self, payload):
        """`UX-107`'s rule. This fixture predates `UX-379`, so it has no
        `resource_pressure` at all - and an empty block would read as
        "measured, and it was zero"."""
        report = json.loads((FIXTURE / "plane2.json").read_text("utf-8"))
        assert "resource_pressure" not in report, (
            "the fixture gained the block, so this clause no longer "
            "exercises the absence it exists for")
        assert "resource_pressure" not in payload


class TestThePressurePathIsGuardedWithoutAFixtureThatHasIt:
    """The committed fixture predates `UX-379`, so every clause above
    that touches `resource_pressure` passes whether the code carries it
    or not.

    The sweep is what showed this: removing the four counters from the
    join reddened **nothing**. So the join is driven here with a report
    that has the block, which is the only way this path is checked at
    all until a fixture is recaptured.
    """

    @staticmethod
    def _joined():
        from bga.correlate import _plane2_view
        return _plane2_view({
            "resource_pressure": {
                "available": True,
                "per_element": {
                    "a.bst": {"read_bytes": 4096, "written_bytes": 8192,
                              "major_faults": 7, "involuntary_switches": 21,
                              "measured": 3, "unmeasured": 0,
                              "coverage": 1.0},
                    # An element the capture measured only partly. The
                    # sweep put this here: with every counter present,
                    # a mutation writing `entry.get(name) or 0` was
                    # indistinguishable from the real thing.
                    "c.bst": {"read_bytes": 512, "measured": 1,
                              "unmeasured": 0, "coverage": 1.0},
                },
            },
        })

    @pytest.mark.parametrize("field,value", (
        ("read_bytes", 4096), ("written_bytes", 8192),
        ("major_faults", 7), ("involuntary_switches", 21)))
    def test_each_counter_reaches_the_join_row(self, field, value):
        assert self._joined()["a.bst"].get(field) == value, field

    def test_an_element_the_block_omits_gets_no_row_of_zeroes(self):
        """`UX-107`'s rule again: an absent counter must not read as a
        measured zero."""
        assert "b.bst" not in self._joined()

    def test_a_counter_the_capture_lacks_is_absent_and_not_zero(self):
        """The same rule one level down, and the clause the sweep
        asked for: `c.bst` has a read count and no fault count, and a
        fault count of zero would read as "measured, and it never
        faulted" - which is a different claim from "not measured"."""
        row = self._joined()["c.bst"]
        assert row["read_bytes"] == 512
        for missing in ("written_bytes", "major_faults",
                        "involuntary_switches"):
            assert missing not in row, (missing, row)


class TestOnePopulationIsStillDrawnOnce:
    """`UX-288`'s rule, which the first draft of this item broke. Three
    new per-element tables would have drawn the nine elements of
    `macro_micro` four times over."""

    def test_no_new_per_element_table_was_added(self, payload):
        for name in ("element_cpu_time", "element_peak_memory",
                     "element_resource_pressure"):
            assert name not in payload, (
                f"`{name}` is a second table over a population "
                f"`element_join` already carries - `UX-382` puts these "
                f"on the join row")

    def test_the_run_level_blocks_carry_no_element_map(self, payload):
        """`per_element` stays in `plane2.json`, where `bga correlate`
        reads it. Projecting it here is what would double the
        population."""
        for key in FROM_EACH_BLOCK:
            block = payload.get(key)
            if block:
                assert "per_element" not in block, key


class TestTheSummingRuleSurvivesTheRendering:
    """The Required Fix's one hard constraint: `peak_rss_bytes` must
    never be summed and the pressure counters may be. A rendering that
    lost the distinction would state the wrong thing about one column,
    and the reader would have no way to know which."""

    def test_the_maximum_says_it_is_one(self):
        text = schemas._JOIN_ITEM_PROPERTIES["peak_rss_bytes"]["description"]
        assert "maximum" in text.lower()
        assert "adding" in text.lower() or "added" in text.lower(), (
            "the peak's sentence does not warn against the operation it "
            "cannot support")

    @pytest.mark.parametrize("field", (
        "read_bytes", "written_bytes", "major_faults",
        "involuntary_switches"))
    def test_each_sum_says_it_is_one(self, field):
        text = schemas._JOIN_ITEM_PROPERTIES[field]["description"]
        assert "summed" in text.lower(), (field, text)

    def test_the_two_rules_are_not_the_same_sentence(self):
        """A distinction, not a rename: the maximum and the sums must
        not carry interchangeable prose."""
        peak = schemas._JOIN_ITEM_PROPERTIES["peak_rss_bytes"]["description"]
        summed = schemas._JOIN_ITEM_PROPERTIES["read_bytes"]["description"]
        assert peak != summed
        assert "summed" not in peak.lower()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
