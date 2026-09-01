"""UX-460: every finding a clone can conclude is reached by a capture a
clone has, or is declared unreachable with a reason.

`FINDING_READERS` is the registry of what `bga analyze` can conclude.
Nothing read it against the fixtures, so a finding could be added,
wired, documented and shipped while **no committed capture ever
produced it** - and the suite would stay green, because every guard
that touches a finding builds its own synthetic payload.

Derived by running `analyze`, never by scanning sources. A first cut of
this census did scan, and reported `efficiency-score`,
`optimization-horizon` and `certified-headroom` as named by no test; in
snake_case they are in 7, 12 and 7 files. A text scan cannot tell a name
from a spelling of it - fixing guide s5, in the census written to find
s5 gaps.
"""
import functools
import subprocess
import sys

import pytest

from bga.findings import FINDING_READERS
from tools import dev_finding_coverage as census


@functools.lru_cache(maxsize=1)
def _census():
    """One census for the whole file - it analyses every committed
    capture, and doing that per clause is the cost of the file. A
    module-level cache rather than a class-scoped fixture, which pytest
    warns is deprecated when written as an instance method."""
    return census.coverage(tracked_only=True)


@pytest.fixture
def got():
    return _census()


class TestEveryFindingIsReachedOrDeclared:
    def test_the_census_covers_the_whole_registry(self, got):
        """A finding missing from the census is invisible to every
        clause below, so the population is asserted before it is read."""
        assert set(got) == set(FINDING_READERS), (
            set(got) ^ set(FINDING_READERS))

    def test_nothing_is_neither_produced_nor_declared(self, got):
        """The item's whole claim. A finding with no capture and no
        declaration is the failure - not a gap somebody will notice."""
        orphans = sorted(name for name, where in got.items()
                         if not where and name not in census.UNREACHABLE)
        assert orphans == [], (
            f"finding(s) no committed capture produces and "
            f"tools/dev_finding_coverage.UNREACHABLE does not declare: "
            f"{orphans}. Add a capture that reaches them (see "
            f"tests/fixtures/topologies.py) or declare why none can.")

    def test_a_declaration_carries_a_reason(self):
        """"Declared unreachable" with no sentence is silence wearing a
        key. `tests/skip_reasons.py` is the same shape one axis over."""
        assert census.UNREACHABLE, "the declaration map is empty"
        for name, reason in census.UNREACHABLE.items():
            assert name in FINDING_READERS, (
                f"{name} is declared unreachable and is not a finding")
            assert len(reason.split()) >= 8, (name, reason)

    def test_a_declared_finding_is_not_also_produced(self, got):
        """A declaration that has quietly become false is worse than no
        declaration: it says a capture cannot exist while one does."""
        contradicted = sorted(name for name in census.UNREACHABLE
                              if got.get(name))
        assert contradicted == [], (
            f"declared unreachable and yet produced: {contradicted}. "
            f"Remove the declaration - the reason it gives is no longer "
            f"true of this tree.")

    def test_the_transfer_finding_has_a_capture_of_its_own(self, got):
        """`cache-transfer-cost` was the last orphan (`UX-459`), and it
        needs two things at once no other fixture has together: a
        Pipeline Summary, and tasks whose primary resource is DOWNLOAD.
        Named rather than left to the count, so removing that fixture
        says which one went."""
        assert "tests/fixtures/a_build_that_pulls" in got["cache-transfer-cost"], (
            got["cache-transfer-cost"])


class TestTheCensusReadsTheTreeAndNotTheMachine:
    def test_it_counts_what_git_tracks_by_default(self):
        """The correction the tool was born from: the first cut globbed
        `examples/*/.bga/runs/*/run` and called what it found committed
        captures. `UX-189` decided a clone ships none, and every
        `.bga/.gitignore` holds `*`, so those exist only on a machine
        that has built them."""
        tracked = set(census.captures(tracked_only=True))
        local = set(census.captures(tracked_only=False))
        assert tracked <= local
        assert not [run for run in tracked if ".bga" in str(run)], (
            "a .bga capture is being counted as tracked, which "
            "git ls-files says is impossible")

    def test_the_command_in_the_task_file_runs(self):
        """The Acceptance Test of `UX-459` and `UX-460` is this command,
        and a census whose CLI has drifted is a census a round cannot
        re-run."""
        done = subprocess.run(
            [sys.executable, "tools/dev_finding_coverage.py"],
            capture_output=True, text=True, cwd=census.REPO)
        assert done.returncode == 0, done.stderr[-2000:]
        assert "0 neither" in done.stdout, done.stdout[-2000:]
