"""UX-709: several ids close in one `--move`, on a copy of the backlog.

Round 80's batch of 24 was 24 invocations and 24 count derivations.
This holds the three-part claim: both markers flip, both rows land in
`closed.md`, the counts sentence is derived once - and a missing note
refuses the whole batch before anything is written.
"""
import pathlib
import shutil
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import dev_close_task as close_task


def _run(*argv):
    return subprocess.run(
        [sys.executable, str(REPO / "tools/dev_close_task.py"), *argv],
        capture_output=True, text=True, cwd=str(REPO), timeout=120)


def _two_open_rows(tmp_path):
    """A copy of the backlog with two synthetic open rows, each with an
    Outcome section already written - `move()`'s other refusal is not
    this guard's claim."""
    scenarios = tmp_path / "scenarios"
    shutil.copytree(REPO / "docs/backlog/scenarios", scenarios)
    ids = (("UX-9801", "UX-9801-a-batch-row-one"),
           ("UX-9802", "UX-9802-a-batch-row-two"))
    for uid, slug in ids:
        (scenarios / f"{slug}.md").write_text(
            f"# {uid}: a row this guard wrote\n\n"
            f"**Priority:** Low | **Status:** \U0001f534 Not Started | "
            f"**Serves:** nobody | **Topic:** guards\n\n"
            f"## Outcome\n\nmeasured.\n", encoding="utf-8")
    readme = scenarios / "README.md"
    text = readme.read_text(encoding="utf-8")
    marker = "\n## UX-333"
    assert marker in text, "the open table's end moved"
    rows = "".join(
        f"| {uid} | [a batch row]({slug}.md) | guards | Low | — | "
        f"\U0001f534 |\n" for uid, slug in ids)
    readme.write_text(text.replace(marker, "\n" + rows + marker, 1),
                      encoding="utf-8")
    return ids, scenarios


class TestABatchClosesInOneMove:

    def test_both_markers_flip_both_rows_move_counts_derive_once(
            self, tmp_path, monkeypatch):
        ids, scenarios = _two_open_rows(tmp_path)
        done = _run("--move", ids[0][0], "--note", "first found",
                    ids[1][0], "--note", "second found",
                    "--scenarios", str(scenarios))
        assert done.returncode == 0, done.stdout + done.stderr

        readme = (scenarios / "README.md").read_text(encoding="utf-8")
        closed = (scenarios / "closed.md").read_text(encoding="utf-8")
        for uid, slug in ids:
            assert f"| {uid} |" not in readme, f"{uid} still in the open table"
            assert f"| {uid} |" in closed, f"{uid} missing from closed.md"
            status = (scenarios / f"{slug}.md").read_text(encoding="utf-8")
            assert "**Status:** \U0001f7e2 Done" in status, uid

        # UX-501: derived once, not per id - the header the rows now say.
        # `monkeypatch` restores the module globals on teardown, so this
        # subprocess-shaped assertion can't leak into another file's run.
        monkeypatch.setattr(close_task, "SCENARIOS", scenarios)
        monkeypatch.setattr(close_task, "INDEX", scenarios / "README.md")
        monkeypatch.setattr(close_task, "CLOSED", scenarios / "closed.md")
        sentence, table = close_task.index_header()
        assert sentence in readme
        assert table in readme

    def test_a_missing_note_refuses_the_whole_batch(self, tmp_path):
        ids, scenarios = _two_open_rows(tmp_path)
        before = (scenarios / "README.md").read_bytes()
        done = _run("--move", ids[0][0], "--note", "first found",
                    ids[1][0], "--scenarios", str(scenarios))
        assert done.returncode != 0
        assert ids[1][0] in done.stderr
        assert (scenarios / "README.md").read_bytes() == before, (
            "a refused batch still wrote to the index")
        assert f"| {ids[0][0]} |" not in (
            scenarios / "closed.md").read_text(encoding="utf-8"), (
            "the first id closed before the batch was refused")

    def test_the_same_id_twice_is_refused_not_closed_twice(self, tmp_path):
        ids, scenarios = _two_open_rows(tmp_path)
        uid = ids[0][0]
        done = _run("--move", uid, "--note", "first", uid, "--note", "second",
                    "--scenarios", str(scenarios))
        assert done.returncode != 0
        assert uid in done.stderr
        closed = (scenarios / "closed.md").read_text(encoding="utf-8")
        assert closed.count(f"| {uid} |") == 0, (
            "a repeated id wrote a closed row before being refused")
