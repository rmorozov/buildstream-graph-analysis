"""UX-236: the front door is not allowed to be a round behind.

`UX-233` pinned the *architecture* document and the spec's contract
table to what the code publishes, and left the two documents a reader
actually arrives at. Measured when this was filed, `README.md` and
`docs/README.md` between them named:

```text
bga whatif              absent   (UX-230)
bga analyze --explain   absent   (UX-229)
bga snapshot --aggregate/--blend  absent   (UX-234)
published schema ids named:  0 of 8
```

The gap is not length — the README is inside a measured line budget and
reads well. It is that a round's worth of the tool existed only in
`cli.md` and the backlog. So the same drift check `UX-233` put on the
architecture is put on the door: what `bga --help` lists and what
`schemas` publishes are the two inventories, and both are checked
against the two front-door documents.
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
FRONT_DOOR = ("README.md", "docs/README.md")
CLI_GUIDE = "docs/guides/cli.md"

# A `tools/` alias may stay off the front door, because the front door
# is what a reader *starts* with and these are not that. The exemption
# is not free: each one still has to be reachable from `cli.md`, which
# is what the second half of `test_a_deliberately_absent_alias_is_still
# _documented` checks - "deliberately absent" must not decay into
# "undocumented".
NOT_ON_THE_FRONT_DOOR = {
    "capture": "the raw Plane 2 tracer; `bga snapshot` is how a reader meets it",
    "checkout-cost": "one measurement, for a question the guides raise, not the door",
    "chrome-to-trace": "a converter between two trace formats",
    "cross-check": "a verification tool for this repository's own figures",
    "graph-from-show": "an ingestion path for projects that cannot run the wrapper",
    "log-to-chrome": "a converter between two trace formats",
    "native-to-chrome": "a converter between two trace formats",
    "rebuild-set": "`bga blast` is the same question with an answer a reader can act on",
    "run-context": "a piece of `bga extract`, for the case where the pieces are needed",
    "timeline": "one view of a capture; `bga view` is the one the door names",
}


def _front_door_text():
    return {name: (REPO / name).read_text(encoding="utf-8") for name in FRONT_DOOR}


def _mentions(text, name):
    """A command is *named* if it appears as a command, not as a word.

    `graph` occurs in `graph.json` and in a dozen sentences about the
    dependency graph; only `` `graph` `` and `bga graph` are the
    command. Matching the bare word would make every check pass for a
    reason that has nothing to do with the command being documented.
    """
    return bool(re.search(rf"`(?:bga )?{re.escape(name)}`|\bbga {re.escape(name)}\b", text))


def _subcommands():
    from bga import cli

    names = set()
    for action in cli.create_parser()._subparsers._group_actions:
        if getattr(action, "choices", None):
            names |= set(action.choices)
    return names


def _published_schemas():
    from bga import hostinfo, schemas

    return sorted(set(schemas.names()) | {hostinfo.SCHEMA})


class TestTheDoorNamesTheTool:
    def test_every_analyzer_subcommand_is_named_at_the_front_door(self):
        """These are the twelve things `bga <x>` does. A reader who
        never opens `cli.md` should still know they exist."""
        front = _front_door_text()
        missing = sorted(name for name in _subcommands()
                         if not any(_mentions(t, name) for t in front.values()))
        assert missing == [], (
            f"subcommand(s) named in no front-door document: {missing}. "
            f"README.md or docs/README.md.")

    def test_a_deliberately_absent_alias_is_still_documented(self):
        """The exemption above is a decision, not a hiding place."""
        guide = (REPO / CLI_GUIDE).read_text(encoding="utf-8")
        undocumented = sorted(name for name in NOT_ON_THE_FRONT_DOOR
                              if not _mentions(guide, name))
        assert undocumented == [], (
            f"alias(es) exempt from the front door and absent from "
            f"{CLI_GUIDE} too: {undocumented}")

    def test_the_exemption_list_names_only_real_aliases(self):
        """An exemption for a command that no longer exists silently
        widens the check it is an exception to."""
        from bga import tools_dispatch

        unreal = sorted(set(NOT_ON_THE_FRONT_DOOR) - set(tools_dispatch.TOOL_ALIASES))
        assert unreal == [], f"exemption(s) for no such alias: {unreal}"

    def test_every_alias_is_at_the_door_or_exempt(self):
        from bga import tools_dispatch

        front = _front_door_text()
        missing = sorted(
            name for name in tools_dispatch.TOOL_ALIASES
            if name not in NOT_ON_THE_FRONT_DOOR
            and not any(_mentions(t, name) for t in front.values()))
        assert missing == [], (
            f"alias(es) neither at the front door nor listed in "
            f"NOT_ON_THE_FRONT_DOOR with a reason: {missing}")


class TestTheDoorNamesWhatItEmits:
    """"What can this thing emit" is a question a reader has before
    they have a run, and `docs/README.md` is where they ask it."""

    def test_every_published_schema_is_reachable_from_the_docs_index(self):
        text = (REPO / "docs/README.md").read_text(encoding="utf-8")
        missing = [name for name in _published_schemas() if name not in text]
        assert missing == [], (
            f"published schema(s) docs/README.md does not name: {missing}")

    def test_the_index_names_no_schema_the_code_does_not_publish(self):
        """The other direction. A retired id left in the index sends a
        consumer to pin something that is gone."""
        text = (REPO / "docs/README.md").read_text(encoding="utf-8")
        published = set(_published_schemas())
        named = set(re.findall(r"`([a-z][a-z-]*/v\d+)`", text))
        stale = sorted(named - published)
        assert stale == [], (
            f"docs/README.md names schema(s) nothing publishes: {stale}")

    def test_the_index_says_how_to_read_a_contract(self):
        """The ids alone are a list; `--schema` is what makes them
        usable without opening `bga/schemas.py`."""
        text = (REPO / "docs/README.md").read_text(encoding="utf-8")
        assert "--schema" in text, (
            "docs/README.md lists the schema ids without saying how to "
            "print one")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
