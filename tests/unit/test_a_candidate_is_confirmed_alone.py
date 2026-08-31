"""UX-455: the parse read a parallel run against single-process floors.

`tests/tiers.py`'s floors are seconds a file costs with nothing else on
the CPU - that is how every one of them was measured, and what
`LARGE_FLOOR_S = 15.0` means. `make test-tiers` parses a `-n auto`
report and compares it against them. For most files the two numbers are
the same; over the 145 files whose `tiers.py` comment records their
seconds, the median parallel/recorded ratio on an unchanged tree is
**1.010** (q1 0.916, q3 1.099), so there is no factor to divide out.

For some files they are not, and 1.0s is a floor a small file can cross
on contention alone:

```text
                                          alone   under -n auto  ratio
test_the_agent_configuration_holds.py     0.72s       1.31s       1.82
```

Round 71 met that as one of three rows in a red `make test-tiers`, two
real and this one not - and a parse that names a file nobody should
move is a parse people learn to skim.

So `dev_tier_drift.confirm()` re-runs each accused file **by itself, in
one process**, which is the quantity the floors are in. Only the
accused, so a green tree pays nothing.

What this file holds is that the confirmation is *load-bearing* rather
than decorative: that it clears a file the parallel report accuses and
the floors do not, that it keeps one they both accuse, that a
confirmation which could not be made is not read as a clearance, and
that the seconds the tool then prints are the confirmed ones and not
the parallel ones a reader would otherwise copy into `tiers.py`.
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import tiers                                        # noqa: E402
from tools import dev_tier_drift as drift                      # noqa: E402

#: A file listed small that the parallel report puts over the medium
#: floor, and the seconds a single-process run of it really costs. Both
#: are `UX-455`'s own measurement rather than invented numbers.
CONTENDED = "tests/unit/test_the_agent_configuration_holds.py"
CONTENDED_PARALLEL = 1.31
CONTENDED_ALONE = 0.72


def _rows(times):
    return drift.drift(times)


def test_the_parallel_report_alone_would_accuse_it():
    """The premise, asserted rather than assumed - otherwise the clause
    below could pass because the file stopped being a candidate."""
    rows = _rows({CONTENDED: CONTENDED_PARALLEL})
    assert [row[0] for row in rows] == [CONTENDED], rows
    assert drift.listed_tier(CONTENDED) == "small"
    assert drift.tier_for(CONTENDED_PARALLEL) == "medium"


def test_a_confirmation_under_the_floor_clears_it(monkeypatch):
    monkeypatch.setattr(drift, "alone_seconds",
                        lambda name, python=None: CONTENDED_ALONE)
    kept, cleared = drift.confirm(_rows({CONTENDED: CONTENDED_PARALLEL}))
    assert kept == []
    assert cleared == [(CONTENDED, CONTENDED_PARALLEL, CONTENDED_ALONE)]


def test_a_confirmation_over_the_floor_keeps_it(monkeypatch):
    """The other direction, because a confirmation that cleared
    everything would satisfy the clause above and guard nothing."""
    monkeypatch.setattr(drift, "alone_seconds",
                        lambda name, python=None: 1.35)
    kept, cleared = drift.confirm(_rows({CONTENDED: CONTENDED_PARALLEL}))
    assert cleared == []
    assert [row[0] for row in kept] == [CONTENDED]


def test_the_kept_row_carries_the_confirmed_seconds(monkeypatch):
    """What a reader copies into `tiers.py` is the number the floors
    are in. A kept row that still carried the parallel seconds would
    put this run's contention into the file's comment for good."""
    monkeypatch.setattr(drift, "alone_seconds",
                        lambda name, python=None: 1.35)
    kept, _ = drift.confirm(_rows({CONTENDED: CONTENDED_PARALLEL}))
    assert kept[0][1] == 1.35, kept


def test_a_confirmation_that_could_not_run_is_not_a_clearance(monkeypatch):
    """`None` means the re-run did not happen. Reading that as "under
    the floor" would turn every broken confirmation into silence, which
    is the failure mode a gate can least afford."""
    monkeypatch.setattr(drift, "alone_seconds", lambda name, python=None: None)
    kept, cleared = drift.confirm(_rows({CONTENDED: CONTENDED_PARALLEL}))
    assert cleared == []
    assert [row[0] for row in kept] == [CONTENDED]


def test_the_re_run_is_really_single_process(monkeypatch):
    """The load-bearing half, and the clause that had to be added.

    The first cut of this file asserted only that the real re-run came
    back under the floor. Mutating `alone_seconds` to pass `-n auto`
    left it **green** - one file on its own under xdist has almost
    nothing to contend with, so the number barely moves and the result
    cannot tell you how it was produced. A guard on the result of a
    measurement is not a guard on the measurement.

    So the call itself is observed. `subprocess.run` is where the
    quantity is decided, and its argv and environment are the decision
    rather than a description of it.
    """
    seen = {}

    class Done:
        returncode = 0

    def watch(argv, **kwargs):
        seen["argv"] = list(argv)
        seen["env"] = kwargs.get("env") or {}
        return Done()

    monkeypatch.setattr(drift.subprocess, "run", watch)
    drift.alone_seconds(CONTENDED)                 # no report -> None
    argv = seen["argv"]
    assert "-n" not in argv or "auto" not in argv, argv
    assert argv[argv.index("-p") + 1] == "no:xdist", argv
    assert seen["env"].get("PYTEST_XDIST") == "", (
        "the Makefile's PYTEST_XDIST would be inherited, and it carries "
        "`-n auto` into this run: " + repr(seen["env"].get("PYTEST_XDIST")))


def test_the_measurement_is_a_real_single_process_run():
    """Not a mock: the function this file mocks elsewhere has to work.

    Run on the file the whole item is about, and asserted against the
    floor rather than against a fixed second-count - the point is which
    side of 1.0 it lands on, and a pinned number would make this a
    timing test that fails on a slower laptop.
    """
    alone = drift.alone_seconds(CONTENDED)
    assert alone is not None, "the confirmation could not be run at all"
    assert alone < tiers.MEDIUM_FLOOR_S, (
        f"{CONTENDED} measured {alone:.2f}s alone, at or over the "
        f"{tiers.MEDIUM_FLOOR_S}s medium floor - either the file grew and "
        f"belongs in MEDIUM now, or this machine is loaded")


if __name__ == "__main__":  # pragma: no cover
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
