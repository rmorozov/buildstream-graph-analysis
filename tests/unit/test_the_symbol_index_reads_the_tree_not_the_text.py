"""`UX-700`: the symbol index is AST, not grep, and the difference shows.

A synthetic package under `tmp_path`, with `dev_symbols`'s own `REPO`
and `DIRS` monkeypatched to it so the walk covers exactly this fixture.
`target_fn` is named inside a string and inside a docstring, and called
for real once; `unused_fn` is never referenced; `pkg.a` is imported both
ways, from two different files.
"""
import json
import pathlib

from tools import dev_symbols as sym

PKG = """\
\"\"\"Module a: one referenced def, one dead one.\"\"\"


def target_fn():
    return 1


def unused_fn():
    return 2


STRING_CALL = "target_fn() as text, never a Call node"


def has_docstring_mention():
    \"\"\"Mentions target_fn() here, in prose, not a call.\"\"\"
    return 0


def real_caller():
    return target_fn()


def imported_only_fn():
    return 3


def attr_called_fn():
    return 4
"""

IMPORT_FORM = "import pkg.a\n"
FROM_FORM = "from pkg.a import target_fn\n"
FROM_FORM_UNCALLED = "from pkg.a import imported_only_fn\n"
# No `from` import anywhere in the fixture reaches `attr_called_fn` - its only
# path to "referenced" is the attribute call below, isolating that branch.
ATTR_CALL_FORM = "import pkg.a\n\n\ndef caller():\n    return pkg.a.attr_called_fn()\n"
DUNDER_FORM = '__all__ = ["nothing_here"]\n'


def _build(tmp_path):
    pkg = tmp_path / "pkg"
    pkg.mkdir()
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "a.py").write_text(PKG, encoding="utf-8")
    (pkg / "b.py").write_text(IMPORT_FORM, encoding="utf-8")
    (pkg / "c.py").write_text(FROM_FORM, encoding="utf-8")
    (pkg / "d.py").write_text(FROM_FORM_UNCALLED, encoding="utf-8")
    (pkg / "e.py").write_text(ATTR_CALL_FORM, encoding="utf-8")
    (pkg / "f.py").write_text(DUNDER_FORM, encoding="utf-8")
    return tmp_path


def _point_at(monkeypatch, tmp_path):
    monkeypatch.setattr(sym, "REPO", tmp_path)
    monkeypatch.setattr(sym, "DIRS", ("pkg",))


def test_a_string_and_a_docstring_are_not_callers(tmp_path, monkeypatch):
    _point_at(monkeypatch, _build(tmp_path))
    rows = sym.find_callers("target_fn", include_tests=False)
    assert rows == [("pkg/a.py:21",)], rows


def test_importers_finds_both_the_import_and_the_from_form(tmp_path, monkeypatch):
    _point_at(monkeypatch, _build(tmp_path))
    files = {r[0] for r in sym.find_importers("pkg.a", include_tests=False)}
    assert files == {"pkg/b.py", "pkg/c.py", "pkg/d.py", "pkg/e.py"}, files


def test_dead_lists_the_unreferenced_name_and_not_the_referenced_one(tmp_path, monkeypatch):
    _point_at(monkeypatch, _build(tmp_path))
    dead_names = {name for _, name in sym.find_dead(include_tests=False)}
    assert "unused_fn" in dead_names
    assert "target_fn" not in dead_names
    assert "attr_called_fn" not in dead_names
    assert "__all__" not in dead_names


def test_a_from_import_alone_counts_as_a_reference(tmp_path, monkeypatch):
    _point_at(monkeypatch, _build(tmp_path))
    dead_names = {name for _, name in sym.find_dead(include_tests=False)}
    assert "imported_only_fn" not in dead_names


def test_json_round_trips_the_table(tmp_path, monkeypatch, capsys):
    _point_at(monkeypatch, _build(tmp_path))
    rows = sym.find_definitions("target_fn", include_tests=False)
    sym.render(["location", "kind", "class"], rows, as_json=True)
    printed = json.loads(capsys.readouterr().out)
    assert printed == [{"location": "pkg/a.py:4", "kind": "def", "class": "-"}]


def test_the_tool_runs_from_the_command_line_on_this_tree():
    # Seconds are the machine's (UX-418): the timing lives in the
    # Outcome, and this holds only that the tool runs and answers.
    import subprocess
    import sys

    repo = pathlib.Path(__file__).resolve().parents[2]
    result = subprocess.run(
        [sys.executable, str(repo / "tools" / "dev_symbols.py"), "def", "analyze"],
        cwd=repo, capture_output=True, text=True, timeout=60, check=True)
    assert "bga/analyzer.py:" in result.stdout, result.stdout
