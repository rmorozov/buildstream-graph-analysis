"""UX-680: the two remote-execution projections are not one number.

`unbounded_builders` (what BuildStream's REAPI buys - it moves whole
sandboxes to workers, so it removes the builder cap) and
`compiler_offload` (what a compiler-level service like recc/reclient
buys - it moves compilations out of the sandbox, so it removes compile
seconds from the agent) both remove time from the *same* critical-path
seconds. Summing them double-counts every second either alone already
removes, so the finding publishes `additive: false` and a sentence
saying why rather than a third, combined number.

Two things could make that claim false without a test catching it: the
flag flips (or the caveat sentence is dropped) while the numbers stay
put, or the numbers themselves stop being what the fixture measures.
This guards both, and the second by recomputing `wall_us_after` for each
half from the fixture directly - the sweep's own unbounded-capacity row
and Plane 2's `binary_cost` critical-path share - never through
`bga.cli`'s own projection helpers, so the finding cannot invent a
number neither of those recomputes.
"""
import contextlib
import io
import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "fixtures" / "macro_micro"

# Same set `bga.cli._COMPILER_LINKER_BINARIES` names - not imported,
# because the whole point of this half is a recomputation that does not
# trust the module under test for anything but the published finding.
_COMPILER_LINKER_BINARIES = frozenset({"cc1plus", "cc1", "ld", "lld", "gold"})


def _analyzed():
    """`bga analyze --format json` on the one committed fixture that
    carries a Plane 2 `binary_cost` (`tests/fixtures/macro_micro`) -
    the same in-process call `tools/dev_finding_coverage.py` uses, so
    this reads what a clone's `analyze` actually emits rather than a
    synthetic payload."""
    from bga.cli import main

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), \
            contextlib.redirect_stderr(io.StringIO()):
        main(["analyze", str(FIXTURE / "run"), "--format", "json"])
    return json.loads(buffer.getvalue())


@pytest.fixture(scope="module")
def analyzed():
    return _analyzed()


@pytest.fixture(scope="module")
def finding(analyzed):
    found = next(
        (f for f in analyzed["findings"] if f["id"] == "remote-execution-whatif"),
        None,
    )
    assert found is not None, (
        "tests/fixtures/macro_micro carries a Plane 2 binary_cost - the "
        "finding must fire on it")
    return found


class TestTheFindingSaysItIsNotAdditive:
    def test_additive_is_false(self, finding):
        assert finding["evidence"]["additive"] is False

    def test_the_text_carries_the_non_additivity_sentence(self, finding):
        from bga.findings import REMOTE_EXECUTION_NOT_ADDITIVE_SENTENCE

        text = finding["title"] + " ".join(finding.get("detail") or [])
        assert REMOTE_EXECUTION_NOT_ADDITIVE_SENTENCE in text


class TestTheTwoFiguresAreNotInvented:
    """Recomputed from the fixture's own primitives, not from
    `bga.cli`'s projection helpers - a mutation that changed what those
    helpers compute, or invented a number in the finding directly,
    reddens here either way."""

    def test_unbounded_builders_matches_the_sweeps_own_unbounded_row(
        self, finding,
    ):
        from bga.analyzer import BuildEfficiencyAnalyzer

        analyzer = BuildEfficiencyAnalyzer()
        analyzer.load(FIXTURE / "run")
        analyzer.normalize()
        scheduler = analyzer.replay_scheduler
        sweep = scheduler.capacity_sweep(
            resource="PROCESS", min_capacity=1, max_capacity=len(scheduler.tasks),
        )
        want_after = sweep.sweeps[-1]["makespan_us"]

        got = finding["evidence"]["unbounded_builders"]
        assert got["wall_us_after"] == pytest.approx(want_after)

    def test_compiler_offload_matches_the_by_binary_critical_path_share(
        self, finding, analyzed,
    ):
        """Per element, restricted to the critical path: a compile
        cannot remove more wall than its own element had, and an
        element off the path contributes nothing (`UX-680`'s session
        judgement - a global clamp let over-subscribed elements borrow
        slack that was never theirs)."""
        binary_cost = json.loads((FIXTURE / "plane2.json").read_text())["binary_cost"]
        path = analyzed["critical_path_detail"]
        path_us = sum(d["duration_us"] for d in path)
        remaining_us = 0
        for entry in path:
            compiler_us = sum(
                row["cpu_us"]
                for row in (binary_cost.get(entry["element_uid"], {}).get("by_cpu") or [])
                if row["binary"] in _COMPILER_LINKER_BINARIES
            )
            remaining_us += max(0, entry["duration_us"] - compiler_us)
        want_after = remaining_us

        got = finding["evidence"]["compiler_offload"]
        assert got["wall_us_before"] == pytest.approx(path_us)
        assert got["wall_us_after"] == pytest.approx(want_after)
