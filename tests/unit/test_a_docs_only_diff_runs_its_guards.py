"""UX-956: a docs-only pull request runs a light lane, and the lane
still runs every guard a doc change can redden.

Three claims: the derived doc set is complete against a textual
witness; the lane is that set plus the selector's (census included);
the heavy jobs carry the docs-only `if:` and nothing that adopts can
run on a lane run.
"""
import io
import pathlib
import re
import subprocess
import sys
import types

import pytest
import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(REPO / "tests"))

import dev_docs_lane
import dev_docs_only
import tiers

WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"
SKIPS = "needs.changes.outputs.docs_only != 'true'"
RUNS = "needs.changes.outputs.docs_only == 'true'"
HEAVY = {"test", "bst-smoke", "bst-tests", "bst-examples"}
#: Jobs that run whatever the diff is; a new job has to be put in one set.
EITHER = {"changes", "tier-reference", "tier-reference-adopt", "touch-map-adopt",
          "flake-ledger-adopt", "agent-config", "packaging", "installed-capture"}

#: The textual witness: a line that walks or lists the tree, and a docs
#: marker on it or on the definition of the name it walks.
WALK = re.compile(r"\.(?:r?glob|iglob|iterdir|listdir|scandir)\(|\bos\.walk\(|ls-files")
MARK = re.compile(r"docs|\.md\b|\.claude|README|CLAUDE|SKILL")
RECEIVER = re.compile(r"(\w+)\)*\s*\.(?:r?glob|iglob|iterdir)\(|(?:listdir|scandir|walk)\(\s*(\w+)")
DEFINITION = re.compile(r"\s*(\w+)\s*(?::[^=]*)?=[^=](.*)")


def _witnessed(text):
    defs = {}
    for line in text.splitlines():
        m = DEFINITION.match(line)
        if m:
            defs.setdefault(m.group(1), []).append(m.group(2))

    def marked(name, depth=0):
        return any(MARK.search(rhs) or (depth < 3 and any(
            marked(other, depth + 1) for other in re.findall(r"[A-Za-z_]\w*", rhs)
            if other != name)) for rhs in defs.get(name, ()))

    for line in text.splitlines():
        if not WALK.search(line):
            continue
        if MARK.search(line) or any(marked(m.group(1) or m.group(2))
                                    for m in RECEIVER.finditer(line)):
            return True
    return False


@pytest.fixture(scope="module")
def readers():
    return set(dev_docs_lane.doc_readers())


@pytest.fixture(scope="module")
def jobs():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]


def _steps(job):
    return "\n".join(f"{step.get('run', '')} {step.get('with', '')}"
                     for step in job["steps"])


def _needs(job):
    needs = job.get("needs", [])
    return [needs] if isinstance(needs, str) else needs


class TestTheDocSetIsComplete:
    def test_every_test_the_witness_sees_reading_docs_is_in_the_lane(self, readers):
        witnessed = {str(p.relative_to(REPO))
                     for p in sorted((REPO / "tests").rglob("test_*.py"))
                     if _witnessed(p.read_text(encoding="utf-8"))}
        assert len(witnessed) >= 20, f"the witness collapsed to {len(witnessed)}"
        missing = sorted(witnessed - readers - set(tiers.CENSUS))
        assert missing == [], (
            f"{len(missing)} test(s) walk docs and a docs-only lane would not "
            f"select them: {missing}")

    @pytest.mark.parametrize("name", [
        # a glob over a docs directory, rooted at a module constant
        "test_documentation_debt_has_a_door.py",
        "test_a_pasted_guide_block_is_fresh_or_dated.py",
        # through a tool function whose own body globs the backlog
        "test_the_premise_is_a_declared_field.py",
        # two hops: `dev_scenario` -> `dev_finding_coverage.tracked_paths`
        "test_a_scenario_is_named_by_its_seed.py",
    ])
    def test_a_reader_the_per_file_grep_misses_is_derived(self, readers, name):
        assert f"tests/unit/{name}" in readers


class TestTheLaneIsThatSetPlusTheCensus:
    DIFF = ["docs/design/styleguide.md", "docs/backlog/scenarios/README.md"]

    def test_the_lane_is_the_selection_and_the_readers(self, readers):
        selected, _ = dev_docs_lane.dev_touching.select(self.DIFF)
        lane = set(dev_docs_lane.lane(self.DIFF))
        assert lane == set(selected) | readers
        assert set(tiers.CENSUS) <= lane

    def test_run_hands_pytest_the_lane(self, monkeypatch):
        seen = {}

        def fake_run(cmd, cwd=None):
            seen["cmd"], seen["cwd"] = cmd, cwd
            return types.SimpleNamespace(returncode=0)

        # A `pytest.main()` reversion is also stubbed, so a mutation
        # reds on the missing `seen["cmd"]` rather than a nested,
        # recursive pytest run inside this worker (measured: it hangs).
        monkeypatch.setattr(subprocess, "run", fake_run)
        monkeypatch.setattr(pytest, "main", lambda argv: 99)
        code = dev_docs_lane.main(["--run"], stdin=io.StringIO("\n".join(self.DIFF)))
        assert code == 0
        assert seen["cwd"] == REPO
        assert {str(REPO / name) for name in dev_docs_lane.lane(self.DIFF)} <= set(seen["cmd"])

    def test_run_is_a_python_dash_m_pytest_subprocess_not_in_process(self):
        """UX-991: `sys.executable -m pytest`, `make test`'s own shape -
        not `pytest.main()`, whose `sys.path[0]` is this script's own
        `tools/`, not REPO."""
        cmd = dev_docs_lane.run_command(["tests/unit/test_x.py"], ["--foo"])
        assert cmd[:3] == [sys.executable, "-m", "pytest"]
        assert str(REPO / "tests/unit/test_x.py") in cmd
        assert "--foo" in cmd

    def test_a_census_file_that_imports_another_test_module_collects(self):
        """UX-991's real gap: `test_a_behaviour_claim_names_the_bst_it_was
        _read_on.py` (in `tiers.CENSUS`, always in the lane) does `from
        tests.unit.test_the_pinned_bst_is_the_documented_one import
        pinned` - a package import only REPO on `sys.path[0]` resolves.
        `run_command`'s own argv, run for real (not mocked, and not
        through `main`'s nested-pytest recursion risk) - an in-process
        `pytest.main()` reversion drops `run_command` and this fails to
        resolve it, rather than passing around the mechanism."""
        target = ("tests/unit/"
                  "test_a_behaviour_claim_names_the_bst_it_was_read_on.py")
        done = subprocess.run(dev_docs_lane.run_command([target], []),
                              cwd=REPO, capture_output=True, text=True)
        assert done.returncode == 0, done.stdout + done.stderr
        assert "ModuleNotFoundError" not in done.stdout + done.stderr

    def test_the_workflow_runs_it_on_one_python(self, jobs):
        lane = jobs["docs-lane"]
        assert lane["if"] == RUNS and _needs(lane) == ["changes"]
        text = _steps(lane)
        for step in ("dev_docs_lane.py --run", "make lint", "make check-clean",
                     "dev_close_task.py --check", "'python-version': '3.11'"):
            assert step in text, step


class TestTheDetector:
    @pytest.mark.parametrize("path, docs", [
        ("docs/guides/cli.md", True), ("README.md", True), ("CLAUDE.md", True),
        (".claude/skills/verify/SKILL.md", True), ("examples/README.md", True),
        ("tools/dev_docs_lane.py", False), (".claude/hooks/no-bulk-add.sh", False),
        ("tests/fixtures/host_cpu/README.md", False), ("Makefile", False),
        (".github/workflows/ci.yml", False), ("docs.py", False),
    ])
    def test_a_path_is_docs_by_where_and_what_it_is(self, path, docs):
        assert dev_docs_only.is_docs(path) is docs

    def test_one_code_path_or_a_push_is_the_full_workflow(self):
        assert dev_docs_only.docs_only(["docs/a.md", "README.md"])
        assert not dev_docs_only.docs_only(["docs/a.md", "bga/cli.py"])
        assert not dev_docs_only.docs_only(["docs/a.md"], event="push")
        assert not dev_docs_only.docs_only([])

    @pytest.mark.parametrize("stdin, event, verdict", [
        ("docs/a.md\n", "pull_request", "true"),
        ("", "pull_request", "false"),  # what a failed `git diff` leaves
        ("docs/a.md\n", "push", "false"),
    ])
    def test_the_verdict_it_prints(self, capsys, stdin, event, verdict):
        dev_docs_only.main(["--event", event], stdin=io.StringIO(stdin))
        assert capsys.readouterr().out.strip() == f"docs_only={verdict}"

    def test_the_workflow_asks_with_its_event(self, jobs):
        text = _steps(jobs["changes"])
        assert "git diff --name-only" in text
        assert "dev_docs_only.py --event \"${{ github.event_name }}\"" in text

    def test_the_diff_base_is_the_merge_refs_first_parent_not_base_sha(self, jobs):
        """UX-991: `base.sha` is the event's push-time snapshot, stale
        the moment main moves before the run starts - `HEAD^1` is the
        merge ref's own first parent, the base actually checked out."""
        expr = "${{ github.event_name == 'pull_request' && 'HEAD^1' || 'HEAD' }}"
        for name in ("changes", "docs-lane"):
            text = _steps(jobs[name])
            assert f'git diff --name-only "{expr}"' in text, name
            assert "base.sha" not in text, name


class TestTheHeavyJobsSkip:
    @pytest.mark.parametrize("name", sorted(HEAVY))
    def test_a_heavy_job_carries_the_docs_only_if(self, jobs, name):
        assert "changes" in _needs(jobs[name]), name
        assert jobs[name].get("if") == SKIPS, name

    def test_every_job_is_classified(self, jobs):
        assert set(jobs) == HEAVY | EITHER | {"docs-lane"}

    def test_nothing_that_adopts_runs_on_a_pull_request(self, jobs):
        writers = [name for name, job in jobs.items()
                   if (job.get("permissions") or {}).get("contents") == "write"]
        assert len(writers) >= 3, writers
        for name in writers:
            assert "github.event_name == 'push'" in jobs[name]["if"], name
