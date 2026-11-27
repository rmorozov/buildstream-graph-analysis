"""UX-1390: the capacity Note names one source for `--max-jobs`.

On `macro_micro` with its `plane2.json` beside the run, the Note said the axis
"is modelled for this capture" and, two sentences on, that the capacity checks
did not run for want of the `--max-jobs` value. The modelled value is per
element, so where the run's own value is unrecorded the Note says it does not
feed the checks; where it is recorded the original clause stands.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "fixtures" / "macro_micro"
MODELLED = "is modelled for this capture"
MISSED = "missing: the --max-jobs value"
DECLINED = "does not feed the capacity checks"


def _note(tmp_path: Path, native_max_jobs=None) -> str:
    shutil.copytree(FIXTURE / "run", tmp_path / "run")
    shutil.copy(FIXTURE / "plane2.json", tmp_path / "plane2.json")
    if native_max_jobs is not None:
        ctx = tmp_path / "run" / "run-context.json"
        data = json.loads(ctx.read_text())
        data["native_max_jobs"] = native_max_jobs
        ctx.write_text(json.dumps(data))
    proc = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(tmp_path / "run"), "--format", "json"],
        capture_output=True,
        text=True,
        cwd=REPO,
        env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin"},
        timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)["floors"]["capacity_model_note"]


def test_a_missing_max_jobs_value_is_not_also_modelled(tmp_path):
    note = _note(tmp_path)
    assert MISSED in note
    assert MODELLED not in note
    assert DECLINED in note


def test_a_recorded_max_jobs_value_keeps_the_modelled_clause(tmp_path):
    note = _note(tmp_path, native_max_jobs=4)
    assert MODELLED in note
    assert MISSED not in note
    assert DECLINED not in note
