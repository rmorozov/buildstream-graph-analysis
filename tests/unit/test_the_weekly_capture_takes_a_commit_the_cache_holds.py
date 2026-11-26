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


def _ago(days):
    return subprocess.run(["date", "-R", "-d", f"{days} days ago"], capture_output=True, text=True).stdout.strip()


def test_a_merged_topic_commit_is_never_the_resolved_ref(tmp_path):
    """Owner's review of #352: the lag applies to the release line, not to a topic's older date."""
    src, shas = _remote(tmp_path, [10])
    ident = ["-c", "user.name=f", "-c", "user.email=f@x"]
    _git(src, "checkout", "-q", "-b", "topic")
    _git(src, *ident, "commit", "-q", "--allow-empty", "-m", "topic", date=_ago(4))
    topic = _git(src, "rev-parse", "HEAD")
    _git(src, "checkout", "-q", BRANCH)
    _git(src, *ident, "commit", "-q", "--allow-empty", "-m", "1", date=_ago(1))
    _git(src, *ident, "merge", "-q", "--no-ff", "-m", "merge", "topic", date=_ago(0))
    done, env = _clone(tmp_path, src)
    assert done.returncode == 0, done.stderr
    assert env == f"FDSDK_REF={shas[10]}\n", (env, topic)


def test_a_quiet_branch_resolves_to_its_tip(tmp_path):
    """Owner's review of #352: a tip older than any shallow-since window must still be fetched."""
    src, shas = _remote(tmp_path, [60, 45])
    done, env = _clone(tmp_path, src)
    assert done.returncode == 0, done.stderr
    assert env == f"FDSDK_REF={shas[45]}\n"


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


def _prefetch(tmp_path):
    fdsdk, bin_dir = tmp_path / "fdsdk", tmp_path / "bin"
    fdsdk.mkdir()
    bin_dir.mkdir()
    (bin_dir / "bst").write_text('#!/bin/sh\necho "$*" >> "$BST_LOG"\n')
    (bin_dir / "bst").chmod(0o755)
    log = tmp_path / "bst.log"
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "BST_LOG": str(log)}
    script = _step("Pre-fetch the sources beyond the cut")
    done = subprocess.run(["bash", "-e", "-c", script], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return log.read_text() if log.exists() else ""


def test_a_straggler_s_sources_are_fetched_before_the_clock_starts(tmp_path):
    """Owner's review of #352: the verify step's record is what the pre-fetch reads."""
    done, _ = _verify(tmp_path, ["a.bst"], ["a.bst", "bootstrap/build/rsync.bst"])
    assert done.returncode == 0, done.stderr
    assert _prefetch(tmp_path) == "--no-interactive source fetch --deps none bootstrap/build/rsync.bst\n"
    names = [step.get("name") for step in STEPS]
    verify, fetch = (
        names.index("Verify the cut is exactly the rebuild set"),
        names.index("Pre-fetch the sources beyond the cut"),
    )
    assert verify < fetch < names.index("Capture the build (both planes)")


def test_an_exact_cut_fetches_nothing_more(tmp_path):
    done, _ = _verify(tmp_path, ["a.bst"], ["a.bst"])
    assert done.returncode == 0, done.stderr
    assert _prefetch(tmp_path) == ""
