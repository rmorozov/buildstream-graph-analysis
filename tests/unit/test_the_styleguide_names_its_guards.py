"""UX-582: §7 said seven sections had no guard, and four of them did.

The ledger was three prose tables written in rounds 55, 58 and 69,
each closing "none with a guard yet". Measured when this was filed:

```text
sections in docs/design/styleguide.md                     33
tracked tests/unit/*.py                                  436
  of those, citing a section                              48
sections §7 called guardless      §1c §1d §3f §4d §5a §3g §4e
  of those, with a guard citing them    §1c §3f §3g §4e    4
§6b, prose        "viewer modules 21"; git ls-files says  22
§3, prose         "default 20"; no constant of that value
```

§7 is now one table and this reads it. The table is the subject; the
prose around it is the argument, and only rows matching `| §X | … |`
are parsed - a paragraph naming a section is not a row.

**This file is excluded from its own scan.** It quotes section ids to
report them, so scanning it would make every row cite its own reader.
"""
import functools
import pathlib
import re
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
STYLEGUIDE = REPO / "docs/design/styleguide.md"
FIXING_GUIDE = REPO / "docs/contributing/fixing-guide.md"
#: The third document that numbers sections, and the one whose name
#: is a letter away from the first. `UX-569` cites its §9 in an
#: exemption reason, and this scan called that section imaginary.
STYLE_GUIDE = REPO / "docs/contributing/style-guide.md"
STRUCTURED = REPO / "bga/viewer/structured.js"

#: A section id in either document: a digit and an optional letter.
#: `[0-9]+`, not `[0-9]`: at one digit a `§42` reads as `§4` and a
#: stray citation passes as a real one - measured, the mutation that
#: was supposed to redden this scan did not.
HEADING = re.compile(r"^#{2,3} ([0-9]+[a-g]?)\. ", re.M)
CITATION = re.compile(r"§([0-9]+[a-g]?)")
ROW = re.compile(r"^\| *§([0-9]+[a-g]?) *\| *(.*?) *\| *(.*?) *\|$", re.M)
GUARD = re.compile(r"`(test_[a-z0-9_]+\.py)`")

#: The word a row uses to say its id is shared with the fixing guide,
#: so the scan cannot tell whose §5 a sentence means.
NAMED = "named"

SELF = pathlib.Path(__file__).name


@functools.lru_cache(maxsize=1)
def _tracked():
    """Paths git has. `UX-577`: a glob walks the checkout, and the main
    checkout holds `.claude/worktrees/<agent>/` - a whole second tree."""
    out = subprocess.run(["git", "ls-files"], cwd=REPO, check=True,
                         capture_output=True, text=True).stdout
    return frozenset(out.splitlines())


def _unit_tests():
    """Tracked and still on disk - a file deleted but not yet committed
    is gone from the scan and named by the row check, not a traceback."""
    return sorted(one for one in _tracked()
                  if re.fullmatch(r"tests/unit/[^/]+\.py", one)
                  and not one.endswith("/" + SELF)
                  and (REPO / one).exists())


def _cited(paths):
    """`{section: {file names}}` over the paths given. Empty in, empty
    out - which is the vacuity `test_the_scan_reads_something` holds."""
    found = {}
    for rel in paths:
        text = (REPO / rel).read_text(encoding="utf-8", errors="replace")
        for section in set(CITATION.findall(text)):
            found.setdefault(section, set()).add(pathlib.Path(rel).name)
    return found


def _sections(path):
    return HEADING.findall(path.read_text(encoding="utf-8"))


def _table():
    """`{section: (guards, note)}` from §7's rows, in document order."""
    text = STYLEGUIDE.read_text(encoding="utf-8")
    body = text[text.index("\n## 7. Enforcement"):]
    return {section: (frozenset(GUARD.findall(guards)), note.strip())
            for section, guards, note in ROW.findall(body)}


def _ambiguous():
    """Ids more than one document numbers. A bare `§5` in a guard
    belongs to whichever document its sentence is about, and nothing in
    the text says which - so these rows are named rather than derived.
    Adding the contributing style guide leaves the set identical today
    (its §1-§7 are already the fixing guide's, and the page has no §8
    or §9), and keeps it right if the page ever grows one."""
    return frozenset(_sections(STYLEGUIDE)) & (
        frozenset(_sections(FIXING_GUIDE)) | frozenset(_sections(STYLE_GUIDE)))


class TestTheTableIsTheGuide:
    def test_every_section_has_a_row(self):
        sections, table = set(_sections(STYLEGUIDE)), _table()
        assert sections == set(table), (
            "§7's table and the guide's headings disagree; "
            f"sections with no row: {sorted(sections - set(table))}; "
            f"rows for no section: {sorted(set(table) - sections)}")

    def test_a_row_with_no_guard_gives_a_reason(self):
        bare = [section for section, (guards, note) in _table().items()
                if not guards and not note.strip("-—  ")]
        assert not bare, (
            f"these rows name no guard and give no reason: {sorted(bare)}")

    def test_every_named_guard_exists_and_cites_its_section(self):
        broken = []
        for section, (guards, _) in _table().items():
            for name in guards:
                rel = f"tests/unit/{name}"
                if not (REPO / rel).exists():
                    broken.append(f"§{section}: {name} is gone")
                    continue
                if rel not in _tracked() and name != SELF:
                    broken.append(f"§{section}: {name} is not a tracked file")
                    continue
                text = (REPO / rel).read_text(encoding="utf-8")
                if section not in CITATION.findall(text):
                    broken.append(f"§{section}: {name} does not cite it")
        assert not broken, "\n".join(broken)


class TestTheTableIsHeldToTheScan:
    def test_no_guard_cites_a_section_the_table_omits(self):
        cited, table, named = _cited(_unit_tests()), _table(), _ambiguous()
        wrong = []
        for section, files in sorted(cited.items()):
            if section in named or section not in table:
                continue
            listed = table[section][0]
            if files - listed:
                wrong.append(f"§{section} is cited by {sorted(files - listed)}, "
                             "and its row does not name them")
            if listed - files:
                wrong.append(f"§{section}'s row names {sorted(listed - files)}, "
                             "which no longer cite it")
        for section, (listed, _) in sorted(table.items()):
            if section not in named and listed and section not in cited:
                wrong.append(f"§{section}'s row names {sorted(listed)} and "
                             "nothing cites it")
        assert not wrong, "\n".join(wrong)

    def test_a_row_is_named_exactly_when_the_scan_cannot_attribute_it(self):
        named = _ambiguous()
        wrong = [f"§{section}" for section, (_, note) in _table().items()
                 if (NAMED in note.split(";")[0]) != (section in named)]
        assert not wrong, (
            f"these rows disagree with the ids the fixing guide also "
            f"numbers ({sorted(named)}): {sorted(wrong)}")

    def test_a_cited_section_exists_in_a_document_that_numbers_sections(self):
        """Three documents number sections, not two - `docs/design/
        styleguide.md`, and both guides under `docs/contributing/`."""
        known = (set(_sections(STYLEGUIDE)) | set(_sections(FIXING_GUIDE))
                 | set(_sections(STYLE_GUIDE)))
        stray = {section: sorted(files)
                 for section, files in _cited(_unit_tests()).items()
                 if section not in known}
        assert not stray, f"cited, and no such section: {stray}"

    def test_the_scan_reads_something(self):
        """A scan that finds no files passes every clause above."""
        assert _cited(()) == {}, "the scan invents citations from nothing"
        paths = _unit_tests()
        assert len(paths) > 300, f"the population is {len(paths)} files"
        cited = _cited(paths)
        assert len(cited) > 15, f"only {len(cited)} sections are cited"


class TestTheCountedFiguresDerive:
    def test_the_row_cap_names_its_constant(self):
        """§3 said "default 20" and no constant had that value."""
        text = STYLEGUIDE.read_text(encoding="utf-8")
        start = text.index("- **Row cap by default.**")
        bullet = text[start:text.index("\n- ", start)]
        names = [one for one in re.findall(r"`([A-Za-z_][A-Za-z_0-9]*)`", bullet)
                 if one.isidentifier()]
        assert names, "the row-cap rule names no constant"
        for name in names:
            found = subprocess.run(["git", "grep", "-q", name, "--",
                                    "bga/viewer"], cwd=REPO)
            assert found.returncode == 0, (
                f"the row-cap rule names {name}, and the viewer has no such "
                "identifier")
        # A section reference is not a number, and the grouped `1,202` is
        # the dated population. A loose integer is the "default 20" the
        # item removed - there was no constant with that value.
        loose = re.findall(r"(?<![\d,])\d{1,3}(?![\d,])",
                           re.sub(r"§[0-9][a-g]?", "", bullet))
        assert not loose, (
            f"the row-cap rule restates {loose} rather than naming a constant")

    def test_the_module_count_derives(self):
        """§6b said twenty-one viewer modules; git says otherwise."""
        text = STYLEGUIDE.read_text(encoding="utf-8")
        section = text[text.index("\n## 6b."):text.index("\n## 6c.")]
        modules = [one for one in _tracked()
                   if re.fullmatch(r"bga/viewer/[^/]+\.js", one)]
        factories = [one for one in modules
                     if 'el("table"' in (REPO / one).read_text(encoding="utf-8")]
        for count, what in ((len(modules), "viewer modules"),
                            (len(factories), "modules that construct a table")):
            row = re.search(rf"^(\d+) +{re.escape(what)}$", section, re.M)
            assert row, f"§6b states no count of {what}"
            assert int(row.group(1)) == count, (
                f"§6b says {row.group(1)} {what}; git ls-files says {count}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
