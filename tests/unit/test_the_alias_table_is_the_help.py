"""UX-552: `cli.md`'s alias table is `bga --help`'s alias block.

Architecture review 12, checklist 4, measured when this was filed:

```text
docs/guides/cli.md:47-65   17 rows
bga --help                 19 aliases
absent from the table      timeline, view
```

Both had a section of their own further down the same file, so the
reader who scrolled found them and the reader who read the table did
not. `architecture.md`'s CLI table was complete at 21 rows because
`test_the_command_table_is_the_cli.py` holds it against the parser;
this table was held by nothing, which is the whole of the difference.

The population here is the **rendered block**, not `TOOL_ALIASES`:
`format_tool_help()` is what `bga --help` prints, so a change to how
the block is rendered is caught rather than walked past by a guard
reading the dict behind it.

Order is deliberately not checked. The two agree on rows and on the
module each row claims; where a document puts a row is a reader
judgement, and a guard asserting it would fail on a reordering that
costs nobody anything.
"""
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga.tools_dispatch import format_tool_help

CLI = REPO / "docs/guides/cli.md"

#: A rendered alias line: two spaces, the name, the help text, and the
#: module in parentheses at the end of the line.
_HELP_LINE = re.compile(r"^ {2}([a-z][a-z-]+) {2,}.+ \((tools\.\w+)\)$", re.M)

#: A table row: `| `bga NAME` | `tools.MODULE` |`.
_TABLE_ROW = re.compile(r"^\| `bga ([a-z][a-z-]+)` \| `(tools\.\w+)` \|$",
                        re.M)


def _the_help():
    """`{alias: module}`, out of the block `bga --help` prints."""
    found = dict(_HELP_LINE.findall(format_tool_help()))
    assert found, "no alias line parsed out of the rendered help block"
    return found


def _the_table():
    """`{alias: module}`, out of the guide's alias table.

    The table is found by its header rather than by line number, so the
    guide can grow above it - it moved 18 lines while this item was
    being written.
    """
    text = CLI.read_text(encoding="utf-8")
    assert "| alias | wraps |" in text, "cli.md has no alias table header"
    block = text.split("| alias | wraps |", 1)[1].split("\n\n", 1)[0]
    found = dict(_TABLE_ROW.findall(block))
    assert found, "no row parsed out of the alias table"
    return found


class TestTheTableIsTheBlock:

    def test_every_alias_the_help_lists_has_a_row(self):
        """The direction the item was filed on: `timeline` and `view`
        were in the block and not in the table."""
        missing = sorted(set(_the_help()) - set(_the_table()))
        assert missing == [], (
            f"alias(es) `bga --help` lists and cli.md's table does not: "
            f"{missing}. The table is that block, and a reader who reads "
            f"it instead of scrolling is entitled to the whole of it")

    def test_no_row_names_an_alias_that_does_not_exist(self):
        """A row for a retired alias is worse than a missing one: it is
        an instruction to type something that fails."""
        phantom = sorted(set(_the_table()) - set(_the_help()))
        assert phantom == [], (
            f"cli.md's alias table names {phantom}, which `bga --help` "
            f"does not list")

    def test_each_row_wraps_what_the_help_says_it_wraps(self):
        """The second column is a claim too - it is what a script that
        wants the underlying program reads."""
        table, block = _the_table(), _the_help()
        wrong = sorted((alias, table[alias], block[alias])
                       for alias in set(table) & set(block)
                       if table[alias] != block[alias])
        assert wrong == [], (
            f"row(s) claiming a module the help does not: {wrong} "
            f"(alias, table, help)")

    def test_both_sides_were_actually_found(self):
        """Every clause above passes on two empty parses."""
        assert len(_the_help()) >= 19, (
            f"only {len(_the_help())} aliases parsed out of the help block; "
            f"there were 19 when this was written, so the line shape moved")
        assert len(_the_table()) == len(_the_help()), (
            f"{len(_the_table())} rows against {len(_the_help())} aliases")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
