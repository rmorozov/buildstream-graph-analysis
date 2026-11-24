"""`UX-1361`: a scheduled capture takes a commit the project's cache still holds.

A pin outlived freedesktop-sdk's cache five times in seven weeks; the clone
step now resolves the newest `FDSDK_BRANCH` commit `FDSDK_LAG_DAYS` old, and
the verify step builds and records a straggler or two instead of going dark.
Both step bodies run here, against a dated local remote and fixture state.
"""

import os
import pathlib
import subprocess

import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = yaml.safe_load((REPO / ".github/workflows/real-project-capture.yml").read_text(encoding="utf-8"))
STEPS = WORKFLOW["jobs"]["capture"]["steps"]
BRANCH = "release/26.08"


def _step(name):
    return next(step for step in STEPS if step.get("name") == name)["run"]


def _git(cwd, *args, date=None):
    env = {**os.environ, **({"GIT_COMMITTER_DATE": date, "GIT_AUTHOR_DATE": date} if date else {})}
    return subprocess.run(["git", *args], cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout.strip()


def _remote(tmp_path, ages_days):
    src = tmp_path / "src"
    _git(tmp_path, "init", "-q", "-b", BRANCH, str(src))
    shas = []
    for age in ages_days:
        date = subprocess.run(["date", "-R", "-d", f"{age} days ago"], capture_output=True, text=True).stdout.strip()
        _git(
            src, "-c", "user.name=f", "-c", "user.email=f@x", "commit", "-q", "--allow-empty", "-m", str(age), date=date
        )
        shas.append(_git(src, "rev-parse", "HEAD"))
    return src, dict(zip(ages_days, shas))


def _clone(tmp_path, src, ref=""):
    script = _step("Clone freedesktop-sdk").replace(
        "https://gitlab.com/freedesktop-sdk/freedesktop-sdk.git", f"file://{src}"
    )
    env_file, summary = tmp_path / "env", tmp_path / "summary"
    env = {
        **os.environ,
        "FDSDK_REF": ref,
        "FDSDK_BRANCH": BRANCH,
        "FDSDK_LAG_DAYS": WORKFLOW["env"]["FDSDK_LAG_DAYS"],
        "GITHUB_ENV": str(env_file),
        "GITHUB_STEP_SUMMARY": str(summary),
    }
    done = subprocess.run(["bash", "-e", "-c", script], cwd=tmp_path, env=env, capture_output=True, text=True)
    return done, (env_file.read_text() if env_file.exists() else "")


def test_a_schedule_takes_the_newest_commit_past_the_lag(tmp_path):
    src, shas = _remote(tmp_path, [9, 3, 1, 0])
    done, env = _clone(tmp_path, src)
    assert done.returncode == 0, done.stderr
    assert env == f"FDSDK_REF={shas[3]}\n"
    assert done.stdout.strip().endswith(shas[3])


def test_a_dispatched_commit_is_taken_as_given(tmp_path):
    src, shas = _remote(tmp_path, [9, 3, 1, 0])
    done, env = _clone(tmp_path, src, ref=shas[9])
    assert done.returncode == 0, done.stderr
    assert env == ""
    assert done.stdout.strip().endswith(shas[9])


def test_a_schedule_takes_nothing_newer_than_the_lag(tmp_path):
    assert WORKFLOW["env"]["FDSDK_LAG_DAYS"] == "2"
    assert "${{" not in WORKFLOW["env"]["FDSDK_BRANCH"]
    assert WORKFLOW["env"]["FDSDK_REF"] == "${{ github.event.inputs.fdsdk_ref }}"


def _verify(tmp_path, rebuild, not_cached, cached=10):
    capture = tmp_path / "capture"
    capture.mkdir()
    (capture / "rebuild-set.txt").write_text("\n".join(rebuild) + "\n")
    rows = [f"c{i}.bst|cached" for i in range(cached)] + [f"{name}|fetch needed" for name in not_cached]
    (capture / "state-after-delete.txt").write_text("\n".join(rows) + "\n")
    done = subprocess.run(
        ["bash", "-e", "-c", _step("Verify the cut is exactly the rebuild set")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    return done, (capture / "beyond-cut.txt")


def test_one_straggler_is_built_and_recorded(tmp_path):
    done, beyond = _verify(tmp_path, ["a.bst", "b.bst"], ["a.bst", "b.bst", "bootstrap/build/rsync.bst"])
    assert done.returncode == 0, done.stderr
    assert beyond.read_text() == "bootstrap/build/rsync.bst\n"
    assert "::warning::1 element(s) beyond the cut" in done.stdout


def test_an_exact_cut_records_nothing_beyond_it(tmp_path):
    done, beyond = _verify(tmp_path, ["a.bst"], ["a.bst"])
    assert done.returncode == 0, done.stderr
    assert beyond.read_text() == ""


def test_three_stragglers_are_a_red_cut(tmp_path):
    done, _ = _verify(tmp_path, ["a.bst"], ["a.bst", "x.bst", "y.bst", "z.bst"])
    assert done.returncode != 0
    assert "3 element(s) would be built beyond the intended cut" in done.stderr
