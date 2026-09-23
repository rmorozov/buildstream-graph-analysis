"""`UX-1000` T2: CI publishes the area pages to `records`, not main.

Against a real, local, bare `origin`: `dev_records.py publish --pages
DIR` overlays `docs/backlog/areas/` from `DIR`'s `.md` files onto the
tip, beside whichever of the four record paths this run changed (none,
here) - a second identical run publishes nothing. The job itself,
`area-pages-publish`, is read off `ci.yml`: `concurrency: records` and
a `fetch` before its `publish --pages` step - ordering otherwise is
`test_an_adopt_job_reads_its_record_before_it_pushes.py`'s, generic
across every publishing job.
"""
import os
import pathlib
import shutil
import subprocess
import sys

import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github/workflows/ci.yml"
TREE = ("tools/dev_records.py", "tools/dev_adopt_check.py", "tools/__init__.py")


def _git(cwd, *args, check=True, env=None):
    run_env = {**os.environ, **(env or {})}
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@t",
                           *args], cwd=cwd, check=check, capture_output=True,
                          text=True, env=run_env)


def _seed(tmp_path_work):
    for rel in TREE:
        dest = tmp_path_work / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(REPO / rel, dest)
    (tmp_path_work / "tests").mkdir(parents=True)
    (tmp_path_work / "tests/ci_reference.json").write_text("{}", encoding="utf-8")
    (tmp_path_work / "tests/touch_map.json").write_text("{}", encoding="utf-8")
    (tmp_path_work / "tests/flake_ledger.json").write_text(
        '{"entries": [], "declared": {}}', encoding="utf-8")
    (tmp_path_work / "docs/audits").mkdir(parents=True)
    (tmp_path_work / "docs/audits/mutation.md").write_text("# mutation\n", encoding="utf-8")


def _repo(tmp_path):
    tmp_path_work, remote = tmp_path / "tmp_path_work", tmp_path / "remote.git"
    _seed(tmp_path_work)
    _git(tmp_path_work, "init", "-q", "-b", "main")
    _git(tmp_path_work, "add", ".")
    _git(tmp_path_work, "commit", "-q", "-m", "base")
    _git(tmp_path, "clone", "-q", "--bare", str(tmp_path_work), str(remote))
    _git(tmp_path_work, "remote", "add", "origin", str(remote))
    return tmp_path_work, remote


def _dev_records(tmp_path_work, *args):
    run_env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    run_env["PATH"] = f"{pathlib.Path(sys.executable).parent}{os.pathsep}{run_env['PATH']}"
    return subprocess.run([sys.executable, "tools/dev_records.py", *args],
                          cwd=tmp_path_work, env=run_env, capture_output=True, text=True)


def _pages(tmp_path, **files):
    out = tmp_path / "pages"
    out.mkdir()
    for name, text in files.items():
        (out / name).write_text(text, encoding="utf-8")
    return out


class TestPublishPages:

    def test_pages_push_beside_untouched_records(self, tmp_path):
        tmp_path_work, remote = _repo(tmp_path)
        seeded = _dev_records(tmp_path_work, "publish")
        assert seeded.returncode == 0, seeded.stdout + seeded.stderr
        assert _dev_records(tmp_path_work, "fetch").returncode == 0

        pages = _pages(tmp_path, **{"bga.md": "# bga\n\ncovered 1 / 1\n"})
        done = _dev_records(tmp_path_work, "publish", "--pages", str(pages))
        assert done.returncode == 0, done.stdout + done.stderr
        shown = _git(remote, "show", "refs/heads/records:docs/backlog/areas/bga.md")
        assert shown.stdout == "# bga\n\ncovered 1 / 1\n"
        # the four record paths are untouched, carried over from the tip
        ledger = _git(remote, "show", "refs/heads/records:tests/flake_ledger.json")
        assert ledger.stdout == '{"entries": [], "declared": {}}'

    def test_a_second_identical_run_publishes_nothing(self, tmp_path):
        tmp_path_work, remote = _repo(tmp_path)
        assert _dev_records(tmp_path_work, "publish").returncode == 0
        assert _dev_records(tmp_path_work, "fetch").returncode == 0
        pages = _pages(tmp_path, **{"bga.md": "# bga\n"})
        first = _dev_records(tmp_path_work, "publish", "--pages", str(pages))
        assert first.returncode == 0, first.stdout + first.stderr
        tip_after_first = _git(remote, "rev-parse", "refs/heads/records").stdout.strip()

        assert _dev_records(tmp_path_work, "fetch").returncode == 0
        again = _dev_records(tmp_path_work, "publish", "--pages", str(pages))
        assert again.stdout.strip() == "nothing to publish - no record changed", again.stdout
        tip_after_second = _git(remote, "rev-parse", "refs/heads/records").stdout.strip()
        assert tip_after_second == tip_after_first


class TestTheJob:

    def _job(self):
        jobs = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]
        return jobs["area-pages-publish"]

    def test_it_needs_both_adopt_jobs(self):
        assert set(self._job()["needs"]) == {"touch-map-adopt", "flake-ledger-adopt"}

    def test_it_shares_the_records_concurrency_group(self):
        assert self._job()["concurrency"] == "records"

    def test_it_fetches_before_it_publishes_pages(self):
        lines = [line for step in self._job()["steps"]
                 for line in (step.get("run") or "").splitlines()]
        fetch_at = next(i for i, s in enumerate(lines) if "dev_records.py fetch" in s)
        publish_at = next(i for i, s in enumerate(lines)
                          if "dev_records.py publish --pages" in s)
        assert fetch_at < publish_at, lines
