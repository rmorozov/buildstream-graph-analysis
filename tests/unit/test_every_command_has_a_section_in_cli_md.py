"""UX-1290: every command `bga --help` lists has a `##` of its own in `cli.md`.

Both halves of the help: the analysis subcommands the parser holds and
the aliases its epilog prints. A heading opens `` ## `bga NAME` ``; the
contracts and the page are their own documents, not chapters of this one.
"""

import argparse
import pathlib
import re

from bga.cli import create_parser
from bga.tools_dispatch import format_tool_help

REPO = pathlib.Path(__file__).resolve().parents[2]
CLI = REPO / "docs/guides/cli.md"
HEADING = re.compile(r"^## `bga ([a-z][a-z-]*)`", re.M)
ALIAS = re.compile(r"^ {2}([a-z][a-z-]+) {2,}.+ \(tools\.\w+\)$", re.M)


def _commands() -> set:
    parser = create_parser()
    actions = [a for a in parser._actions if isinstance(a, argparse._SubParsersAction)]
    assert len(actions) == 1, "the parser holds no one subcommand group"
    aliases = set(ALIAS.findall(format_tool_help()))
    assert aliases, "no alias parsed out of the help block"
    return set(actions[0].choices) | aliases


def _headed() -> set:
    return set(HEADING.findall(CLI.read_text(encoding="utf-8")))


def test_every_command_in_the_help_has_a_section():
    missing = sorted(_commands() - _headed())
    assert missing == [], f"command(s) `bga --help` lists with no `## \\`bga NAME\\`` in cli.md: {missing}"


def test_every_command_section_names_a_command():
    phantom = sorted(_headed() - _commands())
    assert phantom == [], f"cli.md heads a section for {phantom}, which `bga --help` does not list"


def test_installation_comes_first():
    first = re.search(r"^## (.+)$", CLI.read_text(encoding="utf-8"), re.M)
    assert first and first.group(1) == "Installation", f"cli.md opens with {first and first.group(1)!r}"


def test_the_contracts_and_the_page_left_the_reference():
    text = CLI.read_text(encoding="utf-8")
    for moved, home in (
        ("## The JSON outputs, and their schemas", "json-contracts.md"),
        ("## `bga view` — the report in a browser", "viewer.md"),
    ):
        assert moved not in text, f"cli.md still carries `{moved}`"
        assert moved in (CLI.parent / home).read_text(encoding="utf-8"), f"{home} does not carry `{moved}`"
