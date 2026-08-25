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
    return (datetime.date.fromisoformat(found.group(1)), found.group(2),
            log[found.start():found.start() + 1200])


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


def _last_commit():
    """When git last recorded a change to this document, or `None`.

    `None` where the clone cannot answer - no history at all, and the
    case the note above documents: the newest commit touching the file
    *is* the graft boundary, where "changed here" and "already present
    when history was cut" look identical.
    """
    done = subprocess.run(
        ["git", "log", "-1", "--date=short", "--format=%ad %H", "--", str(DOC)],
        capture_output=True, text=True, cwd=REPO, timeout=60)
    if done.returncode != 0 or not done.stdout.strip():
        return None
    when, _, sha = done.stdout.strip().partition(" ")
    if sha.strip() in _graft_boundary():
        return None
    return datetime.date.fromisoformat(when)


class TestTheLogIsNotStaleAboutItself:

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
