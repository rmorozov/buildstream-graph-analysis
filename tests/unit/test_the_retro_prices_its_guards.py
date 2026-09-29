"""UX-1122: the retro's guard-price join lists a quiet or unowned file for
a scheduled lane or an owner, and never one named and recently caught."""

from tools import dev_guard_prices as prices_tool
from tools.dev_guard_prices import proposals

PRICES = {"tests/unit/test_recent.py": 5.0, "tests/unit/test_quiet.py": 3.0, "tests/unit/test_unnamed.py": 1.0}
GUARDS = {"test_recent.py": [("UX-1", "named")], "test_quiet.py": [("UX-2", "named")]}
CATCHES = {"tests/unit/test_recent.py": 149, "tests/unit/test_quiet.py": 138}


def test_only_the_quiet_and_the_unnamed_are_proposed():
    rows = proposals(PRICES, GUARDS, CATCHES, 150, n=10)
    assert [(r[0], r[4]) for r in rows] == [
        ("tests/unit/test_quiet.py", "scheduled lane"),
        ("tests/unit/test_unnamed.py", "needs owner"),
    ]


def test_a_named_unrecorded_file_is_never_a_scheduled_lane():
    prices = {**PRICES, "tests/unit/test_new.py": 9.0}
    guards = {**GUARDS, "test_new.py": [("UX-4", "named")]}
    rows = proposals(prices, guards, CATCHES, 150)
    assert "tests/unit/test_new.py" not in {r[0] for r in rows}
    assert "scheduled lane" not in [r[4] for r in proposals(prices, guards, {}, 150)]


def test_an_inferred_owner_reads_confirm_first():
    rows = proposals({"tests/a/test_x.py": 2.0}, {"test_x.py": [("UX-3", "inferred")]}, {}, 150)
    assert rows[0][4] == "confirm inferred"


def test_guard_map_reads_the_header_line(tmp_path):
    (tmp_path / "UX-9-x.md").write_text("# UX-9: x\n\n**Guard:** test_x.py\n\n## Motivation\n")
    assert prices_tool.guard_map(tmp_path) == {"test_x.py": [("UX-9", "named")]}
