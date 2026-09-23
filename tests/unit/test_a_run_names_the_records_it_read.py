"""`UX-997`: a run names the records it read, at the sha it read them.

`tools/dev_records.py` against a real, local, bare `origin`: `fetch`
prints the tip sha it reached, honours `--at` a past one, and falls
back to the last cached copy - printed `(cached)` - when the remote is
unreachable. `publish` seeds the branch the first time, builds a new
commit on its tip the second, and refuses (pushing nothing) a record
`dev_adopt_check` rejects - the flake ledger's own guard, for real.
"""
import json
import os
import pathlib
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]

#: What `dev_records.py publish` needs to run for real, including one
#: guard chain (`tests/flake_ledger.json`'s) to prove a rejection.
TREE = ("tools/dev_records.py", "tools/dev_adopt_check.py",
        "tools/__init__.py", "tools/dev_flake_census.py",
        "tests/unit/__init__.py",
        "tests/unit/test_a_file_with_three_excursions_has_a_filed_task.py")


def _git(cwd, *args, check=True, env=None):
    run_env = {**os.environ, **(env or {})}
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                           *args], cwd=cwd, check=check, capture_output=True,
                          text=True, env=run_env)


def _ledger(*files):
    return json.dumps({"entries": [
        {"file": name, "run_id": str(i), "shift": 1.7, "confirmed": False}
        for i, name in enumerate(files)], "declared": {}})


def _seed(work):
    for rel in TREE:
        dest = work / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, dest)
    (work / "docs/backlog/scenarios").mkdir(parents=True)
    (work / "docs/backlog/scenarios/.keep").write_text("", encoding="utf-8")
    (work / "docs/audits").mkdir(parents=True)
    (work / "docs/audits/mutation.md").write_text("# mutation\n", encoding="utf-8")
    (work / "tests/ci_reference.json").write_text("{}", encoding="utf-8")
    (work / "tests/touch_map.json").write_text("{}", encoding="utf-8")
    (work / "tests/flake_ledger.json").write_text(_ledger(), encoding="utf-8")


def _repo(tmp_path):
    """A work checkout with a bare `origin`, the tree `dev_records.py`
    needs, and one commit on `main`."""
    work, remote = tmp_path / "work", tmp_path / "remote.git"
    _seed(work)
    _git(work, "init", "-q", "-b", "main")
    _git(work, "add", ".")
    _git(work, "commit", "-q", "-m", "base")
    _git(tmp_path, "clone", "-q", "--bare", str(work), str(remote))
    _git(work, "remote", "add", "origin", str(remote))
    return work, remote


def _parents(cwd, ref):
    """The commit object's own `parent` header lines - `cat-file`, not
    `log`: a direct object read, not a history walk (`UX-637`)."""
    body = _git(cwd, "cat-file", "-p", ref).stdout.splitlines()
    return [line.split()[1] for line in body if line.startswith("parent ")]


def _clone_job(tmp_path, remote, name):
    """A second checkout of `main` off `remote` - a different CI job,
    which never saw whatever another job has since published."""
    job = tmp_path / name
    _git(tmp_path, "clone", "-q", str(remote), str(job))
    return job


def _recorded_base(cwd):
    got = _git(cwd, "config", "--get", "bga.records-base", check=False)
    return got.stdout.strip() if got.returncode == 0 else None


def _dev_records(work, *args):
    run_env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    run_env["PATH"] = f"{pathlib.Path(sys.executable).parent}{os.pathsep}{run_env['PATH']}"
    return subprocess.run([sys.executable, "tools/dev_records.py", *args],
                          cwd=work, env=run_env, capture_output=True, text=True)


class TestPublishSeedsThenBuilds:

    def test_the_first_publish_seeds_an_orphan_root(self, tmp_path):
        work, remote = _repo(tmp_path)
        (work / "tests/flake_ledger.json").write_text(_ledger("t.py", "t.py"),
                                                       encoding="utf-8")
        done = _dev_records(work, "publish")
        assert done.returncode == 0, done.stdout + done.stderr
        assert "records @ " in done.stdout, done.stdout
        assert _parents(remote, "refs/heads/records") == [], \
            "the seeding commit has a parent"
        shown = _git(remote, "show", "refs/heads/records:tests/ci_reference.json").stdout
        assert shown == "{}"

    def test_a_second_publish_builds_on_the_tip(self, tmp_path):
        work, remote = _repo(tmp_path)
        (work / "tests/flake_ledger.json").write_text(_ledger("t.py", "t.py"),
                                                       encoding="utf-8")
        first = _dev_records(work, "publish")
        assert first.returncode == 0, first.stdout + first.stderr
        first_sha = first.stdout.strip().rsplit(" ", 1)[-1]

        refetch = _dev_records(work, "fetch")
        assert refetch.returncode == 0, refetch.stdout + refetch.stderr
        (work / "tests/flake_ledger.json").write_text(
            _ledger("t.py", "t.py", "other.py"), encoding="utf-8")
        second = _dev_records(work, "publish")
        assert second.returncode == 0, second.stdout + second.stderr
        assert _parents(remote, "refs/heads/records") == [first_sha]


class TestFetch:

    def test_the_tip_sha_is_printed_and_files_written(self, tmp_path):
        work, remote = _repo(tmp_path)
        (work / "tests/flake_ledger.json").write_text(_ledger("t.py"), encoding="utf-8")
        published = _dev_records(work, "publish")
        assert published.returncode == 0, published.stdout + published.stderr
        tip = published.stdout.strip().rsplit(" ", 1)[-1]

        reader = tmp_path / "reader"
        shutil.copytree(work, reader)
        (reader / "tests/ci_reference.json").write_text("garbage", encoding="utf-8")
        done = _dev_records(reader, "fetch")
        assert done.returncode == 0, done.stdout + done.stderr
        assert done.stdout.strip() == f"records @ {tip}"
        assert (reader / "tests/ci_reference.json").read_text() == "{}"
        assert (reader / "tests/.records-sha").read_text().strip() == tip

    def test_at_a_past_sha_is_honoured(self, tmp_path):
        work, remote = _repo(tmp_path)
        (work / "tests/flake_ledger.json").write_text(_ledger("t.py"), encoding="utf-8")
        first = _dev_records(work, "publish")
        assert first.returncode == 0, first.stdout + first.stderr
        first_sha = first.stdout.strip().rsplit(" ", 1)[-1]

        refetch = _dev_records(work, "fetch")
        assert refetch.returncode == 0, refetch.stdout + refetch.stderr
        (work / "tests/flake_ledger.json").write_text(_ledger("t.py", "t.py"),
                                                       encoding="utf-8")
        second = _dev_records(work, "publish")
        assert second.returncode == 0, second.stdout + second.stderr

        reader = tmp_path / "reader"
        shutil.copytree(work, reader)
        done = _dev_records(reader, "fetch", "--at", first_sha)
        assert done.returncode == 0, done.stdout + done.stderr
        assert done.stdout.strip() == f"records @ {first_sha}"
        assert (reader / "tests/flake_ledger.json").read_text() == _ledger("t.py")

    def test_offline_with_a_cached_copy_says_so(self, tmp_path):
        work, remote = _repo(tmp_path)
        (work / "tests/flake_ledger.json").write_text(_ledger("t.py"), encoding="utf-8")
        published = _dev_records(work, "publish")
        assert published.returncode == 0, published.stdout + published.stderr
        tip = published.stdout.strip().rsplit(" ", 1)[-1]
        first = _dev_records(work, "fetch")
        assert first.stdout.strip() == f"records @ {tip}"

        _git(work, "remote", "set-url", "origin",
             str(tmp_path / "no-such-remote.git"), check=True)
        offline = _dev_records(work, "fetch")
        assert offline.returncode == 0, offline.stdout + offline.stderr
        assert offline.stdout.strip() == f"{tip} (cached)"

    def test_offline_with_no_cache_is_refused(self, tmp_path):
        work, remote = _repo(tmp_path)
        _git(work, "remote", "set-url", "origin",
             str(tmp_path / "no-such-remote.git"), check=True)
        done = _dev_records(work, "fetch")
        assert done.returncode != 0
        assert "::error::" in done.stdout + done.stderr


class TestPublishRefusesARejectedRecord:

    def test_a_ledger_its_guard_accepts_is_published(self, tmp_path):
        """The control: without it, the refusal below could be a broken fixture."""
        work, remote = _repo(tmp_path)
        before = _git(remote, "rev-parse", "--verify", "refs/heads/records",
                      check=False)
        (work / "tests/flake_ledger.json").write_text(_ledger("t.py", "t.py"),
                                                       encoding="utf-8")
        done = _dev_records(work, "publish")
        assert done.returncode == 0, done.stdout + done.stderr
        after = _git(remote, "rev-parse", "--verify", "refs/heads/records")
        assert before.returncode != 0 and after.returncode == 0

    def test_a_ledger_its_guard_rejects_is_refused_and_nothing_is_pushed(self, tmp_path):
        work, remote = _repo(tmp_path)
        (work / "tests/flake_ledger.json").write_text(
            _ledger("t.py", "t.py", "t.py"), encoding="utf-8")
        done = _dev_records(work, "publish")
        assert done.returncode != 0, done.stdout + done.stderr
        assert "test_the_real_ledger_has_no_unfiled_repeat_excursion" in done.stdout, done.stdout
        refused = _git(remote, "rev-parse", "--verify", "refs/heads/records",
                       check=False)
        assert refused.returncode != 0, "the rejected record was pushed anyway"


class TestPublishRefusesAStaleBase:
    """The verifier's own repro: `fetch`'s failure is swallowed by the
    workflow's `|| true`, `publish`'s own second fetch (`_records_tip`)
    then succeeds, and a naive overlay would drop whatever the branch
    gained in between. Two checkouts of the same `remote`, one for each
    job."""

    def test_a_swallowed_fetch_failure_refuses_rather_than_drops_a_row(self, tmp_path):
        _, remote = _repo(tmp_path)

        # A second job fetches (the branch does not exist yet: a known,
        # empty base), then publishes "b" - the row a naive overlay
        # would later lose.
        other = _clone_job(tmp_path, remote, "other")
        refetch = _dev_records(other, "fetch")
        assert refetch.returncode == 0, refetch.stdout + refetch.stderr
        assert _recorded_base(other) == "none"
        (other / "tests/flake_ledger.json").write_text(_ledger("b"), encoding="utf-8")
        published_b = _dev_records(other, "publish")
        assert published_b.returncode == 0, published_b.stdout + published_b.stderr
        tip_b = published_b.stdout.strip().rsplit(" ", 1)[-1]
        assert _git(remote, "show", f"{tip_b}:tests/flake_ledger.json").stdout \
            == _ledger("b")

        # The victim job: a fresh checkout - `main`'s own tracked copy,
        # never touched by either publish above - whose fetch fails.
        victim = _clone_job(tmp_path, remote, "victim")
        _git(victim, "remote", "set-url", "origin",
             str(tmp_path / "no-such-remote.git"), check=True)
        failed = _dev_records(victim, "fetch")
        assert failed.returncode != 0, failed.stdout + failed.stderr
        assert _recorded_base(victim) is None, "a failed fetch recorded a base"

        # Its own adopt tool appends "e" on top of the stale tree it has.
        (victim / "tests/flake_ledger.json").write_text(_ledger("e"), encoding="utf-8")

        # The remote answers again by the time `publish` runs.
        _git(victim, "remote", "set-url", "origin", str(remote), check=True)
        refused = _dev_records(victim, "publish")
        assert refused.returncode != 0, refused.stdout + refused.stderr
        assert "::error::" in refused.stdout, refused.stdout
        assert "none" in refused.stdout and tip_b in refused.stdout, refused.stdout

        # Nothing moved, and "b" is exactly where the other job left it.
        after = _git(remote, "rev-parse", "refs/heads/records").stdout.strip()
        assert after == tip_b
        assert _git(remote, "show", f"{tip_b}:tests/flake_ledger.json").stdout \
            == _ledger("b")
