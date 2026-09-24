"""UX-998: a bookkeeping finding is one line, swept once a round.

Fixture ledgers only, save the one clause that reads the real one.
`validate()` is transactional-refusal's own reader: `add()` and `mark()`
both call it on the candidate text before writing, so refusing to write
is asserted through them and never by poking `write_text` directly.

holds: rules.md#a-drift-you-notice-is-a-line-anything-else-a-row
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import dev_bookkeeping as bk


@pytest.fixture
def repo(tmp_path):
    """A fake tree: one real path an open line may point at, and the
    scenarios directory a `promoted` status is checked against."""
    (tmp_path / "docs" / "backlog" / "scenarios").mkdir(parents=True)
    (tmp_path / "docs" / "backlog" / "scenarios" / "UX-0001-fake.md").write_text(
        "# UX-1\n", encoding="utf-8")
    (tmp_path / "CLAUDE.md").write_text("real\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def ledger(tmp_path):
    return tmp_path / "bookkeeping.md"


@pytest.fixture
def paths(repo, ledger):
    return bk.Paths(ledger, repo)


GOOD = ("- r140 · open · figure · `CLAUDE.md` · a stale figure · "
       "`dev_round_register.py --check`")


class TestMalformedLines:
    def test_a_well_formed_line_parses_clean(self, repo):
        entries, problems = bk.parse_entries(GOOD)
        assert problems == []
        assert len(entries) == 1

    def test_a_command_with_no_backticks_is_named(self, repo):
        bad = ("- r140 · open · figure · `CLAUDE.md` · a stale figure · "
              "dev_round_register.py --check")
        entries, problems = bk.parse_entries(bad)
        assert entries == []
        assert len(problems) == 1
        assert "line 1" in problems[0]

    def test_an_unknown_status_word_is_named(self, repo):
        bad = "- r140 · pending · figure · `CLAUDE.md` · a stale figure · `x`"
        _, problems = bk.parse_entries(bad)
        assert len(problems) == 1


class TestDuplicateKeys:
    def test_two_lines_one_key_fails(self, repo):
        other = ("- r140 · open · count · `CLAUDE.md` · a stale figure · "
                "`dev_impact.py --check`")
        problems = bk.validate(GOOD + "\n" + other, repo_root=repo)
        assert any("duplicates" in p for p in problems)


class TestOpenLinePath:
    def test_an_existing_path_is_clean(self, repo):
        assert bk.validate(GOOD, repo_root=repo) == []

    def test_a_missing_path_is_named(self, repo):
        bad = GOOD.replace("CLAUDE.md", "does-not-exist.md")
        problems = bk.validate(bad, repo_root=repo)
        assert any("does not exist" in p for p in problems)

    def test_a_resolved_lines_path_is_not_checked(self, repo):
        resolved = GOOD.replace("open", "swept r141 UX-999", 1)
        assert bk.validate(resolved, repo_root=repo) == []


class TestSweepSurvival:
    #: three other lines resolved at rounds after r1's filing - three
    #: distinct sweeps survived by the still-open line.
    THREE_SWEEPS = "\n".join([
        "- r1 · open · figure · `CLAUDE.md` · a stale figure · `x`",
        "- r1 · swept r2 UX-1 · figure · `CLAUDE.md` · b · `x`",
        "- r1 · swept r3 UX-1 · figure · `CLAUDE.md` · c · `x`",
        "- r1 · swept r4 UX-1 · figure · `CLAUDE.md` · d · `x`",
    ])

    def test_no_open_line_past_three_sweeps(self, repo):
        problems = bk.validate(self.THREE_SWEEPS, repo_root=repo)
        assert any("past 3 sweeps" in p for p in problems)

    def test_two_sweeps_is_still_open(self, repo):
        two = "\n".join(self.THREE_SWEEPS.splitlines()[:3])
        problems = bk.validate(two, repo_root=repo)
        assert not any("sweeps" in p for p in problems)


class TestPromotedNamesATaskFile:
    def test_a_real_task_file_is_clean(self, repo):
        line = "- r1 · promoted r2 UX-1 · figure · `CLAUDE.md` · x · `y`"
        assert bk.validate(line, repo_root=repo) == []

    def test_an_unfiled_id_is_named(self, repo):
        line = "- r1 · promoted r2 UX-9999 · figure · `CLAUDE.md` · x · `y`"
        problems = bk.validate(line, repo_root=repo)
        assert any("no task file" in p for p in problems)


class TestAdd:
    def test_it_round_trips(self, ledger, paths):
        finding = bk.Finding("CLAUDE.md", "a stale figure",
                             "dev_round_register.py")
        line = bk.add(finding, "figure", 140, paths=paths, new_class=True)
        entries, problems = bk.parse_entries(ledger.read_text(encoding="utf-8"))
        assert problems == []
        assert len(entries) == 1
        assert entries[0].path == "CLAUDE.md"
        assert entries[0].command == "dev_round_register.py"
        assert line in ledger.read_text(encoding="utf-8")

    def test_it_refuses_an_unknown_class(self, paths):
        with pytest.raises(ValueError, match="unknown class"):
            bk.add(bk.Finding("CLAUDE.md", "x", "y"), "newclass", 140,
                  paths=paths)

    def test_a_registered_class_needs_no_flag(self, ledger, paths):
        bk.add(bk.Finding("CLAUDE.md", "x", "y"), "figure", 140, paths=paths,
              new_class=True)
        bk.add(bk.Finding("CLAUDE.md", "x2", "y2"), "figure", 141, paths=paths)
        entries, _ = bk.parse_entries(ledger.read_text(encoding="utf-8"))
        assert len(entries) == 2


class TestMark:
    def test_it_refuses_leaving_an_aged_line_open(self, ledger, paths):
        ledger.write_text(TestSweepSurvival.THREE_SWEEPS + "\n", encoding="utf-8")
        key = bk.derive_key("CLAUDE.md", "a stale figure")
        before = ledger.read_text(encoding="utf-8")
        with pytest.raises(ValueError, match="refused"):
            bk.mark(key, "open", 5, paths=paths)
        assert ledger.read_text(encoding="utf-8") == before

    def test_it_resolves_the_same_aged_line(self, ledger, paths):
        ledger.write_text(TestSweepSurvival.THREE_SWEEPS + "\n", encoding="utf-8")
        key = bk.derive_key("CLAUDE.md", "a stale figure")
        bk.mark(key, "promoted", 5, detail="UX-1", paths=paths)
        entries, problems = bk.parse_entries(ledger.read_text(encoding="utf-8"))
        assert problems == []
        target = next(e for e in entries if e.what == "a stale figure")
        assert target.status == "promoted r5 UX-1"


class TestTheRealLedgerParses:
    def test_it(self):
        text = bk.LEDGER.read_text(encoding="utf-8")
        entries, problems = bk.parse_entries(text)
        assert problems == []
        assert bk.validate(text) == []
