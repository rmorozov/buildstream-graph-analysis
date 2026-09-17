"""UX-885: `make test` writes `.gate-covered` (the sha
`.claude/hooks/gate_covers_push.py` lets past a push), and round 125
pushed a blob a local gate passed and CI's pinned PyMarkdown reddened -
because `make lint` was not in the gate, so the lint failure skipped the
whole 3.9-3.12 matrix. `lint` is now a prerequisite of `test`, so a
lint-red tree never reaches the `.gate-covered` write. Asserted through
`make -n test` - the gate's own recipe, printed, no suite run."""
import pathlib
import subprocess

REPO = pathlib.Path(__file__).resolve().parents[2]


def _dry_run_test():
    """The commands `make test` would run, in order, without running
    them - `-n` prints the recipe for `.PHONY` `test` and its prereqs."""
    done = subprocess.run(["make", "-n", "test"], cwd=REPO,
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    return done.stdout.splitlines()


def _first(lines, needle):
    for i, line in enumerate(lines):
        if needle in line:
            return i
    return None


class TestThePushGateIncludesLint:
    def test_ruff_runs_before_the_suite(self):
        lines = _dry_run_test()
        ruff, suite = _first(lines, "ruff check"), _first(lines, "pytest")
        assert ruff is not None, lines
        assert suite is not None, lines
        assert ruff < suite, lines

    def test_the_markdown_lint_is_in_the_gate(self):
        # round 125's actual failure was a PyMarkdown finding, not ruff
        assert _first(_dry_run_test(), "pymarkdown") is not None, "no markdown lint in `make test`"

    def test_the_baseline_check_is_in_the_gate(self):
        assert _first(_dry_run_test(), "dev_baseline.py") is not None, "no baseline check in `make test`"

    def test_the_coverage_marker_is_written_after_lint_and_the_suite(self):
        lines = _dry_run_test()
        marker = _first(lines, ".gate-covered")
        ruff, suite = _first(lines, "ruff check"), _first(lines, "pytest")
        assert marker is not None, lines
        assert ruff is not None and ruff < marker, lines
        assert suite is not None and suite < marker, lines
