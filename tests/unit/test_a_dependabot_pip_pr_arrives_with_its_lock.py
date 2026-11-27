"""`UX-1383`: a dependabot pip bump gets its lock from a job, not a hand commit.

`generate` runs the lock check's own seeded compile (`make lock-sync`) on the
event's head sha with no write credential; `publish` runs no project code,
commits the generated `requirements.lock` alone while the branch still points
at that sha, and dispatches CI and Quality on it - a GITHUB_TOKEN push starts
no workflow, a GITHUB_TOKEN dispatch does. Its shell runs against a bare remote.
"""

import os
import pathlib
import re
import subprocess

import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = yaml.safe_load((REPO / ".github/workflows/dependabot-lock.yml").read_text(encoding="utf-8"))
GENERATE, PUBLISH = WORKFLOW["jobs"]["generate"], WORKFLOW["jobs"]["publish"]
BRANCH = "dependabot/pip/python-abc"
HEAD_SHA = "${{ github.event.pull_request.head.sha }}"


def _step(job, prefix):
    return next(step for step in job["steps"] if step.get("name", step.get("uses", "")).startswith(prefix))


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def _clone(tmp_path):
    remote, work = tmp_path / "remote.git", tmp_path / "work"
    _git(tmp_path, "init", "-q", "--bare", str(remote))
    _git(tmp_path, "init", "-q", "-b", BRANCH, str(work))
    (work / "requirements.lock").write_text("ruff==0.17.3\n")
    (work / "pyproject.toml").write_text('dev = ["ruff==0.17.6"]\n')
    _git(work, "add", ".")
    _git(work, "-c", "user.name=d", "-c", "user.email=d@x", "commit", "-q", "-m", "bump")
    _git(work, "remote", "add", "origin", str(remote))
    _git(work, "push", "-q", "origin", f"HEAD:refs/heads/{BRANCH}")
    return remote, work, _git(work, "rev-parse", "HEAD")


def _push_step(tmp_path, work, head_sha, lock="ruff==0.17.6\n"):
    generated, bin_dir, log = tmp_path / "generated.lock", tmp_path / "bin", tmp_path / "gh.log"
    generated.write_text(lock)
    bin_dir.mkdir(exist_ok=True)
    (bin_dir / "gh").write_text('#!/bin/sh\necho "$*" >> "$GH_LOG"\n')
    (bin_dir / "gh").chmod(0o755)
    env = {
        **os.environ,
        "PATH": f"{bin_dir}:{os.environ['PATH']}",
        "GH_LOG": str(log),
        "GITHUB_HEAD_REF": BRANCH,
        "HEAD_SHA": head_sha,
        "LOCK": str(generated),
    }
    script = _step(PUBLISH, "Push")["run"]
    done = subprocess.run(["bash", "-e", "-c", script], cwd=work, env=env, capture_output=True, text=True)
    return done, (log.read_text() if log.exists() else "")


def test_it_runs_only_on_a_dependabot_pip_branch():
    assert "github.actor == 'dependabot[bot]'" in GENERATE["if"]
    assert "startsWith(github.head_ref, 'dependabot/pip/')" in GENERATE["if"]
    assert PUBLISH["needs"] == "generate"


def test_it_resolves_with_the_checks_own_compile_and_no_upgrade():
    assert re.search(r"^\s*make lock-sync$", _step(GENERATE, "Re-resolve")["run"], re.M)
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    recipe = re.search(r"^lock-sync:\n((?:\t.*\n)+)", makefile, re.M).group(1)
    assert recipe.strip() == "$(LOCK_COMPILE) -o requirements.lock"


def test_the_compile_runs_on_the_event_sha_with_no_write_credential():
    """Owner's review of #352: the job that runs project code never holds the token."""
    assert WORKFLOW["permissions"] == {"contents": "read"}
    assert GENERATE["permissions"] == {"contents": "read"}
    checkout = _step(GENERATE, "actions/checkout")["with"]
    assert checkout == {"ref": HEAD_SHA, "persist-credentials": False}
    assert "secrets." not in yaml.safe_dump(GENERATE)
    upload = _step(GENERATE, "actions/upload-artifact")["with"]
    assert upload["path"] == "requirements.lock"


def test_the_job_that_writes_runs_no_project_code_and_needs_no_secret():
    """Owner's call on #352: no personal token; the lock commit's CI comes by dispatch."""
    assert PUBLISH["permissions"] == {"contents": "write", "actions": "write"}
    assert "secrets." not in (REPO / ".github/workflows/dependabot-lock.yml").read_text(encoding="utf-8")
    checkout = _step(PUBLISH, "actions/checkout")["with"]
    assert checkout == {"ref": HEAD_SHA}
    runs = [step["run"] for step in PUBLISH["steps"] if "run" in step]
    assert len(runs) == 1
    assert not re.search(r"^\s*(make|pip|python3?|uv|bash|sh|\./)", runs[0], re.M), runs[0]
    assert _step(PUBLISH, "Push")["env"] == {
        "GH_TOKEN": "${{ github.token }}",
        "HEAD_SHA": HEAD_SHA,
        "LOCK": "${{ runner.temp }}/lock/requirements.lock",
    }


def test_every_workflow_it_dispatches_accepts_a_dispatch():
    for name in ("ci.yml", "quality.yml"):
        on = yaml.safe_load((REPO / ".github/workflows" / name).read_text(encoding="utf-8"))[True]
        assert "workflow_dispatch" in on and "pull_request" in on, name


def test_a_moved_lock_is_committed_alone_and_its_ci_dispatched(tmp_path):
    remote, work, sha = _clone(tmp_path)
    (work / "pyproject.toml").write_text("# a stray edit, not this commit's\n")
    done, gh = _push_step(tmp_path, work, sha)
    assert done.returncode == 0, done.stderr
    assert _git(remote, "show", f"{BRANCH}:requirements.lock") == "ruff==0.17.6"
    assert _git(remote, "show", "--name-only", "--format=", BRANCH).split() == ["requirements.lock"]
    assert gh.splitlines() == [f"workflow run ci.yml --ref {BRANCH}", f"workflow run quality.yml --ref {BRANCH}"]


def test_an_agreeing_lock_pushes_and_dispatches_nothing(tmp_path):
    remote, work, sha = _clone(tmp_path)
    done, gh = _push_step(tmp_path, work, sha, lock="ruff==0.17.3\n")
    assert done.returncode == 0, done.stderr
    assert _git(remote, "rev-parse", BRANCH) == sha
    assert "already agrees" in done.stdout
    assert gh == ""


def test_a_branch_moved_past_the_event_sha_is_left_alone(tmp_path):
    remote, work, sha = _clone(tmp_path)
    _git(work, "-c", "user.name=d", "-c", "user.email=d@x", "commit", "-q", "--allow-empty", "-m", "rebased")
    _git(work, "push", "-q", "origin", f"HEAD:refs/heads/{BRANCH}")
    newer = _git(work, "rev-parse", "HEAD")
    _git(work, "checkout", "-q", sha)
    done, gh = _push_step(tmp_path, work, sha)
    assert done.returncode == 0, done.stderr
    assert _git(remote, "rev-parse", BRANCH) == newer
    assert "moved past" in done.stdout
    assert gh == ""
