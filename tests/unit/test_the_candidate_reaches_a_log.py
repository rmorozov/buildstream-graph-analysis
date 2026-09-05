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

from tools import dev_tier_drift as drift

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


def _summary_path():
    """The path `--against` writes its own line to, from the workflow.

    Read out of the gate step for the same reason `_recorded_path` is
    read out of the record step: the claim is that the two sites agree.
    """
    for step in _jobs()["test"]["steps"]:
        script = step.get("run") or ""
        found = re.search(r"--summary\s+\"?\$\{\{[^}]+\}\}/(\S+?)\"?\s",
                          script)
        if found:
            return found.group(1)
    raise AssertionError("no step in `test` runs --against with --summary")


def _candidate_step():
    for step in _jobs()["test"]["steps"]:
        if "--record" in (step.get("run") or ""):
            return step.get("run")
    raise AssertionError("no step in `test` runs --record any more")


def test_the_gate_line_is_printed_where_a_log_tail_reader_gets_it():
    """`UX-491`. The gate prints its line, then ~400 lines of candidate
    document follow it, and a client bounded to a log tail gets the
    document and not the line - so `UX-488` could read the recorded
    `spread` and not the shift it had to be paired with.

    The route is the gate's own line, written to a file and printed by
    the later step. Both halves are read out of the workflow here: a
    rename on either side is the failure this catches.
    """
    wrote = _summary_path()
    assert wrote in _candidate_step(), (
        f"the gate writes its line to `{wrote}` and the step that prints "
        f"the candidate does not read it, so the line is still two steps "
        f"and one collapsed document above the tail")


def test_the_line_lands_after_the_document_not_inside_it():
    """Adjacency is the whole point: the shift and the spread recorded
    against it have to be in the same tail. Inside the `::group::` the
    line is at the document's *top*, ~400 lines from the end."""
    script = _candidate_step()
    assert "::endgroup::" in script, script
    tail = script.split("::endgroup::")[-1]
    assert _summary_path() in tail, (
        f"`{_summary_path()}` is printed before the document's "
        f"`::endgroup::`, so the tail still ends in the document")


def test_the_later_step_does_not_recompute_the_shift():
    """Fixing guide §5. A step that ran the tool again would print a
    line that agrees with the document by construction, and the pairing
    `UX-488` wanted would be checking nothing."""
    tail = _candidate_step().split("::endgroup::")[-1]
    assert "--against" not in tail, tail


def test_a_gate_that_never_ran_does_not_fail_the_printing():
    """The candidate step is `always()` and the gate step is not, so the
    file can be absent - and a bare `cat` on a missing path would turn
    UX-491's convenience into a red step."""
    tail = _candidate_step().split("::endgroup::")[-1]
    assert "||" in tail, (
        "the summary is printed with no fallback, so a run whose gate "
        "step never reached its return fails here instead")


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
