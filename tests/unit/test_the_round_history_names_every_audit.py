"""UX-583: the round history is a table over `docs/audits/`, not a memory.

Measured on the base of round 83 (`8481f99`), before this file existed:

```text
docs/audits/*.md round documents   44   42 round-N.md + 2 named walks
round-history table                44 rows, 43 links, 41 distinct targets
no row at all                       3   round-83, guard-census-round-64,
                                        planted-defect-walk-round-72
rows 25 and 26                          link to round-24.md; rounds 25 and
                                        26 have no audit file (round-27.md:127)
docs/README.md audits links        45   missing round-83, the guard census
directions.md:5 and :1446               text `optimization-walkthrough-06.md`
                                        for case-study-06-macro-micro.md
```

The table is where the arguments and the rounds meet and it is typed by
whichever session remembers, so it is read against the directory in both
directions. Enumeration is `git ls-files`, never a glob: the checkout
carries `.claude/worktrees/<agent>/` — whole copies of this tree, each
with its own `docs/audits/` — and a recursive glob reads them.

`docs/audits/data/` is out: those are appendices to a round document,
not rounds, and the row belongs to the round that cites them.
"""
import functools
import os
import pathlib
import posixpath
import re
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
AUDITS = "docs/audits"
DIRECTIONS = "docs/design/directions.md"
README = "docs/README.md"
HISTORY_HEADING = "## Round history"

# `[text](target)` on one line; markdown tables are one row per line.
LINK = re.compile(r"\[([^\]\n]*)\]\(([^)\s]+)\)")

# The scan finding nothing must not pass everything. Measured 44 round
# documents, 43 table links and 45 README audits links on `8481f99`.
FLOOR = 40


@functools.lru_cache(maxsize=None)
def _tracked():
    out = subprocess.run(["git", "ls-files"], cwd=str(REPO), check=True,
                         capture_output=True, text=True).stdout
    return frozenset(out.splitlines())


def _round_documents():
    """Every audit document that records a round, directly under `docs/audits/`."""
    return tuple(sorted(
        p for p in _tracked()
        if posixpath.dirname(p) == AUDITS
        and re.search(r"round-\d+", posixpath.basename(p))))


def _links(doc, prefix):
    """The `prefix`-targeting links in `doc`, as (text, target, resolved)."""
    text = (REPO / doc).read_text(encoding="utf-8")
    here = posixpath.dirname(doc)
    found = []
    for label, target in LINK.findall(text):
        if not target.startswith(prefix):
            continue
        found.append((label, target,
                      os.path.normpath(posixpath.join(here, target))))
    return found


def _history_table():
    """The table rows under `## Round history` — the subject, not the argument."""
    text = (REPO / DIRECTIONS).read_text(encoding="utf-8")
    after = text.split("\n" + HISTORY_HEADING + "\n", 1)
    assert len(after) == 2, f"{DIRECTIONS} has no {HISTORY_HEADING!r} section"
    section = after[1].split("\n## ", 1)[0]
    return tuple(ln for ln in section.splitlines()
                 if ln.startswith("| ") and not ln.startswith("| round |"))


def _table_links():
    rows = _history_table()
    here = posixpath.dirname(DIRECTIONS)
    return tuple((label, target, os.path.normpath(posixpath.join(here, target)))
                 for row in rows for label, target in LINK.findall(row))


def _audits_links():
    """Every link into `docs/audits/` from the two hand-typed documents."""
    return ([(DIRECTIONS,) + link for link in _links(DIRECTIONS, "../audits/")]
            + [(README,) + link for link in _links(README, "audits/")])


def test_the_scan_is_not_vacuous():
    """A walk that finds no audit files, or no links, passes anything."""
    documents = _round_documents()
    assert len(documents) >= FLOOR, (
        f"only {len(documents)} round documents under {AUDITS}/ — the "
        f"enumeration is broken, not the directory")
    assert len(_table_links()) >= FLOOR, (
        f"only {len(_table_links())} links in the round-history table")
    readme = [ln for ln in _audits_links() if ln[0] == README]
    assert len(readme) >= FLOOR, f"only {len(readme)} audits links in {README}"


def test_every_round_document_has_a_history_row():
    linked = {resolved for _, _, resolved in _table_links()}
    missing = [d for d in _round_documents() if d not in linked]
    assert not missing, (
        "no row in the round-history table of "
        f"{DIRECTIONS} links to: {', '.join(missing)}")


def test_every_round_document_is_linked_from_the_readme():
    linked = {resolved for doc, _, _, resolved in _audits_links() if doc == README}
    missing = [d for d in _round_documents() if d not in linked]
    assert not missing, f"{README} links to no: {', '.join(missing)}"


def test_every_audits_link_points_at_a_file_that_exists():
    tracked = _tracked()
    dead = [f"{doc}: [{label}]({target})"
            for doc, label, target, resolved in _audits_links()
            if resolved not in tracked]
    assert not dead, "link to a file this repository does not track: " + "; ".join(dead)


@pytest.mark.parametrize("doc", [DIRECTIONS, README])
def test_a_links_text_names_the_file_it_opens(doc):
    """A bare round number, or a filename in the text, must be the target's."""
    wrong = []
    for _, label, target, resolved in [ln for ln in _audits_links() if ln[0] == doc]:
        base = posixpath.basename(resolved)
        bare = label.strip().strip("`")
        if re.fullmatch(r"\d+", bare) and base != f"round-{bare}.md":
            wrong.append(f"text {bare!r} opens {base}")
            continue
        named = re.search(r"[\w.-]+\.md", bare)
        if named and named.group(0) != base:
            wrong.append(f"text names {named.group(0)}, target is {base}")
    assert not wrong, f"{doc}: " + "; ".join(wrong)
