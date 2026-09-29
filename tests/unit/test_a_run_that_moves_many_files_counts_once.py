"""`UX-950`: a run that moves several files together names itself once.

19 run ids: one run touches six files, eighteen touch one each, every
file appearing exactly once. Against the ledger's own rate (1/19 per
file), that six-file run's tail is 1.2557e-3 - below 0.05/19 - and the
eighteen single-file runs are not. `per_run` names only the first;
`counts` then reads each of its six files one fewer.
"""

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import dev_flake_census as census

MULTI_FILES = [f"tests/unit/test_f{i}.py" for i in range(1, 7)]
SINGLE_FILES = [f"tests/unit/test_s{i}.py" for i in range(1, 19)]


def _ledger():
    entries = [{"file": name, "run_id": "r-multi", "shift": 1.7, "confirmed": False} for name in MULTI_FILES]
    entries += [
        {"file": name, "run_id": f"r{i}", "shift": 1.7, "confirmed": False}
        for i, name in enumerate(SINGLE_FILES, start=1)
    ]
    return {"entries": entries, "declared": {}}


def test_per_run_names_the_multi_file_run_alone():
    flagged = census.per_run(_ledger())
    assert [run_id for run_id, _k, _tail in flagged] == ["r-multi"]
    _run_id, k, tail = flagged[0]
    assert k == 6
    assert tail < 0.05 / 19


def test_the_single_file_runs_are_not_named():
    flagged = {run_id for run_id, _k, _tail in census.per_run(_ledger())}
    assert flagged.isdisjoint(f"r{i}" for i in range(1, 19))


def test_the_multi_run_files_count_one_fewer():
    document = _ledger()
    raw = census._raw_counts(document)
    adjusted = census.counts(document)
    for name in MULTI_FILES:
        assert adjusted[name] == raw[name] - 1 == 0


def test_dropping_the_per_run_reading_counts_every_row(monkeypatch):
    """Mutation: without `per_run`, every row counts toward its file -
    the six-file run's files would read 1, not 0."""
    monkeypatch.setattr(census, "per_run", lambda document: [])
    document = _ledger()
    adjusted = census.counts(document)
    for name in MULTI_FILES:
        assert adjusted[name] == 1


def test_record_run_dedupes_a_repeated_id(tmp_path):
    path = tmp_path / "flake_ledger.json"
    census.record_run("12345", path=path)
    census.record_run("12345", path=path)
    document = census.load(path)
    assert document["runs"] == ["12345"]
