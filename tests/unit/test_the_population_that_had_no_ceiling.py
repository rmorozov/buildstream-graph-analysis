"""UX-375: the one Plane 2 population with no bound.

Every other population in `plane2/v2` is bounded — `binary_cost` takes
a `top_n` of 5, and `by_binary`, `per_element_parallelism`,
`opens_captured` and `static_census` are `O(elements)` or
`O(distinct binaries)`. `redundant_operations` returned every finding
and `load_and_summarize` wrote the list whole, so on a build with
repeated work in it the section was most of the report:

```text
run   elems    stored  above 50ms     bytes  % of report
C         4       267         179   155,005        91.7%
D        10       267         206   174,399        87.2%
E        40       267         247   278,510        76.8%
```

**The floor that existed was applied to the rendering, not to the
contract.** `_REDUNDANCY_MIN_SECONDS = 0.05` was read in `_format_text`
alone: the terminal dropped the sub-50ms findings and said how many,
and the stored JSON kept all of them. Two different answers to "what is
a finding", and the larger one was the one that went to disk and to
every consumer.

After, on the same 40-element capture:

```text
findings stored : 40      (was 267)
bytes           : 32,728  (was 278,510)
coverage        : excluded_below_floor 20, omitted_beyond_cap 207,
                  findings_above_floor 247, findings_cap 40
```

Both reasons a finding can be missing are named, because a shorter list
reads as a cleaner build — which is `UX-73`'s own argument for the two
exclusion counts that were already there.
"""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools.bst_native_build_tracer import (    # noqa: E402
    _REDUNDANCY_MIN_SECONDS,
    REDUNDANCY_FINDINGS_MAX,
    detect_redundant_operations,
)

FIXTURE = REPO / "tests/fixtures/macro_micro/plane2.json"


def _records(signatures, seconds=1.0, elements=("a.bst", "b.bst")):
    """One signature per distinct command, run once under each element -
    which is what makes it a finding at all (`UX-73`: 2+ *resolved*
    elements)."""
    out = []
    for index in range(signatures):
        for element in elements:
            out.append({
                "element": element, "cmd": f"cc -c file{index}.c",
                "open": False, "start_ts": 0.0, "end_ts": seconds,
                "duration_s": seconds, "pid": index, "src": "hook",
                "invocation": "1", "exec_chain": 1,
            })
    return out


class TestThePopulationIsBounded:
    def test_more_signatures_than_the_cap_are_cut_to_it(self):
        findings, coverage = detect_redundant_operations(
            _records(REDUNDANCY_FINDINGS_MAX + 60))
        assert len(findings) == REDUNDANCY_FINDINGS_MAX
        assert coverage["findings_cap"] == REDUNDANCY_FINDINGS_MAX
        assert coverage["omitted_beyond_cap"] == 60

    def test_the_bound_holds_whatever_the_signature_count(self):
        """The Falsification's own shape: the same elements, different
        numbers of distinct signatures. The stored length must not
        track the input."""
        lengths = set()
        for signatures in (5, 50, 500):
            findings, _ = detect_redundant_operations(_records(signatures))
            lengths.add(len(findings))
            assert len(findings) <= REDUNDANCY_FINDINGS_MAX, signatures
        assert lengths == {5, REDUNDANCY_FINDINGS_MAX}, (
            f"the list is not bounded by the cap: {sorted(lengths)}")

    def test_a_short_list_is_not_capped_and_says_so(self):
        findings, coverage = detect_redundant_operations(_records(5))
        assert len(findings) == 5
        assert coverage["omitted_beyond_cap"] == 0

    def test_what_survives_the_cap_is_the_most_costly(self):
        """The cap is only safe because the list is ranked first. A cap
        applied to an unsorted list would drop findings by accident of
        dictionary order."""
        records = []
        for index in range(REDUNDANCY_FINDINGS_MAX + 10):
            # The last signature is by far the most expensive, and it is
            # constructed last so insertion order would lose it.
            seconds = 100.0 if index == REDUNDANCY_FINDINGS_MAX + 9 else 0.1
            records += _records(1, seconds=seconds)[:2]
            for record in records[-2:]:
                record["cmd"] = f"cc -c sig{index}.c"
        findings, _ = detect_redundant_operations(records)
        assert findings[0]["max_element_duration_s"] == pytest.approx(100.0)
        durations = [f["max_element_duration_s"] for f in findings]
        assert durations == sorted(durations, reverse=True)


class TestTheFloorStaysADisplayThresholdAndSaysSo:
    """The filing offered two endings for the floor. The obvious one -
    move it into the contract - is wrong here, and the fixture is what
    says so: **14 of `macro_micro`'s 20 findings fall below it**, and
    `correlate.py` iterates every finding to build each element's
    `redundancy_count` and `worst_redundancy`. Moving the floor would
    have changed a published per-element number for a reason no reader
    could see. So the floor stays a display threshold and the contract
    states that it does."""

    def test_a_sub_floor_finding_is_still_stored(self):
        findings, coverage = detect_redundant_operations(
            _records(3, seconds=_REDUNDANCY_MIN_SECONDS / 10))
        assert len(findings) == 3, (
            "the display floor was applied to the contract, which silently "
            "changes every element's redundancy_count in correlate")
        assert coverage["display_floor_seconds"] == _REDUNDANCY_MIN_SECONDS

    def test_the_contract_says_the_list_holds_what_the_terminal_hides(self):
        _findings, coverage = detect_redundant_operations(_records(3))
        note = coverage["note"]
        assert "display_floor_seconds" in note, (
            "nothing tells a reader of the JSON that it holds findings the "
            "terminal will not show")
        assert "redundancy_count" in note

    def test_the_cap_still_bounds_a_list_full_of_small_findings(self):
        """The cap is the bound, and it works whatever the floor does -
        which is why it is the half that had to land."""
        findings, coverage = detect_redundant_operations(
            _records(REDUNDANCY_FINDINGS_MAX + 30,
                     seconds=_REDUNDANCY_MIN_SECONDS / 10))
        assert len(findings) == REDUNDANCY_FINDINGS_MAX
        assert coverage["omitted_beyond_cap"] == 30
        assert coverage["total_findings"] == REDUNDANCY_FINDINGS_MAX + 30


class TestEveryFindingSaysHowWideItIs:
    def test_a_finding_carries_its_element_count(self):
        findings, _ = detect_redundant_operations(
            _records(1, elements=("a.bst", "b.bst", "c.bst")))
        assert findings[0]["element_count"] == 3
        assert findings[0]["element_count"] == len(findings[0]["elements"])


class TestTheCommittedCaptureIsUnchangedByThis:
    """The other direction, so the fix is not "drop the section": the
    fixture has 20 findings, well under the cap, and every one of them
    must survive."""

    def test_the_fixture_is_below_the_cap(self):
        stored = json.loads(FIXTURE.read_text(encoding="utf-8"))
        findings = stored.get("redundant_operations") or []
        assert 0 < len(findings) <= REDUNDANCY_FINDINGS_MAX, (
            f"{len(findings)} findings - this fixture no longer discriminates "
            f"between 'the cap did nothing' and 'the cap dropped everything'")

    def test_the_fixture_is_why_the_floor_did_not_move(self):
        """Not a regression guard - a record of the measurement that
        chose between the filing's two endings, so a later round does
        not re-derive it. Most of this capture's findings are below the
        display floor, and `correlate` counts every one of them."""
        stored = json.loads(FIXTURE.read_text(encoding="utf-8"))
        findings = stored.get("redundant_operations") or []
        below = [f for f in findings
                 if f["max_element_duration_s"] < _REDUNDANCY_MIN_SECONDS]
        assert len(below) >= len(findings) // 2, (
            f"only {len(below)} of {len(findings)} findings are below the "
            f"display floor; the argument for keeping the floor in the "
            f"renderer rested on that being most of them, and it should be "
            f"re-made rather than assumed")
        source = (REPO / "bga/correlate.py").read_text(encoding="utf-8")
        assert "redundancy_count" in source and (
            'native_report.get("redundant_operations")' in source), (
            "correlate no longer iterates every finding, which is half the "
            "reason the floor stayed where it is")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
