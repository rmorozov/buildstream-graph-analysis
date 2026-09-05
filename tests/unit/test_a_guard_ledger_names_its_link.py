"""UX-601: two guard ledgers, two ways a row reaches its guard.

Round 83 built both, days apart, and neither knew about the other.
Measured when this was filed:

```text
docs/design/styleguide.md §7   33 rows, 22 naming a guard, 34 guard files
                               linked by a `§N` citation in the guard
docs/contributing/rules.md     30 rule rows, 11 naming a tests/unit guard,
                               10 files, 9 carrying a `holds:` line
```

The style guide's guard-ledger rule is the registry: this file parses
its table and applies whichever link each row declares, so the rule and
the tree cannot drift apart. The third clause is the one the item
exists for - a document that grows a guard column and adopts neither
link is named here, not discovered by the next session to add a rule.

Not re-checked here: that each named guard really holds its row. That
is `test_the_styleguide_names_its_guards.py` and the rules-card clauses
in `test_the_agent_configuration_holds.py`, both ways, and two guards
on one claim is how the two disagree.
"""
import functools
import pathlib
import posixpath
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from test_the_agent_configuration_holds import TestTheRulesCardIsTheEntryPoint as CARD_GUARD

STYLE_GUIDE = REPO / "docs/contributing/style-guide.md"

#: The registry's own heading, matched by what it is about rather than
#: by its number - the number is derived, and renumbering the guide
#: must not silently empty this scan.
RULE_HEADING = re.compile(r"^## (\d+)\. .*guard ledger.*$", re.M | re.I)

#: A row of a markdown table, and the delimiter that makes the line
#: above it a header.
DELIMITER = re.compile(r"^\|[\s:|-]+\|$")
#: A backticked test module, in a ledger cell or a link cell.
GUARD_FILE = re.compile(r"`([\w./-]*test_[a-z0-9_]+\.py)`")
#: The two link forms, read off the registry cell rather than typed:
#: a citation template (`§N`) and a marker template (`holds: <doc>#`).
CITATION_FORM = re.compile(r"`§([A-Z])`")
MARKER_FORM = re.compile(r"`(holds: [\w.-]+#)<[a-z]+>`")
#: A markdown link's target, or a bare backticked path.
LINK_TARGET = re.compile(r"\[`?([^`\]]+)`?\]\(([^)]+)\)|`([\w./-]+\.md)`")

#: What a document must reach before its guard column is a ledger and
#: not a table that happens to name a test. Three, so one sighting in
#: an audit's prose table is not a ledger and a real one cannot hide.
LEDGER_FLOOR = 3


@functools.lru_cache(maxsize=1)
def _tracked():
    """`UX-577`: git's list, never a glob - the main checkout holds
    `.claude/worktrees/<agent>/`, a whole second tree."""
    out = subprocess.run(["git", "ls-files"], cwd=REPO, check=True,
                         capture_output=True, text=True).stdout
    return frozenset(out.splitlines())


def _cells(line):
    return [one.strip() for one in line.strip().strip("|").split("|")]


def _tables(text):
    """`[(header cells, [body lines])]` - every markdown table, found by
    its delimiter row so a `guard` in a prose cell is not a header."""
    lines = text.splitlines()
    found = []
    for n, line in enumerate(lines):
        if not line.startswith("|") or n + 1 >= len(lines):
            continue
        if not DELIMITER.match(lines[n + 1].strip()):
            continue
        body = []
        for after in lines[n + 2:]:
            if not after.startswith("|"):
                break
            body.append(after)
        found.append((_cells(line), body))
    return found


def _named_guards(cell):
    """The tracked `tests/unit` modules a cell names."""
    return [one for one in
            (pathlib.Path(name).name for name in GUARD_FILE.findall(cell))
            if f"tests/unit/{one}" in _tracked()]


def _guard_columns(text):
    """`[(column index, header, body lines)]` for each table with a
    guard column."""
    found = []
    for header, body in _tables(text):
        for index, name in enumerate(header):
            if name.lower().rstrip("s") == "guard":
                found.append((index, header, body))
    return found


def _ledger_weight(rel):
    """How many rows of `rel` point a guard column at a tracked test."""
    text = (REPO / rel).read_text(encoding="utf-8", errors="replace")
    total = 0
    for index, _header, body in _guard_columns(text):
        for line in body:
            cells = _cells(line)
            if index < len(cells) and _named_guards(cells[index]):
                total += 1
    return total


@functools.lru_cache(maxsize=1)
def _registry():
    """`{document: (kind, probe)}` from the style guide's rule.

    `kind` is `citation` or `marker`; `probe` is the literal the rule
    states, used below to look for the link. Read off the rule so a
    mechanism renamed in prose is a mechanism this file then looks for.
    """
    text = STYLE_GUIDE.read_text(encoding="utf-8")
    heading = RULE_HEADING.search(text)
    assert heading, "the style guide states no guard-ledger rule"
    body = text[heading.end():]
    body = body[:body.index("\n## ")] if "\n## " in body else body
    out = {}
    for header, rows in _tables(body):
        if [one.lower() for one in header] != ["ledger", "link"]:
            continue
        for line in rows:
            ledger, link = _cells(line)[:2]
            found = LINK_TARGET.search(ledger)
            assert found, f"the registry row {ledger!r} names no document"
            target = found.group(2) or found.group(3)
            # A registry link is relative to the guide that holds it.
            rel = posixpath.normpath(
                posixpath.join(posixpath.dirname(STYLE_GUIDE.relative_to(
                    REPO).as_posix()), target))
            if CITATION_FORM.search(link):
                out[rel] = ("citation", CITATION_FORM.search(link).group(0))
            elif MARKER_FORM.search(link):
                out[rel] = ("marker", MARKER_FORM.search(link).group(1))
            else:
                out[rel] = ("none", link)
    return out


def _section_rows(rel):
    """`{section id: cell}` for a ledger keyed by a `§` id."""
    text = (REPO / rel).read_text(encoding="utf-8", errors="replace")
    rows = {}
    for index, _header, body in _guard_columns(text):
        for line in body:
            cells = _cells(line)
            if index >= len(cells) or not cells[0].startswith("§"):
                continue
            rows[cells[0].lstrip("§")] = cells[index]
    return rows


def _sentence_rows(rel):
    """`[(rule, cell)]` for a ledger keyed by a sentence."""
    text = (REPO / rel).read_text(encoding="utf-8", errors="replace")
    rows = []
    for index, _header, body in _guard_columns(text):
        for line in body:
            cells = _cells(line)
            if index < len(cells) and not cells[0].startswith("§"):
                rows.append((cells[0], cells[index]))
    return rows


def _headings(rel):
    text = (REPO / rel).read_text(encoding="utf-8", errors="replace")
    return frozenset(re.findall(r"^#{2,3} ([0-9]+[a-g]?)\. ", text, re.M))


class TestTheRegistryIsReadable:
    def test_the_rule_declares_two_ledgers_and_two_links(self):
        registry = _registry()
        assert len(registry) == 2, (
            f"the guard-ledger rule declares {len(registry)} ledgers: "
            f"{sorted(registry)}")
        kinds = sorted(kind for kind, _ in registry.values())
        assert kinds == ["citation", "marker"], (
            f"the rule's links are {kinds}; it must name both mechanisms, "
            f"so a third ledger has two to choose between")
        for rel in registry:
            assert rel in _tracked(), f"the rule names {rel}, which git has not"


class TestEachLedgerUsesItsDeclaredLink:
    """The declared mechanism is the one the rows are actually linked
    by. Coverage, not per-row correctness: the two ledgers' own guards
    hold each row, and this holds the convention."""

    def _ledger(self, kind):
        found = [rel for rel, (declared, _) in _registry().items()
                 if declared == kind]
        assert len(found) == 1, f"{len(found)} ledgers declare {kind}"
        return found[0], _registry()[found[0]][1]

    def test_the_citation_ledger_is_linked_by_citations(self):
        rel, probe = self._ledger("citation")
        rows = _section_rows(rel)
        assert len(rows) >= 30, f"{rel}'s ledger is {len(rows)} rows"
        named = {section: _named_guards(cell)
                 for section, cell in rows.items() if _named_guards(cell)}
        assert len(named) >= 20, (
            f"only {len(named)} of {rel}'s rows name a guard")
        assert len({one for guards in named.values() for one in guards}) >= 30
        missing = []
        for section, guards in sorted(named.items()):
            want = probe.strip("`").replace("N", section)
            for name in guards:
                text = (REPO / "tests/unit" / name).read_text(encoding="utf-8")
                if not re.search(re.escape(want) + r"(?![0-9a-g])", text):
                    missing.append(f"{rel} row {want} names {name}, which does "
                                   f"not cite it")
        assert not missing, (
            f"{rel} is linked by a {probe} citation in the guard's own "
            f"text:\n" + "\n".join(missing))

    def test_the_marker_ledger_is_linked_by_markers(self):
        rel, probe = self._ledger("marker")
        rows = _sentence_rows(rel)
        assert len(rows) >= 25, f"{rel}'s ledger is {len(rows)} rows"
        named = sorted({one for _, cell in rows for one in _named_guards(cell)})
        assert len(named) >= 8, (
            f"only {len(named)} of {rel}'s rows name a tracked guard")
        # A row whose marker has not landed yet is a debt the card's own
        # guard already carries, with the reason and a clause that reds
        # when it goes stale. Anything else skipped the convention.
        missing = [name for name in named
                   if probe not in (REPO / "tests/unit" / name).read_text(
                       encoding="utf-8")
                   and name not in CARD_GUARD.UNMARKED]
        assert not missing, (
            f"{rel} is linked by a `{probe}<slug>` line in the guard, and "
            f"these name no such line: {missing}")
        assert len(named) - len(CARD_GUARD.UNMARKED) >= 8, (
            f"{len(CARD_GUARD.UNMARKED)} of {len(named)} guards are deferred; "
            f"the ledger is a list of intentions")


class TestNoThirdLedgerInventsAThirdLink:
    """The clause `UX-601` exists for. A guard column is a ledger, and
    the tree has exactly the ones the rule declares - so a document
    that grows one is a decision somebody makes, not a mechanism that
    appears."""

    def test_the_tree_has_only_the_declared_ledgers(self):
        found = sorted(rel for rel in _tracked()
                       if rel.endswith(".md") and (REPO / rel).is_file()
                       and _ledger_weight(rel) >= LEDGER_FLOOR)
        assert found == sorted(_registry()), (
            "these documents map rows to guards and the style guide's "
            "guard-ledger rule does not say how they link: "
            f"{sorted(set(found) - set(_registry()))}; declared and no "
            f"longer a ledger: {sorted(set(_registry()) - set(found))}")

    def test_the_scan_reads_a_population(self):
        """Every clause above passes on a scan that finds nothing."""
        docs = [rel for rel in _tracked() if rel.endswith(".md")]
        assert len(docs) > 100, f"the corpus is {len(docs)} documents"
        weights = {rel: _ledger_weight(rel) for rel in _registry()}
        assert all(one >= LEDGER_FLOOR for one in weights.values()), weights


class TestTheRuleStatesTheTestForChoosing:
    def test_the_rule_asks_a_question(self):
        text = STYLE_GUIDE.read_text(encoding="utf-8")
        heading = RULE_HEADING.search(text)
        body = text[heading.end():]
        body = body[:body.index("\n## ")]
        assert "?" in body, (
            "the guard-ledger rule names two links and no test for "
            "choosing between them")

    def test_the_stated_test_separates_the_two_ledgers(self):
        """The rule says the citation works where the row *is* a
        numbered section. Held as a property, so a rule stating a test
        that does not discriminate cannot pass."""
        registry = _registry()
        cited = [rel for rel, (kind, _) in registry.items()
                 if kind == "citation"][0]
        marked = [rel for rel, (kind, _) in registry.items()
                  if kind == "marker"][0]
        sections = _section_rows(cited)
        assert sections, (
            f"{cited} is linked by citation and its rows carry no id to "
            f"cite; the rule's test says they do")
        stray = sorted(set(sections) - _headings(cited))
        assert not stray, (
            f"{cited} is linked by citation and these rows are not "
            f"sections it numbers: {stray}")
        sentences = _sentence_rows(marked)
        assert sentences, (
            f"{marked} is linked by a declared line and has no rows the "
            f"rule's test can be asked about")
        numbered = [rule for rule, _ in sentences
                    if rule.lstrip("§") in _headings(marked)]
        assert not numbered, (
            f"{marked}'s rows carry ids after all ({numbered}); the rule "
            f"says they do not, and a citation would do")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
