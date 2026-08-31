"""UX-449: a skip reason is only checked where the skip happens.

The census in `conftest.py` is a **runtime** instrument. It counts a
skip when one fires, so it can only ever see a reason on a machine that
lacks the thing being gated - which is never the machine that writes
the gate. Twice, five rounds apart, that shipped a coined reason to CI
and failed four interpreters *after every test passed*.

These clauses read the reason as **written**, so the same fact is
checked on the author's own machine whatever it happens to have
installed. `tests/skip_reasons.py` does the parsing and says why it
parses rather than greps.

What the scan found on its first run is the argument for it: eighteen
undeclared reasons on a tree where every session was green, and a
second blind spot nobody had named - sixteen of the eighteen were
`pytest.skip()` raised in a **test body**, which the census hook cannot
see at all because it counts `report.when == "setup"`.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tests"))

import conftest  # noqa: E402
import skip_reasons  # noqa: E402

#: What the scan could not read statically, measured 2026-08-31 on the
#: whole suite:
#:
#:     {'Name': 33, 'JoinedStr': 17, 'Attribute': 4, 'BinOp': 1}
#:
#: `Name` is a constant this scan cannot follow (defined in a class, or
#: imported through more than one hop); `JoinedStr` is an f-string;
#: `Attribute` is another module's constant reached by attribute rather
#: than by `from ... import`; `BinOp` is a computed concatenation.
#:
#: This is a **ceiling, not a target**. The number is asserted so that
#: a new unresolvable reason is a change somebody has to argue for
#: rather than a silence - which is the failure mode the whole item is
#: about. Lowering it is always welcome; the guard says so.
UNRESOLVABLE = 55


def test_every_declared_skip_reason_is_known():
    """The item's fix, in one clause.

    A reason written into the suite but absent from
    `KNOWN_SKIP_REASONS` is a skip nobody has accounted for. The census
    says the same thing about a reason that *fired*; this says it about
    one that exists.
    """
    resolved, _ = skip_reasons.scan()
    known = set(conftest.KNOWN_SKIP_REASONS)
    undeclared = {
        reason: sorted(sites)[0]
        for reason, sites in resolved.items() if reason not in known
    }
    assert undeclared == {}, (
        "skip reason(s) written into the suite that tests/conftest.py's "
        "KNOWN_SKIP_REASONS has never declared. The runtime census cannot "
        "see these until a machine without the thing being gated runs the "
        "suite - which is what CI is, and is too late:\n  "
        + "\n  ".join(f"{reason!r} first at {site[0]}:{site[1]}"
                      for reason, site in sorted(undeclared.items()))
    )


def test_the_unreadable_reasons_are_counted_not_ignored():
    """A reason built at runtime has no literal to compare.

    Dropping those silently would make the clause above pass by reading
    less, which is the way a guard goes quiet. So they are counted, and
    the count is the thing asserted.
    """
    _resolved, unresolved = skip_reasons.scan()
    assert len(unresolved) <= UNRESOLVABLE, (
        f"{len(unresolved)} skip reason(s) cannot be read statically, up "
        f"from the {UNRESOLVABLE} measured. A new one is a reason no guard "
        f"can check before it fires - prefer a module-level constant, which "
        f"this scan follows:\n  "
        + "\n  ".join(f"{f}:{line} ({what})"
                      for f, line, what in unresolved[UNRESOLVABLE:])
    )


def test_the_scan_reads_calls_and_not_text(tmp_path):
    """Fixing guide §5, on this scan itself.

    A text search for `pytest.skip(` would find all four strings below.
    Only one of them is a skip; the other three are a comment, a
    docstring and a piece of data. Round 70 shipped exactly that
    mistake in `UX-429`'s first guard, which matched a comment.
    """
    (tmp_path / "test_decoy.py").write_text(
        'import pytest\n'
        '\n'
        '# pytest.skip("a reason in a comment")\n'
        'DOC = """pytest.skip("a reason in a docstring")"""\n'
        'DATA = {"sql": \'pytest.skip("a reason in data")\'}\n'
        '\n'
        '\n'
        'def test_real():\n'
        '    pytest.skip("the only real reason here")\n',
        encoding="utf-8")
    resolved, _ = skip_reasons.scan(tmp_path)
    assert set(resolved) == {"the only real reason here"}, resolved


def test_the_order_guards_fake_reasons_are_not_in_the_population():
    """The item's second bullet, confirmed rather than excluded.

    `test_the_order_the_page_has.py` passes invented reasons
    (`"because I said so"`, `"x"`, `"gone"`) straight to
    `census_complaints` to test the census itself. They are arguments
    to a function, not skips - so a scan that reads skip call sites has
    them out of its population already, and needs no exclusion list.

    Written as a clause because "it already works" is the kind of claim
    that stops being true silently: if the scan ever widened to any
    string near the word `skip`, this is what would notice.
    """
    resolved, _ = skip_reasons.scan()
    invented = {"because I said so", "x", "gone"}
    assert invented & set(resolved) == set(), (
        "the scan picked up a reason that is test *data* for the census, "
        "not a skip: it is reading more than the call sites")


def test_the_scan_knows_the_forms_the_suite_uses():
    """A form the scan does not know is a family it cannot see.

    `pytest.mark.skip` is deliberately not among the forms read, on the
    measurement that the suite has none. If one appears, this fails and
    the scan gains a line - rather than the skip being invisible.
    """
    import ast

    # Parsed, not searched. The first cut of this clause did search the
    # text, and matched the `pytest.mark.skip(` written in its own
    # docstring one paragraph up - fixing guide §5, committed inside
    # the guard built to enforce §5. Left recorded rather than tidied.
    used = set()
    for path in sorted((REPO / "tests").rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        aliases = skip_reasons._aliases(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if skip_reasons._dotted(node.func, aliases) == (
                    "pytest", "mark", "skip"):
                used.add(path.relative_to(REPO).as_posix())
    assert used == set(), (
        f"`pytest.mark.skip(` now appears in {sorted(used)}, and "
        f"tests/skip_reasons.py's SKIP_FORMS does not read it - so those "
        f"reasons are invisible to the clause above. Add the form.")


def test_the_census_cannot_see_an_in_body_skip(pytester=None):
    """Why the scan is not a duplicate of the census.

    Measured, not asserted: the hook in `conftest.py` counts
    `report.when == "setup"`, and a `pytest.skip()` raised in a test
    body reports at `call`. 42 of the suite's 195 skip sites are that
    shape, and the census has never counted one of them.
    """
    import collections
    seen = collections.Counter()

    class Report:
        def __init__(self, when, reason):
            self.when, self.skipped = when, True
            self.longrepr = ("f", 1, f"Skipped: {reason}")

    # The hook, called with the two reports pytest would produce.
    original = conftest._SKIPS
    conftest._SKIPS = seen
    try:
        conftest.pytest_runtest_logreport(Report("setup", "a marker"))
        conftest.pytest_runtest_logreport(Report("call", "an in-body skip"))
    finally:
        conftest._SKIPS = original
    assert dict(seen) == {"a marker": 1}, (
        "the census counted an in-body skip, so this scan's second reason "
        "for existing is gone and this clause should be deleted rather "
        "than adjusted")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
