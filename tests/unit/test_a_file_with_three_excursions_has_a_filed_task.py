"""`UX-691`: a file the flake ledger excurses on three times names itself.

Two synthetic excursions of one file, then a third - the Acceptance
Test's own case - against a fixture scenarios directory that files
none of them; the real ledger is checked too, so a round that lets a
file reach three excursions unfiled is caught here rather than read
off whichever task file happened to record the third.
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import dev_flake_census as census


def _ledger(*files, declared=None):
    return {"entries": [{"file": name, "run_id": str(i), "shift": 1.7,
                         "confirmed": False}
                        for i, name in enumerate(files)],
            "declared": declared or {}}


def test_two_excursions_are_not_yet_named(tmp_path):
    document = _ledger("tests/unit/test_x.py", "tests/unit/test_x.py")
    assert census.unaccounted(document, scenarios=tmp_path) == []


def test_a_third_excursion_names_the_file(tmp_path):
    document = _ledger(*(["tests/unit/test_x.py"] * 3))
    assert census.unaccounted(document, scenarios=tmp_path) == [
        ("tests/unit/test_x.py", 3)]


def test_a_filed_task_clears_it(tmp_path):
    (tmp_path / "UX-000-x.md").write_text(
        "# UX-000: x\n\n**Flake:** tests/unit/test_x.py\n", encoding="utf-8")
    document = _ledger(*(["tests/unit/test_x.py"] * 3))
    assert census.unaccounted(document, scenarios=tmp_path) == []


def test_a_longer_path_containing_the_name_does_not_clear_it(tmp_path):
    """`UX-785`: a `**Flake:**` field names `tests/unit/old_test_x.py`,
    a different file whose path merely contains `test_x.py` as a
    substring - not the same file, and not a match."""
    (tmp_path / "UX-000-x.md").write_text(
        "# UX-000: x\n\n**Flake:** tests/unit/old_test_x.py\n",
        encoding="utf-8")
    document = _ledger(*(["test_x.py"] * 3))
    assert census.unaccounted(document, scenarios=tmp_path) == [
        ("test_x.py", 3)]


def test_a_mention_in_prose_does_not_clear_it(tmp_path):
    """`UX-785`: a task's header names the file only in a `**Flake:**`
    field - being discussed in an unrelated closed task's prose is not
    that, however specific the mention."""
    (tmp_path / "UX-000-x.md").write_text(
        "# UX-000: something else\n\n**Status:** closed\n\n"
        "## Motivation\n\nthis broke tests/unit/test_x.py once.\n",
        encoding="utf-8")
    document = _ledger(*(["tests/unit/test_x.py"] * 3))
    assert census.unaccounted(document, scenarios=tmp_path) == [
        ("tests/unit/test_x.py", 3)]


def test_a_declared_reason_clears_it_without_a_filed_task(tmp_path):
    document = _ledger(*(["tests/unit/test_x.py"] * 3),
                       declared={"tests/unit/test_x.py": "known: fixture I/O"})
    assert census.unaccounted(document, scenarios=tmp_path) == []


def test_only_the_named_file_is_cleared(tmp_path):
    """A declared reason on one file must not silence another's count."""
    document = _ledger(*(["tests/unit/test_x.py"] * 3),
                       *(["tests/unit/test_y.py"] * 3),
                       declared={"tests/unit/test_x.py": "known"})
    assert census.unaccounted(document, scenarios=tmp_path) == [
        ("tests/unit/test_y.py", 3)]


def test_the_real_ledger_has_no_unfiled_repeat_excursion():
    """The guard CI actually runs: today's committed ledger, unfixtured."""
    assert census.unaccounted(census.load()) == []
