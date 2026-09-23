"""`UX-942`: a changed record selects the guards that load it through a tool.

The real ledger and CI reference, then a synthetic tool and tests: the
constant, a parameter defaulting to it, a call reaching one, and the
`tmp_path` and bare-import cases that must not select.
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import _record_readers
import dev_touching

LEDGER_GUARD = "tests/unit/test_a_file_with_three_excursions_has_a_filed_task.py"
SHAPE_GUARD = "tests/unit/test_the_suite_holds_its_shape_budget.py"

TOOL = '''
import pathlib
REPO = pathlib.Path(__file__).resolve().parents[1]
TESTS = REPO / "tests"
RECORD = TESTS / "rec.json"
ELSEWHERE = REPO / "docs" / "rec.json"

def load(path=RECORD):
    return path.read_text()

def check(ci=None):
    return load() if ci is None else ci

def inline():
    return (REPO / "tests/rec.json").read_text()

def unrelated(x):
    return x
'''


def _selects(body, record="tests/rec.json"):
    test = "from tools import dev_rec as rec\n\n" + body + "\n"
    return record_readers_of(record, test)


def record_readers_of(record, test):
    found = _record_readers.record_readers(
        record, {"dev_rec": TOOL}, {"tests/unit/test_x.py": test})
    return found.get("tests/unit/test_x.py", [])


def test_the_ledger_selects_the_guard_that_loads_it():
    """The Acceptance Test: the ledger alone selects its census guard."""
    selected, why = dev_touching.select(["tests/flake_ledger.json"])
    assert LEDGER_GUARD in selected, why
    assert any("dev_flake_census.load()" in r for r in why[LEDGER_GUARD])


def test_the_reference_selects_a_guard_two_calls_away():
    """`ledger_problems()` -> `browser_share_pct` -> `ci_seconds()`."""
    selected, why = dev_touching.select(["tests/ci_reference.json"])
    assert SHAPE_GUARD in selected, why


def test_a_call_on_the_default_path_selects():
    assert _selects("rec.load()") == ["dev_rec.load()"]


def test_a_call_on_its_own_path_does_not():
    assert _selects("rec.load(tmp_path / 'rec.json')") == []
    assert _selects("rec.load(path=tmp_path)") == []


def test_the_constant_itself_selects():
    assert _selects("rec.RECORD.read_text()") == ["dev_rec.RECORD"]


def test_a_function_calling_the_loader_selects():
    assert _selects("rec.check()") == ["dev_rec.check()"]


def test_a_parameterless_body_spelling_the_path_selects():
    assert _selects("rec.inline()") == ["dev_rec.inline()"]


def test_importing_the_tool_is_not_reading_the_record():
    """The widest derivation's proxy: the module names the record, this
    test never reaches it."""
    assert _selects("rec.unrelated(1)") == []


def test_a_same_named_record_elsewhere_is_another_record():
    assert _selects("rec.ELSEWHERE.read_text()") == []
    assert _selects("rec.ELSEWHERE.read_text()",
                    record="docs/rec.json") == ["dev_rec.ELSEWHERE"]


def test_a_test_mid_edit_is_skipped_not_fatal():
    assert _selects("rec.load(\n") == []


def test_a_name_imported_from_the_tool_selects():
    test = "from tools.dev_rec import load as fetch\n\nfetch()\n"
    assert record_readers_of("tests/rec.json", test) == ["dev_rec.load()"]
