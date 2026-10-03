"""Every schema's `emitted_by` names a command `bga` registers (UX-1332)."""

import re

from bga import schemas
from bga.cli import create_parser
from bga.tools_dispatch import TOOL_ALIASES


def _commands() -> set[str]:
    parser = create_parser()
    sub = next(a for a in parser._actions if hasattr(a, "choices") and a.choices)
    return set(sub.choices) | set(TOOL_ALIASES)


def test_every_emitted_by_command_is_registered():
    commands = _commands()
    bad = {}
    for name in sorted(schemas._SCHEMAS):
        title = schemas._SCHEMAS[name]()["title"]
        m = re.match(r"bga ([a-z][a-z-]*)", title)
        if m and m.group(1) not in commands:
            bad[name] = title
    assert not bad


def test_the_renamed_command_is_the_one_named():
    title = schemas._SCHEMAS["junction-cost/v1"]()["title"]
    assert title.startswith("bga variant-cost ")


def test_the_check_reads_a_command_that_is_not_there():
    assert "no-such-command" not in _commands()
