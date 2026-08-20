"""UX-158: `--help` is where users look first, and it was a design lecture.

The docs corpus was cut 3,128 -> 2,203 lines for concision (UX-135..139)
and the help surface was never audited. Measured before this item, in
lines of rendered `--help`:

    compare 143   cache-logs 88   capture-run 82   extract 77
    capture 66    bga (top) 66    analyze 60      baseline 59
    snapshot 53   sweep 47        correlate 43

`bga capture --help` opened with UX-11's five brainstormed options, an
external contribution's proxy design, a risk-reduction spike and a Deep
Experiment - the module docstrings were fed to argparse as
`description`, so the backlog's design history *was* the help text.

This guard exists so the next design saga lands in a file rather than in
argparse.
"""
import io
import contextlib

import pytest

# A subcommand's help is usage + a few lines of description + one line
# per flag. 45 leaves room for the widest of those (`capture run`, 14
# flags) without leaving room for a paragraph per flag.
CAP = 45

# The top level is a *list*: one line per command, and there are 22 of
# them. Its length is the command count, not prose, so it gets its own
# bound - the thing to guard here is that no entry grows to two lines.
TOP_LEVEL_CAP = 50

SUBCOMMANDS = [
    "analyze", "graph", "floors", "replay", "sweep", "utilisation",
    "diagnostics", "correlate", "cache-trend", "compare",
    "extract", "capture", "snapshot", "cache-logs", "baseline", "doctor",
]


def _help(argv):
    from bga.cli import main
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out):
        with pytest.raises(SystemExit):
            main(argv)
    return out.getvalue()


@pytest.mark.parametrize("command", SUBCOMMANDS)
def test_each_subcommand_help_fits_a_screen(command):
    rendered = _help([command, "--help"]).splitlines()
    assert len(rendered) <= CAP, (
        f"`bga {command} --help` is {len(rendered)} lines (cap {CAP}). "
        f"Design history belongs in docs/backlog, not in argparse."
    )


def test_the_nested_capture_run_help_fits_too():
    """The worst offender after `compare`, and a subparser of a subparser -
    easy to miss when only top-level commands are checked."""
    rendered = _help(["capture", "run", "--help"]).splitlines()
    assert len(rendered) <= CAP, f"{len(rendered)} lines"


def test_the_top_level_lists_commands_rather_than_explaining_them():
    rendered = _help(["--help"]).splitlines()
    assert len(rendered) <= TOP_LEVEL_CAP, f"{len(rendered)} lines"


def test_flags_are_visible_on_the_first_screen():
    """The acceptance's real requirement: a user asking "what do I type"
    should not scroll to find out."""
    for command in ("capture", "compare", "extract"):
        rendered = _help([command, "--help"]).splitlines()
        first_screen = rendered[:24]
        assert any(line.lstrip().startswith(("-", "{", "positional", "options"))
                   for line in first_screen), (
            f"`bga {command} --help` shows no flags in its first 24 lines")


def test_module_docstrings_are_no_longer_the_help_text():
    """The specific regression: `description=__doc__` on a module whose
    docstring is a design record. The docstrings themselves may stay any
    length - they just stop being what argparse prints."""
    import tools.bst_native_build_tracer as tracer
    assert tracer.HELP != tracer.__doc__
    assert len(tracer.HELP.splitlines()) <= 10
    # the history is still there for a reader of the source
    assert "UX-11" in tracer.__doc__


def test_snapshots_two_command_loop_survived_the_cut():
    """UX-158 is out of scope for epilogue examples of the short kind, and
    snapshot's is the one that teaches the whole local loop."""
    rendered = _help(["snapshot", "--help"])
    assert "bga snapshot" in rendered
