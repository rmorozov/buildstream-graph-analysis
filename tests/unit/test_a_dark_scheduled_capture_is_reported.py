"""UX-1361: a red scheduled real-project capture opens or updates one issue.

Four weekly reds (2026-10-04..25) went unseen: the job's only output is a
branch it never wrote. The step is read from the workflow, not mocked.
"""

import pathlib

import yaml

WORKFLOW = pathlib.Path(__file__).resolve().parents[2] / ".github/workflows/real-project-capture.yml"


def _job():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]["capture"]


def _reporting_steps():
    return [
        s
        for s in _job()["steps"]
        if "failure()" in str(s.get("if", "")) and "schedule" in str(s.get("if", "")) and "gh issue" in s.get("run", "")
    ]


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
