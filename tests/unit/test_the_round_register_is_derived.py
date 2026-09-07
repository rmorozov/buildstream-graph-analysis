"""`UX-744`: `dev_round_register.py`'s pure functions, over fixtures -
not the live repository, so a guard here does not depend on which
commits happen to exist when the suite runs, and mutation testing does
not need a real commit to land first.
"""
import pathlib
import subprocess
import sys

import pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from tools import dev_round_register as reg


class TestCommitSignalReadsTheSubjectOnly:
    """A body mentioning an old round in passing must not count - this
    task's own commits mention several by number."""

    def test_a_body_mentioning_an_old_round_does_not_count(self):
        commits = [("2026-01-01", "UX-744: the round register\n\n"
                                   "notes about round 90 in the body")]
        assert reg.commit_signal(commits) == {}

    def test_a_subject_naming_a_round_is_matched_case_insensitively(self):
        commits = [("2026-01-01", "round 12 closes UX-1"),
                   ("2026-01-02", "Round 12: the document")]
        signal = reg.commit_signal(commits)
        assert set(signal) == {"12"}
        assert signal["12"]["dates"] == ["2026-01-01", "2026-01-02"]


class TestRoundsJoinsTwoSources:
    """A commit and the ledger each contribute a round the other does
    not know about, so removing either's contribution is visible here.
    No ids column: a verifier found `commit_signal()` cannot tell a
    commit that documents a round from one that is in it (round 101,
    contaminated by `UX-757`'s retroactive documentation commit)."""

    def test_a_ledger_only_round_appears_with_a_dashed_date(self):
        result = reg.rounds(commits=[], ledger_runs=[{"round": "5"}])
        assert result == {"5": {"date": "—"}}

    def test_a_commit_only_round_appears_with_its_date(self):
        commits = [("2026-01-01", "round 7 closes UX-1")]
        result = reg.rounds(commits=commits, ledger_runs=[])
        assert result == {"7": {"date": "2026-01-01"}}

    def test_the_latest_of_several_naming_commits_wins(self):
        commits = [("2026-01-01", "round 7 opens"),
                   ("2026-01-03", "round 7 closes")]
        result = reg.rounds(commits=commits, ledger_runs=[])
        assert result["7"]["date"] == "2026-01-03"


class TestDocumentDate:
    """The round's own document, read directly - the source the ids
    column should have used, and now the date-comparison test does."""

    def test_the_first_stated_date_wins(self, tmp_path):
        (tmp_path / "docs" / "audits").mkdir(parents=True)
        (tmp_path / "docs/audits/round-9.md").write_text(
            "Opens at `abc123` (2026-01-05 10:00), closes 2026-01-06.\n",
            encoding="utf-8")
        assert reg.document_date("9", repo=tmp_path) == "2026-01-05"

    def test_a_document_with_no_stated_date_is_none_here(self, tmp_path):
        (tmp_path / "docs" / "audits").mkdir(parents=True)
        (tmp_path / "docs/audits/round-9.md").write_text(
            "No date in this text at all.\n", encoding="utf-8")
        assert reg._first_date_in_text(
            (tmp_path / "docs/audits/round-9.md").read_text()) is None

    def test_a_missing_document_is_none(self, tmp_path):
        assert reg.document_date("404", repo=tmp_path) is None


class TestWrittenRoundsExcludesOnlyAnUndocumentedNewest:
    """The self-reference fix (fixing-guide.md §7a), bounded: a round
    in progress cannot commit the row that names it, but a documented
    round must not stay excluded forever waiting for a strictly higher
    round to appear - the permanence risk a verifier named."""

    def test_an_undocumented_newest_is_excluded(self):
        full = {"5": {"date": "a"}, "9": {"date": "b"}}
        written = reg.written_rounds(full, documented=lambda n: False)
        assert set(written) == {"5"}

    def test_a_documented_newest_is_kept(self):
        """The permanence-risk pin: if this ever regresses to "always
        drop the max", a round with a finished document stays out
        forever once the naming convention pauses."""
        full = {"5": {"date": "a"}, "9": {"date": "b"}}
        written = reg.written_rounds(full, documented=lambda n: n == "9")
        assert set(written) == {"5", "9"}

    def test_every_other_round_survives_either_way(self):
        full = {str(n): {"date": "x"} for n in (1, 2, 3)}
        assert set(reg.written_rounds(
            full, documented=lambda n: False)) == {"1", "2"}

    def test_an_empty_register_writes_nothing(self):
        assert reg.written_rounds({}, documented=lambda n: False) == {}


class TestRenderAndCheckRoundTrip:
    def test_check_reds_when_the_file_is_stale(self, tmp_path, monkeypatch):
        path = tmp_path / "round-register.md"
        path.write_text("stale\n", encoding="utf-8")
        monkeypatch.setattr(reg, "REGISTER", path)
        monkeypatch.setattr(reg, "rounds", lambda: {"3": {"date": "d"}})
        assert reg.check() != []

    def test_check_is_clean_once_written(self, tmp_path, monkeypatch):
        path = tmp_path / "round-register.md"
        monkeypatch.setattr(reg, "REGISTER", path)
        monkeypatch.setattr(
            reg, "rounds",
            lambda: {"3": {"date": "d"}, "4": {"date": "e"}})
        path.write_text(reg.render(reg.written_rounds()), encoding="utf-8")
        assert reg.check() == []


class TestAShallowCloneIsRefused:
    """`UX-776`: `git log` stops at the shallow boundary, so the
    derivation is a property of the checkout. This container's 610
    commits derived 32 rounds; CI's 1,538 derived 71, and `--check`
    reddened on the register `--write` had produced here."""

    @staticmethod
    def _repo(root, commits, shallow=False):
        """A repository with a real history. A cut one is made by
        cloning this at `--depth 1`, not by writing a marker."""
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        env = ["-c", "user.email=t@t", "-c", "user.name=t"]
        for n in range(commits):
            subprocess.run(["git", "-C", str(root), *env, "commit", "-q",
                            "--allow-empty", "-m", f"c{n}"], check=True)
        return root

    def test_check_refuses_rather_than_deriving_from_half_a_history(
            self, tmp_path, monkeypatch):
        origin = self._repo(tmp_path / "o", commits=3)
        root = tmp_path / "r"
        subprocess.run(["git", "clone", "-q", "--depth", "1",
                        f"file://{origin}", str(root)], check=True)
        monkeypatch.setattr(reg, "REPO", root)
        monkeypatch.setattr(reg, "rounds", lambda: {"3": {"date": "d"}})
        problems = reg.check()
        assert problems and "shallow" in problems[0], problems

    def test_a_left_behind_marker_is_not_a_shallow_history(self, tmp_path):
        """The one CI taught: the file's presence is a proxy. `UX-781`:
        the marker names a real commit that HEAD cannot reach, so an
        empty file is not what makes this pass - a boundary off this
        history cuts nothing this derivation walks."""
        root = self._repo(tmp_path / "r", commits=2)
        env = ["-c", "user.email=t@t", "-c", "user.name=t"]
        subprocess.run(["git", "-C", str(root), *env, "commit", "-q",
                        "--allow-empty", "-m", "off-history"], check=True)
        off = subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                             capture_output=True, text=True,
                             check=True).stdout.strip()
        subprocess.run(["git", "-C", str(root), "reset", "-q", "--hard",
                        "HEAD~1"], check=True)
        (root / ".git" / "shallow").write_text(off + "\n", encoding="utf-8")
        assert not reg.is_shallow(root)

    def test_a_complete_clone_is_not_refused(self, tmp_path, monkeypatch):
        """The discriminator: the same tree without the boundary
        passes, so the refusal reads history and not a directory."""
        root = self._repo(tmp_path / "r", commits=2)
        path = root / "round-register.md"
        monkeypatch.setattr(reg, "REPO", root)
        monkeypatch.setattr(reg, "REGISTER", path)
        monkeypatch.setattr(reg, "rounds", lambda: {"3": {"date": "d"}})
        path.write_text(reg.render(reg.written_rounds()), encoding="utf-8")
        assert reg.check() == []

    def test_a_depth_fetch_onto_a_complete_clone_is_shallow(
            self, tmp_path):
        """`UX-781`, and the case that falsified the first two
        readings. The clone is complete, so every object is on disk and
        no parent is missing - but a `--depth` fetch grafts a boundary
        and `git log` stops at it. CI did this to itself at
        `ci.yml`'s base-diff step, on the 3.11 job only."""
        origin = self._repo(tmp_path / "o", commits=6)
        root = tmp_path / "r"
        subprocess.run(["git", "clone", "-q", f"file://{origin}", str(root)],
                       check=True)
        assert not reg.is_shallow(root), "a full clone, before the fetch"
        walked = len(subprocess.run(
            ["git", "-C", str(root), "rev-list", "--count", "HEAD"],
            capture_output=True, text=True, check=True).stdout.split())
        subprocess.run(["git", "-C", str(root), "fetch", "--no-tags",
                        "--depth=2", "origin", "HEAD"], check=True,
                       capture_output=True)
        boundary = (root / ".git" / "shallow").read_text(
            encoding="utf-8").split()
        assert boundary, "the depth fetch wrote no boundary"
        # The reading UX-776 shipped: the parent objects are all still
        # here, so object-presence reads this repository as complete.
        present = all(subprocess.run(
            ["git", "-C", str(root), "cat-file", "-e", line.split()[1]],
            capture_output=True, check=False).returncode == 0
            for sha in boundary
            for line in subprocess.run(
                ["git", "-C", str(root), "cat-file", "-p", sha],
                capture_output=True, text=True, check=True).stdout.splitlines()
            if line.startswith("parent "))
        assert present, "no parent object is missing - the falsifying half"
        assert reg.is_shallow(root), (
            f"{walked} commits were reachable and the fetch grafted "
            f"{boundary}; the derivation must refuse")

    def test_the_real_checkout_is_complete(self):
        """The one that would have caught this round: a shallow clone
        writes a truncated register and CI reds on it."""
        assert not reg.is_shallow(), (
            "this checkout is shallow - run `git fetch --unshallow` "
            "before deriving anything from git history")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
