"""UX-602: two published hard gates are named in no document.

Measured when this was filed, and re-measured in round 84:

```text
$ python3 -c "...json.load(with_timeline/analyze.json)['confidence']['hard_gates']"
blame_chain_coverage_full  critical_path_coverage_full
dominator_coverage_full    occupancy_within_capacity
ordering_violations_zero   run_identity_consistent          6
$ sed -n '1913,1926p' docs/spec/specification.md            4
$ <36 front-of-house .md> grep run_identity_consistent
                          |occupancy_within_capacity        0 hits
```

Part 33's text is outside the region a round may edit, so Part 32.7.5
records the full set - one row per key, in the order the code writes
them. This reads that table against a real run's `hard_gates` in both
directions, and reads the table's `Part 33.1's line` column against
33.1's own fenced blocks. The population is the analyzer's own output,
never a list restated here.
"""
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

SPEC = REPO / "docs/spec/specification.md"
RUN = REPO / "tests/fixtures/macro_micro/run"
STORED = REPO / "tests/fixtures/with_timeline/analyze.json"

ROW = "### 32.7.5 "
NOT_NAMED = "-"


def _registry_rows():
    """32.7.5's table, as (gate key, 33.1 cell, invariant cell).

    Bounded to the section, so the prose above it arguing for the table
    cannot be mistaken for the table.
    """
    text = SPEC.read_text(encoding="utf-8")
    start = text.index(ROW)
    note = text[start:text.index("\n---\n", start)]
    head = note.index("| `hard_gates` key |")
    table = note[head:note.index("\n\n", head)]
    rows = []
    for line in table.splitlines()[2:]:
        cells = [c.strip() for c in line.split("|")[1:-1]]
        rows.append((cells[0].strip("`"), cells[1], cells[2]))
    return rows


def _part_33_1_quantities():
    """The left-hand identifiers of 33.1's fenced blocks, in order.

    33.1's subject is its two fenced blocks; the sentence between them
    is the argument and is not read.
    """
    text = SPEC.read_text(encoding="utf-8")
    start = text.index("## 33.1 Hard Gates")
    section = text[start:text.index("\n## 33.2", start)]
    fenced = "\n".join(re.findall(r"```text\n(.*?)```", section, re.S))
    return re.findall(r"^([a-z_]+)\s*==", fenced, re.M)


def _published():
    """`confidence.hard_gates`, from a live run and from a stored one.

    Two runs of different shape, because a key that only one run
    publishes would make a registry row look wrong when it is the gate
    that is conditional.
    """
    import json

    from bga.analyzer import analyze_run

    live = analyze_run(RUN).confidence["hard_gates"]
    stored = json.loads(STORED.read_text(encoding="utf-8"))
    return live, stored["confidence"]["hard_gates"]


class TestTheRegistryIsThePublishedSet:
    """The finding itself: six published, four stated, two named
    nowhere. Both directions, because each has its own failure."""

    def test_the_run_publishes_gates_at_all(self):
        live, stored = _published()
        assert len(live) >= 4 and live.keys() == stored.keys(), (
            "the two runs do not publish the same gate keys, or the "
            "fixture broke - every claim below would pass vacuously",
            sorted(live), sorted(stored))

    def test_every_published_gate_has_a_registry_row(self):
        live, stored = _published()
        recorded = {key for key, _, _ in _registry_rows()}
        unnamed = sorted((live.keys() | stored.keys()) - recorded)
        assert not unnamed, (
            "a hard gate is published and Part 32.7.5 does not name it - "
            "this is UX-602's defect arriving again", unnamed)

    def test_every_registry_row_names_a_published_gate(self):
        live, stored = _published()
        recorded = {key for key, _, _ in _registry_rows()}
        stale = sorted(recorded - (live.keys() | stored.keys()))
        assert not stale, (
            "Part 32.7.5 records a hard gate no run publishes; the row "
            "outlived its gate", stale, sorted(live))

    def test_the_rows_are_in_the_order_the_code_writes_them(self):
        """32.7.5 says "in the order the code writes them", which is the
        `hard_gates` dict's own order."""
        live, _ = _published()
        assert [key for key, _, _ in _registry_rows()] == list(live), (
            "32.7.5's rows are not in the published order",
            [key for key, _, _ in _registry_rows()], list(live))


class TestTheRowsSayWhichFourPart331States:
    """The other half of the gap: which gates a reader of Part 33.1
    would already have met, and which two are only here."""

    def test_the_named_column_is_exactly_part_33_1s_blocks(self):
        quantities = _part_33_1_quantities()
        assert quantities, (
            "33.1's fenced blocks parsed to nothing; the column below "
            "would match an empty set")
        claimed = []
        for key, cell, _ in _registry_rows():
            if cell == NOT_NAMED:
                continue
            match = re.match(r"`([a-z_]+)\s*==", cell)
            assert match, (
                "32.7.5's `Part 33.1's line` cell is neither `-` nor an "
                "expression Part 33.1 could contain", key, cell)
            claimed.append(match.group(1))
        assert claimed == quantities, (
            "32.7.5's 33.1 column is not Part 33.1's own list, in order",
            claimed, quantities)

    def test_each_named_row_quotes_the_line_for_its_own_gate(self):
        """Without this the column could be 33.1's four list against the
        wrong four keys, and the two that are absent would be a
        different two."""
        for key, cell, _ in _registry_rows():
            if cell == NOT_NAMED:
                continue
            quantity = re.match(r"`([a-z_]+)", cell).group(1)
            assert key.startswith(quantity), (
                "32.7.5 quotes a Part 33.1 line beside a gate it is not "
                "the line for", key, cell)

    def test_each_omitted_gate_cites_the_invariant_that_carries_it(self):
        """A gate 33.1 does not state is only defensible because Part 34
        does; the row has to say which."""
        for key, cell, invariant in _registry_rows():
            if cell != NOT_NAMED:
                continue
            assert re.fullmatch(r"I\d+", invariant), (
                "a gate Part 33.1 omits must name its Part 34 invariant",
                key, invariant)
            assert f"## {invariant} " in SPEC.read_text(encoding="utf-8"), (
                "32.7.5 cites an invariant Part 34 does not state",
                key, invariant)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
