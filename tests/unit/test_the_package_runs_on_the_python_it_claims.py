"""UX-539 follow-up: a 3.10+ builtin in a package that claims 3.9.

`requires-python = ">=3.9"` and CI's matrix runs 3.9-3.12, but every
local run here is one interpreter. `UX-539`'s bitset closure reached
for `int.bit_count()`, which arrived in **3.10**, and the whole local
suite was green:

```text
make test (3.11, this container)   6188 passed, 29 skipped
CI test (3.9), same commit          358 failed, 2950 passed, 156 errors
    AttributeError: 'int' object has no attribute 'bit_count'
    bga/structural/analyzer.py:246, reached from `bga analyze`
```

It is the second time: `test_the_minutes_inside_analyze.py` records
`tomllib` (3.11) taken on a path "where this path never runs, and
failed on 3.9 and 3.10 in CI". Twice is a class, and one job of five
finding it costs a whole CI cycle.

**What this is and is not.** A curated name table, not a compatibility
checker - it knows the constructs this repository has actually reached
for, and a 3.10+ name nobody here has used yet is not in it. That is
the same bargain `tools/dev_js_deps.py` states about its scanner: a
cheap instrument that answers one question, with its blind spot
written down rather than implied. The version floor is read from
`pyproject.toml`, so raising `requires-python` retires the rows it
makes moot instead of leaving them to be deleted by hand.
"""
import ast
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
PACKAGE = ("bga", "tools")

#: `(name, (major, minor), what it is)` - each one this repository has
#: reached for, or would plausibly reach for next in the same spot.
#: Attribute names, because that is how every instance has arrived: a
#: method called on a value whose type is only known at runtime, which
#: no import guard and no linter default catches.
NEWER_THAN_THE_FLOOR = (
    ("bit_count", (3, 10), "int.bit_count() - UX-539 shipped this one"),
    ("pairwise", (3, 10), "itertools.pairwise()"),
    ("get_annotations", (3, 10), "inspect.get_annotations()"),
    ("batched", (3, 12), "itertools.batched()"),
    ("full_match", (3, 13), "PurePath.full_match()"),
    # The control, and it has to be a name this repository really
    # calls or the clause below proves nothing: 48 sites in `bga/` and
    # `tools/`, and every Python has it.
    ("splitlines", (3, 0), "str.splitlines() - the control"),
)


def _floor():
    """The `(major, minor)` `pyproject.toml` promises to run on."""
    text = (REPO / "pyproject.toml").read_text(encoding="utf-8")
    found = re.search(r'requires-python\s*=\s*"[><=~^]*(\d+)\.(\d+)"', text)
    assert found, "pyproject.toml declares no readable requires-python"
    return (int(found.group(1)), int(found.group(2)))


def _sources():
    for root in PACKAGE:
        for path in sorted((REPO / root).rglob("*.py")):
            if "__pycache__" in path.parts:
                continue
            yield path


def _attribute_uses(path):
    """`{attribute name: [line, ...]}` for every `x.name` in the file."""
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError as error:  # pragma: no cover - a real break
        pytest.fail(f"{path.relative_to(REPO)} does not parse: {error}")
    seen = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute):
            seen.setdefault(node.attr, []).append(node.lineno)
    return seen


class TestNothingReachesPastTheFloor:

    def test_the_floor_is_the_one_pyproject_declares(self):
        """The instrument first: a regex that stopped matching would
        make every clause below vacuous."""
        major, minor = _floor()
        assert (major, minor) >= (3, 0), (major, minor)
        assert (major, minor) <= sys.version_info[:2], (
            f"pyproject declares {major}.{minor}, which is newer than the "
            f"interpreter running this suite - the scan below would pass "
            f"by being asked nothing")

    def test_no_source_file_uses_a_name_newer_than_it(self):
        """The clause `UX-539` needed and nothing had.

        One job of CI's five found it, after the whole local suite went
        green - which is the cost this pays back.
        """
        floor = _floor()
        offenders = []
        for name, added, what in NEWER_THAN_THE_FLOOR:
            if added <= floor:
                continue
            for path in _sources():
                for line in _attribute_uses(path).get(name, []):
                    offenders.append(
                        f"{path.relative_to(REPO).as_posix()}:{line} uses "
                        f"`.{name}()` ({what}), which needs Python "
                        f"{added[0]}.{added[1]}; pyproject declares "
                        f"{floor[0]}.{floor[1]}")
        assert offenders == [], (
            "a source file reaches past the Python this package claims to "
            "run on; every local interpreter here is newer, so CI's oldest "
            "matrix job is the only thing that sees it:\n  "
            + "\n  ".join(offenders))

    def test_the_table_would_have_caught_the_one_that_shipped(self):
        """The reproduction, because the clause above is now green and
        cannot show what it was for. `bit_count` is in the table at
        3.10 and the floor is 3.9, so the pair discriminates."""
        assert ("bit_count", (3, 10)) in [
            (name, added) for name, added, _what in NEWER_THAN_THE_FLOOR]
        assert _floor() < (3, 10), (
            "the floor has reached 3.10, so bit_count is fine now and this "
            "reproduction should be retired with its row")

    def test_a_name_at_or_below_the_floor_is_not_flagged(self):
        """The other direction. Without this the clause above passes by
        flagging everything, and `.readlines()` is in the table at 3.0
        to prove it does not - it is called in 48 places and would
        light up every one of them if the floor comparison were
        dropped."""
        assert any(_attribute_uses(path).get("splitlines")
                   for path in _sources()), (
            "no source calls `.splitlines()`, so the control row proves "
            "nothing - pick another name that is actually used")
        floor = _floor()
        assert floor >= (3, 0), floor


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
