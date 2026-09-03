"""`UX-603`: the Python floor, stated where a contributor reads.

`UX-588` holds the tree to `requires-python` - no PEP 604 union may
reach a 3.9 runtime - so the floor was enforced and invisible. Measured
at `8f51a26`: `grep -nE 'Python 3|python3\\.[0-9]|requires-python'` over
the 33 front-of-house `.md` files returned 0 hits, so a contributor on
3.8 learned it from a `pip` error.

Both figures are read, never typed: the floor from `pyproject.toml` and
the matrix from `.github/workflows/ci.yml`. Raising one and leaving the
prose is what this reddens on.
"""
import ast
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
CI = REPO / ".github/workflows/ci.yml"

#: Where a contributor reads before writing code. The fixing guide is
#: `UX-603`'s other named door and is not here: see that task's Outcome.
STATES_THE_FLOOR = ("README.md",)


def _floor():
    """`"3.9"` from `pyproject.toml`, as written."""
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    found = re.search(r'requires-python\s*=\s*"[>=~^]*\s*(\d+\.\d+)', text)
    assert found, "pyproject.toml declares no requires-python"
    return found.group(1)


def _matrix():
    """Every Python the CI matrix runs, in the order it lists them."""
    text = CI.read_text(encoding="utf-8")
    found = re.search(r"python-version:\s*\[([^\]]*)\]", text)
    assert found, f"{CI.name} declares no python-version matrix"
    return re.findall(r"\d+\.\d+", found.group(1))


def _versions_named(path):
    """Every `Python X.Y` the document states - what it says, not what
    it should say, so a red can name both figures."""
    text = (REPO / path).read_text(encoding="utf-8")
    return re.findall(r"Python \*{0,2}(\d+\.\d+)", text)


def _states_the_range(path, low, high):
    text = (REPO / path).read_text(encoding="utf-8")
    return f"{low}-{high}" in text or f"{low}–{high}" in text


def test_the_matrix_runs_the_floor_it_enforces():
    """The tie `UX-588` leaves implicit: `requires-python` is only
    enforced because the lowest matrix job is that version."""
    matrix = _matrix()
    assert matrix, "the matrix is empty"
    assert min(matrix, key=lambda v: tuple(map(int, v.split(".")))) == _floor(), (
        f"pyproject.toml declares >={_floor()} and the CI matrix runs "
        f"{matrix}; the floor is enforced by whichever job is lowest")


@pytest.mark.parametrize("path", STATES_THE_FLOOR)
def test_the_document_states_the_declared_floor(path):
    """`UX-603`'s acceptance. Raising `requires-python` and leaving the
    prose reds here, naming the figure each side carries."""
    floor, matrix = _floor(), _matrix()
    named = _versions_named(path)
    assert floor in named, (
        f"pyproject.toml declares requires-python >={floor}, and {path} "
        f"states {named or 'no Python version at all'}")
    assert _states_the_range(path, matrix[0], matrix[-1]), (
        f"the CI matrix runs {matrix[0]}-{matrix[-1]} and {path} does not "
        f"state that range, so the prose can drift off the matrix")


def _string_literals(path):
    """Every string constant in the module except its docstrings."""
    tree = ast.parse(path.read_text(encoding="utf-8"), str(path))
    skip = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
                             ast.ClassDef)) and node.body:
            first = node.body[0]
            if (isinstance(first, ast.Expr)
                    and isinstance(first.value, ast.Constant)
                    and isinstance(first.value.value, str)):
                skip.add(id(first.value))
    return [node.value for node in ast.walk(tree)
            if isinstance(node, ast.Constant) and isinstance(node.value, str)
            and id(node) not in skip]


def test_the_floor_and_the_matrix_are_read_and_not_typed():
    """The vacuity floor. Both readers parse a real file, and the floor
    written into this file's body would make every clause above agree
    with itself. Docstrings are exempt - they are prose about it."""
    assert re.fullmatch(r"\d+\.\d+", _floor()), _floor()
    assert len(_matrix()) >= 2, _matrix()
    typed = [one for one in _string_literals(pathlib.Path(__file__))
             if _floor() in one]
    assert typed == [], (
        f"this file writes the floor {_floor()} as a literal: {typed}")


def test_a_document_naming_another_floor_is_not_accepted(tmp_path):
    """The clauses above pass on the tree as it stands, which says
    nothing about whether they can fail. This runs the same readers
    over a document that states 3.8."""
    assert _versions_named("README.md"), "the reader finds nothing to read"
    wrong = tmp_path / "wrong.md"
    wrong.write_text("Needs Python 3.8 or newer; CI runs 3.8-3.11.\n")
    named = re.findall(r"Python \*{0,2}(\d+\.\d+)", wrong.read_text())
    assert named == ["3.8"], named
    assert _floor() not in named, (
        "the probe document happens to state the real floor")
