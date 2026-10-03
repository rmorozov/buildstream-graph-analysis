"""UX-1167: each row of cli.md's ceilings table states its constant's value.

`test_the_ceilings_reach_a_reader.py` finds a row per bound, but not its
number: `PAGE_BUDGET_B` moved 150,000 -> 160,000 and a row still saying
150,000 B passed every guard.
"""

import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests.unit.test_the_ceilings_reach_a_reader import _table_rows
from tools import bga_view as view

#: The units the table writes a value in, as a multiplier.
_UNITS = {"B": 1, "KiB": 1024, "MiB": 1024**2, "GiB": 1024**3, "tracks": 1}


def _stated(row: str) -> int:
    """The second column of a table row, as the integer it names."""
    cell = row.split("|")[2].strip()
    found = re.fullmatch(r"([\d,]+)\s+(\w+)", cell)
    assert found and found.group(2) in _UNITS, f"unreadable value {cell!r} in {row[:80]!r}"
    return int(found.group(1).replace(",", "")) * _UNITS[found.group(2)]


def test_each_row_states_the_value_its_constant_holds():
    rows = _table_rows()
    assert rows, "no ceilings rows read - the table scan is broken"
    wrong = {
        name: (_stated(row), getattr(view, name)) for name, row in rows.items() if _stated(row) != getattr(view, name)
    }
    assert wrong == {}, (
        f"docs/guides/viewer.md states a bound the code does not hold, {{name: (stated, code)}}: {wrong}"
    )
