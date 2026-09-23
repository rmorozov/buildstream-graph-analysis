"""UX-932: `--check --write --scenarios <tmp>` writes and deletes only in `<tmp>`.

The area pages are written, and pages no area keeps are deleted, under
`AREA_PAGES`. It was `REPO`-based while `--scenarios` moved only what the
tool reads, so a sandboxed run rewrote the real pages and a fixture
narrower than the tree deleted them.
"""
import hashlib
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import dev_close_task as close_task
from test_an_unmerged_index_derives_nothing import README, TASK


def _listing(directory):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.glob("*.md"))}


def _narrow_sandbox(tmp_path):
    """One task file under area `tools`: narrower than any real tree."""
    scenarios = tmp_path / "sandbox/scenarios"
    scenarios.mkdir(parents=True)
    (scenarios / "UX-0001-a-row.md").write_text(TASK.format(line="x"),
                                                encoding="utf-8")
    (scenarios / "README.md").write_text(README, encoding="utf-8")
    (scenarios / "closed.md").write_text("# Closed\n", encoding="utf-8")
    return scenarios


def _decoy(tmp_path):
    """Stands in for the repository's pages: `tools.md` a sandboxed write
    would rewrite, `bga.md` a narrow one would delete."""
    decoy = tmp_path / "repo/docs/backlog/areas"
    decoy.mkdir(parents=True)
    (decoy / "tools.md").write_text("the real tools page\n", encoding="utf-8")
    (decoy / "bga.md").write_text("the real bga page\n", encoding="utf-8")
    return decoy


class TestASandboxedWriteStaysInTheSandbox:

    def test_the_default_is_the_repository_s_pages(self):
        assert close_task.AREA_PAGES == REPO / "docs/backlog/areas"

    def test_a_narrow_sandbox_adds_removes_and_rewrites_nothing_outside(
            self, tmp_path, monkeypatch, capsys):
        scenarios = _narrow_sandbox(tmp_path)
        decoy = _decoy(tmp_path)
        # `main` rebinds these with `global`; setattr first so they are restored.
        for name in ("SCENARIOS", "INDEX", "CLOSED"):
            monkeypatch.setattr(close_task, name, getattr(close_task, name))
        # Both spellings of the old constant land in the decoy, never the tree.
        monkeypatch.setattr(close_task, "REPO", tmp_path / "repo")
        monkeypatch.setattr(close_task, "AREA_PAGES", decoy)
        before = _listing(decoy)

        close_task.main(["--check", "--write", "--scenarios", str(scenarios)])
        capsys.readouterr()

        assert _listing(decoy) == before, (
            "a sandboxed `--write` added, removed or rewrote a page outside "
            "the sandbox")
        inside = tmp_path / "sandbox/areas"
        assert sorted(_listing(inside)) == ["tools.md"], sorted(_listing(inside))
        assert "UX-1" in (inside / "tools.md").read_text(encoding="utf-8")
