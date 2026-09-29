"""UX-1129: a key present both open and swept reads as swept; `--collapse` leaves one line."""

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import dev_bookkeeping as bk
import dev_close_task as close

OPEN = "- r140 · open · figure · `CLAUDE.md` · a stale figure · `x --check`"
SWEPT = "- r140 · swept r152 UX-1 · figure · `CLAUDE.md` · a stale figure · `x --check`"


def _paths(tmp_path, *lines):
    ledger = tmp_path / "bookkeeping.md"
    ledger.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return bk.Paths(ledger, tmp_path)


def test_the_open_copy_of_a_swept_key_is_not_listed(tmp_path):
    assert bk.sweep(_paths(tmp_path, OPEN, SWEPT)) == []
    assert bk.sweep(_paths(tmp_path, SWEPT, OPEN)) == []


def test_a_lone_open_line_is_still_listed(tmp_path):
    assert len(bk.sweep(_paths(tmp_path, OPEN))) == 1


def test_collapse_leaves_the_resolved_line_only(tmp_path):
    paths = _paths(tmp_path, OPEN, SWEPT)
    assert len(bk.collapse(paths)) == 1
    assert paths.ledger.read_text(encoding="utf-8") == SWEPT + "\n"


def test_shape_write_goes_before_reading_and_replaces_in_place():
    head = "# UX-1: t\n\n**Priority:** High | **Status:** X | **Reading:** container\n"
    out = close.with_shape(head, "bounded")
    assert "| **Shape:** bounded | **Reading:** container" in out
    again = close.with_shape(out, "judgement")
    assert "| **Shape:** judgement | **Reading:** container" in again
    assert again.count("**Shape:**") == 1
