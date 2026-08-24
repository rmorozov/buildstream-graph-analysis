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
    assert len(body.splitlines()) < 60, (
        f"{len(body.splitlines())} lines - the inventory is meant to be one "
        f"line per contract, not a copy of them")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
