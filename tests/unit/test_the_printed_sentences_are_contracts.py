"""UX-326: what the tool prints about itself has to be true.

Two frictions from round 45's stranger walk, one rule.

**F3.** `bga analyze` ends with a "Next:" block, and its third line read

    bga snapshot /abs/path/to/project

Run verbatim that crashes — `snapshot`'s positional is
`argparse.REMAINDER`, the *build command*, so the project path arrived
as a command to execute and the wrapper refused it with a raw
`ValueError`. `UX-218` made published `next_steps` argvs *executed* in
tests; what it actually executed was a **hand-written list of two step
ids**, and neither of the two store-shaped steps was in it. Same defect
as `UX-325`'s CI list, in a test rather than in a workflow.

**F4.** `bga compare @prev @last` printed

    (--allow-mismatch was given; treat every figure below with real
     skepticism)

with no flags given at all. The sentence was gated on
`comparability_warning`, which also accumulates the cross-host caveat
(`UX-186`) and the producer note (`UX-249`) — neither of which is a
mismatch and neither of which needs a flag.

So: a printed command is checked by **parsing it into the shape it
claims**, and a printed sentence naming a flag is checked against the
state that flag produces.
"""
import contextlib
import io
import json
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import cli
from bga.tools_dispatch import TOOL_ALIASES
from tools import bga_snapshot

# The alias parsers this guard can reach. `bga snapshot` is the one the
# advice block prints; a step that starts printing another alias needs
# its parser added here, which is a smaller ask than it looks and is
# deliberately not a shell-out (see `bga_snapshot.create_parser`).
ALIAS_PARSERS = {"snapshot": bga_snapshot.create_parser}

FIXTURE_RUN = REPO / "tests/fixtures/macro_micro/run"

# A step whose command cannot be run by a test, and why. The same shape
# `tests/installed_command_sweep.py` uses: an exemption has to be argued
# in writing, and `test_only_one_step_is_exempt` keeps it from spreading.
UNRUNNABLE = {
    "measure-again": "it runs the build again, which needs `bst` and a "
                     "sandbox - so this one is parsed into its shape instead",
    "compare-with-the-run-before": "it compares against a capture that does "
                                   "not exist yet - the whole point of the "
                                   "step is that you take one next",
}

# Every sentence in `bga/report/` that claims a flag *was passed*, with
# the state it is gated on. A new one has to be classified here, which
# is the whole of F4: this sentence was gated on something that is true
# without the flag.
FLAG_CLAIMS = {
    "--allow-mismatch was given": "comparison.mismatches",
    "`--fail-on-low-confidence` was passed": "the sentence is conditional "
                                             "prose about behaviour, not a "
                                             "claim that it was",
}
_CLAIM = re.compile(r"`?--[a-z-]+`? was (?:given|passed)")


@pytest.fixture
def store_run(tmp_path):
    """A run *inside a store*, which is the only shape that offers the
    two steps `UX-218`'s guard never executed."""
    project = tmp_path / "project"
    snapshot = project / ".bga" / "runs" / "20260101T000000Z"
    snapshot.mkdir(parents=True)
    shutil.copytree(FIXTURE_RUN, snapshot / "run")
    (project / "project.conf").write_text("name: ux326\n", encoding="utf-8")
    return snapshot / "run"


def _native_subcommands(parser):
    for action in parser._actions:
        if getattr(action, "choices", None):
            return frozenset(action.choices)
    raise AssertionError("no subparser action on the CLI parser")


def _comparison_of(baseline, candidate, compare_runs):
    return compare_runs(pathlib.Path(baseline), pathlib.Path(candidate))


def _steps(run):
    from bga.cli import main

    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        main(["analyze", str(run), "--format", "json"])
    return {s["id"]: s for s in json.loads(buffer.getvalue())["next_steps"]}


class TestEveryPrintedCommandParsesIntoWhatItMeans:

    def test_the_store_shaped_steps_are_offered_at_all(self, store_run):
        """Without this the clauses below pass by finding nothing - which
        is exactly how F3 survived six rounds behind a guard."""
        offered = set(_steps(store_run))
        assert {"measure-again", "compare-with-the-run-before"} <= offered, (
            f"the store-shaped steps are not offered for a run inside a "
            f"store; got {sorted(offered)}")

    def test_every_published_argv_parses(self, store_run):
        """Against the *real* parser, natives through `create_parser` and
        aliases through the tool's own `main` - `bga snapshot` is an
        alias, so a check that only knew the native parser would call it
        an invalid command and prove nothing.

        This is what caught `compare-with-the-run-before` publishing
        `--project`, a flag `bga compare` has never had."""
        parser = cli.create_parser()
        native = _native_subcommands(parser)
        for step_id, step in sorted(_steps(store_run).items()):
            argv = step["argv"]
            assert argv[0] == "bga", (step_id, argv)
            if argv[1] in native:
                try:
                    parser.parse_args(argv[1:])
                except SystemExit as exit_code:
                    pytest.fail(f"{step_id} publishes `{' '.join(argv)}`, "
                                f"which the parser rejects (exit {exit_code})")
            else:
                assert argv[1] in TOOL_ALIASES, (
                    f"{step_id} publishes `{' '.join(argv)}`, whose command "
                    f"is neither a subcommand nor an alias bga dispatches")
                alias_parser = ALIAS_PARSERS.get(argv[1])
                assert alias_parser is not None, (
                    f"{step_id} publishes `bga {argv[1]}`, and no parser for "
                    "it is reachable here - add one rather than shelling out: "
                    "`--help` appended to a REMAINDER argv runs the build")
                try:
                    alias_parser().parse_args(argv[2:])
                except SystemExit as exit_code:
                    pytest.fail(f"{step_id} publishes `{' '.join(argv)}`, "
                                f"which the parser rejects (exit {exit_code})")

    def test_the_capture_step_puts_the_project_where_the_project_goes(
            self, store_run):
        """F3, by name. `bga snapshot <project>` also *parses* - the
        positional is a REMAINDER and swallows anything - so parsing is
        not the check. What it parses **into** is."""
        step = _steps(store_run)["measure-again"]
        parsed = bga_snapshot.create_parser().parse_args(step["argv"][2:])
        assert parsed.project, (
            f"`{' '.join(step['argv'])}` leaves --project unset, so the "
            "project path is being parsed as the build command. That is the "
            "UX-326 crash: `ValueError: command must start with 'bst'`.")
        command = [token for token in parsed.cmd if token != "--"]
        assert command and command[0] == "bst", (
            f"the build command parsed out of `{' '.join(step['argv'])}` is "
            f"{command}, which `bga snapshot` refuses")
        assert bga_snapshot.why_the_build_cannot_start(command) is None or \
            shutil.which("bst") is None, (
            "the command this step prints cannot start on a machine that "
            "has bst")

    @pytest.mark.parametrize("step_id", [
        "shorten-what-the-build-waits-for", "blast-the-top-element"])
    def test_the_runnable_steps_run(self, store_run, step_id):
        steps = _steps(store_run)
        if step_id not in steps:
            pytest.skip(f"{step_id} is not offered for this fixture")
        argv = steps[step_id]["argv"]
        done = subprocess.run([sys.executable, "-m", "bga.cli", *argv[1:]],
                              capture_output=True, text=True,
                              cwd=str(store_run.parent), timeout=300)
        assert done.returncode == 0, (
            f"`{' '.join(argv)}` exited {done.returncode}:\n{done.stderr[-800:]}")

    def test_exemption_from_execution_stays_a_minority(self, store_run):
        """If the exemption list grows, the guard becomes the thing it
        replaced: a list of commands nobody runs. Every step is parsed
        either way; this is about how many are also *run*."""
        offered = set(_steps(store_run))
        exempt = offered & set(UNRUNNABLE)
        assert len(exempt) <= len(offered) // 2, (
            f"{len(exempt)} of {len(offered)} steps are exempt from "
            f"execution ({sorted(exempt)}); UX-326 replaced a guard that ran "
            "two of four and this is how that starts again")
        for step_id in exempt:
            assert len(UNRUNNABLE[step_id]) > 40, (
                f"{step_id} is exempt with no written reason")

    def test_no_step_is_exempt_that_is_not_offered(self, store_run):
        """A stale exemption is an exemption nobody can see expire."""
        stale = sorted(set(UNRUNNABLE) - set(_steps(store_run)))
        assert not stale, f"UNRUNNABLE names steps that are not offered: {stale}"


class TestNoSentenceClaimsAFlagThatWasNotPassed:

    def test_the_caveat_does_not_claim_a_flag(self):
        """F4: two runs that are merely *caveated* - here by the producer
        note, since neither fixture carries a stamp - print no flag."""
        done = subprocess.run(
            [sys.executable, "-m", "bga.cli", "compare",
             str(FIXTURE_RUN), str(FIXTURE_RUN)],
            capture_output=True, text=True, cwd=str(REPO), timeout=300)
        assert done.returncode == 0, done.stderr[-800:]
        assert "Warning:" in done.stdout, (
            "this fixture pair no longer produces a caveat at all, so the "
            "clause is asserting nothing - pick a pair that does")
        assert "--allow-mismatch was given" not in done.stdout, (
            "a comparison run with no flags still says a flag was given:\n"
            + done.stdout[:2000])
        assert "a caveat, not a refusal" in done.stdout

    def test_a_real_mismatch_still_says_the_flag_was_given(self):
        """The other direction, so the fix is a gate and not a deletion.

        Rendered through the real `format_compare_text`, on a comparison
        built by the real `compare` and then given the mismatch a
        `--allow-mismatch` run would have carried past the refusal."""
        from bga.compare import compare_runs
        from bga.report.text import format_compare_text

        comparison = _comparison_of(FIXTURE_RUN, FIXTURE_RUN, compare_runs)
        comparison.comparability_warning = "these runs share too few elements"
        comparison.mismatches = [{"check": "shared_elements", "message": "..."}]
        rendered = format_compare_text(comparison)
        assert "--allow-mismatch was given" in rendered
        assert "a caveat, not a refusal" not in rendered

    def test_every_flag_claim_in_the_report_is_classified(self):
        """The sweep the filing asked for, kept. Any *new* sentence
        claiming a flag was passed has to be argued here."""
        found = set()
        for path in sorted((REPO / "bga" / "report").glob("*.py")):
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.lstrip().startswith("#"):
                    continue
                for match in _CLAIM.findall(line):
                    found.add(match)
        unclassified = sorted(found - set(FLAG_CLAIMS))
        assert not unclassified, (
            f"{unclassified} claim a flag was passed and are not in "
            "FLAG_CLAIMS. Say what state proves it - F4 was a sentence "
            "gated on something that is true without the flag.")
        assert found, "the scan matched nothing; the pattern has rotted"
