"""UX-247: a document's claim about its own currency, checked.

Review 1 found the smallest defect with the worst shape:

```text
docs/design/architecture.md, "## Verification Log":
  "Updated 2026-08-18 (after `UX-76`) ..."

git log -1 --date=short -- docs/design/architecture.md:
  7bb63cf 2026-08-23 UX-233: the architecture document meets the viewer axis
```

Five commits had touched the file since that line was written. A reader
who checks the log to decide whether to trust the document gets a date
five days and one whole axis out of date - and the log is the one place
that is *supposed* to answer that question, which makes it worse than no
log, the same way `UX-239`'s context map was worse than no map.

**What is mechanical here and what is not.** The currency can be checked
against the file's own history; *what was re-grounded, and against what*
cannot, and that is the half worth writing - so the item declines a
hook that stamps the date and asks for a log entry that says something,
guarded by the one clause a machine can hold.

`UX-652` changed the unit that check is made in. The comparison was two
`datetime.date`s and this repository lands three rounds in a day, so
`UX-641` rewrote the contracts table the newest entry describes without
the entry's date moving. It is commits now: the entry credits an item,
the item resolves to the commit that closed it, and the question is
whether anything substantive touched the document after it.
"""
import datetime
import pathlib
import re
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
DOC = REPO / "docs/design/architecture.md"
HEADING = "## Verification Log"

NO_HISTORY = "the clone has no history for this file (a shallow checkout)"

# UX-306 follow-up, found by this guard failing on PR #155 for a reason
# that was not the document's. `actions/checkout@v4` clones at depth 1,
# and in a one-commit clone `git log -1 -- <path>` does not report "when
# this file last changed" - it reports **the single commit**, whatever
# it touched. On a pull request that commit is the merge commit GitHub
# builds at request time, so the comparison below was
#
#     the date the log claims   vs   the date CI built its checkout
#
# which is a clock, not a history. It passed for as long as every log
# entry happened to be written the same UTC day CI ran, and failed the
# first time a PR's merge commit landed on the next one - reporting a
# document as stale that was not.
#
# Reproduced before this line was written: `git clone --depth 1` of this
# repository, then `git log -1 --date=short -- docs/design/architecture.md`
# returns the head commit even when that commit does not touch the file.
#
# The skip above was written for exactly this case and never fired,
# because a depth-1 clone answers the question rather than failing it.
#
# **`--is-shallow-repository` is not the predicate**, and reaching for
# it first was wrong: this repository is normally worked in a *grafted*
# clone that is shallow and still carries hundreds of commits, five of
# them touching this document. Skipping on shallowness would have
# turned the guard off where it works, which is a guard deleted rather
# than repaired.
#
# The exact question is narrower: **is the commit git reported the
# graft boundary?** At the boundary git cannot tell "changed here" from
# "already present when history was cut", so its answer is not one; one
# commit deeper it is. `.git/shallow` lists those boundary commits, and
# comparing against it separates the depth-1 checkout (reported commit
# *is* the boundary) from the grafted working clone (reported commit is
# `5e55452`, well inside the history it has).


def _claimed():
    """The date the log claims, and the item it credits."""
    text = DOC.read_text(encoding="utf-8")
    assert HEADING in text, f"{DOC.name} has no {HEADING!r}"
    log = text.split(HEADING, 1)[1]
    found = re.search(r"Updated (\d{4}-\d{2}-\d{2}) \(after `(UX-\d+)`\)", log)
    assert found, (
        "the log's first entry does not read `Updated YYYY-MM-DD (after "
        "`UX-N`)` - which is the shape this guard, and a reader deciding "
        "whether to trust the document, both read")
    # `UX-604`: the entry ends where the next one begins, not 1200
    # characters later. At a fixed width the window reached into the
    # entry below and found *its* "re-grounded in", so the clause
    # passed for any newest entry shorter than the slice.
    rest = log[found.end():]
    following = re.search(r"^Updated \d{4}-\d{2}-\d{2} \(after `UX-\d+`\)",
                          rest, re.M)
    ends = found.end() + (following.start() if following else len(rest))
    return (datetime.date.fromisoformat(found.group(1)), found.group(2),
            log[found.start():ends])


def stale(landed):
    """Whether an entry is stale: something substantive landed after the
    commit it credits. One function, used by the guard below and by the
    reproduction beneath it - a reproduction that re-implemented the
    comparison would pass while the guard used a different one."""
    return bool(landed)


def _graft_boundary():
    """The commits where a shallow clone's history was cut, if any."""
    done = subprocess.run(["git", "rev-parse", "--git-dir"],
                          capture_output=True, text=True, cwd=REPO, timeout=60)
    if done.returncode != 0:
        return set()
    shallow = pathlib.Path(REPO, done.stdout.strip(), "shallow")
    if not shallow.exists():
        return set()
    return {line.strip() for line in
            shallow.read_text(encoding="utf-8").splitlines() if line.strip()}


# `UX-620`: the counts `tools/dev_close_task.py --write` derives into the
# opening sentence. They are computed from `git ls-files`, so they are
# true by construction and cannot make a grounding wrong - but they move
# the file's date, and every round that files or closes a row moves them.
_COUNT = re.compile(r"\d+ (`docs/backlog/\w+/` files)")


def only_the_count_moved(removed, added):
    """Do these diff lines differ in nothing but a derived count?

    Compared with the digits normalised away rather than by matching a
    pattern against each line: a commit that edits the sentence *and*
    the count would match a pattern for the count, and must not be
    excused. Pure, so the discrimination is testable without a fixture
    repository - `_only_a_derived_figure_moved` is the git half.
    """
    if not removed or len(removed) != len(added):
        return False
    return all(_COUNT.sub(r"N \1", a) == _COUNT.sub(r"N \1", b)
               for a, b in zip(removed, added))


def _only_a_derived_figure_moved(sha):
    """`only_the_count_moved`, over this commit's change to `DOC`."""
    done = subprocess.run(
        ["git", "show", "--format=", "--unified=0", sha, "--", str(DOC)],
        capture_output=True, text=True, cwd=REPO, timeout=60)
    if done.returncode != 0:
        return False
    lines = done.stdout.splitlines()
    return only_the_count_moved(
        [ln[1:] for ln in lines
         if ln.startswith("-") and not ln.startswith("---")],
        [ln[1:] for ln in lines
         if ln.startswith("+") and not ln.startswith("+++")])


def _history_is_readable():
    """Can this clone answer "when did the document last change" at all?

    Separated from the range above so the non-vacuity clause can tell
    "no history here" from "the exclusion ate everything".
    """
    done = subprocess.run(["git", "log", "-1", "--format=%H", "--", str(DOC)],
                          capture_output=True, text=True, cwd=REPO, timeout=60)
    if done.returncode != 0 or not done.stdout.strip():
        return False
    return done.stdout.strip() not in _graft_boundary()


def closing_commit(item, rows):
    """The commit that closed `item`, from `(sha, subject)` newest first.

    A closing subject names the id **first**, bare or inside a
    conventional-commit prefix (`UX-641: ...`, `fix(UX-535): ...`).
    `Merge UX-628, UX-629: ...` is not one - it is where two items met,
    not either's close - and the trailing `:` is what separates `UX-63`
    from `UX-637`.

    The **oldest** match, not the newest: a later commit naming the id
    again would walk the anchor forward and switch the clause that uses
    it off without failing anything. Pure, so both of those are testable
    claims rather than intentions - `_closing_commit` is the git half.
    """
    wanted = re.compile(rf"^(?:\w+\()?{re.escape(item)}\)?:")
    matched = [sha for sha, subject in rows if wanted.match(subject)]
    return matched[-1] if matched else None


def _closing_commit(item):
    """`closing_commit` over this clone's log. `None` where the clone
    has no such commit - a cut history, or an entry crediting an item
    whose commit is not written yet."""
    done = subprocess.run(["git", "log", "--format=%H%x09%s"],
                          capture_output=True, text=True, cwd=REPO, timeout=60)
    if done.returncode != 0:
        return None
    found = closing_commit(item, [line.split("\t", 1) for line
                                  in done.stdout.splitlines() if "\t" in line])
    return None if found in _graft_boundary() else found


def _commits_touching(*revs):
    """The commits touching `DOC` in this revision range, newest first.

    `None` where git could not answer at all - which must not read as
    "nothing landed".
    """
    done = subprocess.run(
        ["git", "log", "--format=%H", *revs, "--", str(DOC)],
        capture_output=True, text=True, cwd=REPO, timeout=60)
    if done.returncode != 0:
        return None
    return done.stdout.split()


def _landed_after(anchor):
    """The substantive commits touching `DOC` that `anchor` does not carry.

    `UX-652`: reachability, not a clock. `<anchor>..HEAD` is what the
    entry does not describe, whatever day any of it was written on;
    `only_the_count_moved` is the same exclusion as before.
    """
    found = _commits_touching(f"{anchor}..HEAD")
    if found is None:
        return None
    return [sha for sha in found if not _only_a_derived_figure_moved(sha)]


def _describe(shas):
    done = subprocess.run(["git", "log", "--no-walk", "--format=%h %s", *shas],
                          capture_output=True, text=True, cwd=REPO, timeout=60)
    return done.stdout.strip() or " ".join(shas)


def _committed_on(sha):
    done = subprocess.run(["git", "log", "-1", "--date=short", "--format=%ad",
                           sha], capture_output=True, text=True, cwd=REPO,
                          timeout=60)
    return done.stdout.strip()


def _is_present(sha):
    """Content, not ancestry: this clone either has the object or not."""
    return subprocess.run(["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                          capture_output=True, text=True, cwd=REPO,
                          timeout=60).returncode == 0


class TestTheExclusionIsNarrow:
    """`UX-620`. The clause below skips commits that moved only a
    derived count. An exclusion drawn too wide does not fail that
    clause - it removes its date and the clause *skips*, which is how a
    guard gets switched off without going red. These hold the width."""

    SENTENCE = ("reconstruct that history from 619 `docs/backlog/scenarios/` "
                "files, 75 `docs/backlog/tasks/` files, and the commit log")

    def test_a_count_only_change_is_excused(self):
        before = self.SENTENCE.replace("619", "604")
        assert only_the_count_moved([before], [self.SENTENCE])

    def test_a_count_and_a_word_on_one_line_is_not_excused(self):
        """The case a per-line pattern would wave through, and the
        reason the comparison normalises instead of matching."""
        before = self.SENTENCE.replace("619", "604").replace(
            "the commit log", "the commit history")
        assert not only_the_count_moved([before], [self.SENTENCE])

    def test_a_prose_only_change_is_not_excused(self):
        before = self.SENTENCE.replace("the commit log", "the commit history")
        assert not only_the_count_moved([before], [self.SENTENCE])

    def test_an_added_line_is_not_excused(self):
        assert not only_the_count_moved([], [self.SENTENCE])

    def test_an_uneven_change_is_not_excused(self):
        assert not only_the_count_moved(
            [self.SENTENCE], [self.SENTENCE, "and one more sentence"])


class TestTheAnchorIsTheItemsOwnCommit:
    """`UX-652`. The anchor decides the whole comparison, so what
    `closing_commit` selects is read here rather than trusted: an anchor
    resolved too far forward empties the range and the clause below
    passes on a document nobody re-grounded."""

    ROWS = (("cb0c31e", "Architecture review 16, and the six rows it filed"),
            ("e6400a1", "Merge UX-628, UX-629: the contract prose goes down"),
            ("6235fc9", "UX-641: a level names its members"),
            ("9beda27", "UX-629: a required set growing under a live id"),
            ("fab3307", "fix(UX-535): the graph's shape is published once"))

    def test_the_id_first_is_the_close(self):
        assert closing_commit("UX-641", self.ROWS) == "6235fc9"
        assert closing_commit("UX-535", self.ROWS) == "fab3307"

    def test_a_merge_naming_two_items_closes_neither(self):
        """`Merge UX-628, UX-629: ...` names the id and is not its
        close. Taken as one it would anchor `UX-629` on a commit later
        than its own, which is the range going quiet."""
        assert closing_commit("UX-628", self.ROWS) is None
        assert closing_commit("UX-629", self.ROWS) == "9beda27"

    def test_the_oldest_match_wins(self):
        """A round that names the id again - a close, a carry, a
        follow-up - must not move the anchor forward."""
        rows = (("aaaaaaa", "UX-641: the follow-up nobody expected"),) \
            + self.ROWS
        assert closing_commit("UX-641", rows) == "6235fc9"

    def test_a_longer_id_is_not_this_one(self):
        assert closing_commit("UX-63", self.ROWS) is None
        assert closing_commit("UX-64", self.ROWS) is None


class TestTheLogIsNotStaleAboutItself:

    #: How far back the non-vacuity clause reads. Bounded because the
    #: exclusion spawns one `git show` per commit and this file is
    #: `small`: 108 commits touch the document, 20 is 0.2s of them.
    WINDOW = 20

    def test_the_clause_below_has_commits_to_compare(self):
        """Non-vacuity for the exclusion: in a clone with history, some
        commit must survive it. An exclusion that excused everything
        would make `_landed_after` empty for every anchor and the clause
        below would pass without reading anything."""
        if not _history_is_readable():
            pytest.skip(NO_HISTORY)
        recent = _commits_touching(f"-{self.WINDOW}")
        if not recent:
            pytest.skip(NO_HISTORY)
        assert [sha for sha in recent
                if not _only_a_derived_figure_moved(sha)], (
            f"all {len(recent)} of the document's newest commits were "
            "excused as a derived figure - the exclusion is too wide and "
            "the clause below is off")

    def test_nothing_landed_after_the_commit_the_entry_credits(self):
        """The mechanical half of item 2, in the unit the tree moves in
        (`UX-652`). The commit that re-grounds the document is the
        commit that writes this entry, so the anchor is normally the
        newest change to the file and the range is empty."""
        if not _history_is_readable():
            pytest.skip(NO_HISTORY)
        claimed, item, _ = _claimed()
        anchor = _closing_commit(item)
        if anchor is None:
            pytest.skip(NO_HISTORY)
        landed = _landed_after(anchor)
        if landed is None:
            pytest.skip(NO_HISTORY)
        assert not stale(landed), (
            f"the Verification Log's newest entry is dated {claimed} and "
            f"credits {item} ({anchor[:7]}); {len(landed)} substantive "
            f"commit(s) have changed {DOC.name} since:\n{_describe(landed)}\n"
            f"Re-ground the document and say what against, or the log is "
            f"worse than no log (UX-247, UX-652).")

    def test_the_window_is_the_entry_and_not_the_one_below(self):
        """`UX-604`: what the clause below reads. A window that runs on
        past the next `Updated ` heading is checking its predecessor,
        which is how the grounding clause passed while saying nothing."""
        _, _, entry = _claimed()
        following = re.findall(
            r"^Updated \d{4}-\d{2}-\d{2} \(after `UX-\d+`\)", entry, re.M)
        assert len(following) == 1, (
            f"the window holds {len(following)} entry headings; it should "
            "end where the next entry begins")

    def test_the_entry_says_what_it_was_grounded_in(self):
        """The half a hook cannot write, which is why the item declined
        one. A date with no "against what" is a timestamp, not a
        verification."""
        _, _, entry = _claimed()
        assert "re-grounded in" in entry, entry[:200]
        # Named sources, not an adjective: a file, a command or a
        # document the next reviewer can open.
        assert re.search(r"`[a-z_/.]+\.(md|py|js)`|`bga [a-z]+", entry), (
            "the entry names no source a reader could re-check")

    def test_the_older_entries_are_kept(self):
        """A log that replaces its own history is a field, not a log."""
        text = DOC.read_text(encoding="utf-8").split(HEADING, 1)[1]
        assert len(re.findall(r"Updated \d{4}-\d{2}-\d{2}", text)) >= 2, (
            "the log holds one entry; earlier groundings were overwritten")
        assert "Originally written" in text


class TestTheGuardWouldHaveCaughtIt:
    """`UX-652`'s reproduction, and it is this repository's own history
    rather than a pair of dates. At `933de24` the newest entry credited
    `UX-629` (`9beda27`) while `UX-641` (`6235fc9`) had already moved
    the contracts table's headline id from `analyze/v5` to `analyze/v6`
    - the table that entry says it checked. Both commits are dated
    2026-09-04, which is why a comparison in days saw nothing.

    Pinned to shas, so it goes on reproducing after the live clause
    above turns green.
    """

    CREDITED = "UX-629"
    ANCHOR = "9beda27"
    AFTER = "6235fc9"

    def _need(self, *shas):
        if not all(_is_present(sha) for sha in shas):
            pytest.skip(NO_HISTORY)

    def test_the_credited_item_resolves_to_the_commit_that_closed_it(self):
        self._need(self.ANCHOR)
        assert (_closing_commit(self.CREDITED) or "").startswith(self.ANCHOR)

    def test_the_filed_reproduction_is_stale(self):
        self._need(self.ANCHOR, self.AFTER)
        landed = _landed_after(self.ANCHOR)
        assert stale(landed)
        assert any(sha.startswith(self.AFTER) for sha in landed), (
            f"{self.AFTER} is not in what landed after {self.ANCHOR}: "
            f"{[sha[:7] for sha in landed]}")

    def test_the_two_commits_share_a_day(self):
        """The resolution, pinned. If these two ever read as different
        days the item's argument is gone and so is this file's unit."""
        self._need(self.ANCHOR, self.AFTER)
        assert _committed_on(self.ANCHOR) == _committed_on(self.AFTER) != ""

    def test_the_documents_newest_change_leaves_nothing_after_it(self):
        """The other direction: an anchor the document has nothing past
        is not stale, whatever the dates say."""
        newest = _commits_touching("-1")
        if not newest:
            pytest.skip(NO_HISTORY)
        assert not stale(_landed_after(newest[0]))
