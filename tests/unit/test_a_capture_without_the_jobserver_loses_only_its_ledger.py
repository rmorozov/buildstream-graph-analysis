"""UX-901: a capture with the mode off carries every key a capture with
it on carries, but the ledger - `report_block()`'s own contract.

Two guards: `report_block()` on a fixture ledger emits only `jobserver*`
keys (never `pool_peak`, never `cache_key_set`); and `bga analyze
--format json` over `tests/fixtures/macro_micro/run`, with and without
those keys in its sibling `plane2.json`, differs only by `jobserver*`
keys, compared recursively.
"""
import json
import pathlib
import shutil
import subprocess

from tools.jobserver import report_block

REPO = pathlib.Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "fixtures" / "macro_micro"


def test_report_block_emits_only_jobserver_keys(tmp_path):
    ledger = tmp_path / "jobserver_ledger.jsonl"
    ledger.write_text(
        '{"t_us": 1000, "busy_cores": 1.0, "psi_some10": null, '
        '"psi_mem10": null, "pool": 3, "action": "hold", "reason": "band"}\n')
    block = report_block({
        "jobserver": 4, "jobserver_seed": 3, "jobserver_auth": "fd",
        "jobserver_pool_mode": "dynamic", "capacity": 4,
        "jobserver_ledger_path": str(ledger), "jobserver_status_path": None,
        "plan_path": None, "broker_status_path": None,
        "element_kinds_present": True, "jobserver_decisions_path": None,
        "jobserver_wrappers": [{"tool": "ninja", "version": "1", "policy": "held"}],
        "pid_to_element": {}, "tool_pids": {}, "element_ends": {},
        "psi_withdraw_counter": lambda _path: 0,
    })
    offenders = [key for key in block if not key.startswith("jobserver")]
    assert not offenders, (
        f"report_block() emitted non-jobserver key(s) {offenders} - it is "
        "the one thing that crosses the import boundary back, and it must "
        "carry the mode's own facts and nothing else")
    # The dynamic/ledger branch actually ran - a guard that never reaches
    # it would pass a `report_block` that dropped this whole branch too.
    assert "jobserver_ledger" in block and "jobserver_tokens_by_element" in block


def _diff_paths(before, after, prefix=()):
    """Every key path where `before`/`after` disagree, dict-recursive."""
    diffs = []
    keys = set(before) | set(after) if isinstance(before, dict) and isinstance(after, dict) else set()
    if not isinstance(before, dict) or not isinstance(after, dict):
        if before != after:
            diffs.append(prefix)
        return diffs
    for key in keys:
        if key not in before or key not in after:
            diffs.append(prefix + (key,))
            continue
        diffs.extend(_diff_paths(before[key], after[key], prefix + (key,)))
    return diffs


def _analyze_json(run_dir: pathlib.Path) -> dict:
    done = subprocess.run(
        ["python3", "-m", "bga.cli", "analyze", str(run_dir), "--format", "json"],
        capture_output=True, text=True, cwd=REPO, timeout=180)
    assert done.returncode == 0, done.stderr[-2000:]
    return json.loads(done.stdout)


#: `document_shape.*` counts leaves/depth over the *whole* document, so
#: adding any key anywhere moves it - a mechanical consequence of one
#: new block landing, not a second fact the mode changed. Excluded here
#: rather than read as a defect (`measure`'s "reads a proxy" trap): the
#: clause under test is "no other *fact* changed", and a leaf count is
#: not a fact about the build.
_EXPECTED_DRIFT = {"document_shape"}


def test_bga_analyze_differs_only_by_jobserver_keys_with_the_mode_on(tmp_path):
    run_dir = tmp_path / "macro_micro"
    shutil.copytree(FIXTURE, run_dir)
    plane2_path = run_dir / "plane2.json"
    baseline = plane2_path.read_text()

    off_report = _analyze_json(run_dir / "run")

    # A real ledger, dynamic mode - so `jobserver_ledger` and
    # `jobserver_tokens_by_element` are populated too, not just the
    # scalar keys `fixed`/no-ledger would leave this test blind to.
    ledger = run_dir / "jobserver_ledger.jsonl"
    ledger.write_text(
        '{"t_us": 1000, "busy_cores": 1.0, "psi_some10": null, '
        '"psi_mem10": null, "pool": 3, "action": "hold", "reason": "band"}\n')
    plane2 = json.loads(baseline)
    plane2.update(report_block({
        "jobserver": 4, "jobserver_seed": 3, "jobserver_auth": "fd",
        "jobserver_pool_mode": "dynamic", "capacity": 4,
        "jobserver_ledger_path": str(ledger), "jobserver_status_path": None,
        "plan_path": None, "broker_status_path": None,
        "element_kinds_present": False, "jobserver_decisions_path": None,
        "jobserver_wrappers": None, "pid_to_element": {}, "tool_pids": {},
        "element_ends": {}, "psi_withdraw_counter": lambda _path: 0,
    }))
    plane2_path.write_text(json.dumps(plane2))
    on_report = _analyze_json(run_dir / "run")

    diffs = _diff_paths(off_report, on_report)
    assert diffs, "the mode-on fixture produced no difference at all - the diff is not exercising anything"
    offenders = [path for path in diffs
                 if not path[0].startswith("jobserver") and path[0] not in _EXPECTED_DRIFT]
    assert not offenders, (
        f"turning the jobserver on changed non-jobserver key path(s) "
        f"{offenders} in `bga analyze --format json` - the mode must not "
        "leak into anything but its own jobserver* keys")
