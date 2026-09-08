"""`UX-691`: the drift gate's own memory, run through the shipped path.

`UX-442`'s own fixture - a file over both gates twice, a run apart -
already produces one `waiting` and one `confirmed` row; this checks
the candidate `--flake-ledger` writes at each step is that pair, and
that `--adopt-flake` appends it into a committed ledger, once each per
`(file, run id)` - the Acceptance Test's mutation, "drop the adopt
step", is what the idempotence clause below stands in for: a run that
never reaches `--adopt-flake` leaves the ledger exactly where it was.
"""
import json
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests import tiers
from tools import dev_tier_drift as drift

#: Doubling clears both `CI_DRIFT_FACTOR` and `CI_DRIFT_SECONDS` -
#: `UX-442`'s own choice, reused so this fixture stands on ground
#: already measured rather than a new magnitude nobody has checked.
FLAKY = "tests/unit/test_the_page_has_geometry.py"


def _report(tmp_path, name, times):
    cases = "".join(
        f'<testcase classname="{n[:-3].replace("/", ".")}.T" name="t" '
        f'time="{s}" />' for n, s in times.items())
    path = tmp_path / name
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?><testsuites>'
        f'<testsuite name="pytest">{cases}</testsuite></testsuites>',
        encoding="utf-8")
    return path


def _run(tmp_path, run_id, over, reference, carry, ledger):
    times = dict(tiers.recorded())
    for name in over:
        times[name] = times[name] * 2
    report = _report(tmp_path, f"junit-{run_id}.xml", times)
    return drift.main([str(report), "--against", str(reference),
                       "--carry", str(carry), "--flake-ledger", str(ledger),
                       "--run-id", run_id])


class TestTheCandidateMatchesTheGate:
    def test_a_first_excursion_is_waiting_not_confirmed(self, tmp_path):
        reference = tmp_path / "ref.json"
        reference.write_text(
            json.dumps(drift.record(dict(tiers.recorded()))),
            encoding="utf-8")
        candidate = tmp_path / "run-1.json"
        _run(tmp_path, "run-1", [FLAKY], reference,
             tmp_path / "carry.json", candidate)
        rows = json.loads(candidate.read_text(encoding="utf-8"))
        assert rows == [{"file": FLAKY, "run_id": "run-1",
                        "shift": rows[0]["shift"], "confirmed": False}], rows
        assert rows[0]["shift"] > 1.0, rows

    def test_a_second_agreeing_run_is_confirmed(self, tmp_path):
        reference = tmp_path / "ref.json"
        reference.write_text(
            json.dumps(drift.record(dict(tiers.recorded()))),
            encoding="utf-8")
        carry = tmp_path / "carry.json"
        _run(tmp_path, "run-1", [FLAKY], reference, carry,
             tmp_path / "run-1.json")
        candidate = tmp_path / "run-2.json"
        _run(tmp_path, "run-2", [FLAKY], reference, carry, candidate)
        rows = json.loads(candidate.read_text(encoding="utf-8"))
        assert rows == [{"file": FLAKY, "run_id": "run-2",
                        "shift": rows[0]["shift"], "confirmed": True}], rows

    def test_a_clean_run_writes_an_empty_candidate(self, tmp_path):
        """Every return, not only the ones that named something - the
        same reason `carry` is written on a clean run too."""
        reference = tmp_path / "ref.json"
        reference.write_text(
            json.dumps(drift.record(dict(tiers.recorded()))),
            encoding="utf-8")
        candidate = tmp_path / "run-1.json"
        _run(tmp_path, "run-1", [], reference, tmp_path / "carry.json",
             candidate)
        assert json.loads(candidate.read_text(encoding="utf-8")) == []


#: A row the ledger already carries before either clause below runs
#: its own adopt - the case neither clause fixtured (`UX-786`).
_EXISTING = {"file": "tests/unit/test_the_page_has_geometry.py",
            "run_id": "run-0", "shift": 1.5, "confirmed": False}


class TestAdoptFlakeAppends:
    def test_a_candidates_rows_are_appended(self, tmp_path, monkeypatch):
        ledger = tmp_path / "ledger.json"
        ledger.write_text(json.dumps({"entries": [_EXISTING],
                                      "declared": {}}), encoding="utf-8")
        monkeypatch.setattr(drift, "FLAKE_LEDGER", ledger)
        candidate = tmp_path / "candidate.json"
        candidate.write_text(json.dumps([
            {"file": FLAKY, "run_id": "run-9", "shift": 1.8,
             "confirmed": True}]), encoding="utf-8")
        assert drift.main(["--adopt-flake", str(candidate)]) == 0
        document = json.loads(ledger.read_text(encoding="utf-8"))
        assert document["entries"] == [_EXISTING,
            {"file": FLAKY, "run_id": "run-9", "shift": 1.8,
             "confirmed": True}]

    def test_readopting_the_same_run_adds_nothing(self, tmp_path, monkeypatch):
        """The Acceptance Test's mutation stands in here: a run that
        never reaches this step, or reaches it twice for the same run
        id, must not grow the ledger a second time for one excursion."""
        ledger = tmp_path / "ledger.json"
        ledger.write_text(json.dumps({"entries": [_EXISTING],
                                      "declared": {}}), encoding="utf-8")
        monkeypatch.setattr(drift, "FLAKE_LEDGER", ledger)
        candidate = tmp_path / "candidate.json"
        candidate.write_text(json.dumps([
            {"file": FLAKY, "run_id": "run-9", "shift": 1.8,
             "confirmed": True}]), encoding="utf-8")
        drift.main(["--adopt-flake", str(candidate)])
        before = ledger.read_text(encoding="utf-8")
        assert drift.main(["--adopt-flake", str(candidate)]) == 0
        assert ledger.read_text(encoding="utf-8") == before
        assert _EXISTING in json.loads(before)["entries"]

    def test_no_candidate_leaves_the_ledger_untouched(self, tmp_path,
                                                       monkeypatch):
        ledger = tmp_path / "ledger.json"
        ledger.write_text('{"entries": []}', encoding="utf-8")
        monkeypatch.setattr(drift, "FLAKE_LEDGER", ledger)
        assert drift.main(["--adopt-flake", str(tmp_path / "missing.json")]) == 0
        assert ledger.read_text(encoding="utf-8") == '{"entries": []}'


def test_ledger_rows_splits_waiting_from_confirmed():
    waiting = [("a.py", 10.0, 5.0, 1.8)]
    confirmed = [("b.py", 12.0, 6.0, 1.9)]
    assert drift.ledger_rows(waiting, confirmed, "run-1") == [
        {"file": "a.py", "run_id": "run-1", "shift": 1.8,
         "confirmed": False},
        {"file": "b.py", "run_id": "run-1", "shift": 1.9,
         "confirmed": True}]
