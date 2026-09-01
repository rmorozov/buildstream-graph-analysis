"""UX-473: the step that builds a generated project is in `ci.yml`.

`tools/bga_gen_project.py` works, and `UX-465` proved it by building two
generated projects in `bst-tests`. What ran nowhere on a schedule is the
**census over one of those builds** - so `build-failed` and
`failed-task-time`, the two findings no committed capture can reach
(`UX-189`: a clone ships none), were reachable only by a command
somebody had to remember to run. That is the "true on one machine" shape
`UX-213` and `UX-459` are both about.

A guard over a workflow is a text read of YAML, and that has a known
failure mode: it can pass on a step that exists and does nothing. So
these clauses assert the *pieces that make the step do its job* - the
generator, the capture, the census, and the `--also` that joins them -
rather than the step's name.
"""
import pathlib

import yaml

import tools.dev_finding_coverage as census
from bga.findings import FINDING_READERS

REPO = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github/workflows/ci.yml"


def _steps(job):
    loaded = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    return loaded["jobs"][job]["steps"]


def _the_step():
    for step in _steps("bst-examples"):
        if "dev_finding_coverage.py" in (step.get("run") or ""):
            return step
    return None


class TestTheStepIsThereAndDoesTheWork:
    def test_bst_examples_runs_the_census(self):
        assert _the_step() is not None, (
            "no step in bst-examples runs tools/dev_finding_coverage.py - "
            "UX-473 is what put it there, and without it the two findings "
            "only a generated build reaches are checked by nothing")

    def test_it_generates_a_project_first(self):
        """A census over nothing is a census that prints the same number
        a clone already prints, which is the state this row is about."""
        run = _the_step()["run"]
        assert "tools/bga_gen_project.py" in run, run
        assert "tests/fixtures/specs/a-build-that-fails.json" in run, run

    def test_the_spec_it_names_is_committed_and_valid(self):
        """The step names one spec by path. A rename would leave the step
        failing on a runner and nothing here saying why."""
        import json

        from tools import bga_gen_project as gen

        spec = REPO / "tests/fixtures/specs/a-build-that-fails.json"
        assert spec.exists(), spec
        gen.validate(json.loads(spec.read_text(encoding="utf-8")))

    def test_it_captures_the_build_rather_than_only_building_it(self):
        """`bst build` alone leaves no run directory, and the census
        reads run directories."""
        run = _the_step()["run"]
        assert "bga snapshot" in run, run
        assert ".bga/runs/" in run, run

    def test_the_census_is_told_where_the_capture_is(self):
        """The generated capture is outside the tree on purpose
        (`UX-189`), so the discovery globs cannot find it and `--also` is
        the whole join between the two halves of this step."""
        assert "--also" in _the_step()["run"], _the_step()["run"]

    def test_a_failing_build_does_not_fail_the_step_on_its_exit_status(self):
        """The spec's build is *meant* to fail - that is how it reaches
        `build-failed` - so `bga snapshot` exits non-zero and the step
        must not treat that as its own failure.

        **This clause used to read the wrong half, and `UX-484` is what
        that cost.** It asserted `set -uo pipefail` was in the body and
        `set -euo pipefail` was not - a text scan for the spelling of a
        line, standing in for "does a non-zero exit end this step".
        Those are different questions, and the distance between them is
        that GitHub starts every `run:` block with
        `shell: /usr/bin/bash -e {0}`: the body sets three options and
        clears none, so `-e` was live and the step died on the failing
        build for five consecutive runs while this clause passed.

        What is asserted now is the mechanism: the snapshot's status is
        **captured**, which makes it a handled failure that `-e` does
        not act on, and the step is then correct whichever shell the
        runner picks. The `set` line stays asserted as a second belt,
        not as the claim.
        """
        run = _the_step()["run"]
        snapshot = next((line for line in run.splitlines()
                         if "bga snapshot" in line), "")
        assert snapshot, run
        # The command and its handler may be split across a continuation,
        # so the test is over the joined body rather than the one line.
        joined = run.replace("\\\n", " ")
        handled = next((line for line in joined.splitlines()
                        if "bga snapshot" in line), "")
        assert "|| status=$?" in handled, (
            "the snapshot's exit status is not captured, so a `-e` shell "
            "- which is what the runner gives every `run:` block - ends "
            "the step on the build this step exists to make fail: "
            + handled)
        assert "$status" in run, (
            "the captured status is never printed, so a reader of the "
            "log cannot tell a failing build from a broken step")
        assert "set -uo pipefail" in run, run

    def test_it_prints_rather_than_gating_on_a_bound(self):
        """`UX-473` Out of Scope: a threshold nobody has measured is
        `UX-458`'s open question one axis over. A `-lt`/`-gt` against a
        count here would be that mistake."""
        run = _the_step()["run"]
        assert "dev_finding_coverage.py --also" in run.replace("\\\n", ""), run
        assert not any(op in run for op in (" -lt ", " -gt ", " -ge ", " -le ")), run


class TestTheCensusCanBeToldAboutARunOutsideTheTree:
    def test_also_adds_a_run_the_globs_cannot_find(self, tmp_path):
        """The mechanism the step rests on, exercised rather than read.
        `captures()` globs two paths inside the repository; a run in
        `tmp_path` matches neither."""
        outside = tmp_path / "somewhere" / "run"
        outside.mkdir(parents=True)
        found = census.captures(tracked_only=True, also=[outside])

        assert outside.resolve() in found
        assert outside.resolve() not in census.captures(tracked_only=True)

    def test_a_run_outside_the_tree_still_gets_a_name(self, tmp_path):
        """`label()` computes a path relative to the repository, which
        raises for anything outside it. A census that crashes on the run
        it was told about is worse than one that never had it."""
        outside = tmp_path / "generated-project" / "run"
        outside.mkdir(parents=True)
        assert census.label(outside) == "run"

        inside_bga = tmp_path / "myproject" / ".bga" / "runs" / "S" / "run"
        inside_bga.mkdir(parents=True)
        assert census.label(inside_bga) == "myproject"

    def test_the_declared_pair_is_what_only_a_generated_build_reaches(self):
        """The two findings this whole step exists for. If either stops
        being declared unreachable, a committed capture now produces it
        and the step's justification has changed."""
        assert set(census.UNREACHABLE) == {"build-failed", "failed-task-time"}
        for name in census.UNREACHABLE:
            assert name in FINDING_READERS, name
