"""UX-233: the architecture document meets the viewer axis.

The user's observation: *we frequently forget to update architecture and
specification documentation, which later increases the cost of big
refactoring.* Measured when this was filed: `design/architecture.md`
described three analysis planes and stopped at round 20 - before the
whole viewer axis and before the contract wave that followed it - and
the published-payload inventory, which is the tool's actual external
surface, existed only as the sum of `--schema` outputs.

The guard below is the part that survives good intentions. A new
published schema without a line in the spec and a line in the
architecture inventory reddens it, which is the only mechanism this
repository has ever found that keeps two hand-maintained copies of one
fact together (`UX-131`, and every round since).

holds: rules.md#architecture-or-spec-made-wrong-same-commit
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
ARCHITECTURE = REPO / "docs/design/architecture.md"
SPEC = REPO / "docs/spec/specification.md"


def _published_schemas():
    """Every schema id the code stamps a document with.

    This used to be `schemas.names()` unioned with one hard-coded id,
    and `UX-248` measured what that costs: `sources/v1` - written to
    `sources.json` in every run directory and read back - was in no
    registry and therefore in no document. A union with a literal only
    ever covers the contracts someone remembered. `contracts.ids()`
    derives the set from the package.
    """
    from bga import contracts

    return contracts.ids()


GUIDES = REPO / "docs/guides"


def test_every_printable_contract_has_a_home_in_the_guides():
    """`UX-295`: a *guide* is where the consumer of a payload looks.

    Review 3 counted homes and found `whatif/v1` named four times
    across the spec, the architecture and a direction - and **zero**
    times in `docs/guides/`. The command that produces it was
    documented (`UX-246`); the document it produces was not, so a
    consumer holding `{"schema": "whatif/v1", ...}` and grepping the
    guides found how to make one and nothing about reading it.

    The clauses above already asked whether every contract has a home.
    Their notion of home is the spec and the architecture - where a
    *maintainer* looks - which is why this gap sat under a green
    guard. This one asks the reader's question instead.

    **Printable only.** `bga.contracts.unprintable()` names the shapes
    a run directory carries rather than a subcommand emits - `host/v1`,
    `sources/v1`, `plane2/*`. No `--format json` hands one to anybody,
    so requiring a CLI guide entry for them would be asking the wrong
    document to explain them; the architecture is their home and the
    clauses above hold it.
    """
    from bga import contracts

    printable = set(contracts.ids()) - set(contracts.unprintable())
    assert printable, "no contract is printable; this guard checks nothing"

    text = "\n".join(path.read_text(encoding="utf-8")
                     for path in sorted(GUIDES.rglob("*.md")))
    missing = sorted(name for name in printable if name not in text)
    assert missing == [], (
        f"published contract(s) named in no guide: {missing}. A consumer "
        f"holding one greps docs/guides/ and finds the command that made "
        f"it, not the document they are reading")


def test_the_unprintable_shapes_are_not_required_to_be_in_a_guide():
    """The exemption is a decision, so it is asserted rather than
    assumed - and it fails if `unprintable()` ever empties, which would
    silently widen the clause above into something nobody chose."""
    from bga import contracts

    unprintable = set(contracts.unprintable())
    assert unprintable, "unprintable() is empty; the exemption above is moot"
    assert unprintable <= set(contracts.ids())
    assert "whatif/v1" not in unprintable, (
        "whatif/v1 is printable - `bga whatif --format json` hands it to a "
        "consumer - and exempting it would undo UX-295")


def test_every_published_schema_is_named_in_the_spec():
    """In **Part 32.5**, not merely somewhere in the file.

    The first version of this asked whether the id appeared anywhere in
    the spec, and deleting a row from 32.5's table left it green -
    every id is also mentioned in Part 32's opening block. A guard that
    a deletion walks past is not guarding the table it is about.
    """
    text = SPEC.read_text(encoding="utf-8")
    section = text.split("## 32.5 The published output schemas", 1)
    assert len(section) == 2, "the spec has no Part 32.5"
    body = section[1].split("\n## ", 1)[0]
    missing = [name for name in _published_schemas() if name not in body]
    assert missing == [], (
        f"published schema(s) Part 32.5 does not list: {missing}")


def test_every_published_schema_is_in_the_architecture_inventory():
    """The inventory is the tool's external surface in one place. A
    payload that reaches a consumer and appears in no document is the
    increased-refactoring-cost failure this item is about."""
    text = ARCHITECTURE.read_text(encoding="utf-8")
    inventory = text.split("## The published contracts", 1)
    assert len(inventory) == 2, (
        "architecture.md has no `## The published contracts` chapter - "
        "the inventory this guard exists to keep current")
    body = inventory[1].split("\n## ", 1)[0]
    missing = [name for name in _published_schemas() if name not in body]
    assert missing == [], (
        f"published schema(s) missing from the architecture inventory: "
        f"{missing}")


def test_the_inventory_names_no_schema_the_code_does_not_emit():
    """The other direction. A schema removed from the code leaves its
    line behind, and the line then documents nothing."""
    text = ARCHITECTURE.read_text(encoding="utf-8")
    body = text.split("## The published contracts", 1)[-1].split("\n## ", 1)[0]
    listed = set(re.findall(r"`([a-z-]+/v\d+)`", body))
    stale = sorted(listed - set(_published_schemas()))
    assert stale == [], (
        f"the inventory names schema(s) nothing emits: {stale}")


def test_the_architecture_document_covers_the_viewer_axis():
    """Rounds 21-26 built a server, a schema-driven page and an export,
    and the architecture document did not mention any of it."""
    text = ARCHITECTURE.read_text(encoding="utf-8")
    assert "## The viewer axis" in text, (
        "architecture.md has no viewer chapter - it still stops at "
        "round 20")
    chapter = text.split("## The viewer axis", 1)[1].split("\n## ", 1)[0]
    for landmark in ("bga view", "--export", "no-arithmetic"):
        assert landmark in chapter, f"the viewer chapter does not mention {landmark}"


def test_the_fixing_guide_asks_whether_the_documents_moved():
    guide = (REPO / "docs/contributing/fixing-guide.md").read_text(
        encoding="utf-8")
    assert "architecture.md" in guide and "same commit" in guide.lower(), (
        "the Definition of Done does not ask whether this change makes "
        "architecture.md or the spec wrong")


def test_the_inventory_points_at_schema_rather_than_copying_it():
    """One line each, linking to `--schema` as the source of truth. A
    chapter that reproduced the schemas would be a second copy to
    maintain, which is the defect this item is about, not the fix."""
    text = ARCHITECTURE.read_text(encoding="utf-8")
    body = text.split("## The published contracts", 1)[-1].split("\n## ", 1)[0]
    assert "--schema" in body, (
        "the inventory does not point a reader at the printed schema")
    # The failure this is really about: somebody pastes the schemas in,
    # and the chapter becomes the second copy the item exists to avoid.
    pasted = [marker for marker in ('"properties"', "$schema", '"type":')
              if marker in body]
    assert pasted == [], (
        f"the inventory reproduces schema internals ({pasted}) instead of "
        f"pointing at `--schema` - that is a second copy to maintain, "
        f"which is the defect, not the fix")
    # The bound is derived rather than a constant: it moves with the
    # inventory, so adding a contract does not redden this and pasting
    # a schema in still does. `UX-384` found it as a literal 60 against
    # a 20-contract inventory, which meant the twenty-first row tripped
    # a guard about *copying* by growing the table it is meant to
    # describe.
    from bga import contracts

    budget = 3 * len(contracts.ids())
    assert len(body.splitlines()) < budget, (
        f"{len(body.splitlines())} lines against a budget of {budget} "
        f"({len(contracts.ids())} contracts) - the inventory is meant to "
        f"be one line per contract, not a copy of them")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
