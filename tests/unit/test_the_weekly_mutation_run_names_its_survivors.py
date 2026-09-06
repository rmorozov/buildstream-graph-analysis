"""UX-703: `dev_mutation.py`'s deterministic half - the part a fast
unit guard can hold, since a real `mutmut` run is a weekly-only cost.

Three claims: the touched-module filter keeps only `bga`/`tools`
Python source (not a test, not a doc); the ledger groups one row per
mutated function rather than one per mutation site inside it; a second
run's section appends rather than overwriting the first's.
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import dev_mutation


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
