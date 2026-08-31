"""UX-457: the reference could be recorded and not read.

`UX-420` gave CI a reference of its own, `UX-427` made CI write the
refreshed document every run, `UX-441` moved it out of the test job's
log into an artifact so a red run's failing assertion stayed the last
thing a reader saw, and `UX-447` put the artifact's name in every
message that asks for a refresh. Four items, and the route still ended
at a download.

That download is served from hosts an agent session is not always
allowed to reach. Round 71 measured it, going to add four rows:

```console
$ curl -sSL -o cand.zip ".../ci-reference-candidate.zip?..."
curl: (56) CONNECT tunnel failed, response 403
- productionresultssa19.blob.core.windows.net:443 - connect_rejected

$ curl -sSL -o r.zip ".../runs/<id>/logs?..."
curl: (56) CONNECT tunnel failed, response 403
- results-receiver.actions.githubusercontent.com:443 - connect_rejected
```

The artifact listed fine over the API - 5,785 bytes, unexpired - and
could not be opened. So the reference stayed four files stale, because
the honest alternative (a local `--record`) is the cross-machine
comparison `UX-418` ruled out.

The fix is a job whose whole log **is** the document. What this file
holds is that the two halves still meet: the step that writes the file
and the job that prints it name the same path, and the printing job
stays a job that only prints - the moment it grows something that can
fail, `UX-441`'s trade is back and the document is burying a failure
again.
"""
import pathlib
import re
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import dev_tier_drift as drift                      # noqa: E402

WORKFLOW = REPO / ".github/workflows/ci.yml"

#: What a step is allowed to do in the printing job. Anything that runs
#: the suite, the tool, or a linter can fail - and a failure here is a
#: failure standing between a reader and the document, which is the
#: state `UX-441` moved the document out of the test job to end.
FORBIDDEN = ("pytest", "make ", "ruff", "pymarkdown", "python -m", "python3 -m")


def _jobs():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]


def _recorded_path():
    """The path `--record` writes, read out of the workflow's own step.

    Not out of this file: the point of the clause below is that the two
    sites agree, and a constant here that both were compared against
    would be a third place to keep in step rather than a check that the
    two real ones are.
    """
    for step in _jobs()["test"]["steps"]:
        script = step.get("run") or ""
        found = re.search(r"--record\s+\"?\$\{\{[^}]+\}\}/(\S+?)\"?\s", script)
        if found:
            return found.group(1)
    raise AssertionError("no step in `test` runs --record any more")


def test_a_job_exists_whose_log_is_the_document():
    jobs = _jobs()
    assert drift.CI_CANDIDATE_JOB in jobs, (
        f"`ci.yml` has jobs {sorted(jobs)} and the drift tool's advice "
        f"sends a reader to `{drift.CI_CANDIDATE_JOB}` - so the route it "
        f"names ends nowhere, which is UX-457's own defect one level over")


def test_that_job_fetches_the_artifact_the_tool_names():
    """The job is the artifact's second door, not a second recording.

    Downloading it is what makes the printed bytes the same bytes the
    download would have given; a job that re-ran `--record` would print
    a *different* run's clock and look identical.
    """
    steps = _jobs()[drift.CI_CANDIDATE_JOB]["steps"]
    fetched = {(step.get("with") or {}).get("name") for step in steps
               if "download-artifact" in (step.get("uses") or "")}
    assert drift.CI_CANDIDATE_ARTIFACT in fetched, (
        f"`{drift.CI_CANDIDATE_JOB}` downloads {sorted(n for n in fetched if n)} "
        f"and the tool names `{drift.CI_CANDIDATE_ARTIFACT}`")


def test_the_job_prints_the_file_the_record_step_wrote():
    """The join a rename breaks, and the reason this file is not a
    string comparison against a constant of its own."""
    wrote = _recorded_path()
    printed = "\n".join(step.get("run") or ""
                        for step in _jobs()[drift.CI_CANDIDATE_JOB]["steps"])
    assert wrote in printed, (
        f"`test` records to `{wrote}` and `{drift.CI_CANDIDATE_JOB}` prints "
        f"{printed!r} - the job would report an empty log on every run")


def test_the_printing_job_cannot_fail_an_assertion():
    """`UX-441`'s trade, kept.

    The document went into an artifact because two red runs this round
    ended with 370 lines of reference between the reader and the
    assertion that failed. Printing it again is only safe while the
    printing happens somewhere nothing else can fail.
    """
    steps = _jobs()[drift.CI_CANDIDATE_JOB]["steps"]
    offending = [step.get("name") or step.get("uses")
                 for step in steps
                 if any(word in (step.get("run") or "") for word in FORBIDDEN)]
    assert offending == [], (
        f"{offending} in `{drift.CI_CANDIDATE_JOB}` can fail, and a failure "
        f"there puts a failing assertion back under the document - which is "
        f"the state UX-441 moved the document out of `test` to end")


def test_the_job_runs_on_the_red_runs_too():
    """The run this is most wanted on is the one whose drift step went
    red, and a failed `test` job skips a plain `needs:` dependant."""
    job = _jobs()[drift.CI_CANDIDATE_JOB]
    assert "always()" in str(job.get("if", "")), (
        f"`{drift.CI_CANDIDATE_JOB}` has no always() condition, so it is "
        f"skipped exactly when the refresh is being asked for")


if __name__ == "__main__":  # pragma: no cover
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
