"""UX-386: `plane2/v3` is described as per-element, and mostly is not.

Both documents that describe the contract said the same thing, and it
was wrong. Measured on `tests/fixtures/macro_micro/plane2.json`, keying
each top-level block by whether it is a map over element uids:

```text
top-level keys                    24
keyed by element                   3   binary_cost, by_element, opens_captured
run-level                         21   by_binary, configure_phase, cpu_time,
                                       declared_vs_used, element_attribution,
                                       invocation_correlation, matched_count,
                                       max_concurrency, open_count,
                                       open_records_note, peak_memory,
                                       per_element_parallelism, process_count,
                                       redundant_operations,
                                       redundant_operations_coverage,
                                       spine_policy, static_binary_disclaimer,
                                       static_census, stream_coverage,
                                       wall_span_s, wrapped_command_exit_code
```

Three of twenty-four. The sentence has been wrong since `UX-297`
retired the record list and kept everything else - the "and nothing
else" was about the **per-process records**, which is what that item
removed, and it read as a claim about the *shape* of what is left.

The cost is not cosmetic. A reader who wants the host's peak memory,
the build's process count or whether the spine ran will not open a file
the documentation says holds per-element reductions - and those are
three of the questions a Plane 2 report is most often opened for.
"""
import json
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import plane2, schemas  # noqa: E402

FIXTURE = REPO / "tests/fixtures/macro_micro/plane2.json"

#: Every document that describes the contract in prose a reader meets.
#: `bga/schemas.py` is here because `analyze/v5`'s `plane2_coverage`
#: carries the same sentence, and the filing named two documents when
#: there were three - which is what a partition checked mechanically
#: catches and a reading does not.
DESCRIBING = (
    "docs/design/architecture.md",
    "docs/README.md",
)


def _partition():
    """`(element-keyed, run-level)` blocks of the committed report."""
    report = json.loads(FIXTURE.read_text(encoding="utf-8"))
    keyed, run = [], []
    for key, value in sorted(report.items()):
        if key in ("schema", "note"):
            continue
        by_element = isinstance(value, dict) and value and all(
            isinstance(name, str) and name.endswith(".bst")
            for name in list(value)[:5])
        (keyed if by_element else run).append(key)
    return keyed, run


def _describing_line(path):
    """The row that describes `plane2/v3` in one document."""
    text = (REPO / path).read_text(encoding="utf-8")
    for line in text.splitlines():
        if "`plane2/v3`" in line and line.lstrip().startswith("|"):
            return line
    raise AssertionError(f"{path} does not describe {plane2.SCHEMA}")


class TestTheShapeIsWhatTheFilingMeasured:
    def test_most_of_the_report_is_run_level(self):
        keyed, run = _partition()
        assert len(keyed) == 3, keyed
        assert len(run) == 21, run

    def test_the_element_keyed_blocks_are_the_ones_the_join_reads(self):
        """The other direction, so the fix is not "call it a bag of
        things": the element-keyed blocks are still a named class,
        because `bga correlate`'s whole join is built on them."""
        keyed, _run = _partition()
        assert keyed == ["binary_cost", "by_element", "opens_captured"]


class TestEveryDescriptionNamesBothClasses:
    """The Falsification. A sentence that names one class sends a reader
    after the other to a different file."""

    @pytest.mark.parametrize("path", DESCRIBING)
    def test_it_says_the_report_is_run_level(self, path):
        line = _describing_line(path).lower()
        assert "run-level" in line, (
            f"{path} describes {plane2.SCHEMA} without naming the class "
            f"that is 21 of its 24 blocks")

    @pytest.mark.parametrize("path", DESCRIBING)
    def test_it_still_names_the_per_element_half(self, path):
        line = _describing_line(path).lower()
        assert "per-element" in line, (
            f"{path} dropped the element-keyed half, which is what "
            f"`bga correlate` joins on")

    @pytest.mark.parametrize("path", DESCRIBING)
    def test_it_no_longer_claims_that_is_all_there_is(self, path):
        """The exact wording that was wrong: "the per-element
        reductions a capture computed, **and nothing else**"."""
        line = _describing_line(path).lower()
        assert "and nothing else" not in line, (
            f"{path} still claims the per-element reductions are the "
            f"whole of the report")

    @pytest.mark.parametrize("path", DESCRIBING)
    def test_the_retirement_is_attached_to_what_it_retired(self, path):
        """`UX-297`'s clause is worth keeping and worth attaching to
        what it was about - the per-process record list - rather than
        reading as a statement about the document's shape."""
        line = _describing_line(path)
        assert "UX-297" in line
        assert "record" in line.lower(), (
            f"{path} cites `UX-297` without saying it is the per-process "
            f"record list that went")


class TestTheSchemaSentenceAgrees:
    """The third instance, which the filing did not name. `analyze/v5`
    publishes `plane2_coverage.source`, whose description said the same
    wrong thing to a reader who opened the `?` door instead of a
    document."""

    @staticmethod
    def _source_description():
        document = schemas.schema(schemas.ANALYZE)
        return (document["properties"]["plane2_coverage"]["properties"]
                ["source"]["description"])

    def test_it_names_both_classes(self):
        text = self._source_description().lower()
        assert "run-level" in text, text
        assert "per-element" in text, text

    def test_it_does_not_claim_the_aggregates_are_all_of_it(self):
        text = self._source_description().lower()
        assert "the aggregates only" not in text
        assert "and nothing else" not in text


class TestTheProseTracksTheContractIdItDescribes:
    """A description of `plane2/v2` on a tree that writes `plane2/v3` is
    the same defect one field over, and `UX-384` moved the id in the
    round this landed in."""

    @pytest.mark.parametrize("path", DESCRIBING)
    def test_the_live_row_names_the_written_contract(self, path):
        assert f"`{plane2.SCHEMA}`" in _describing_line(path)

    @pytest.mark.parametrize("path", DESCRIBING)
    def test_the_retired_shapes_are_described_separately(self, path):
        text = (REPO / path).read_text(encoding="utf-8")
        for retired in plane2.SUPERSEDED:
            rows = [line for line in text.splitlines()
                    if f"`{retired}`" in line and line.lstrip().startswith("|")]
            assert rows, (path, retired)
            assert any(re.search(r"read,? never written", row, re.I)
                       for row in rows), (path, retired)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
