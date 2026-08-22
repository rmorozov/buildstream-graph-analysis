"""UX-200: the analyze pipeline had no progress at all.

Field report: *"bga analyze in bga snapshot work for considerable
several minutes, maybe progress here would be great"* — and round 22
ground-truthed it: `UX-183`'s five tickers all live *outside* the
analyze pipeline (Plane 2 processing, `bst show`, the store walk).
Nothing under `bga/analyzer.py`, `bga/correlate.py` or `bga/ingest/`
imported `progress`, so the phases where the minutes go were silent
from invocation to report.

The fix draws for real because `bga snapshot` calls analyze
**in-process**, so stderr is still the user's terminal.

The second half is `[all]`: `[dev]`, `[bst]` and `[completion]` existed
and a user who wanted the full experience assembled it by hand.
"""
import os
import subprocess
import sys

import pytest

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"

# Every stage `analyze()` runs, and the label it draws under. Named
# here rather than scraped, so a phase that loses its ticker fails
# instead of quietly shrinking the list.
PHASES = ("floors", "attribution", "utilisation", "diagnostics",
          "structural", "confidence")


def _analyze(env_extra, run=GOLDEN, argv=None):
    env = dict(os.environ)
    env.pop("BGA_NO_PROGRESS", None)
    env.pop("BGA_FORCE_PROGRESS", None)
    env.update(env_extra)
    return subprocess.run(
        [sys.executable, "-c",
         "from bga.cli import main; raise SystemExit(main(%r))"
         % (argv or ["analyze", run, "--format", "json"],)],
        capture_output=True, env=env, cwd=os.getcwd())


class TestEveryNamedPhaseDraws:
    def test_the_pipeline_imports_progress_at_all(self):
        """The reproduction, kept: nothing in the analyze pipeline had
        any instrumentation."""
        source = open("bga/analyzer.py", encoding="utf-8").read()
        assert "import progress" in source, (
            "the pipeline is silent again")

    @pytest.mark.parametrize("phase", PHASES)
    def test_it_draws(self, phase):
        result = _analyze({"BGA_FORCE_PROGRESS": "1"})
        assert result.returncode == 0, result.stderr
        assert f"analyzing: {phase}".encode() in result.stderr, (
            f"{phase} ran without saying so:\n{result.stderr.decode()[:400]}")

    def test_the_attribution_ticker_counts_elements(self):
        """`UX-42` documents attribution as quadratic per gap, which is
        where the minutes actually go - so it is the one phase that
        gets a denominator rather than a spinner."""
        result = _analyze({"BGA_FORCE_PROGRESS": "1"})
        assert b"analyzing: attribution: 4/4" in result.stderr, result.stderr


class TestThePipeStaysExactlyAsItWas:
    """`UX-183`'s contract, re-pointed at the new call sites."""

    def test_stdout_is_byte_identical(self):
        on = _analyze({"BGA_FORCE_PROGRESS": "1"})
        off = _analyze({"BGA_NO_PROGRESS": "1"})
        assert on.stdout == off.stdout
        assert b"\r" not in on.stdout

    def test_a_piped_run_draws_nothing_at_all(self):
        """The default. Not "less"; nothing - these tickers are new
        stderr traffic on the path CI and every script take."""
        piped = _analyze({})
        assert piped.stderr == b"", piped.stderr[:200]

    def test_the_off_switch_still_wins(self):
        assert _analyze({"BGA_FORCE_PROGRESS": "1",
                         "BGA_NO_PROGRESS": "1"}).stderr == b""

    def test_forcing_it_on_really_does_draw(self):
        """The precondition `UX-197` had to add once already: without
        this, every comparison above is between two silent runs."""
        on = _analyze({"BGA_FORCE_PROGRESS": "1"})
        assert on.stderr, "nothing drew, so the guards above prove nothing"
        assert b"\r" in on.stderr, "a ticker redraws in place"


class TestASectionDrawsOnlyItsOwnPhases:
    """`UX-47` skips stages a section does not consume; the tickers are
    inside those branches, so a skipped stage says nothing rather than
    announcing work it did not do."""

    def test_graph_draws_structural_and_not_attribution(self):
        result = _analyze({"BGA_FORCE_PROGRESS": "1"},
                          argv=["graph", GOLDEN, "--format", "json"])
        assert result.returncode == 0, result.stderr
        assert b"analyzing: structural" in result.stderr
        assert b"analyzing: attribution" not in result.stderr, (
            "announced a phase this section skips")


class TestTheEverythingExtra:
    def _extras(self):
        try:
            import tomllib
        except ImportError:                      # pragma: no cover - <3.11
            import ast
            import re

            text = open("pyproject.toml", encoding="utf-8").read()
            out = {}
            for name in ("dev", "bst", "completion", "all"):
                match = re.search(rf'^{name} = (\[[^\]]*\])', text, re.M)
                if match:
                    out[name] = ast.literal_eval(match.group(1))
            return out
        return tomllib.load(open("pyproject.toml", "rb"))[
            "project"]["optional-dependencies"]

    def test_it_exists(self):
        assert "all" in self._extras()

    def test_it_covers_the_user_facing_extras(self):
        extras = self._extras()
        wanted = set(extras["bst"]) | set(extras["completion"])
        assert wanted <= set(extras["all"]), sorted(wanted - set(extras["all"]))

    def test_the_contributor_set_stays_out_of_it(self):
        """`dev` is not part of "everything" for a user: the runtime
        emits schemas and never validates against them, so `jsonschema`
        is a contributor's concern."""
        extras = self._extras()
        assert "jsonschema>=4.0" not in extras["all"]
        assert not set(extras["dev"]) <= set(extras["all"])

    def test_ci_installs_and_checks_it(self):
        import yaml

        workflow = yaml.safe_load(open(".github/workflows/ci.yml",
                                       encoding="utf-8"))
        steps = "\n".join(str(s.get("run", ""))
                          for s in workflow["jobs"]["packaging"]["steps"])
        assert "[all]" in steps, "nothing installs the form the README documents"
        assert "import argcomplete, buildstream" in steps

    def test_the_readme_names_it(self):
        assert "bga[all]" in open("README.md", encoding="utf-8").read()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
