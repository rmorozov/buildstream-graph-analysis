"""UX-446: three bounds on the hand-off, and the table said two.

`UX-430` added `TRACE_TRACK_BUDGET` - the bound in the unit Perfetto
actually spends - and a round later two documents still said the
hand-off had one:

```text
docs/guides/cli.md      "Two ceilings ... the only part either ceiling
                         singles out"
docs/design/styleguide.md §3g
                        "carries the only bound the Perfetto handoff has"

$ git grep -c TRACE_TRACK_BUDGET -- docs
(nothing)
```

A reader whose export refused for **16,832 tracks** met a table of byte
ceilings, found the trace comfortably under the one it named, and had
nowhere to go.

**The table is checked against the constants, not maintained beside
them.** That is the item's own condition: a fourth bound in a fourth
unit, left out of the document, has to redden something. It reddens
`test_every_budget_constant_is_declared_a_ceiling` before anybody has
to notice the prose - the population is the module's own `*_BUDGET*`
attributes, read from the imported module rather than from its text, so
a constant added with any spelling is in it.
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import bga_view as view                             # noqa: E402

CLI = REPO / "docs/guides/cli.md"
STYLEGUIDE = REPO / "docs/design/styleguide.md"

#: What makes a module constant a *bound* rather than a number. Read
#: off `dir(view)` rather than grepped, so a rename that keeps the
#: convention is still in the population and one that leaves it is a
#: change somebody has to argue for here.
BUDGET_NAME = re.compile(r"BUDGET")


def _declared():
    """`{name: (unit, remedy)}` from the module's own registry."""
    return {name: (unit, remedy) for name, unit, remedy in view.CEILINGS}


def _table_rows():
    """The ceilings table in `cli.md`, keyed by the constant it names.

    Found by the constant in its first column, so the table can be
    reordered or reworded and this still reads it - and a row for a
    bound that does not exist is still visible, which is the other
    direction.
    """
    text = CLI.read_text(encoding="utf-8")
    body = text.split("Three ceilings", 1)[1].split("\n\n", 3)[1]
    return {match.group(1): match.group(0)
            for match in re.finditer(r"^\| `(\w+)` \|.*$", body, re.M)}


def test_every_budget_constant_is_declared_a_ceiling():
    """The clause the item's acceptance test asks for.

    A fourth bound is a new `*_BUDGET*` in this module, and it fails
    here the moment it exists - before it can reach a release with no
    row in any document.
    """
    exported = {name for name in dir(view) if BUDGET_NAME.search(name)}
    assert exported, "no budget constant found at all - the scan is broken"
    undeclared = sorted(exported - set(_declared()))
    assert undeclared == [], (
        f"bound(s) this module exports that `CEILINGS` does not declare: "
        f"{undeclared}. Every bound on the hand-off has to be in that "
        f"tuple, because the reader-facing table is checked against it")


def test_every_declared_ceiling_has_a_row_a_reader_can_find():
    rows = _table_rows()
    missing = sorted(set(_declared()) - set(rows))
    assert missing == [], (
        f"ceiling(s) with no row in docs/guides/cli.md: {missing} - which "
        f"is the state UX-446 was filed on, where a refusal quotes a "
        f"number no document has")


def test_the_table_names_no_bound_that_does_not_exist():
    """The other direction, so a bound deleted in code leaves a row a
    reader would go looking for."""
    extra = sorted(set(_table_rows()) - set(_declared()))
    assert extra == [], (
        f"docs/guides/cli.md's ceilings table names {extra}, which is not "
        f"a declared ceiling any more")


def test_each_row_carries_the_remedy_its_registry_entry_names():
    """A table of three numbers and no actions is the table this item
    replaced. The tracks row is the one that matters: `--planes 1` is
    documented a section earlier and was connected to nothing."""
    rows = _table_rows()
    tracks = rows["TRACE_TRACK_BUDGET"]
    for flag in ("--planes 1", "--only-element"):
        assert flag in tracks, (
            f"the tracks row does not name `{flag}`, so a reader whose "
            f"export refused for tracks is told a number and no action: "
            f"{tracks}")
    assert "drawn" in tracks, (
        "the tracks row does not say the flags narrow what is *drawn* - "
        "which is the distinction from the two byte bounds above it")


def test_the_styleguide_no_longer_says_there_is_only_one():
    """§3g's opening, closed the way §4e's was. The section is a rule
    with a worked example, and the example's "only bound" is the thing
    the rule went on to fix."""
    text = STYLEGUIDE.read_text(encoding="utf-8")
    section = text.split("## 3g.", 1)[1].split("\n## ", 1)[0]
    assert "the only bound the Perfetto handoff has" not in section, (
        "styleguide §3g still opens on the claim UX-430 falsified")
    assert "UX-446" in section, (
        "§3g does not say where its rule was applied, so a reader of the "
        "rule cannot find the table it produced")


if __name__ == "__main__":  # pragma: no cover
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
