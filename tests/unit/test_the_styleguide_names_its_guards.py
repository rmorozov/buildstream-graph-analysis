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
import collections
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
#: `UX-667`: `[a-g]` stopped at the seventh sub-section any topic had
#: reached; `§3h` is the eighth, so the range widens to the whole
#: alphabet rather than to eight letters that would need widening again.
HEADING = re.compile(r"^#{2,3} ([0-9]+[a-z]?)\. ", re.M)
CITATION = re.compile(r"§([0-9]+[a-z]?)")
ROW = re.compile(r"^\| *§([0-9]+[a-z]?) *\| *(.*?) *\| *(.*?) *\|$", re.M)
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


#: Where a document that numbers sections could live - not the
#: population itself, only where `_process_documents()` looks.
_PROCESS_DIRS = ("docs/design/", "docs/contributing/")


def _display_name(path):
    """The short name a citation elsewhere would use for `path`: a
    skill's directory, since every `SKILL.md` shares that filename, or
    a guide's stem otherwise."""
    rel = path.relative_to(REPO).as_posix()
    if rel.startswith(".claude/skills/") and path.name == "SKILL.md":
        return path.parent.name
    return path.stem


def _cites_own_id(path, ids, tracked):
    """`UX-771`: the heading shape alone is not enough - `review`'s own
    §1-§5 pass it, and `directions.md`'s "review §6/§7" does not name
    one of them. A document is in scope only if some *other* tracked
    file cites it by name at an id it actually numbers.

    The lookbehind guards the boundary a verifier found missing: with
    none, `self-review §3` reads as `review` cited at `3`, since
    `self-review` ends in `review` - pulling `review/SKILL.md` into
    the population on a citation nobody wrote about it."""
    name = _display_name(path)
    rel = path.relative_to(REPO).as_posix()
    for alias in {name, name.replace("-", " ")}:
        cite = re.compile(r"(?<![\w-])" + re.escape(alias)
                          + r"(?:\.md)?`?\s*§([0-9]+[a-z]?)")
        for other in tracked:
            if other == rel or not other.endswith(".md"):
                continue
            text = (REPO / other).read_text(encoding="utf-8", errors="replace")
            if any(found in ids for found in cite.findall(text)):
                return True
    return False


@functools.lru_cache(maxsize=1)
def _process_documents():
    """The documents `_ambiguous()` reads - derived, not five paths
    typed in, so a sixth such document is in scope the day it exists.
    A candidate is in `_PROCESS_DIRS` or a `SKILL.md`, numbers at
    least two sections, and does so for at least half its `##`/`###`
    headings (`architecture.md` and `directions.md` fail this: a few
    numbered items in an otherwise prose document); `_cites_own_id`
    then requires it be named elsewhere at one of its own ids."""
    tracked = _tracked()
    candidates = []
    for rel in tracked:
        if not rel.endswith(".md"):
            continue
        if not (rel.startswith(_PROCESS_DIRS)
                or (rel.startswith(".claude/skills/") and rel.endswith("/SKILL.md"))):
            continue
        path = REPO / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        total = len(re.findall(r"^#{2,3} ", text, re.M))
        numbered = HEADING.findall(text)
        if not total or len(numbered) < 2 or len(numbered) / total < 0.5:
            continue
        candidates.append((path, frozenset(numbered)))
    return frozenset(path for path, ids in candidates
                      if _cites_own_id(path, ids, tracked))


def _table():
    """`{section: (guards, note)}` from §7's rows, in document order."""
    text = STYLEGUIDE.read_text(encoding="utf-8")
    body = text[text.index("\n## 7. Enforcement"):]
    return {section: (frozenset(GUARD.findall(guards)), note.strip())
            for section, guards, note in ROW.findall(body)}


def _ambiguous():
    """`{(id, owners)}` for every id more than one process document
    numbers, `owners` the sorted display names of all that do. A bare
    `§5` in a guard belongs to whichever document its sentence is
    about, and nothing in the text says which - so these rows are
    named rather than derived.

    `UX-765` found the gap this replaced: pairing `STYLEGUIDE` against
    the union of the other two sees a collision either shares with it,
    but not one `FIXING_GUIDE` and `STYLE_GUIDE` share with each other
    and not with `STYLEGUIDE`. `UX-771` widened the population from
    the three to `_process_documents()`; naming the *owners*, not just
    the id, is what lets the population shrinking back red with no new
    section needed to prove it."""
    owners = collections.defaultdict(set)
    for doc in _process_documents():
        name = _display_name(doc)
        for section in _sections(doc):
            owners[section].add(name)
    return frozenset((section, tuple(sorted(names)))
                      for section, names in owners.items() if len(names) > 1)


#: `_ambiguous()`, measured the day `UX-771` widened the population to
#: five documents. A census, not a judgement that sharing these is
#: fine - a new id, or an id gaining or losing an owner, is exactly
#: the collision this guard exists to catch, so it fails naming the
#: pair rather than silently widening the set it compares against.
KNOWN_AMBIGUOUS = frozenset({
    ("1", ("decompose", "fixing-guide", "style-guide", "styleguide", "verify")),
    ("2", ("decompose", "fixing-guide", "style-guide", "styleguide", "verify")),
    ("3", ("decompose", "fixing-guide", "style-guide", "styleguide", "verify")),
    ("4", ("decompose", "fixing-guide", "style-guide", "styleguide", "verify")),
    ("4a", ("fixing-guide", "styleguide")),
    ("5", ("decompose", "fixing-guide", "style-guide", "styleguide", "verify")),
    ("6", ("fixing-guide", "style-guide", "styleguide", "verify")),
    ("6a", ("fixing-guide", "styleguide")),
    ("7", ("fixing-guide", "style-guide", "styleguide", "verify")),
})


class TestTheIdSpaceGrowsNoSilentCollision:
    """`UX-765`: `## 8.` in `fixing-guide.md` duplicated `STYLE_GUIDE`'s
    own `§8`, and the old `_ambiguous()` - `STYLEGUIDE` paired against
    the union of the other two - could not see a collision neither
    document shares with `STYLEGUIDE`. This is the direct check: any
    `(id, owners)` `_ambiguous()` did not already carry is new, whether
    the id is new or an existing id gained or lost an owner."""

    def test_no_new_id_is_shared_across_the_process_documents(self):
        extra = _ambiguous() - KNOWN_AMBIGUOUS
        assert extra == set(), (
            f"{sorted(extra)} - a section id and its owning documents "
            f"that KNOWN_AMBIGUOUS does not already carry; a document "
            f"started numbering an id it did not before, or a new "
            f"document joined the population - update KNOWN_AMBIGUOUS "
            f"or give the section a number none of "
            f"{sorted(_display_name(d) for d in _process_documents())} "
            f"already uses")

    def test_the_known_set_is_not_stale(self):
        """The other direction: a retired id, or an owner that no
        longer numbers it, left in the allowlist would let a real new
        collision hide underneath it."""
        gone = KNOWN_AMBIGUOUS - _ambiguous()
        assert gone == set(), (
            f"{sorted(gone)} no longer matches an id's live owner set "
            f"- shrink or update `KNOWN_AMBIGUOUS` to match")

    def test_the_population_is_the_five_documents_this_widened_to(self):
        """`UX-771`: the heading shape alone is not enough. `directions.
        md` cites `.claude/skills/review/SKILL.md` at ids past its own
        highest (5), so that citation cannot be about its own sections -
        `review` and its neighbor `self-review` stay out; `verify` and
        `decompose` are named at ids they do number, and join in."""
        names = {_display_name(d) for d in _process_documents()}
        assert names == {"styleguide", "fixing-guide", "style-guide",
                          "verify", "decompose"}, sorted(names)

    def test_self_review_cannot_stand_in_for_review(self, tmp_path):
        """A verifier found `_cites_own_id`'s alias match unbounded on
        the left: `self-review` ends in `review`, so a file citing only
        the former read as the latter cited at an id it holds. A
        hermetic probe, not a real tracked file - the corpus has no
        such citation today, so this would pass without the fix."""
        review = REPO / ".claude/skills/review/SKILL.md"
        ids = frozenset(_sections(review))
        probe = tmp_path / "probe.md"
        tracked = _tracked() | {str(probe)}
        probe.write_text("See self-review §3 for detail.\n", encoding="utf-8")
        assert not _cites_own_id(review, ids, tracked), (
            "self-review §3 pulled review into the population")
        probe.write_text("See review §3 for detail.\n", encoding="utf-8")
        assert _cites_own_id(review, ids, tracked), (
            "a genuine review §3 did not pull review in")


class TestTheTableIsTheGuide:
    def test_every_section_has_a_row(self):
        sections, table = set(_sections(STYLEGUIDE)), _table()
        assert sections == set(table), (
            "§7's table and the guide's headings disagree; "
            f"sections with no row: {sorted(sections - set(table))}; "
            f"rows for no section: {sorted(set(table) - sections)}")

    def test_a_row_with_no_guard_gives_a_reason(self):
        bare = [section for section, (guards, note) in _table().items()
                if not guards and all(ch in "-— " for ch in note)]
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
        cited, table = _cited(_unit_tests()), _table()
        named = {section for section, _ in _ambiguous()}
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
        named = {section for section, _ in _ambiguous()}
        wrong = [f"§{section}" for section, (_, note) in _table().items()
                 if (NAMED in note.split(";")[0]) != (section in named)]
        assert not wrong, (
            f"these rows disagree with the ids the fixing guide also "
            f"numbers ({sorted(named)}): {sorted(wrong)}")

    def test_a_cited_section_exists_in_a_document_that_numbers_sections(self):
        """`UX-771`: the population is `_process_documents()`, derived -
        not a fixed count of documents typed here."""
        known = set()
        for doc in _process_documents():
            known |= set(_sections(doc))
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
