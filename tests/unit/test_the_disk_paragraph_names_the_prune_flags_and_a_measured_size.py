"""UX-1306: real-project.md's disk paragraph names the prune flags `bga snapshot --help` has and a size that is the tree."""

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUIDE = ROOT / "docs/guides/real-project.md"
DISK = "### Disk"


def _squash(text: str) -> str:
    return " ".join(text.split())


def _section(heading: str) -> str:
    text = GUIDE.read_text(encoding="utf-8")
    assert heading in text, f"real-project.md lost `{heading}`"
    return _squash(text.split(heading, 1)[1].split("\n---\n", 1)[0].split("\n## ", 1)[0])


def _help(*argv: str) -> str:
    env = {"PYTHONPATH": str(ROOT), "PATH": "/usr/bin:/bin", "COLUMNS": "200"}
    done = subprocess.run([sys.executable, "-m", "bga.cli", *argv, "--help"], capture_output=True, text=True, env=env)
    return _squash(done.stdout)


def test_the_disk_paragraph_names_the_prune_flags_and_a_figure_that_is_the_tree():
    section = _section(DISK)
    text = _help("snapshot")
    for flag in ("--prune", "--keep", "--older-than", "--max-store", "--dry-run"):
        assert flag in text, f"bga snapshot --help lost {flag}"
        assert flag in section, f"the disk paragraph does not name {flag}"
    fixture = ROOT / "tests/fixtures/macro_micro"
    size = subprocess.run(["du", "-sb", str(fixture)], capture_output=True, text=True, check=True).stdout.split()[0]
    assert re.search(rf"\b{size}\s+tests/fixtures/macro_micro", section), (
        f"the guide's figure is not the fixture's {size} bytes"
    )


def test_the_readme_points_at_the_disk_paragraph():
    assert "docs/guides/real-project.md#disk" in (ROOT / "README.md").read_text(encoding="utf-8")


def test_the_snapshot_figure_is_the_skills_and_the_fixture_is_labelled_not_a_snapshot():
    section = _section(DISK)
    skill = (ROOT / ".claude/skills/measure/SKILL.md").read_text(encoding="utf-8")
    assert "311 KB" in skill and "311 KB" in section
    assert "neither is a snapshot" in section and "a committed fixture" in section
    assert "per element" not in section


def test_the_husk_rule_is_the_one_the_prune_code_has():
    section = _section(DISK)
    source = (ROOT / "tools/bga_snapshot.py").read_text(encoding="utf-8")
    assert "husks = [s for s in snapshots if not run_store.has_run(s)]" in source
    assert "doomed = list(husks)" in source
    assert "always deletes a snapshot that has no `run/` directory, whatever `--keep` says" in section
