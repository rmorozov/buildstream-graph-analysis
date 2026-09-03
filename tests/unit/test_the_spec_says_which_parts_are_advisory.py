"""UX-566: two "recommended" Parts describe a tool that was never built that way.

Re-measured in round 83, and the filed figures were low:

```text
Part 38 (specification.md:2349-2416)   11 upper-case chapters
`bga analyze` on the golden run         9, different names, one conditional
Part 39 (specification.md:2427-2489)   40 modules named  (filed as 32)
the tree                                13 of them exist (filed as 12); bga/structural/ unnamed
Part 37.1                               --cold, with no mention of --history-dir
```

Part 32.7.3 records which Parts are advisory and what supersedes each.
Part 39's two figures are counted here off the tree rather than written
into the note (§3.12: a counted figure in Part 32 is derived by a
guard), and the note's own subject is the table - the paragraphs around
it argue for it and are not read.
"""
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

SPEC = REPO / "docs/spec/specification.md"

WORDS = {11: "eleven", 12: "twelve", 13: "thirteen", 14: "fourteen",
         30: "thirty", 39: "thirty-nine", 40: "forty", 41: "forty-one"}


def _note_table():
    """32.7.3's table only. The prose above and below it makes the
    argument; a guard that read the whole subsection would match the
    sentence arguing for a row rather than the row."""
    text = SPEC.read_text(encoding="utf-8")
    start = text.index("| Part | what it recommends | what is current |")
    return text[start:text.index("\n\n", start)]


def _note_rows():
    rows = {}
    for line in _note_table().splitlines()[2:]:
        cells = [c.strip() for c in line.split("|")[1:-1]]
        rows[cells[0]] = cells[2]
    return rows


def _part(number):
    """One Part's body, by its own heading."""
    text = SPEC.read_text(encoding="utf-8")
    start = text.index(f"\n# Part {number} — ")
    return text[start:text.index("\n# Part ", start + 10)]


def _part_39_modules():
    """(named by Part 39, present in the tree) - counted off both."""
    body = _part(39).split("```text\n", 1)[1].split("\n```", 1)[0]
    package, named = None, []
    for line in body.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.endswith("/"):
            if stripped != "bga/":
                package = stripped[:-1]
        elif stripped.endswith(".py"):
            named.append((package, stripped))
    present = [one for one in named if (REPO / "bga" / one[0] / one[1]).exists()]
    return named, present


class TestTheNoteNamesEveryAdvisoryPart:
    """The filing's ask: the spec carries its own map of what to trust."""

    def test_the_four_parts_each_have_a_row(self):
        assert sorted(_note_rows()) == ["37.1", "38", "39", "40"], (
            "32.7.3 should name 37.1, 38, 39 and 40", sorted(_note_rows()))

    def test_every_row_names_a_current_document(self):
        for part, current in _note_rows().items():
            assert current and current != "—", (
                f"Part {part}'s row names no current document", current)

    def test_the_history_dir_flag_the_spec_never_names_is_named_here(self):
        """37.1's whole defect: `--cold` is useless without a flag the
        spec does not mention. Read against the parser, so the row
        cannot outlive the flag."""
        from bga.cli import create_parser

        # The flag is real: a row about an imaginary flag would be worse
        # than the omission it records. Read off the parser, not a doc.
        floors = create_parser()._subparsers._group_actions[0].choices["floors"]
        flags = {one for action in floors._actions
                 for one in action.option_strings}
        assert {"--cold", "--history-dir"} <= flags, (
            "bga floors no longer takes both flags, so 32.7.3's 37.1 row "
            "is about a CLI that changed", sorted(flags))
        assert "--history-dir" not in _part(37), (
            "Part 37 now names --history-dir itself, so 32.7.3's row is "
            "about a defect that no longer exists")
        assert "--history-dir" in _note_rows()["37.1"], (
            "32.7.3's 37.1 row should name the flag the Part omits")


class TestPart39sFiguresAreCountedOffTheTree:
    """§3.12's second half: a counted figure in Part 32 is derived,
    never restated. Both of these were wrong in the filing."""

    def test_the_named_and_present_counts_are_the_ones_the_row_states(self):
        named, present = _part_39_modules()
        row = _note_rows()["39"]
        assert f"names {WORDS[len(named)]} modules" in row, (
            f"32.7.3's Part 39 row should say 'names {WORDS[len(named)]} "
            f"modules'; Part 39 names {len(named)}")
        assert f"{WORDS[len(present)]} exist" in row, (
            f"the row should say '{WORDS[len(present)]} exist'; "
            f"{len(present)} of the named modules are in the tree",
            sorted(f"{p}/{m}" for p, m in present))

    def test_the_package_the_part_never_names_is_the_one_the_row_names(self):
        named, _ = _part_39_modules()
        packages = {d.name for d in (REPO / "bga").iterdir()
                    if d.is_dir() and (d / "__init__.py").exists()}
        unnamed = sorted(packages - {p for p, _ in named})
        assert unnamed == ["structural"], (
            "32.7.3's Part 39 row calls out `bga/structural/` as the one "
            "package Part 39 never mentions; the set has moved", unnamed)
        assert "`bga/structural/`" in _note_rows()["39"]


class TestPart38sChaptersAreNotIdentifiers:
    """The consequence the note draws, and the reason it matters: a
    reader greps `RECOMMENDATIONS` and finds one hit, in the spec."""

    def test_no_report_chapter_of_part_38_is_a_heading_the_tool_prints(self):
        from bga.report import text as report_text

        body = _part(38).split("```text\n", 1)[1].split("\n```", 1)[0]
        chapters = [line.strip() for line in body.splitlines()
                    if re.fullmatch(r"[A-Z][A-Z /-]*", line.strip() or "x")]
        assert len(chapters) >= 11, (
            "Part 38 stopped listing upper-case chapters, so this guard "
            "is reading the wrong block", chapters)
        source = pathlib.Path(report_text.__file__).read_text(encoding="utf-8")
        printed = [one for one in chapters if f'"{one}' in source]
        assert not printed, (
            "the renderer prints a Part 38 chapter name after all, so 38 is "
            "not purely advisory and 32.7.3's row is wrong", printed)


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
