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

`UX-591`: and the documents that are *not* rounds, which this file's
first version enumerated past. `architecture-review.md` is 45,132 B
and thirteen reviews long and no index carried it — the round list is
a run of `·`-separated numbers, so a standing document put there
reads as a round. They get a table row instead, and a row is what is
asserted, not a link anywhere on the page.
"""
import functools
import os
import pathlib
import posixpath
import re
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import dev_track_cost

AUDITS = "docs/audits"
DIRECTIONS = "docs/design/directions.md"
README = "docs/README.md"
SCENARIOS = "docs/backlog/scenarios"
CLOSED = f"{SCENARIOS}/closed.md"
HISTORY_HEADING = "## Round history"

#: `UX-798`: rows from here on carry a derived "N closed, M filed";
#: older rows are records, read by nobody but a person.
COUNTED_FROM_ROUND = 109

#: Spelled words, one to ninety-nine, built from `count_word`'s own
#: table so the two cannot drift (`UX-752`'s reasoning, `UX-798`'s
#: guard; ninety-nine because `count_word` builds hundreds separately
#: since `UX-794` and no row here has reached one).
_WORD_FOR = {n: dev_track_cost.count_word(n) for n in range(1, 100)}
NUMBER_FOR_WORD = {word: n for n, word in _WORD_FOR.items()}

# `[text](target)` on one line; markdown tables are one row per line.
LINK = re.compile(r"\[([^\]\n]*)\]\(([^)\s]+)\)")

# The scan finding nothing must not pass everything. Measured 44 round
# documents, 43 table links and 45 README audits links on `8481f99`.
FLOOR = 40

# `UX-591`: architecture-review, case-study-06, optimization-walkthrough-04,
# spec-compliance-review. Measured 4 on the base of round 84.
NAMED_FLOOR = 4


@functools.cache
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


def _named_documents():
    """Every audit document that is not a round (`UX-591`)."""
    return tuple(sorted(
        p for p in _tracked()
        if posixpath.dirname(p) == AUDITS
        and not re.search(r"round-\d+", posixpath.basename(p))))


def _readme_table_links():
    """Links inside a markdown table row of `README` — a row, not a run."""
    here = posixpath.dirname(README)
    found = []
    for line in (REPO / README).read_text(encoding="utf-8").splitlines():
        if not line.startswith("| "):
            continue
        for _label, target in LINK.findall(line):
            if target.startswith("audits/"):
                found.append(os.path.normpath(posixpath.join(here, target)))
    return tuple(found)


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
    assert len(_named_documents()) >= NAMED_FLOOR, (
        f"only {len(_named_documents())} non-round documents under {AUDITS}/ — "
        f"the enumeration is broken, not the directory")


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


def test_every_named_audit_document_has_a_readme_table_row():
    """`UX-591`. A row says what the document records; a number in the
    round run says only that it is a round, which these are not."""
    rows = set(_readme_table_links())
    missing = [d for d in _named_documents() if d not in rows]
    assert not missing, (
        f"{README} has no table row for: {', '.join(missing)} - a link in "
        f"the round run is not a row, and these are not rounds")


def test_no_named_audit_document_is_listed_as_a_round():
    """The other direction: the run under `## Audits` is rounds only."""
    run = {resolved for doc, _, _, resolved in _audits_links()
           if doc == README} - set(_readme_table_links())
    stray = [d for d in _named_documents() if d in run]
    assert not stray, (
        f"{README} lists as a round: {', '.join(stray)}")


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
    for _, label, _target, resolved in [ln for ln in _audits_links() if ln[0] == doc]:
        base = posixpath.basename(resolved)
        bare = label.strip().strip("`")
        if re.fullmatch(r"\d+", bare) and base != f"round-{bare}.md":
            wrong.append(f"text {bare!r} opens {base}")
            continue
        named = re.search(r"[\w.-]+\.md", bare)
        if named and named.group(0) != base:
            wrong.append(f"text names {named.group(0)}, target is {base}")
    assert not wrong, f"{doc}: " + "; ".join(wrong)


def _closed_status():
    """`UX-798`: id -> the marker on that id's own row in `closed.md`."""
    status = {}
    for line in (REPO / CLOSED).read_text(encoding="utf-8").splitlines():
        head = re.match(r"^\| (UX-\d+) \|", line)
        if not head:
            continue
        marker = re.search(r"\| ?(🟢|🔴|🟡|⚪|🟠)", line[len(head.group(0)):])
        status[head.group(1)] = marker.group(1) if marker else None
    return status


#: The row's tail, `"<n or word> closed, <n or word> filed |"` at the
#: line's end. `(?<=\s)` — not `\b` — anchors the first word: `\b` sits
#: at *every* internal hyphen too, so greedy backtracking on the row's
#: free text read `thirty-one closed` as `one` (verifier finding on
#: this file, `UX-798`).
_COUNT_TRAILER = re.compile(
    r"(?<=\s)(\d+|[A-Za-z]+(?:-[A-Za-z]+)?)\s+closed,\s+"
    r"(\d+|[A-Za-z]+(?:-[A-Za-z]+)?)\s+filed \|$")


def _parse_count_trailer(row):
    """`(closed, filed)` as ints, or `None` if `row` has no such tail."""
    m = _COUNT_TRAILER.search(row)
    return None if m is None else (_as_number(m.group(1)), _as_number(m.group(2)))


def _round_history_rows():
    """(round, closed_n, filed_n) for every row with a count trailer."""
    rows = []
    for row in _history_table():
        counts = _parse_count_trailer(row)
        if counts is None:
            continue
        label = LINK.search(row).group(1)
        rows.append((int(label),) + counts)
    return rows


def _as_number(word_or_digit):
    if word_or_digit.isdigit():
        return int(word_or_digit)
    return NUMBER_FOR_WORD[word_or_digit.lower()]


def _what_closed_ids(round_):
    """The ids that head a `## What closed` bullet — never an id merely
    named inside another bullet's prose (round 110's `UX-772`, `UX-607`)."""
    doc = (REPO / AUDITS / f"round-{round_}.md").read_text(encoding="utf-8")
    after = doc.split("\n## What closed\n", 1)
    assert len(after) == 2, f"round-{round_}.md has no '## What closed' section"
    section = after[1].split("\n## ", 1)[0]
    ids = []
    for line in section.splitlines():
        # UX-813: a bullet with no em dash is prose, not a closed row.
        if not line.startswith("- ") or " — " not in line:
            continue
        for uid in re.findall(r"UX-\d+", line.split(" — ", 1)[0]):
            if uid not in ids:
                ids.append(uid)
    return ids


def test_what_closed_ids_reads_each_bullet_s_head_once(tmp_path, monkeypatch):
    """`UX-813`: round 111 derived sixteen from fifteen ids, one twice."""
    (tmp_path / AUDITS).mkdir(parents=True)
    (tmp_path / AUDITS / "round-999.md").write_text(
        "# Round 999\n\n## What closed\n\n"
        "- `UX-1` — a row.\n"
        "- `UX-1`, `UX-2` — the same row named again, and another.\n"
        "- Direction 9 marked landed once `UX-3` closed.\n\n"
        "## In progress\n\n- `UX-4` — not closed.\n", encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "REPO", tmp_path)
    assert _what_closed_ids(999) == ["UX-1", "UX-2"]


def _found_by_round(round_):
    """Task files whose header field, not any quoted prose, names `round_`."""
    ids = []
    for f in sorted((REPO / SCENARIOS).glob("UX-*.md")):
        for line in f.read_text(encoding="utf-8").splitlines():
            if not line.startswith("**Priority:**"):
                continue
            m = re.search(r"\*\*Found by:\*\* ([^|]*)\|", line)
            if m and re.search(rf"\bround {round_}\b", m.group(1)):
                ids.append("UX-" + f.stem.split("-")[1].lstrip("0"))
            break
    return ids


def test_a_history_row_s_counts_are_derived():
    """`UX-798`: the row's typed "N closed, M filed" against the round
    document's own bulleted ids and the tasks that name the round."""
    status = _closed_status()
    checked = 0
    for round_, said_closed, said_filed in _round_history_rows():
        if round_ < COUNTED_FROM_ROUND:
            continue
        checked += 1
        closed_ids = _what_closed_ids(round_)
        not_green = [i for i in closed_ids if status.get(i) != "🟢"]
        assert not not_green, (
            f"round {round_}: What closed names {', '.join(not_green)}, "
            f"not 🟢 in {CLOSED}")
        derived_closed = len(closed_ids)
        derived_filed = len(_found_by_round(round_))
        assert (said_closed, said_filed) == (derived_closed, derived_filed), (
            f"round {round_}: directions.md says "
            f"{said_closed} closed, {said_filed} filed; derived "
            f"{derived_closed} closed, {derived_filed} filed")
    assert checked >= 2, "no history row at or after round " \
        f"{COUNTED_FROM_ROUND} was checked — the scan is vacuous"


def test_the_count_trailer_reads_a_compound_word_past_thirty():
    """A verifier read `thirty-one closed` as `1`: a `\\b`-anchored word
    class lets greedy backtracking start inside a hyphenated word.
    `_parse_count_trailer` must read the whole compound, and the word
    table must cover it (`_WORD_FOR` stops at 30 before this fix)."""
    row = "| [111](../audits/round-111.md) | free text. thirty-one closed, twenty-two filed |"
    assert _parse_count_trailer(row) == (31, 22)
