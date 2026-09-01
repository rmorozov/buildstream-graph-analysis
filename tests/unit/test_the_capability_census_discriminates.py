"""UX-470: the capability census, checked against itself.

`tools/dev_plane_capability.py` answers "what could a plane record and
does not". Like `UX-466`'s census and `UX-449`'s probe it is an
instrument, so what it needs is clauses that fail when it stops
discriminating rather than clauses that agree with whatever it says.

The four ways it could go quiet, and the clause for each:

- the `rusage` probe stops moving anything, so every unrecorded field
  reads `unmaintained` and the census reports no gap ever;
- the name map drifts from the record's keys, so a field recorded all
  along is reported as a gap - the failure that would have this census
  file a row about `UX-379`'s own work;
- the record-kind scan reads the `OPENS` path arena as record kinds,
  which is what its first run did;
- one of the verdicts becomes unreachable, so the census has only one
  thing it can say.
"""
import pathlib
import shutil
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import dev_plane_capability as capability  # noqa: E402

#: Both halves of this census compile a C source and run it, so a
#: machine without a compiler cannot be asked the question at all.
#: Skipped rather than passed vacuously - the same gate every other
#: module that builds the hook uses.
needs_cc = pytest.mark.skipif(
    shutil.which("cc") is None and shutil.which("gcc") is None,
    reason="no C compiler on PATH")

pytestmark = needs_cc


@pytest.fixture(scope="module")
def report(tmp_path_factory):
    """One real census: both planes compiled, run and read."""
    return capability.census(str(tmp_path_factory.mktemp("capability")))


class TestTheProbeReallyMovesWhatItClaims:
    """`unmaintained` means "exercised and still zero", so the exercise
    has to be real. A probe that did nothing would report every
    unrecorded field as unmaintained and the census would never find a
    gap - which is the shape of quiet this instrument is most likely to
    fail into."""

    def test_the_probe_moves_the_fields_the_hook_records(self, tmp_path):
        filled = capability.rusage_probe(str(tmp_path))
        moved = {name for name, value in filled.items() if float(value) > 0}
        # Every one of these is a field the hook records, so the census
        # never judges it - which is exactly why they are the honest
        # test of whether the probe does anything at all.
        assert {"ru_utime", "ru_maxrss", "ru_minflt", "ru_oublock",
                "ru_nvcsw"} <= moved, sorted(moved)

    def test_the_probe_reaches_the_block_layer(self, tmp_path):
        """`ru_inblock` is the one that needs `O_DIRECT`: a read served
        from the page cache is genuinely zero, so a probe that only
        opened and read the file it had just written would leave it at
        zero and prove nothing."""
        filled = capability.rusage_probe(str(tmp_path))
        assert float(filled["ru_inblock"]) > 0, filled["ru_inblock"]


class TestTheNameMapIsHeldToTheRecord:

    def test_a_map_claiming_a_key_no_record_carries_is_refused(self):
        with pytest.raises(SystemExit) as raised:
            capability._check_map("probe", {"ru_utime": "cpu_seconds"},
                                  {"utime", "stime"})
        assert "cpu_seconds" in str(raised.value)

    def test_the_shipped_map_passes_against_a_real_record(self, report):
        carried = set().union(*report["kinds"].values())
        capability._check_map("plane 2", capability.RUSAGE_KEYS, carried)

    def test_no_recorded_field_is_ever_reported_a_gap(self, report):
        recorded = {f for f, key in capability.RUSAGE_KEYS.items()
                    if key is not None}
        reported = {f for f, verdict, _d in report["plane2"]
                    if verdict == "gap"}
        assert not recorded & reported, sorted(recorded & reported)


class TestTheRecordKindsAreKindsAndNotPaths:

    def test_a_path_line_is_not_a_record_kind(self):
        """The `OPENS` record is followed by the paths it recorded, one
        per line. Reading the first token of every line called 35
        `.pyc` files Plane 2 record kinds on this module's first run."""
        kinds = capability._kinds([
            "START pid=1 element=a.bst cmd=/bin/sh",
            "OPENS pid=1 element=a.bst unique=2 dropped=0 part=0",
            "/usr/lib/python3.11/enum.py",
            "/etc/hostname",
        ])
        assert sorted(kinds) == ["OPENS", "START"]

    def test_the_real_run_finds_the_three_the_hook_writes(self, report):
        assert sorted(report["kinds"]) == ["END", "OPENS", "START"]


class TestBothVerdictsAreReachable:
    """A census that can only say one thing says nothing. Both of these
    are negative clauses about the tree as it is, and both must fail
    the day that stops being true - the gap one because the gaps were
    closed, which is the point of filing them."""

    def test_the_census_finds_a_gap_and_an_unmaintained_field(self, report):
        verdicts = {v for _f, v, _d in report["plane2"]}
        verdicts |= {v for _n, v, _d in (report["plane3"] or [])}
        assert "unmaintained" in verdicts, verdicts
        assert "gap" in verdicts, (
            "the census reports no gap at all. Either the six UX-470 found "
            "were closed - in which case say so here - or the instrument "
            "stopped discriminating")

    def test_the_hook_interposes_the_open_family_and_nothing_else(self, report):
        """What the hook can see about a process is what it interposes,
        and it is four symbols. Asserted so that a fifth arriving has
        to come and change this line - the capability side of the
        census is the half no emitted artifact states."""
        assert report["interposed"] == ["open", "open64", "openat",
                                        "openat64"], report["interposed"]
