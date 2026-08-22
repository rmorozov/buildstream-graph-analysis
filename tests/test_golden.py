"""P3-08: golden/regression test.

Runs the full pipeline (via the real CLI, subprocess - the same
end-to-end path a user actually invokes) against a checked-in fixture
and diffs the output against a checked-in expected snapshot, exactly.
No tolerance of any kind: the pipeline is fully deterministic (Part 35/
I11, see tests/unit/test_determinism.py), so any diff here is either a
genuine behavior change (update the snapshot deliberately, see below)
or a real regression.

This is a coarse safety net on top of the targeted unit/invariant tests
(P3-03 through P3-07) - it catches unintended drift in *any* output
field, but doesn't explain *why* something changed. Don't add new
correctness assertions here; add them to the targeted test files instead.

## Regenerating the expected output after a deliberate behavior change

    PYTHONPATH=. python3 -m bga.cli analyze \\
        tests/fixtures/golden/mixed_task_kinds --format json --diagnostics \\
        | python3 -c 'import json,sys; d=json.load(sys.stdin); \\
              d.pop("run_instance", None); print(json.dumps(d, indent=4))' \\
        > tests/fixtures/golden/mixed_task_kinds/expected_output.json

`run_instance` is dropped because `_run_analyze` below pops it from the
actual payload before comparing - a recipe that leaves it in writes a
snapshot this file can never match.

Then re-run this file and confirm the diff you expected is the only
change (`git diff tests/fixtures/golden/mixed_task_kinds/expected_output.json`).
"""
import json
import subprocess
import sys
from pathlib import Path

GOLDEN_DIR = Path(__file__).parent / "fixtures" / "golden"


def _run_analyze(fixture_dir: Path) -> dict:
    cmd = [
        sys.executable, "-m", "bga.cli", "analyze", str(fixture_dir),
        "--format", "json", "--diagnostics",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0, f"stdout={proc.stdout}\nstderr={proc.stderr}"
    payload = json.loads(proc.stdout)
    # `UX-95`'s run-instance block names *which capture* this is - a
    # wall-clock stamp and the absolute path it was read from. Both are
    # properties of the machine that ran it, not of the analysis, so
    # they cannot live in a committed snapshot. Removed here rather than
    # withheld from the report: the identity hash, which is what a
    # snapshot is about, is untouched and still compared.
    payload.pop("run_instance", None)
    return payload


def test_mixed_task_kinds_golden_snapshot():
    fixture_dir = GOLDEN_DIR / "mixed_task_kinds"
    expected = json.loads((fixture_dir / "expected_output.json").read_text())
    actual = _run_analyze(fixture_dir)
    assert actual == expected


def test_mixed_task_kinds_golden_snapshot_is_deterministic_across_runs():
    """Two independent CLI invocations against the same fixture must
    produce byte-identical output (Part 35/I11) - a weaker but
    complementary check to the fixed-snapshot comparison above, since it
    can't be fooled by an expected_output.json that was itself captured
    from a nondeterministic run."""
    fixture_dir = GOLDEN_DIR / "mixed_task_kinds"
    first = _run_analyze(fixture_dir)
    second = _run_analyze(fixture_dir)
    assert first == second
