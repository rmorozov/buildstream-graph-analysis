"""UX-1038: a reader-facing CLI sentence chooses its plural by count,
never spells it `(s)`.

Walks `bga`'s own package (minus `bga/viewer`, `UX-1020`'s row) plus
the three tools `bga view`/`snapshot`/`doctor` dispatch to
(`bga/tools_dispatch.py`) for a string literal matching `[a-z]\\(s\\)`,
skipping every module/class/function docstring - a comment is already
invisible to `ast`. Dev tools under `tools/dev_*` are Out of Scope.
"""
import ast
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

_PLURAL_S = re.compile(r"[a-z]\(s\)")

_MODULES = sorted(
    p for p in (REPO / "bga").rglob("*.py") if "viewer" not in p.parts
) + [
    REPO / "tools/bga_view.py",
    REPO / "tools/bga_snapshot.py",
    REPO / "tools/bga_doctor.py",
]


def _docstring_ids(tree: ast.AST) -> set:
    ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            body = getattr(node, "body", None) or []
            if (body and isinstance(body[0], ast.Expr)
                    and isinstance(body[0].value, ast.Constant)
                    and isinstance(body[0].value.value, str)):
                ids.add(id(body[0].value))
    return ids


def _offenders(path: pathlib.Path) -> list:
    tree = ast.parse(path.read_text(), filename=str(path))
    docstrings = _docstring_ids(tree)
    return [
        (node.lineno, node.value) for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and id(node) not in docstrings and _PLURAL_S.search(node.value)
    ]


def test_no_reader_facing_cli_string_spells_a_parenthesised_plural():
    findings = {}
    for path in _MODULES:
        offenders = _offenders(path)
        if offenders:
            findings[str(path.relative_to(REPO))] = offenders
    assert not findings, (
        "a reader-facing CLI module still spells a plural `(s)` rather "
        f"than choosing it by count (bga/units.py's `plural`): {findings}")
