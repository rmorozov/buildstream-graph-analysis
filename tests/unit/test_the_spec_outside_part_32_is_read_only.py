"""UX-585: the one hard rule the card named a guard for and had none.

`rules.md` sent "never touch the spec outside Part 32" to
`test_docs_links_and_commands.py`, which has no clause about Part 32 at
all - measured with `git grep -c "Part 32" tests/unit/test_docs_links_
and_commands.py`, which prints nothing. The rule was kept by attention
while the card said otherwise, which is worse than an empty cell.

Here it is a digest. Part 32's range is read off the spec's own `# `
headings, so a change *inside* it - the one Part a round may edit -
moves no byte outside and leaves this green. Anything else reddens,
including a one-character fix, which is the rule: `fixing-guide.md`
item 12 says a factual error outside Part 32 is **filed, not fixed**.

Updating `DIGEST` is the deliberate act. A round that means to edit
outside Part 32 says so in a task file and changes this line; a round
that did it by accident finds out here.

holds: rules.md#never-touch-docs-spec-specification-md-outside-part-32s-registry
"""
import hashlib
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
SPEC = REPO / "docs/spec/specification.md"

#: sha256 of every line outside Part 32, taken on `5b4c05f` (round 83).
#: 2,624 lines, 44,232 bytes.
DIGEST = "5f4c6d400c064928297264808c4132ded38f2a4a688f8ef2b3fcc805bf3bb42b"

#: What the guide's item 12 quotes. Derived below, asserted so the two
#: cannot drift - `UX-584` found it saying 1515-1788.
GUIDE = REPO / "docs/contributing/fixing-guide.md"


def _part_32():
    """`(first, last)` line numbers, from the spec's own `# ` headings."""
    lines = SPEC.read_text(encoding="utf-8").splitlines()
    starts = [n for n, line in enumerate(lines, 1) if line.startswith("# ")]
    first = next(n for n in starts if lines[n - 1].startswith("# Part 32"))
    return first, next(n for n in starts if n > first) - 1


def _outside():
    """The spec less Part 32, as bytes."""
    lines = SPEC.read_text(encoding="utf-8").splitlines(keepends=True)
    first, last = _part_32()
    return "".join(lines[:first - 1] + lines[last:]).encode("utf-8")


class TestTheSpecOutsidePart32DoesNotMove:
    def test_the_digest_is_unchanged(self):
        found = hashlib.sha256(_outside()).hexdigest()
        assert found == DIGEST, (
            f"the spec changed outside Part 32 (lines {_part_32()[0]}-"
            f"{_part_32()[1]} are the editable Part). A factual error out "
            f"there is filed, not fixed - fixing guide item 12. If the edit "
            f"is deliberate and a task file says so, set DIGEST to {found}")

    def test_the_range_is_the_part_and_not_a_number_someone_typed(self):
        """The boundary must follow the headings, or an inserted Part
        silently widens what a round may edit."""
        first, last = _part_32()
        lines = SPEC.read_text(encoding="utf-8").splitlines()
        assert lines[first - 1].startswith("# Part 32"), lines[first - 1]
        assert lines[last].startswith("# "), (
            f"line {last + 1} is not the next Part heading: {lines[last]!r}")
        assert last > first, (first, last)

    def test_the_guide_quotes_the_range_the_headings_give(self):
        first, last = _part_32()
        assert f"Part 32 spans {first}-{last}" in GUIDE.read_text(
            encoding="utf-8"), (
            f"the fixing guide's item 12 does not say Part 32 spans "
            f"{first}-{last}")

    def test_the_digest_covers_most_of_the_document(self):
        """A range bug that made `_outside()` empty would pass every
        clause above once `DIGEST` matched the empty hash."""
        whole = SPEC.read_bytes()
        assert len(_outside()) > len(whole) // 2, (
            f"{len(_outside())} B of {len(whole)} B is outside Part 32; the "
            f"range is wrong and the digest guards almost nothing")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
