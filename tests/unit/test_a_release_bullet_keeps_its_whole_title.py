"""UX-1394: `bga release-notes` does not cut a linked title at a `;` inside it."""

import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import bga_release_notes

TITLE = "`viewer.md` says staleness is not a version comparison; `UX-1367` made it one"
LINKED = f"[{TITLE}](UX-1392-x.md)"


def test_a_linked_title_with_a_semicolon_is_kept_whole_and_closed():
    assert bga_release_notes._first_sentence(LINKED) == LINKED


def test_a_plain_summary_still_ends_at_its_first_clause():
    assert bga_release_notes._first_sentence("one clause; another") == "one clause;"


def test_a_long_linked_title_is_shortened_inside_its_brackets():
    out = bga_release_notes._first_sentence(f"[{'word ' * 80}](u.md)")
    assert out.startswith("[") and out.endswith("…](u.md)")
