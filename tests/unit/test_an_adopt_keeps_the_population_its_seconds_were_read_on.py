"""UX-955: `adopt` wrote `files` on every run but never `population`,
so `against` kept scaling a `POPULATION_CLASS` guard's `expected`
seconds by a tree size the guard was no longer measured on - `UX-929`'s
reading found the backlog guard at population 737 while the tree it
was actually run against had grown to 942, a 1.28x scale that hid a
1.9x regression as `ok`.

`adopt` now rewrites `population` for every name it samples, through
`population_for` - the same helper `record` uses - so `files` and
`population` move together.
"""

import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import tiers
from tools import dev_tier_drift as drift

#: `UX-929`'s own reading: the backlog guard, whose population is the
#: scenario count `dev_close_task._backlog_counts()` reads.
THIS_FILE = "tests/unit/test_docs_links_and_commands.py"
RECORDED_SECONDS = 34.03


def _reference(recorded_population):
    """A reference built by `drift.record`, `population` patched to
    `recorded_population` - the number the seconds above were read on."""
    times = dict(tiers.recorded())
    times[THIS_FILE] = RECORDED_SECONDS
    reference = drift.record(times, "a recording run")
    reference["population"] = dict(reference.get("population") or {})
    reference["population"][THIS_FILE] = recorded_population
    return reference


def _candidate():
    """A same-clock candidate (`shift` 1.0) that samples `THIS_FILE`."""
    times = dict(tiers.recorded())
    times[THIS_FILE] = RECORDED_SECONDS
    return drift.record(times, "a candidate run")


def _reading(scale):
    times = dict(tiers.recorded())
    times[THIS_FILE] = RECORDED_SECONDS * scale
    return times


class TestAdoptRewritesThePopulation:
    def test_adopt_rewrites_the_name_it_sampled(self, monkeypatch):
        reference = _reference(recorded_population=737)
        monkeypatch.setattr(drift, "population_size", lambda _pop: 942)
        document, _added = drift.adopt(reference, _candidate())
        assert document["population"][THIS_FILE] == 942, document["population"]

    def test_a_name_it_did_not_sample_keeps_its_old_population(self, monkeypatch):
        """`for each POPULATION_CLASS name it samples` (Decision) - a
        run that never measured a name must not invent a size for it."""
        reference = _reference(recorded_population=737)
        candidate = drift.record(
            {name: seconds for name, seconds in tiers.recorded().items() if name != THIS_FILE}, "a candidate run"
        )
        monkeypatch.setattr(drift, "population_size", lambda _pop: 942)
        document, _added = drift.adopt(reference, candidate)
        assert document["population"][THIS_FILE] == 737, document["population"]

    def test_1_6x_reads_drift_once_population_is_current(self, monkeypatch):
        reference = _reference(recorded_population=737)
        monkeypatch.setattr(drift, "population_size", lambda _pop: 942)
        document, _added = drift.adopt(reference, _candidate())
        verdict, _shift, rows = drift.against(_reading(1.6), document)
        assert verdict == "drift", rows

    def test_1_2x_still_reads_ok(self, monkeypatch):
        reference = _reference(recorded_population=737)
        monkeypatch.setattr(drift, "population_size", lambda _pop: 942)
        document, _added = drift.adopt(reference, _candidate())
        verdict, _shift, rows = drift.against(_reading(1.2), document)
        assert verdict == "ok", rows

    def test_the_stale_population_the_bug_left_reads_1_6x_ok(self, monkeypatch):
        """The regression this guard falsifies: `population` stuck at
        737 while the tree measuring `THIS_FILE` grew to 942 scales
        `expected` by 942/737 = 1.28 and hides a 1.6x reading as `ok` -
        `UX-929`'s own finding, reproduced rather than narrated."""
        reference = _reference(recorded_population=737)
        monkeypatch.setattr(drift, "population_size", lambda _pop: 942)
        verdict, _shift, rows = drift.against(_reading(1.6), reference)
        assert verdict == "ok", rows


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
