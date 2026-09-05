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
import contextlib
import io

import pytest

# A subcommand's help is usage + a few lines of description + one line
# per flag. 45 leaves room for the widest of those (`capture run`, 14
# flags) without leaving room for a paragraph per flag.
CAP = 45

# The top level is a *list*: one line per command, and there are 23 of
# them. Its length is the command count, not prose, so it gets its own
# bound - the thing to guard here is that no entry grows to two lines.
# Raised by one per command added: 50 -> 51 for `bundle` (`UX-520`).
TOP_LEVEL_CAP = 51

# UX-179: `blast` was outside this list, so neither the line cap nor the
# terminator check ran over its help - a guard that does not cover the
# newest subcommand is the shape UX-176 exists to hunt. Every subcommand
# `bga` dispatches belongs here, and the test below checks that.
SUBCOMMANDS = [
    "analyze", "graph", "floors", "replay", "sweep", "utilisation",
    "diagnostics", "correlate", "cache-trend", "compare", "blast",
    "extract", "capture", "snapshot", "cache-logs", "baseline", "doctor",
    "whatif", "bundle",
]

# UX-192: the `UX-67` aliases dispatch through `tools/` rather than
# through a registered subparser, so `create_parser()` cannot see them
# and the coverage check below could not either. They are what `bga
# --help` lists, a user types them exactly like a subcommand, and five
# of them were over the cap when this list was written (`rebuild-set`
# 55, `cross-check` 55, `run-context` 67, `gen-synthetic` 67,
# `native-to-chrome` 75) - the design-history-in-argparse shape UX-158
# was filed about, still live in the half of the surface its guard
# could not reach.
TOOL_COMMANDS = [
    "wrap", "rebuild-set", "checkout-cost", "run-context",
    "graph-from-show", "log-to-chrome", "native-to-chrome",
    "chrome-to-trace", "cross-check", "gen-synthetic", "timeline", "view",
    "release-notes",
]


def test_every_command_bga_dispatches_is_covered_by_this_file():
    """The lists cannot silently fall behind the parser or the aliases.

    `blast` shipped and was not added here for a whole round; nothing
    said so, because a list of names cannot notice what is missing from
    it. The alias table had the same hole one layer down.
    """
    from bga.cli import create_parser
    from bga.tools_dispatch import TOOL_ALIASES

    registered = set()
    for action in create_parser()._actions:
        if getattr(action, "choices", None) and hasattr(action.choices, "keys"):
            registered |= set(action.choices.keys())
    covered = set(SUBCOMMANDS) | set(TOOL_COMMANDS)
    missing = sorted((registered | set(TOOL_ALIASES)) - covered - {"version"})
    assert not missing, (
        f"command(s) with no help guard: {', '.join(missing)}. "
        f"Add them to SUBCOMMANDS or TOOL_COMMANDS."
    )


def _help(argv):
    from bga.cli import main
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(out), pytest.raises(SystemExit):
        main(argv)
    return out.getvalue()


@pytest.mark.parametrize("command", SUBCOMMANDS + TOOL_COMMANDS)
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
    assert tracer.__doc__ != tracer.HELP
    assert len(tracer.HELP.splitlines()) <= 10
    # the history is still there for a reader of the source
    assert "UX-11" in tracer.__doc__


def test_snapshots_two_command_loop_survived_the_cut():
    """UX-158 is out of scope for epilogue examples of the short kind, and
    snapshot's is the one that teaches the whole local loop."""
    rendered = _help(["snapshot", "--help"])
    assert "bga snapshot" in rendered

# UX-165: the cut that UX-158's guard could not see.
#
# "flag help cut to its first sentence" was applied by deleting
# continuation *lines*, and nine strings lost their sentence's back half.
# The line-count guard cannot catch that - a truncated string is
# *shorter*, which is exactly what the cap rewards. So this checks shape
# instead of length.

def _help_blocks(rendered):
    """Each flag or positional and its help, as one joined string."""
    import re
    blocks, current = [], None
    for line in rendered.splitlines():
        if re.match(r"^  (-|\{|[a-z][\w-]*\s{2,})", line):
            if current:
                blocks.append(current)
            current = [line]
        elif current is not None and line.startswith("      "):
            current.append(line)
        else:
            if current:
                blocks.append(current)
            current = None
    if current:
        blocks.append(current)
    return [" ".join(l.strip() for l in b).rstrip() for b in blocks]


def _carries_prose(block: str) -> bool:
    """Whether this block has help text, rather than only an invocation.

    argparse renders `  -f {text,json}, --format {text,json}` with its
    help on the same or the next line; a block that is only the
    invocation has no sentence in it to end.
    """
    words = block.split()
    if len(words) < 4:
        return False
    # Everything after the last token that still looks like part of the
    # invocation - a flag, a metavar, a choice list.
    for index, word in enumerate(words):
        if not (word.startswith("-") or word.startswith("{")
                or word.rstrip(",").isupper() or word.endswith(",")):
            return len(words) - index >= 3
    return False


@pytest.mark.parametrize("command", SUBCOMMANDS + TOOL_COMMANDS)
def test_no_help_string_ends_mid_sentence(command):
    """A help block must not stop on a word the sentence was still using."""
    # Words a sentence cannot end on. Deliberately a small, concrete list:
    # this is a shape check for a known failure, not a grammar checker.
    dangling = {
        "the", "a", "an", "of", "for", "and", "or", "to", "in", "on", "at",
        "by", "with", "from", "same", "when", "which", "that", "this", "its",
        "than", "as", "is", "are", "was", "were", "be", "into", "per", "via",
        "but", "so", "if", "then", "while", "because", "each", "knee",
    }
    for block in _help_blocks(_help([command, "--help"])):
        if not block or block.startswith("-h,"):
            continue
        words = block.split()
        if not words:
            continue
        last = words[-1]
        # UX-176: the terminator requirement, applied to blocks that
        # actually carry prose. The pass-list used to include `,` `:`
        # `)` `]`, so a help string ending mid-clause was waved through
        # while the log claimed "every one must end in a terminator" -
        # a description of a check that was not running.
        #
        # A block with no help text at all is argparse's own rendering
        # of a metavar (`{text,json}`) or a bare positional, and is not
        # a sentence anybody wrote.
        if _carries_prose(block):
            assert last.rstrip(")]\"'").endswith((".", "!", "?")), (
                f"`bga {command} --help` ends a help block on {last!r}, "
                f"which is not the end of a sentence:\n    {block}"
            )
        assert last.lower() not in dangling, (
            f"`bga {command} --help` ends a help block on {last!r}:\n"
            f"  ...{block[-90:]}\n"
            f"The sentence's back half was cut. UX-158 did this to nine "
            f"strings and its line-count cap could not see it - a truncated "
            f"string is shorter, which is what the cap rewards."
        )


@pytest.mark.parametrize("command", SUBCOMMANDS + TOOL_COMMANDS)
def test_help_brackets_balance(command):
    """`(default: the same significance` - an unbalanced paren is the other
    shape a mid-sentence cut takes."""
    for block in _help_blocks(_help([command, "--help"])):
        assert block.count("(") == block.count(")"), (
            f"`bga {command} --help` has an unbalanced bracket:\n  ...{block[-90:]}")


def test_no_help_string_in_source_ends_on_a_dangling_space():
    """The signature of the cut, at the source rather than the render: a
    complete `help='...'` whose text ends with a space is a string whose
    continuation line was deleted."""
    import glob
    import re
    offenders = []
    for path in ["bga/cli.py"] + glob.glob("tools/*.py") + glob.glob("tools/native_trace/*.py"):
        lines = open(path, encoding="utf-8").read().split("\n")
        for n, line in enumerate(lines):
            match = re.match(r"\s*help=f?(['\"])(.*)\1,?\s*$", line.rstrip())
            if not match or not match.group(2).endswith(" "):
                continue
            following = lines[n + 1].strip() if n + 1 < len(lines) else ""
            if following.startswith(("'", '"', "f'", 'f\"')):
                continue  # a real continuation follows
            offenders.append(f"{path}:{n + 1}")
    assert not offenders, (
        "help strings ending in a space with no continuation - the "
        f"signature of a deleted line: {offenders}")
