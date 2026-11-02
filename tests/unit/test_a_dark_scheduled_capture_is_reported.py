"""UX-1361: a red scheduled real-project capture, or one whose baseline set the trend refuses, opens or updates one issue.

Four weekly reds (2026-10-04..25) went unseen: the job's only output is a
branch it never wrote. The trend step exits 0 on a refusal, so `failure()`
alone never saw that half (review 2). The steps are read from the workflow
and their shell bodies run against a stub `bga` and `gh`, not mocked.
"""

import os
import pathlib
import re
import stat
import subprocess

import pytest
import yaml

from tools import bst_baseline_set

WORKFLOW = pathlib.Path(__file__).resolve().parents[2] / ".github/workflows/real-project-capture.yml"
OUTPUT_TEST = re.compile(r"steps\.(\w+)\.outputs\.(\w+) == '(\w+)'")


def _job():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["capture"]


def _reporting_steps():
    return [
        s
        for s in _job()["steps"]
        if "failure()" in str(s.get("if", "")) and "schedule" in str(s.get("if", "")) and "gh issue" in s.get("run", "")
    ]


def _trend_step():
    (step,) = [s for s in _job()["steps"] if "bga cache-trend" in s.get("run", "")]
    return step


class TestADarkScheduleIsReported:
    def test_one_step_reports_a_red_schedule(self):
        assert len(_reporting_steps()) == 1

    def test_it_comments_on_an_open_issue_before_opening_another(self):
        run = _reporting_steps()[0]["run"]
        assert run.index("gh issue list") < run.index("gh issue comment") < run.index("gh issue create")

    def test_the_job_may_write_issues(self):
        assert _job()["permissions"].get("issues") == "write"

    def test_it_is_the_last_step_so_every_earlier_red_reaches_it(self):
        assert _job()["steps"][-1] == _reporting_steps()[0]


# --- review 2: a successful capture whose baseline set is refused ----------------------------------------


def _stub(directory: pathlib.Path, name: str, body: str) -> None:
    path = directory / name
    path.write_text("#!/bin/bash\n" + body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def _bash(script: str, tmp_path: pathlib.Path, **env) -> subprocess.CompletedProcess:
    full = {**os.environ, "PATH": f"{tmp_path / 'bin'}:{os.environ['PATH']}", "RUNNER_TEMP": str(tmp_path), **env}
    return subprocess.run(
        ["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", script],
        capture_output=True,
        text=True,
        env=full,
        timeout=60,
    )


def _empty_history_stderr(monkeypatch, capsys) -> str:
    """The real tool's own words for a glob that matches nothing."""
    monkeypatch.setattr(bst_baseline_set, "list_capture_refs", lambda *a, **k: [])
    assert bst_baseline_set.main(["--glob", "captures/fdsdk/x-*"]) == 1
    return capsys.readouterr().err


def _run_trend(tmp_path, rc: int, stderr: str) -> dict:
    (tmp_path / "bin").mkdir()
    (tmp_path / "refusal.txt").write_text(stderr, encoding="utf-8")
    _stub(tmp_path / "bin", "bga", f'cat "{tmp_path / "refusal.txt"}" >&2\nexit {rc}\n')
    output = tmp_path / "github_output"
    output.write_text("", encoding="utf-8")
    done = _bash(
        _trend_step()["run"],
        tmp_path,
        GITHUB_OUTPUT=str(output),
        FDSDK_REF="953683fb0000",
        REF_MODE="cold",
        BUILDERS="4",
        MAX_JOBS="4",
    )
    assert done.returncode == 0, done.stderr
    return dict(line.split("=", 1) for line in output.read_text(encoding="utf-8").splitlines())


REFUSALS = {
    "inhomogeneous set": (6, "Refusing to compare against a set that is not internally comparable. ...\n"),
    "ls-remote failed": (1, "Error: git ls-remote failed: fatal: unable to access\n"),
}


@pytest.mark.parametrize("case", sorted(REFUSALS))
def test_a_refused_baseline_set_reaches_the_report_condition(case, tmp_path):
    report_if = _reporting_steps()[0]["if"]
    assert "failure() ||" in report_if, report_if
    step_id, key, value = OUTPUT_TEST.search(report_if).groups()
    assert _trend_step().get("id") == step_id
    assert _run_trend(tmp_path, *REFUSALS[case]).get(key) == value


def test_an_empty_initial_history_stays_quiet(tmp_path, monkeypatch, capsys):
    stderr = _empty_history_stderr(monkeypatch, capsys)
    _step_id, key, value = OUTPUT_TEST.search(_reporting_steps()[0]["if"]).groups()
    outputs = _run_trend(tmp_path, 1, stderr)
    assert outputs.get(key) == "empty" != value, outputs


def _report_body(tmp_path, job_status: str, refused: str) -> str:
    (tmp_path / "bin").mkdir()
    created = tmp_path / "created.txt"
    _stub(tmp_path / "bin", "gh", f'if [ "$2" = create ]; then printf "%s\\n" "$@" > "{created}"; fi\n')
    script = re.sub(r"\$\{\{[^}]*\}\}", "x", _reporting_steps()[0]["run"])
    done = _bash(script, tmp_path, JOB_STATUS=job_status, TREND_REFUSED=refused, CAPTURE_MODE="cold", FDSDK_REF="r")
    assert done.returncode == 0, done.stderr
    return created.read_text(encoding="utf-8")


def test_the_issue_names_a_refused_trend_on_a_green_job(tmp_path):
    body = _report_body(tmp_path, "success", "true")
    assert "bga baseline refused the retained history" in body and "the job failed" not in body, body


def test_the_issue_names_a_failed_job(tmp_path):
    body = _report_body(tmp_path, "failure", "")
    assert "the job failed" in body and "refused" not in body, body
