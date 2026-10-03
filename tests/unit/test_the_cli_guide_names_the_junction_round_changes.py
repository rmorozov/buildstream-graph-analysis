"""`cli.md` carries a sentence for each of round 170's four undocumented changes (UX-1334)."""

from pathlib import Path

CLI = (Path(__file__).resolve().parents[2] / "docs" / "guides" / "cli.md").read_text()


def _section(title: str) -> str:
    start = CLI.index(title)
    end = CLI.find("\n## ", start + 1)
    return CLI[start : end if end != -1 else len(CLI)]


def test_the_snapshot_section_names_the_wrapper_script_capture():
    assert "UX-1322" in _section("## `bga snapshot`")


def test_the_doctor_section_names_the_container_and_junction_checks():
    section = _section("## `bga doctor`")
    assert "UX-1328" in section and "UX-1331" in section


def test_the_cache_logs_section_names_the_junction_trees():
    assert "UX-1325" in _section("## `bga cache-logs`")


def test_the_guide_names_the_start_here_block():
    assert "UX-1329" in CLI
