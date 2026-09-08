"""UX-698: the analyses too slow for the inner loop run on GitHub.

Code scanning, a lockfile audit and dependency updates are hosted
jobs on a pull request and a weekly schedule; `make lint` never runs
them. The lockfile is the dev extra resolved, so an audit reads what
CI installs; an archive member that escapes its directory is dropped.
"""
import io
import pathlib
import re
import sys
import tarfile

import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import bst_baseline_set

QUALITY = REPO / ".github/workflows/quality.yml"
LOCK = REPO / "requirements.lock"


def _dev_extra_names():
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    block = text[text.index("dev = ["):]
    block = block[:block.index("\n]")]
    return {re.match(r"[A-Za-z0-9_.-]+", line.strip().strip('",')).group(0).lower()
            for line in block.splitlines()[1:]
            if line.strip().startswith('"')}


class TestTheShelfIsHosted:
    def test_the_workflow_carries_the_four_jobs_on_both_triggers(self):
        text = QUALITY.read_text(encoding="utf-8")
        jobs = set(re.findall(r"^  ([a-z-]+):$", text, re.M))
        assert {"eslint", "codeql", "pip-audit", "sizes"} <= jobs, jobs
        assert "pull_request:" in text and "schedule:" in text

    def test_each_shelf_job_names_its_tool(self):
        """A job named `sizes` whose `run:` was swapped for `echo skip`
        still has a job named `sizes` - the name alone does not say
        the job runs what it claims. Each job's steps must mention
        the tool, in `run:` or `uses:`."""
        workflow = yaml.safe_load(QUALITY.read_text(encoding="utf-8"))
        expect = {
            "sizes": "dev_sizes.py --check",
            "pip-audit": "pip-audit",
            "codeql": "github/codeql-action/analyze",
            "eslint": "eslint",
        }
        for job, needle in expect.items():
            steps = workflow["jobs"][job]["steps"]
            blob = "\n".join(str(step.get("run", "")) + str(step.get("uses", ""))
                             for step in steps)
            assert needle in blob, (job, blob)

    def test_make_lint_runs_none_of_them(self):
        lint = (REPO / "Makefile").read_text(encoding="utf-8")
        target = lint[lint.index("\nlint:"):lint.index("\nlint-docs:")]
        for word in ("codeql", "pip-audit", "eslint", "dependabot", "dev_sizes"):
            assert word not in target, word

    def test_dependabot_covers_pip_and_actions(self):
        text = (REPO / ".github/dependabot.yml").read_text(encoding="utf-8")
        assert "package-ecosystem: pip" in text
        assert "package-ecosystem: github-actions" in text


class TestTheLockfileIsTheDevExtra:
    def test_every_dev_dependency_is_pinned(self):
        pinned = {line.split("==")[0].lower() for line in LOCK.read_text(encoding="utf-8").splitlines()
                  if "==" in line and not line.startswith("#")}
        missing = _dev_extra_names() - pinned
        assert not missing, missing

    def test_every_pin_is_exact(self):
        loose = [line for line in LOCK.read_text(encoding="utf-8").splitlines()
                 if line and not line.startswith(("#", " ")) and "==" not in line]
        assert loose == [], loose


class TestAnArchiveStaysInsideItsDirectory:
    def _archive(self, tmp_path, names):
        buffer = io.BytesIO()
        with tarfile.open(fileobj=buffer, mode="w") as tar:
            for name in names:
                info = tarfile.TarInfo(name)
                info.size = 1
                tar.addfile(info, io.BytesIO(b"x"))
        path = tmp_path / "a.tar"
        path.write_bytes(buffer.getvalue())
        return path

    def test_a_member_that_escapes_is_not_written(self, tmp_path):
        dest = tmp_path / "dest"
        dest.mkdir()
        archive = self._archive(tmp_path, ["run/inside.txt", "../outside.txt"])
        with tarfile.open(archive) as tar:
            bst_baseline_set._extract_within(tar, str(dest))
        assert (dest / "run" / "inside.txt").read_bytes() == b"x"
        assert not (tmp_path / "outside.txt").exists()
