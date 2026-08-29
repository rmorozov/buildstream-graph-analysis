"""UX-384: a redundancy finding no longer carries every element it spans.

`UX-375` capped `redundant_operations` at 40 findings. What that cap
does not bound is the *names inside* a row, and with the rows fixed the
list was the one term still `O(elements)`. Measured with 40 capped rows
and the element count varied:

```text
 elements  rows  section B  elements B   share
       40    40     36,901      28,840   78.2%
      400    40    296,221     288,040   97.2%
     1200    40    880,341     872,040   99.1%
```

A capped section that is 99% element names at 1,200 elements is not a
capped section. `element_count` and `worst_element` were already
published beside the list and are what a consumer reads, so the list
went and the contract moved to `plane2/v3` - removing a published key
being what makes a version, on the precedent `UX-297` set when it
removed the per-process record list for the same reason.

**The item said nothing read `elements`, and that was wrong.**
`bga/correlate.py` did, at one site, for `len()` alone - the sentence
"it pays 20.4s for an operation 3 other elements also run". The row is
keyed by `worst_element`, so that length is exactly `element_count - 1`
and the sentence is preserved rather than dropped. Recorded here
because a filing's premise being false is the kind of thing the next
round should be able to find.
"""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import contracts, plane2  # noqa: E402
from bga.correlate import _other_element_count  # noqa: E402
from tools.bst_native_build_tracer import (  # noqa: E402
    REDUNDANCY_FINDINGS_MAX,
    detect_redundant_operations,
)


def _records(signatures, elements):
    """One signature per command, run once under each of `elements`."""
    names = [f"element-{index:03d}.bst" for index in range(elements)]
    out = []
    for index in range(signatures):
        for name in names:
            out.append({
                "element": name, "cmd": f"cc -c file{index}.c",
                "open": False, "start_ts": 0.0, "end_ts": 1.0,
                "duration_s": 1.0, "pid": index, "src": "hook",
                "invocation": "1", "exec_chain": 1,
            })
    return out


def _names_in(finding):
    """How many element names a finding carries, at any depth.

    Counting only string *values* was this clause's own first draft and
    it did not discriminate: the defect being guarded puts the names in
    a **list**, which `isinstance(value, str)` walks straight past. The
    mutation that restores `elements` reddened two other clauses and
    not this one, which is how it was found.
    """
    total = 0
    for value in finding.values():
        if isinstance(value, str):
            total += value.endswith(".bst")
        elif isinstance(value, (list, tuple)):
            total += sum(isinstance(item, str) and item.endswith(".bst")
                         for item in value)
    return total


def _section_bytes(elements):
    findings, _coverage = detect_redundant_operations(
        _records(REDUNDANCY_FINDINGS_MAX + 20, elements))
    return len(json.dumps(findings, separators=(",", ":"))), findings


class TestTheSectionIsBoundedInBothDimensions:
    def test_the_rows_are_capped(self):
        """`UX-375`'s half, restated so this file fails if it regresses
        - the two bounds are one property and a reader of either wants
        to know the other holds."""
        _size, findings = _section_bytes(40)
        assert len(findings) == REDUNDANCY_FINDINGS_MAX

    def test_the_bytes_do_not_grow_with_the_element_count(self):
        """The Falsification, and the number it is set against.

        Same signatures, thirty times the elements. Measured before and
        after, with the row cap in place throughout:

        ```text
                    before      after
              40    36,901 B    7,581 B
             400   296,221 B    7,701 B
            1200   880,341 B    7,821 B
                    23.8x        1.03x
        ```

        1.03x rather than 1.00x is not a leak: it is digit width. Each
        row publishes `element_count` and `occurrence_count`, and 1200
        is two characters longer than 40. That is `O(log elements)` over
        a fixed row count, which is what "bounded" means here - the
        clause below pins the term that would be linear.
        """
        small, _ = _section_bytes(40)
        huge, _ = _section_bytes(1200)
        assert huge < small * 1.1, (
            f"the section is {small:,} B over 40 elements and {huge:,} B "
            f"over 1,200 - something in a row still scales with the "
            f"population")

    def test_a_row_names_exactly_one_element_whatever_the_population(self):
        """The term that was linear, pinned directly. One name per row -
        `worst_element` - so the bytes spent on element names are the
        row count times a name, at any population."""
        widths = []
        for elements in (40, 400, 1200):
            _size, findings = _section_bytes(elements)
            named = [_names_in(finding) for finding in findings]
            assert set(named) == {1}, (elements, sorted(set(named)))
            widths.append(sum(len(f["worst_element"]) for f in findings))
        assert len(set(widths)) == 1, (
            f"the bytes spent on element names move with the population: "
            f"{widths}")

    def test_no_finding_names_an_element_it_merely_spans(self):
        _size, findings = _section_bytes(400)
        carrying = [f for f in findings if "elements" in f]
        assert carrying == [], (
            f"{len(carrying)} finding(s) still carry the list")


class TestTheWidthIsStillPublished:
    """The other direction, so the fix is not "drop what the section
    said": how wide a finding is and which element paid most are both
    still there, which is all any consumer read."""

    def test_a_finding_says_how_many_elements_it_spans(self):
        _size, findings = _section_bytes(7)
        assert findings[0]["element_count"] == 7

    def test_a_finding_still_names_the_element_that_paid_most(self):
        _size, findings = _section_bytes(7)
        assert findings[0]["worst_element"].startswith("element-")


class TestTheSentenceCorrelateWritesIsUnchanged:
    """`bga correlate` was the one reader, and it used the list for
    `len()`. The row is keyed by `worst_element`, so the count it wants
    is `element_count - 1`."""

    def test_it_counts_the_others_from_the_count(self):
        assert _other_element_count({"element_count": 4}) == 3

    def test_a_report_written_before_the_count_existed_still_reads(self):
        """A store is full of captures from before `UX-375` added
        `element_count`; `tests/fixtures/macro_micro/plane2.json` is
        one. The sentence has to say the same thing about them, so the
        list is still read when it is the only thing there."""
        assert _other_element_count(
            {"elements": ["a.bst", "b.bst", "c.bst"]}) == 2

    def test_the_committed_fixture_is_such_a_report(self):
        report = json.loads(
            (REPO / "tests/fixtures/macro_micro/plane2.json"
             ).read_text(encoding="utf-8"))
        findings = report.get("redundant_operations") or []
        assert findings, "the fixture has no redundancy findings"
        assert "elements" in findings[0]
        assert "element_count" not in findings[0], (
            "the fixture gained a count, so this clause no longer "
            "exercises the older shape it exists for")

    def test_a_finding_with_neither_does_not_crash(self):
        assert _other_element_count({}) == 0

    def test_a_lone_element_never_goes_negative(self):
        assert _other_element_count({"element_count": 1}) == 0
        assert _other_element_count({"element_count": 0}) == 0


class TestTheContractMoved:
    """Removing a published key is a version, not an addition."""

    def test_the_report_stamps_v3(self):
        assert plane2.SCHEMA == "plane2/v3"

    def test_the_shape_it_replaced_is_inventoried_as_read(self):
        assert plane2.PREVIOUS_SCHEMA == "plane2/v2"
        assert "plane2/v2" in contracts.superseded(), (
            "the shape a store is full of is not declared as one the "
            "tool still opens")
        assert "plane2/v2" not in contracts.printable()

    def test_the_whole_chain_is_still_openable(self):
        for shape in (plane2.SCHEMA, plane2.PREVIOUS_SCHEMA,
                      plane2.LEGACY_SCHEMA):
            assert shape in contracts.ids(), shape

    def test_an_unstamped_report_still_reads_as_the_legacy_shape(self):
        assert plane2.shape_of({}) == "plane2/v1"
        assert plane2.shape_of({"schema": "plane2/v2"}) == "plane2/v2"
        assert plane2.shape_of({"schema": "plane2/v3"}) == "plane2/v3"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
