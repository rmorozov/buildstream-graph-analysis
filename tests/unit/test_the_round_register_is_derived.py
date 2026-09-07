"""`UX-744`: `dev_round_register.py`'s pure functions, over fixtures -
not the live repository, so a guard here does not depend on which
commits happen to exist when the suite runs, and mutation testing does
not need a real commit to land first.
"""
import pathlib
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


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
