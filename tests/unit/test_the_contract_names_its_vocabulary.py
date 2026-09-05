"""UX-306: a style guide nobody is routed to governs nothing.

Round 41 wrote the web report's visual contract
(`docs/design/styleguide.md`) and left it sitting beside the tree it
governs rather than wired into it. This is the wiring, and the one
piece of it worth a guard: **every `bga:` hint the schemas emit is
documented in exactly one place, and that place is §1a.**

The hints are the seam between the pipeline and the page — a schema
declares what a value *is* and the viewer draws it accordingly, with
no page edit (`UX-193`, `UX-201`). A hint whose meaning lives only in
`bga/schemas.py` is a seam nobody outside this repository can read,
and the repository has been bitten twice by a vocabulary kept in two
places: `UX-214` (verdict kinds re-listed in JavaScript) and `UX-273`
(a rendering threshold living in a task file). This holds the emitted
set and the documented set equal **in both directions** — an
undocumented hint reddens, and so does a documented hint nothing
emits, because a table naming a hint that does not exist is worse
than no table.

Emitted when this landed, eleven of them:

```text
bga:columns  bga:direction  bga:distribution  bga:markers
bga:presets  bga:quantity   bga:question      bga:rail
bga:role     bga:series     bga:severity
```
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCHEMAS = REPO / "bga" / "schemas.py"
VISUAL = REPO / "docs" / "design" / "styleguide.md"
DOCS = REPO / "docs" / "contributing" / "style-guide.md"
FIXING = REPO / "docs" / "contributing" / "fixing-guide.md"
INDEX = REPO / "docs" / "README.md"
FORMAT = REPO / "bga" / "viewer" / "format.js"


def _emitted():
    """Every `bga:` hint the schema module names."""
    return set(re.findall(r'"(bga:[\w-]+)"', SCHEMAS.read_text(encoding="utf-8")))


def _documented():
    """Every hint §1a's table has a row for."""
    text = VISUAL.read_text(encoding="utf-8")
    table = text.split("## 1a.", 1)[1].split("\n## ", 1)[0]
    return set(re.findall(r"^\|\s*`(bga:[\w-]+)`\s*\|", table, re.M))


def _declared_in_format():
    """Every `bga:` key `format.js` binds a constant to."""
    return set(re.findall(r'^(?:export )?const \w+ = "(bga:[\w-]+)";',
                          FORMAT.read_text(encoding="utf-8"), re.M))


def _format_opening():
    """`format.js`'s opening comment, unwrapped to one line."""
    head = FORMAT.read_text(encoding="utf-8").split("*/", 1)[0]
    return " ".join(re.sub(r"^\s*/?\*+ ?", "", line)
                    for line in head.splitlines())


class TestEveryHintIsDocumentedOnce:
    def test_the_table_exists_and_is_not_empty(self):
        assert _documented(), "§1a names no hints - the table is gone"

    def test_every_emitted_hint_has_a_row(self):
        missing = sorted(_emitted() - _documented())
        assert not missing, (
            f"emitted by `bga/schemas.py` and documented nowhere: {missing}. "
            f"A hint whose meaning lives only in the code is a seam nobody "
            f"outside this repository can read.")

    def test_every_documented_hint_is_emitted(self):
        stale = sorted(_documented() - _emitted())
        assert not stale, (
            f"documented in §1a and emitted by nothing: {stale}. A table "
            f"naming a hint that does not exist is worse than no table.")

    def test_each_row_says_what_it_declares_and_who_reads_it(self):
        """Three columns, all filled. A row with an empty cell is a
        hint listed rather than documented."""
        text = VISUAL.read_text(encoding="utf-8")
        table = text.split("## 1a.", 1)[1].split("\n## ", 1)[0]
        for line in table.splitlines():
            if not re.match(r"^\|\s*`bga:", line):
                continue
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            assert len(cells) == 3, line
            assert all(cells), f"an empty cell in: {line}"


class TestTheModuleSaysHowManyItDeclares:
    """UX-654: `format.js` opened with "the nine `bga:` hint keys" while
    declaring 17 of the 19 the schemas emit. Both figures the sentence
    now carries are derived here, so neither can age unnoticed."""

    def test_the_count_of_keys_the_module_declares(self):
        said = re.search(r"the (\d+) `bga:` hint keys this module declares",
                         _format_opening())
        assert said, (
            "format.js's opening paragraph no longer states how many "
            "`bga:` hint keys it declares, in the words this guard reads")
        assert int(said.group(1)) == len(_declared_in_format()), (
            f"format.js says it declares {said.group(1)} `bga:` hint keys "
            f"and declares {len(_declared_in_format())}: "
            f"{sorted(_declared_in_format())}")

    def test_the_size_of_the_vocabulary_it_is_part_of(self):
        said = re.search(r"\(of the (\d+) `bga/schemas\.py` emits\)",
                         _format_opening())
        assert said, (
            "format.js's opening paragraph no longer states the size of "
            "the emitted vocabulary its keys are drawn from")
        assert int(said.group(1)) == len(_emitted()), (
            f"format.js says the schemas emit {said.group(1)} hints and "
            f"they emit {len(_emitted())}")

    def test_the_keys_it_declares_are_drawn_from_that_vocabulary(self):
        """The sentence's `of the 19` is a subset claim, not only a
        smaller number."""
        invented = sorted(_declared_in_format() - _emitted())
        assert not invented, (
            f"declared in format.js and emitted by nothing: {invented}. "
            f"A renderer reading a key no schema writes draws nothing.")


class TestTheGuideIsRoutedTo:
    """The rest of the wiring, each asserted where a reader would
    arrive from."""

    def test_the_docs_index_rows_it(self):
        """The *link target*, not the words. A row whose link was
        repointed still reads correctly and goes nowhere - and a
        mutation that repointed exactly that passed a clause matching
        the display text."""
        text = INDEX.read_text(encoding="utf-8")
        assert "](design/styleguide.md)" in text, (
            "the docs index does not link the visual contract")

    def test_the_two_style_guides_name_each_other(self):
        assert "design/styleguide.md" in DOCS.read_text(encoding="utf-8"), (
            "the documentation style guide does not name its sibling")
        assert "contributing/style-guide.md" in VISUAL.read_text(
            encoding="utf-8"), (
            "the visual contract does not name its sibling")

    def test_the_fixing_guide_routes_a_page_change(self):
        text = FIXING.read_text(encoding="utf-8")
        assert "design/styleguide.md" in text
        assert "conformance checklist" in text.lower()


if __name__ == "__main__":  # pragma: no cover
    import pytest

    raise SystemExit(pytest.main([__file__, "-v"]))
