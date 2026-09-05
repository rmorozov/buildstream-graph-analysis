"""UX-322: the architecture's command table, held against the parser.

`UX-245` found this table two commands behind, at review 1. `UX-322`
found it two commands behind again, at review 4, and the two missing
were `bga view` — the entry point for the whole viewer axis — and `bga
timeline`. Three reviews apart, the same table, the same defect. A list
maintained by hand against a parser that knows the answer will drift a
third time, so this is the guard that turns the next drift into a red
test.

**What the rule cannot be.** "Every command has a row" is wrong: `bga`
has 12 native subcommands and 19 `tools/` aliases, and eleven of those
aliases are format converters and internal utilities (`log-to-chrome`,
`gen-synthetic`, `run-context`, `release-notes` …). Giving each a row
would bury the eight commands a reader is actually looking for.

So the rule is the one the table already follows, written down:

* every **native subcommand** has its own row — no judgement involved,
  the parser is the list;
* every **promoted alias** in `PROMOTED` below has its own row — the
  aliases that answer a question rather than convert a format, which is
  a judgement, so it is made once here and not re-made per reader;
* every **row** names a command that exists — the direction `UX-245`
  did not check and that goes wrong when a command is renamed.

Promotion is the only judgement, and it is deliberately hard to fudge:
a new alias defaults to *not* promoted and no clause fails, which is
right for a converter and wrong for the next `bga view`. What catches
that one is a review — but a review that has to argue about one name,
not re-derive the whole table.
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import cli
from bga.tools_dispatch import TOOL_ALIASES

ARCHITECTURE = REPO / "docs/design/architecture.md"

# The aliases that answer a question, as against the ones that convert a
# format or exist for this repository's own plumbing. Each is a command
# a reader would go looking for in the table.
PROMOTED = frozenset((
    "capture",      # Plane 2 - trace processes inside sandboxes
    "cache-logs",   # Plane 3 - BuildStream's own element logs
    "snapshot",     # the local loop as one command
    "doctor",       # can this machine capture at all
    "baseline",     # assemble a baseline set and band-compare
    "wrap",         # the wrapped-log capture the whole pipeline starts at
    "view",         # UX-322: the report as a page
    "timeline",     # UX-322: both planes on one clock
))

_ROW = re.compile(r"^\| `bga ([a-z-]+)", re.M)


def _native():
    parser = cli.create_parser()
    for action in parser._actions:
        if getattr(action, "choices", None):
            return frozenset(action.choices)
    raise AssertionError("no subparser action found on the CLI parser")


def _rows():
    return frozenset(_ROW.findall(ARCHITECTURE.read_text(encoding="utf-8")))


class TestEveryCommandAReaderLooksForHasARow:

    def test_every_native_subcommand_has_a_row(self):
        missing = sorted(_native() - _rows())
        assert not missing, (
            f"{len(missing)} subcommand(s) the parser has and the "
            f"architecture's command table does not: {missing}")

    def test_every_promoted_alias_has_a_row(self):
        missing = sorted(PROMOTED - _rows())
        assert not missing, (
            f"promoted alias(es) with no row: {missing}. This is the "
            "UX-245/UX-322 defect: a command that answers a question, "
            "reachable only through the catch-all row.")

    def test_the_two_ux322_found_missing_are_named(self):
        """The regression this file exists for, by name rather than count."""
        for command in ("view", "timeline"):
            assert command in _rows(), (
                f"`bga {command}` has lost its row again. It was missing at "
                "review 4 and is the entry point readers look for first.")


class TestEveryRowNamesSomethingReal:

    def test_no_row_names_a_command_that_does_not_exist(self):
        real = _native() | frozenset(TOOL_ALIASES)
        phantom = sorted(_rows() - real)
        assert not phantom, (
            f"the table names {phantom}, which `bga` does not have - the "
            "direction UX-245 never checked, and the one a rename breaks")

    def test_the_table_was_actually_found(self):
        """A scan that matched nothing would pass every clause above."""
        rows = _rows()
        assert len(rows) >= 18, (
            f"only {len(rows)} rows matched; the table had 21 when UX-322 "
            "wrote this and a near-empty match means the row shape moved")


class TestThePromotionListIsHonest:

    def test_every_promoted_name_is_a_real_alias(self):
        unknown = sorted(PROMOTED - frozenset(TOOL_ALIASES))
        assert not unknown, (
            f"PROMOTED names {unknown}, which is not in TOOL_ALIASES - "
            "either the alias was renamed or the list has rotted")

    def test_promotion_is_a_minority_of_the_aliases(self):
        """If most aliases end up promoted, the distinction has stopped
        meaning anything and the table is a command dump again."""
        assert len(PROMOTED) < len(TOOL_ALIASES) / 2, (
            f"{len(PROMOTED)} of {len(TOOL_ALIASES)} aliases are promoted; "
            "the table is supposed to carry the ones a reader looks for, "
            "not all of them")
