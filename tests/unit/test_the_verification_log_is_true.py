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

**What is mechanical here and what is not.** The date can be checked
against the file's own history; *what was re-grounded, and against what*
cannot, and that is the half worth writing - so the item declines a
hook that stamps the date and asks for a log entry that says something,
guarded by the one clause a machine can hold.
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


def stale(claimed, last):
    """Whether a log claiming `claimed` is stale against a change at
    `last`. One function, used by the guard below and by the
    reproduction beneath it - a reproduction that re-implemented the
    comparison would pass while the guard used a different one."""
    return claimed < last


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

    Separated from `_last_commit` so the non-vacuity clause can tell
    "no history here" from "the exclusion ate everything".
    """
    done = subprocess.run(["git", "log", "-1", "--format=%H", "--", str(DOC)],
                          capture_output=True, text=True, cwd=REPO, timeout=60)
    if done.returncode != 0 or not done.stdout.strip():
        return False
    return done.stdout.strip() not in _graft_boundary()


def _last_commit():
    """When git last recorded a *substantive* change to this document.

    `None` where the clone cannot answer - no history at all, and the
    case the note above documents: the newest commit touching the file
    *is* the graft boundary, where "changed here" and "already present
    when history was cut" look identical.
    """
    done = subprocess.run(
        ["git", "log", "--date=short", "--format=%ad %H", "--", str(DOC)],
        capture_output=True, text=True, cwd=REPO, timeout=60)
    if done.returncode != 0 or not done.stdout.strip():
        return None
    boundary = _graft_boundary()
    for line in done.stdout.strip().splitlines():
        when, _, sha = line.strip().partition(" ")
        sha = sha.strip()
        if sha in boundary:
            return None
        if _only_a_derived_figure_moved(sha):
            continue
        return datetime.date.fromisoformat(when)
    return None


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


class TestTheLogIsNotStaleAboutItself:

    def test_the_clause_below_has_a_date_to_compare(self):
        """Non-vacuity for the exclusion: in a clone with history, some
        commit must survive it. An exclusion that excused everything
        would leave `_last_commit()` empty and the clause below would
        skip rather than fail."""
        if not _history_is_readable():
            pytest.skip(NO_HISTORY)
        assert _last_commit() is not None, (
            "every commit touching the document was excused as a derived "
            "figure - the exclusion is too wide and the clause below is off")


    def test_the_claimed_date_is_not_older_than_the_last_change(self):
        """The mechanical half of item 2. Equal is the normal case: the
        commit that re-grounds the document is the commit that moves
        this line, so they land on the same day."""
        last = _last_commit()
        if last is None:
            pytest.skip(NO_HISTORY)
        claimed, item, _ = _claimed()
        assert not stale(claimed, last), (
            f"the Verification Log claims {claimed} (after {item}), and "
            f"{DOC.name} was last changed {last}. Re-ground the document and "
            f"say what against, or the log is worse than no log (UX-247).")

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
    """The acceptance test names the reproduction: the log as it stood,
    2026-08-18 against a 2026-08-23 commit. It cannot be re-run against
    the file - the file is fixed now - so it runs against the same
    comparison with the dates it had."""

    @staticmethod
    def _pair(claimed, last):
        return (datetime.date.fromisoformat(claimed),
                datetime.date.fromisoformat(last))

    def test_the_filed_reproduction_is_stale(self):
        assert stale(*self._pair("2026-08-18", "2026-08-23"))

    def test_the_same_day_is_not(self):
        assert not stale(*self._pair("2026-08-25", "2026-08-25"))

    def test_a_later_commit_than_the_claim_is(self):
        assert stale(*self._pair("2026-08-25", "2026-08-26"))
