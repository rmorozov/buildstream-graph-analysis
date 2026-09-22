"""`UX-934`: an adopt job runs its record's guards before it pushes.

A push made with `GITHUB_TOKEN` starts no workflow, so what an adopt job
pushes is checked by nothing. The wiring is read from `ci.yml` - every
job that pushes checks exactly what it adds, before the push - and the
ledger job's own script is run against a scratch remote, once with a
record its guard rejects and once with one it accepts.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import dev_adopt_check

WORKFLOW = REPO / ".github/workflows/ci.yml"
CHECK = "tools/dev_adopt_check.py"


def _pushing_jobs():
    jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
    found = {}
    for name, job in jobs.items():
        for step in job.get("steps") or []:
            if "git push" in (step.get("run") or ""):
                found[name] = step
    return found


def _arguments(lines, command):
    return [line.split(command, 1)[1].split() for line in lines
            if command in line]


def test_the_workflow_has_the_three_adopt_jobs():
    """A parse that found nothing would pass every check below."""
    assert len(_pushing_jobs()) >= 3, sorted(_pushing_jobs())


@pytest.mark.parametrize("name", sorted(_pushing_jobs()))
def test_a_pushing_job_checks_exactly_what_it_adds_before_it_pushes(name):
    step = _pushing_jobs()[name]
    lines = [line.strip() for line in step["run"].splitlines()]
    added = _arguments(lines, "git add ")
    checked = _arguments(lines, CHECK)
    assert len(added) == 1 and len(checked) == 1, (name, added, checked)
    assert set(checked[0]) == set(added[0]), (
        f"{name} checks {checked[0]} but adds {added[0]}")
    at = next(i for i, line in enumerate(lines) if CHECK in line)
    push = next(i for i, line in enumerate(lines) if "git push" in line)
    assert at < push, f"{name} checks after it pushes"
    assert "||" not in lines[at] and not step.get("continue-on-error"), (
        f"{name} swallows the check's exit status")


@pytest.mark.parametrize("record", sorted(dev_adopt_check.GUARDS))
def test_every_declared_guard_exists(record):
    for guard in dev_adopt_check.GUARDS[record]:
        assert (REPO / guard).is_file(), guard


def test_an_undeclared_record_is_refused(capsys):
    assert dev_adopt_check.main(["tests/not_a_record.json"]) == 2
    assert "::error::" in capsys.readouterr().out


#: What the ledger job's script needs of the tree, and nothing else - a
#: file a later change makes it need fails the accepting case loudly.
_LEDGER_TREE = ("pyproject.toml", "tools/__init__.py", "tools/dev_adopt_check.py",
                "tools/dev_tier_drift.py", "tools/dev_flake_census.py",
                "tests/tiers.py", "tests/unit/__init__.py",
                *dev_adopt_check.GUARDS["tests/flake_ledger.json"])


def _git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                           *args], cwd=cwd, check=True, capture_output=True,
                          text=True).stdout.strip()


def _run_the_ledger_job(tmp_path, excursions):
    """The job's own script on a scratch clone; `(exit status, remote moved)`."""
    work, remote = tmp_path / "work", tmp_path / "remote.git"
    for name in _LEDGER_TREE:
        (work / name).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / name, work / name)
    (work / "docs/backlog/scenarios").mkdir(parents=True)
    (work / "docs/backlog/scenarios/.keep").write_text("", encoding="utf-8")
    (work / "tests/flake_ledger.json").write_text(
        json.dumps({"entries": [], "declared": {}}), encoding="utf-8")
    _git(work, "init", "-q", "-b", "main")
    _git(work, "add", ".")
    _git(work, "commit", "-q", "-m", "base")
    _git(tmp_path, "clone", "-q", "--bare", str(work), str(remote))
    _git(work, "remote", "add", "origin", str(remote))
    before = _git(remote, "rev-parse", "main")
    (work / "flake_ledger.candidate.json").write_text(json.dumps(
        [{"file": "tests/unit/test_nothing_files.py", "run_id": str(n),
          "shift": 1.7, "confirmed": False} for n in range(excursions)]),
        encoding="utf-8")
    script = _pushing_jobs()["flake-ledger-adopt"]["run"].replace(
        "${{ github.ref }}", "refs/heads/main")
    # The job's `python` is this interpreter; a caller's GIT_* would aim git elsewhere.
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["PATH"] = f"{pathlib.Path(sys.executable).parent}{os.pathsep}{env['PATH']}"
    status = subprocess.run(["bash", "-e", "-c", script], cwd=work, env=env,
                            capture_output=True, text=True, check=False)
    return status, _git(remote, "rev-parse", "main") != before


def test_a_ledger_its_guard_accepts_is_pushed(tmp_path):
    """The control: without it, the refusal below could be a broken fixture."""
    status, moved = _run_the_ledger_job(tmp_path, excursions=2)
    assert status.returncode == 0, status.stdout + status.stderr
    assert moved


def test_a_ledger_its_guard_rejects_fails_the_job_and_is_not_pushed(tmp_path):
    status, moved = _run_the_ledger_job(tmp_path, excursions=3)
    assert status.returncode != 0, status.stdout + status.stderr
    assert not moved
    assert "test_the_real_ledger_has_no_unfiled_repeat_excursion" in status.stdout
    assert "::error::" in status.stdout
