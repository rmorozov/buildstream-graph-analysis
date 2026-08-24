"""UX-245: the chapter titled "Real current CLI surface" is not allowed
to be behind the CLI.

Found by review 1 (`UX-241`). `UX-233` pinned the architecture's
*contract* inventory and guarded it; the chapter a reader actually
starts from went on drifting because nothing measured it. Measured when
this was filed:

```text
subcommands in `bga --help`, absent from "## Real current CLI surface":
  blast    shipped round 19 (UX-172)
  whatif   shipped round 28 (UX-230)
```

`blast` is the sharper half: ten rounds shipped, on the front door and
in `cli.md`, and absent from the chapter whose title claims to be
current.

So the same check `test_the_front_door_is_current.py` puts on the two
front-door documents is put on the chapter: `bga --help` is the
inventory, the table is the claim, and both directions are checked. The
reverse direction is not decoration - a row for a command that has been
removed sends a reader to type something that does not exist, which is
the failure `UX-122` measured on ref globs.
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
ARCHITECTURE = REPO / "docs/design/architecture.md"
CHAPTER = "## Real current CLI surface"


def _first_column():
    """The table's first column only - the cells that *name* a command.

    Not the whole chapter, and not the whole row. Every row's second
    cell is prose about what the command reports, and prose about
    `bga blast` mentions `bga blast`; a guard that reads it would be
    satisfied by one command being *discussed* rather than listed,
    which is the distinction the table exists to make.
    """
    text = ARCHITECTURE.read_text(encoding="utf-8")
    assert CHAPTER in text, f"architecture.md has no {CHAPTER!r} chapter"
    chapter = text.split(CHAPTER, 1)[1].split("\n## ", 1)[0]
    cells = []
    for line in chapter.splitlines():
        if not line.startswith("|"):
            continue
        cell = line.split("|")[1].strip()
        if cell and not set(cell) <= set("- :"):
            cells.append(cell)
    assert cells, "the CLI-surface chapter has no table"
    return cells


def _named_in_the_table():
    """Every command name the first column lists.

    Two shapes occur: `` `bga blast TARGET` `` for a row of its own, and
    the aliases row's `` `bga wrap` / `extract` / `rebuild-set` ``,
    where the continuation drops the `bga`.
    """
    names = set()
    for cell in _first_column():
        names |= set(re.findall(r"`bga ([a-z][a-z-]+)", cell))
        names |= set(re.findall(r"/ *`([a-z][a-z-]+)`", cell))
    return names


def _subcommands():
    from bga import cli

    names = set()
    for action in cli.create_parser()._subparsers._group_actions:
        if getattr(action, "choices", None):
            names |= set(action.choices)
    return names


def _aliases():
    from bga import tools_dispatch

    return set(tools_dispatch.TOOL_ALIASES)


class TestTheTableNamesTheCLI:
    def test_every_subcommand_is_in_the_table(self):
        """The direction that was wrong: `blast` and `whatif` shipped,
        and the chapter titled "Real current CLI surface" did not have
        them."""
        missing = sorted(_subcommands() - _named_in_the_table())
        assert missing == [], (
            f"subcommand(s) `bga --help` lists and the architecture's "
            f"CLI-surface table does not: {missing}. "
            f"docs/design/architecture.md, {CHAPTER!r}.")

    def test_the_table_names_nothing_that_does_not_exist(self):
        """A row for a retired command is worse than a missing row: it
        is an instruction to type something that fails."""
        unreal = sorted(_named_in_the_table() - _subcommands() - _aliases())
        assert unreal == [], (
            f"the architecture's CLI-surface table names command(s) "
            f"neither `bga --help` nor `tools_dispatch` has: {unreal}")

    def test_the_table_is_not_one_row(self):
        """The two checks above both pass on an empty table. This is
        the floor under them."""
        assert len(_first_column()) >= len(_subcommands()), (
            f"the CLI-surface table has {len(_first_column())} rows for "
            f"{len(_subcommands())} subcommands, before aliases")


class TestTheEntryPointsAreNamed:
    """A mechanism the document describes and never says how to reach
    reads as internal - which is what `--explain` did for four rounds."""

    def test_explain_is_named(self):
        text = ARCHITECTURE.read_text(encoding="utf-8")
        assert "--explain" in text, (
            "architecture.md describes the provenance chain and names no "
            "way to print it (`bga analyze --explain`, UX-229)")

    def test_the_flag_is_named_beside_the_provenance_it_prints(self):
        """Named anywhere would pass the check above; the point is that
        a reader meeting provenance is told how to see it."""
        text = ARCHITECTURE.read_text(encoding="utf-8")
        where = text.index("--explain")
        window = text[max(0, where - 600):where + 600]
        assert "provenance" in window, (
            "`--explain` is named in architecture.md but not near any "
            "description of the provenance it prints")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
