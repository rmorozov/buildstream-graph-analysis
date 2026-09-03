"""docs/guides/cli.md's Exit Codes list is `bga/exceptions.py`'s codes.

UX-574: the list said `1: ... invalid arguments` while argparse exited
`2`, the code the same list gives to ingestion failure. Three claims:
the listed codes are the registry's, `bga/cli.py`'s own constants are
the registry's, and a bad flag really exits the code the row for
invalid arguments carries.
"""
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CLI_GUIDE = REPO / "docs" / "guides" / "cli.md"

# Only the list under `## Exit Codes` is the subject; the prose above it
# and every other section is argument and is not read.
_ROW = re.compile(r"^- `(\d+)`:")


def _exit_code_rows() -> dict[int, str]:
    lines = CLI_GUIDE.read_text().splitlines()
    start = lines.index("## Exit Codes")
    rows: dict[int, str] = {}
    code = None
    for line in lines[start + 1:]:
        if line.startswith("## "):
            break
        m = _ROW.match(line)
        if m:
            code = int(m.group(1))
            rows[code] = line
        elif code is not None and line.startswith("  "):
            rows[code] += "\n" + line
        elif not line.strip():
            continue
        else:
            code = None
    return rows


def test_the_listed_codes_are_the_registrys():
    from bga.exceptions import EXIT_CODES

    assert set(_exit_code_rows()) == set(EXIT_CODES.values())


def test_the_cli_constants_are_the_registrys():
    from bga import cli
    from bga.exceptions import (
        EXIT_EFFICIENCY_REGRESSION,
        EXIT_MISMATCHED_RUNS,
        EXIT_REGRESSION,
        EXIT_SIGNAL_UNAVAILABLE,
    )

    assert cli.EXIT_CODE_REGRESSION == EXIT_REGRESSION
    assert cli.EXIT_CODE_EFFICIENCY_REGRESSION == EXIT_EFFICIENCY_REGRESSION
    assert cli.EXIT_CODE_MISMATCHED_RUNS == EXIT_MISMATCHED_RUNS
    assert cli.EXIT_CODE_SIGNAL_UNAVAILABLE == EXIT_SIGNAL_UNAVAILABLE


def test_a_bad_flag_exits_the_code_the_row_for_invalid_arguments_carries(tmp_path):
    rows = _exit_code_rows()
    named = [code for code, text in rows.items() if "invalid arguments" in text]
    assert len(named) == 1, named
    documented = named[0]

    result = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", "--bogus", str(tmp_path)],
        capture_output=True, text=True, cwd=REPO,
    )
    assert "unrecognized arguments: --bogus" in result.stderr
    assert result.returncode == documented, result.stderr
