"""`UX-1383`: a dependabot pip bump gets its lock from a job, not a hand commit.

The job runs the lock check's own seeded compile (`make lock-sync`), then
its push step commits `requirements.lock` alone to the dependabot branch.
The step's shell is run here against a real bare remote.
"""

import os
import pathlib
import re
import subprocess

import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
JOB = yaml.safe_load((REPO / ".github/workflows/dependabot-lock.yml").read_text(encoding="utf-8"))["jobs"]["lock"]
BRANCH = "dependabot/pip/python-abc"


def _step(name):
    return next(step for step in JOB["steps"] if step.get("name", "").startswith(name))


def _git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout


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
    return remote, work


def _push_step(work, has_token="false"):
    env = {**os.environ, "GITHUB_HEAD_REF": BRANCH, "HAS_TOKEN": has_token}
    return subprocess.run(["bash", "-e", "-c", _step("Push")["run"]], cwd=work, env=env, capture_output=True, text=True)


def test_it_runs_only_on_a_dependabot_pip_branch():
    assert "github.actor == 'dependabot[bot]'" in JOB["if"]
    assert "startsWith(github.head_ref, 'dependabot/pip/')" in JOB["if"]


def test_it_resolves_with_the_checks_own_compile_and_no_upgrade():
    assert re.search(r"^\s*make lock-sync$", _step("Re-resolve")["run"], re.M)
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    recipe = re.search(r"^lock-sync:\n((?:\t.*\n)+)", makefile, re.M).group(1)
    assert recipe.strip() == "$(LOCK_COMPILE) -o requirements.lock"


def test_its_checkout_pushes_with_the_token_that_starts_ci():
    checkout = next(step for step in JOB["steps"] if step.get("uses", "").startswith("actions/checkout"))
    assert checkout["with"]["token"].startswith("${{ secrets.DEPENDABOT_LOCK_TOKEN ||")
    assert checkout["with"]["ref"] == "${{ github.head_ref }}"


def test_a_moved_lock_is_committed_alone_to_the_dependabot_branch(tmp_path):
    remote, work = _clone(tmp_path)
    (work / "requirements.lock").write_text("ruff==0.17.6\n")
    (work / "pyproject.toml").write_text("# a stray edit, not this commit's\n")
    done = _push_step(work)
    assert done.returncode == 0, done.stderr
    assert _git(remote, "show", f"{BRANCH}:requirements.lock") == "ruff==0.17.6\n"
    assert _git(remote, "show", "--name-only", "--format=", BRANCH).split() == ["requirements.lock"]
    assert "DEPENDABOT_LOCK_TOKEN" in done.stdout


def test_an_agreeing_lock_pushes_nothing(tmp_path):
    remote, work = _clone(tmp_path)
    before = _git(remote, "rev-parse", BRANCH)
    done = _push_step(work, has_token="true")
    assert done.returncode == 0, done.stderr
    assert _git(remote, "rev-parse", BRANCH) == before
    assert "already agrees" in done.stdout
