"""UX-996: a derived figure is computed where it is read, never committed.

19 catch-up merges since 2026-09-10 conflicted on 47 paths, 40 of them
registers or derived documents - `dev_close_task.py --check --write`
and `dev_touching.py --spread --write` re-derived only the closing
branch's own view. So neither writes any more: the counts sentence,
the topic table, `architecture.md`'s backlog count and the touch-map
spread are printed where a reader needs them, and `docs/backlog/areas/`
- the one *directory* of derived pages - is `git rm`ed rather than
regenerated. `closed.md` gets `merge=union` (`.gitattributes`): every
pair of closes collides on its last row, and union keeps both.
"""
import pathlib
import re
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import dev_close_task as close_task

#: The process documents a session reads, plus the three sites that
#: used to carry a committed figure - the same population
#: `test_the_process_documents_derive_their_figures.py` reads, widened
#: by the ones outside `.claude/`/`docs/contributing/` (`UX-996`).
#: The backlog itself is excluded: `closed.md` and a task file quote a
#: past measurement verbatim, as history (`UX-769`), and `docs/audits/`
#: round documents do the same.
_EXTRA = ("docs/design/architecture.md", "docs/backlog/scenarios/README.md",
         "CLAUDE.md")

SENTENCE_RE = re.compile(r"^\d+ scenarios: \*\*\d+ open\*\*, \d+ closed\.$",
                         re.M)
TOPIC_TABLE_RE = re.compile(r"^\| Topic \| Open \| Total \|\n\|[-| ]+\|\n"
                            r"(?:\|.*\n)+", re.M)
BACKLOG_COUNT_RE = re.compile(r"\d+ `docs/backlog/(?:scenarios|tasks)/` files")
SPREAD_FIGURE_RE = re.compile(r"\d+-\d+ of \d+ test files")


def _population():
    out = subprocess.run(["git", "ls-files"], cwd=REPO, check=True,
                         capture_output=True, text=True).stdout.splitlines()
    return [REPO / p for p in out
            if (re.fullmatch(r"\.claude/.+\.md", p)
                or re.fullmatch(r"docs/contributing/[^/]+\.md", p)
                or p in _EXTRA)]


def _hits(pattern):
    return [p for p in _population()
            if pattern.search(p.read_text(encoding="utf-8"))]


class TestNoTrackedDocumentCommitsADerivedFigure:

    def test_the_population_is_not_empty(self):
        assert len(_population()) >= 10, _population()

    def test_no_counts_sentence(self):
        assert _hits(SENTENCE_RE) == [], (
            "the counts sentence is committed; `dev_close_task.py "
            f"--counts` prints it: {_hits(SENTENCE_RE)}")

    def test_no_topic_table(self):
        assert _hits(TOPIC_TABLE_RE) == [], (
            "the topic table is committed; `dev_close_task.py --counts` "
            f"prints it: {_hits(TOPIC_TABLE_RE)}")

    def test_no_backlog_count(self):
        assert _hits(BACKLOG_COUNT_RE) == [], (
            "architecture.md's backlog count is committed: "
            f"{_hits(BACKLOG_COUNT_RE)}")

    def test_no_spread_figure(self):
        assert _hits(SPREAD_FIGURE_RE) == [], (
            "the touch-map spread is committed; `dev_touching.py "
            f"--spread` prints it: {_hits(SPREAD_FIGURE_RE)}")


class TestAreaPagesAreNeverCommitted:

    def test_git_ls_files_carries_no_area_page(self):
        out = subprocess.run(["git", "ls-files", "docs/backlog/areas"],
                             cwd=REPO, check=True, capture_output=True,
                             text=True).stdout
        assert out == "", f"a committed area page survives: {out}"


class TestCountsPrintsTheDerivation:

    def test_counts_prints_index_header(self):
        sentence, table = close_task.index_header()
        done = subprocess.run(
            [sys.executable, str(REPO / "tools/dev_close_task.py"),
             "--counts"], cwd=REPO, capture_output=True, text=True,
            timeout=60)
        assert done.returncode == 0, done.stdout + done.stderr
        assert sentence in done.stdout, done.stdout
        assert table in done.stdout, done.stdout


#: The task file this item introduces, so two branches can each close a
#: real (Outcome-carrying) row without depending on the live backlog's
#: current open table - a non-adjacent pair, by row index.
_TASK = ("# UX-{n}: a batch row\n\n"
        "**Priority:** Low | **Status:** \U0001f534 Not Started | "
        "**Serves:** nobody | **Topic:** guards | **Shape:** judgement\n\n"
        "## Outcome\n\nmeasured.\n")


def _git(repo, *argv, check=True):
    return subprocess.run(["git", *argv], cwd=repo, check=check,
                          capture_output=True, text=True)


def _scratch_repo(tmp_path):
    """A throwaway backlog: two open rows, several apart, so the two
    branches' row edits are non-adjacent hunks."""
    repo = tmp_path / "repo"
    scenarios = repo / "docs/backlog/scenarios"
    scenarios.mkdir(parents=True)
    rows = []
    for n in (9801, 9802, 9803, 9804, 9805):
        (scenarios / f"UX-{n}-a-batch-row.md").write_text(
            _TASK.format(n=n), encoding="utf-8")
        rows.append(f"| UX-{n} | [a batch row](UX-{n}-a-batch-row.md) | "
                    f"guards | Low | — | \U0001f534 |")
    (scenarios / "README.md").write_text(
        "# Index\n\n## Open scenarios\n\n" + "\n".join(rows) + "\n",
        encoding="utf-8")
    (scenarios / "closed.md").write_text(
        "# Closed\n\n| UX-1 | done row | guards | Low | — | "
        "\U0001f7e2 Done — x | [UX-1](UX-1.md) |\n", encoding="utf-8")
    shutil.copyfile(REPO / ".gitattributes", repo / ".gitattributes")
    for argv in (["init", "-q", "-b", "main"],
                 ["config", "user.email", "a@b"],
                 ["config", "user.name", "a"],
                 ["add", "-f", "docs", ".gitattributes"],
                 ["commit", "-qm", "base"]):
        _git(repo, *argv)
    return repo, scenarios


def _move(scenarios, uid, note):
    return subprocess.run(
        [sys.executable, str(REPO / "tools/dev_close_task.py"), uid,
         "--move", "--note", note, "--scenarios", str(scenarios)],
        cwd=scenarios, capture_output=True, text=True, timeout=60)


class TestTwoClosesMergeCleanly:
    """The Acceptance Test: two scratch branches off one base, each
    closing a different row not adjacent in the open table, merge with
    no conflict and a green `--check`."""

    def test_two_non_adjacent_closes_merge_and_check_green(self, tmp_path):
        repo, scenarios = _scratch_repo(tmp_path)
        _git(repo, "checkout", "-qb", "close-a")
        moved = _move(scenarios, "UX-9801", "first found")
        assert moved.returncode == 0, moved.stdout + moved.stderr
        _git(repo, "commit", "-qam", "close UX-9801")

        _git(repo, "checkout", "-q", "main")
        _git(repo, "checkout", "-qb", "close-b")
        moved = _move(scenarios, "UX-9805", "second found")
        assert moved.returncode == 0, moved.stdout + moved.stderr
        _git(repo, "commit", "-qam", "close UX-9805")

        # Sequential, not octopus: a single `merge a b` skips path-level
        # merge drivers (`.gitattributes`' `merge=union`) on anything but
        # a trivial merge, which would hide the property this proves.
        _git(repo, "checkout", "-q", "main")
        _git(repo, "merge", "-q", "close-a")
        merged = _git(repo, "merge", "-q", "close-b", check=False)
        assert merged.returncode == 0, merged.stdout + merged.stderr

        checked = subprocess.run(
            [sys.executable, str(REPO / "tools/dev_close_task.py"),
             "--check", "--scenarios", str(scenarios)],
            cwd=repo, capture_output=True, text=True, timeout=60)
        assert checked.returncode == 0, checked.stdout + checked.stderr


if __name__ == "__main__":  # pragma: no cover
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
