"""UX-1390: the capacity Note names one source for `--max-jobs`, and only claims a model that exists.

On `macro_micro` with its `plane2.json` beside the run, the Note said the axis
"is modelled for this capture" and, two sentences on, that the capacity checks
did not run for want of the `--max-jobs` value. The modelled value is per
element: where the run's own value is unrecorded the Note says it does not
feed the checks, and points at the per-element advice only when that exists.
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
FIXTURE = REPO / "tests" / "fixtures" / "macro_micro"
HOST_CPU = REPO / "tests" / "fixtures" / "host_cpu"
MODELLED = "is modelled for this capture"
PER_ELEMENT = "modelled per element"
MISSED = "missing: the --max-jobs value"
DECLINED = "does not feed the capacity checks"
NO_ESTIMATE = "has no per-element estimate"


def _analyze(tmp_path: Path, run: Path, native_max_jobs, host_samples: Path = None, keep_lines: int = None) -> dict:
    shutil.copytree(run, tmp_path / "run")
    shutil.copy(FIXTURE / "plane2.json", tmp_path / "plane2.json")
    if host_samples is not None:
        lines = host_samples.read_text().splitlines(keepends=True)
        (tmp_path / "host-samples.jsonl").write_text("".join(lines[:keep_lines]))
    ctx = tmp_path / "run" / "run-context.json"
    data = json.loads(ctx.read_text())
    data["native_max_jobs"] = native_max_jobs
    data["native_max_jobs_source"] = None if native_max_jobs is None else data.get("native_max_jobs_source")
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
    return json.loads(proc.stdout)


def test_a_missing_max_jobs_value_with_no_advice_claims_no_model(tmp_path):
    result = _analyze(tmp_path, FIXTURE / "run", None)
    note = result["floors"]["capacity_model_note"]
    recommendation = result["capacity_recommendation"]
    assert recommendation["native_max_jobs"] is None
    assert "max_jobs_advice" not in recommendation
    assert MISSED in note
    assert MODELLED not in note
    assert PER_ELEMENT not in note
    assert NO_ESTIMATE in note


def test_a_missing_max_jobs_value_with_advice_points_at_it(tmp_path):
    result = _analyze(tmp_path, HOST_CPU / "run", None, HOST_CPU / "host-samples.jsonl")
    note = result["floors"]["capacity_model_note"]
    recommendation = result["capacity_recommendation"]
    assert recommendation["native_max_jobs"] is None
    assert recommendation["max_jobs_advice"]["elements"]
    assert MISSED in note
    assert MODELLED not in note
    assert PER_ELEMENT in note
    assert DECLINED in note
    assert NO_ESTIMATE not in note


def test_a_missing_max_jobs_value_with_every_row_refused_claims_no_model(tmp_path):
    result = _analyze(tmp_path, HOST_CPU / "run", None, HOST_CPU / "host-samples.jsonl", keep_lines=4)
    note = result["floors"]["capacity_model_note"]
    rows = result["capacity_recommendation"]["max_jobs_advice"]["elements"]
    assert rows
    assert all(row["recommended_max_jobs"] is None and row["refusal"] for row in rows)
    assert MISSED in note
    assert PER_ELEMENT not in note
    assert NO_ESTIMATE in note


def test_a_recorded_max_jobs_value_keeps_the_modelled_clause(tmp_path):
    note = _analyze(tmp_path, FIXTURE / "run", 4)["floors"]["capacity_model_note"]
    assert MODELLED in note
    assert MISSED not in note
    assert DECLINED not in note
    assert NO_ESTIMATE not in note


def test_a_recorded_zero_max_jobs_is_not_reported_as_unrecorded(tmp_path):
    result = _analyze(tmp_path, FIXTURE / "run", 0)
    assert result["capacity_recommendation"]["native_max_jobs"] == 0
    assert MISSED not in result["floors"]["capacity_model_note"]
    text = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(tmp_path / "run")],
        capture_output=True,
        text=True,
        cwd=REPO,
        env={"PYTHONPATH": str(REPO), "PATH": "/usr/bin:/bin"},
        timeout=120,
    ).stdout
    assert "builders 4 x max-jobs 0 (BuildStream auto)" in text
    assert "native max-jobs unrecorded" not in text
