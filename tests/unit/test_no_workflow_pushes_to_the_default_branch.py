"""`UX-997`: no workflow's `git push` lands a commit on the default branch.

Every `git push` line in every `.github/workflows/*.yml` step must name
`refs/heads/records` or `captures/*` - literally, or through a same-
script shell variable it is built from. `dev_records.py publish` is the
other route: it pushes internally, so a step that calls it needs no
literal `git push` line of its own to be read as compliant.
"""
import pathlib
import re

import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((REPO / ".github/workflows").glob("*.yml"))
ALLOWED = ("refs/heads/records", "captures/")
GIT_PUSH = re.compile(r"\bgit push\b")


def _push_lines():
    """`(workflow, job, line, the step's whole script)` for every `git push`."""
    for workflow in WORKFLOWS:
        jobs = yaml.safe_load(workflow.read_text(encoding="utf-8"))["jobs"]
        for job_name, job in jobs.items():
            for step in job.get("steps") or []:
                script = step.get("run") or ""
                for line in script.splitlines():
                    if GIT_PUSH.search(line):
                        yield workflow.name, job_name, line.strip(), script


def _names_an_allowed_ref(line, script):
    """The push line itself, or a same-script `VAR="..."` it references."""
    if any(allowed in line for allowed in ALLOWED):
        return True
    for var in set(re.findall(r"\$\{?(\w*REF\w*)\}?", line)):
        for value in re.findall(rf'{re.escape(var)}="([^"]*)"', script):
            if any(allowed in value for allowed in ALLOWED):
                return True
    return False


def test_the_population_is_not_empty():
    """A parse that found nothing would pass every check below."""
    assert len(list(_push_lines())) >= 2


def test_no_git_push_line_targets_the_default_branch():
    offending = [(workflow, job, line) for workflow, job, line, script
                 in _push_lines() if not _names_an_allowed_ref(line, script)]
    assert not offending, offending


def test_ci_and_mutation_publish_through_dev_records_instead_of_pushing():
    """The two workflows `UX-997` moved off main: no literal `git push`
    left in either, and `dev_records.py publish` present instead."""
    for name in ("ci.yml", "mutation.yml"):
        text = (REPO / ".github/workflows" / name).read_text(encoding="utf-8")
        assert not GIT_PUSH.search(text), name
        assert "dev_records.py publish" in text, name
