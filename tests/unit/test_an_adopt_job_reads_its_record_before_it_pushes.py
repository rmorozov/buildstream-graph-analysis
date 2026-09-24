"""`UX-934`/`UX-997`: an adopt job runs its record's guards before it publishes.

A push made with `GITHUB_TOKEN` starts no workflow, so what an adopt job
publishes is checked by nothing else. `UX-997` moved the add/commit/push
into `tools/dev_records.py publish`, one call site shared by every
publishing job (`UX-1000` T2 added a fourth) - so the property this
file reads off `ci.yml` narrows to: no job recomputes that sequence
itself (the duplication `UX-934` was filed on), each fetches the
branch it is about to adopt onto before its own tool runs, and
`publish` runs last. `publish`'s own refusal of a record its guard
rejects is `test_a_run_names_the_records_it_read.py`, against a
scratch remote.
"""
import pathlib
import re
import sys

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import dev_adopt_check

WORKFLOW = REPO / ".github/workflows/ci.yml"
PUBLISH = "dev_records.py publish"
RECOMPUTED = re.compile(r"git add |git commit|git push|dev_adopt_check\.py")


def _publishing_jobs():
    jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    found = {}
    for name, job in jobs.items():
        for step in job.get("steps") or []:
            if PUBLISH in (step.get("run") or ""):
                found[name] = job
    return found


def test_the_workflow_has_the_three_adopt_jobs():
    """A parse that found nothing would pass every check below."""
    assert len(_publishing_jobs()) >= 4, sorted(_publishing_jobs())


@pytest.mark.parametrize("name", sorted(_publishing_jobs()))
def test_a_publishing_job_does_not_recompute_add_commit_push(name):
    """The sequence `dev_records.py publish` now owns, once - a job that
    still ran `git add`/`git commit`/`git push`/`dev_adopt_check.py`
    itself would be the duplication this file was filed to prevent."""
    job = _publishing_jobs()[name]
    scripts = [step.get("run") or "" for step in job["steps"]]
    hits = [line for script in scripts for line in script.splitlines()
            if RECOMPUTED.search(line)]
    assert not hits, (name, hits)


@pytest.mark.parametrize("name", sorted(_publishing_jobs()))
def test_a_publishing_job_reads_the_branch_it_adopts_onto_first(name):
    """`fetch` before the tool that edits the record, `publish` last -
    reversed, a run would adopt onto its own stale copy and republish
    a regression (`UX-997`)."""
    job = _publishing_jobs()[name]
    lines = [line for step in job["steps"]
             for line in (step.get("run") or "").splitlines()]
    fetch_at = next(i for i, s in enumerate(lines) if "dev_records.py fetch" in s)
    publish_at = next(i for i, s in enumerate(lines) if PUBLISH in s)
    tool_at = next(i for i, s in enumerate(lines)
                   if re.search(r"dev_(tier_drift|touch_map)\.py --adopt"
                                 r"|dev_area_pages\.py --out", s))
    assert fetch_at < tool_at < publish_at, (name, lines)


def test_every_declared_guard_exists():
    for record, guards in dev_adopt_check.GUARDS.items():
        for guard in guards:
            assert (REPO / guard).is_file(), (record, guard)


def test_an_undeclared_record_is_refused(capsys):
    assert dev_adopt_check.main(["tests/not_a_record.json"]) == 2
    assert "::error::" in capsys.readouterr().out
