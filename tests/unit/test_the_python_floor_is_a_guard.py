"""`UX-588`: the floor `pyproject.toml` declares, read here.

`requires-python = ">=3.9"` is a promise, and until this file the only
thing that checked it was the CI matrix - so a track working on 3.11
could write `str | None`, pass everything it ran, and learn seven
minutes later that 3.9 refuses to import the module at all.

PEP 604 unions are a *runtime* TypeError on 3.9, not a syntax error, so
`ast.parse(..., feature_version=(3, 9))` does not see them. This walks
the annotations instead, which is where they are.
"""

import ast
import pathlib
import re
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
#: Directories whose modules ship or are imported at collection time.
SCANNED = ("bga", "tools", "tests")


def _floor():
    """`(3, 12)` from `pyproject.toml`, not from a constant here."""
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    found = re.search(r'requires-python\s*=\s*"[>=~^]*\s*(\d+)\.(\d+)', text)
    assert found, "pyproject.toml declares no requires-python"
    return int(found.group(1)), int(found.group(2))


def _tracked_python():
    out = subprocess.run(["git", "ls-files", "--", "*.py"], cwd=REPO, check=True, capture_output=True, text=True).stdout
    return [REPO / one for one in out.splitlines() if one.split("/", 1)[0] in SCANNED]


def _pep604_annotations(path):
    """Every `X | Y` used as an annotation, as `(line, source)`.

    A module with `from __future__ import annotations` is exempt: its
    annotations are strings and never evaluated.
    """
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, str(path))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "__future__"
            and any(a.name == "annotations" for a in node.names)
        ):
            return []
    lines = source.splitlines()
    found = []
    for node in ast.walk(tree):
        annotations = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            annotations = [node.returns] + [
                a.annotation for a in (node.args.args + node.args.kwonlyargs + node.args.posonlyargs)
            ]
        elif isinstance(node, ast.AnnAssign):
            annotations = [node.annotation]
        for annotation in annotations:
            if annotation is None:
                continue
            for inner in ast.walk(annotation):
                if isinstance(inner, ast.BinOp) and isinstance(inner.op, ast.BitOr):
                    found.append((inner.lineno, lines[inner.lineno - 1].strip()))
    return found


def test_the_floor_is_declared_and_read():
    assert _floor() == (3, 12), _floor()


def test_no_annotation_needs_a_newer_python_than_the_floor():
    """`UX-588`'s clause. PEP 604 lands in 3.10; retired since `UX-1348`'s 3.12 floor."""
    if _floor() >= (3, 10):
        pytest.skip("the floor has moved to 3.10; PEP 604 is allowed")
    offenders = [
        f"{path.relative_to(REPO)}:{line}: {text}"
        for path in _tracked_python()
        for line, text in _pep604_annotations(path)
    ]
    assert offenders == [], (
        "PEP 604 unions (`X | Y`) are a TypeError on the declared floor "
        f"{_floor()}; write Optional[X]/Union[X, Y]:\n  " + "\n  ".join(offenders)
    )


def test_the_scan_reads_files(self=None):
    """The vacuity floor: a scan that finds no file passes anything."""
    assert len(_tracked_python()) > 300, len(_tracked_python())


def _classmethod_fixtures(source, name="<probe>"):
    """`(line, function)` for each def stacking `@classmethod` on `@pytest.fixture`."""
    found = []
    for node in ast.walk(ast.parse(source, name)):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        names = [ast.unparse(d.func if isinstance(d, ast.Call) else d) for d in node.decorator_list]
        if "classmethod" in names and any(n.endswith("fixture") for n in names):
            found.append((node.lineno, node.name))
    return found


def test_no_fixture_is_a_classmethod():
    """`UX-1348`: 3.13 dropped classmethod descriptor chaining, so pytest
    no longer finds a fixture under `@classmethod` - "fixture not found"."""
    offenders = [
        f"{path.relative_to(REPO)}:{line}: {name}"
        for path in _tracked_python()
        if path.parts[len(REPO.parts)] == "tests"
        for line, name in _classmethod_fixtures(path.read_text(encoding="utf-8"), str(path))
    ]
    assert offenders == [], "drop `@classmethod` and take `self`:\n  " + "\n  ".join(offenders)


def test_the_classmethod_scan_sees_one():
    probe = (
        "import pytest\nclass T:\n    @classmethod\n    @pytest.fixture(scope='class')\n    def f(cls):\n        pass\n"
    )
    assert _classmethod_fixtures(probe) == [(5, "f")]
