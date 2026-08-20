"""Compact `--help` layout (UX-158).

argparse puts a flag's help on its own second line whenever the flag is
longer than 24 characters, and a third of this CLI's flags are (
`--fail-on-inefficient-additions` is 31). That doubled those entries for
no information gained - on `bga compare`, 24 flags became 48 lines.

Two classes because the two families of parser want different things
from the *description*: `bga`'s own subcommands pass a single sentence
that should wrap to the terminal, while the tool parsers pass a short
pre-formatted block whose line breaks are deliberate.
"""
import argparse

# Wide enough for the longest flag in this CLI to share its line, narrow
# enough to leave a readable help column at 80 columns.
_HELP_POSITION = 38
_WIDTH = 96


class CompactHelp(argparse.HelpFormatter):
    """Wrapped description, compact flag column."""

    def __init__(self, prog):
        super().__init__(prog, max_help_position=_HELP_POSITION, width=_WIDTH)


class CompactRawHelp(argparse.RawDescriptionHelpFormatter):
    """Description kept verbatim, compact flag column."""

    def __init__(self, prog):
        super().__init__(prog, max_help_position=_HELP_POSITION, width=_WIDTH)
