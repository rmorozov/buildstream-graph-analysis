"""UX-703/UX-790: `dev_mutation.py`'s deterministic half - the part a
fast unit guard can hold, since a real `mutmut` run is a weekly-only
cost.

Four claims: the touched-module filter keeps only `bga`/`tools` Python
source (not a test, not a doc); the ledger groups one row per mutated
function rather than one per mutation site inside it; a second run's
section appends rather than overwriting the first's; `classify` turns
`mutmut results --all true`'s text into counts by verdict, `_CAUGHT`
applied.

`CENSUS_RESULTS` is a real `mutmut results --all true` capture:
`python3 tools/dev_mutation.py --module tools/dev_page_census.py
--max-children 4` (UX-790), matching `UX-703`'s Outcome for that
module (4 killed / 46 survivors of 50).
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import dev_mutation

CENSUS_RESULTS = """
    tools.dev_page_census.x_census__mutmut_1: survived
    tools.dev_page_census.x_census__mutmut_2: killed
    tools.dev_page_census.x_census__mutmut_3: killed
    tools.dev_page_census.x_census__mutmut_4: killed
    tools.dev_page_census.x_census__mutmut_5: killed
    tools.dev_page_census.x_census__mutmut_6: survived
    tools.dev_page_census.x_census__mutmut_7: survived
    tools.dev_page_census.x_census__mutmut_8: survived
    tools.dev_page_census.x_census__mutmut_9: survived
    tools.dev_page_census.x_census__mutmut_10: survived
    tools.dev_page_census.x_census__mutmut_11: survived
    tools.dev_page_census.x_census__mutmut_12: survived
    tools.dev_page_census.x_census__mutmut_13: survived
    tools.dev_page_census.x_main__mutmut_1: no tests
    tools.dev_page_census.x_main__mutmut_2: no tests
    tools.dev_page_census.x_main__mutmut_3: no tests
    tools.dev_page_census.x_main__mutmut_4: no tests
    tools.dev_page_census.x_main__mutmut_5: no tests
    tools.dev_page_census.x_main__mutmut_6: no tests
    tools.dev_page_census.x_main__mutmut_7: no tests
    tools.dev_page_census.x_main__mutmut_8: no tests
    tools.dev_page_census.x_main__mutmut_9: no tests
    tools.dev_page_census.x_main__mutmut_10: no tests
    tools.dev_page_census.x_main__mutmut_11: no tests
    tools.dev_page_census.x_main__mutmut_12: no tests
    tools.dev_page_census.x_main__mutmut_13: no tests
    tools.dev_page_census.x_main__mutmut_14: no tests
    tools.dev_page_census.x_main__mutmut_15: no tests
    tools.dev_page_census.x_main__mutmut_16: no tests
    tools.dev_page_census.x_main__mutmut_17: no tests
    tools.dev_page_census.x_main__mutmut_18: no tests
    tools.dev_page_census.x_main__mutmut_19: no tests
    tools.dev_page_census.x_main__mutmut_20: no tests
    tools.dev_page_census.x_main__mutmut_21: no tests
    tools.dev_page_census.x_main__mutmut_22: no tests
    tools.dev_page_census.x_main__mutmut_23: no tests
    tools.dev_page_census.x_main__mutmut_24: no tests
    tools.dev_page_census.x_main__mutmut_25: no tests
    tools.dev_page_census.x_main__mutmut_26: no tests
    tools.dev_page_census.x_main__mutmut_27: no tests
    tools.dev_page_census.x_main__mutmut_28: no tests
    tools.dev_page_census.x_main__mutmut_29: no tests
    tools.dev_page_census.x_main__mutmut_30: no tests
    tools.dev_page_census.x_main__mutmut_31: no tests
    tools.dev_page_census.x_main__mutmut_32: no tests
    tools.dev_page_census.x_main__mutmut_33: no tests
    tools.dev_page_census.x_main__mutmut_34: no tests
    tools.dev_page_census.x_main__mutmut_35: no tests
    tools.dev_page_census.x_main__mutmut_36: no tests
    tools.dev_page_census.x_main__mutmut_37: no tests
"""


def test_touched_modules_keeps_only_bga_and_tools_python_source(
        monkeypatch, tmp_path):
    for real in ("tools/dev_mutation.py", "bga/findings.py",
                 "tools/test_helper.py", "bga/__init__.py"):
        path = tmp_path / real
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    changed = [
        "tools/dev_mutation.py",
        "bga/findings.py",
        "docs/contributing/rules.md",
        "tests/unit/test_something.py",
        "tools/test_helper.py",
        "tools/does_not_exist.py",
        "bga/__init__.py",
    ]
    monkeypatch.setattr(dev_mutation, "REPO", tmp_path)
    monkeypatch.setattr(dev_mutation.dt, "changed_files", lambda base: changed)
    assert dev_mutation.touched_modules("HEAD~1") == [
        "bga/__init__.py", "bga/findings.py", "tools/dev_mutation.py"]


def test_render_row_groups_by_function_not_by_mutation_site():
    run = {
        "module": "tools/example_widget.py",
        "guards": ["tests/unit/test_a.py"],
        "survivors": [
            ("tools.example_widget.x_grind__mutmut_1", "survived"),
            ("tools.example_widget.x_grind__mutmut_2", "survived"),
            ("tools.example_widget.x_run__mutmut_1", "no tests"),
        ],
    }
    row = dev_mutation.render_row(run)
    lines = [line for line in row.splitlines() if line]
    assert len(lines) == 2, f"one row per function, not per site: {lines}"
    assert "x2" in [l for l in lines if "x_grind" in l][0]
    assert "x_run" in row and "no tests" in row


def test_no_guard_naming_the_module_is_its_own_row():
    run = {"module": "tools/orphan.py", "guards": [], "survivors": []}
    row = dev_mutation.render_row(run)
    assert "no test names this module" in row


def test_write_ledger_appends_a_new_dated_section(tmp_path, monkeypatch):
    ledger = tmp_path / "mutation.md"
    monkeypatch.setattr(dev_mutation, "LEDGER", ledger)
    run = {"module": "tools/a.py", "guards": ["tests/unit/test_a.py"],
           "survivors": [("tools.a.x_f__mutmut_1", "survived")]}
    dev_mutation.write_ledger("2026-01-01", [run], dry_run=False)
    dev_mutation.write_ledger("2026-01-08", [run], dry_run=False)
    text = ledger.read_text(encoding="utf-8")
    assert text.count("## 2026-01-01") == 1
    assert text.count("## 2026-01-08") == 1
    assert text.index("## 2026-01-01") < text.index("## 2026-01-08")


def test_classify_matches_ux_703s_captured_census_run():
    counts = dev_mutation.classify(CENSUS_RESULTS)
    assert counts == {
        "survived": 9, "killed": 4, "no tests": 37,
        "caught": 4, "survivors": 46,
    }


def test_classify_applies_caught_to_the_verdict_it_names():
    sample = "\n".join([
        "mod.x_f__mutmut_1: killed",
        "mod.x_f__mutmut_2: timeout",
        "mod.x_f__mutmut_3: survived",
    ])
    counts = dev_mutation.classify(sample)
    assert counts["caught"] == 1, "only killed is in _CAUGHT by default"
    assert counts["survivors"] == 2, "timeout and survived both count"
