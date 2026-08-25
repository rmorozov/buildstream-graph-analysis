"""UX-293: a check may not pin a contract version the tool has moved.

`UX-288` bumped `analyze/v1` to `analyze/v2` — a deliberate change, made
because fields were removed, with the versioning rule in
`architecture.md` and a guard asserting the new version on purpose. The
full suite was green and `make lint` was clean.

CI went red anyway, in the one file the suite does not scan:

```text
.github/workflows/ci.yml:173
    assert d['schema']=='analyze/v1', d.get('schema')
AssertionError: analyze/v2
```

The step's own purpose — does an installed wheel serve its assets and a
real payload — never needed the literal. It had one, so a contract bump
broke a check about packaging, and the failure arrived from a runner
rather than from the suite.

This is the same shape as `UX-276`: a rule everybody knew (`the version
moves when a field is removed`) with nothing mechanical behind it in the
places that are not Python. So: **every contract version written into a
CI check must be one the tool currently declares.** Prose may name a
past version — that is history, and `directions.md` is full of it — but
an executable check that pins one is a stale assertion waiting for the
next bump.
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]

# Executable checks, not prose. A workflow that runs on every push is
# exactly where a stale pin costs a red build; a document that says what
# `analyze/v1` used to publish is recording what happened.
CHECK_ROOTS = (".github/workflows",)

_LITERAL = re.compile(r"([a-z][a-z0-9-]*/v\d+)")


def _declared():
    from bga import contracts

    return set(contracts.inventory())


def _checks():
    for root in CHECK_ROOTS:
        base = REPO / root
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if path.is_file() and path.suffix in (".yml", ".yaml", ".sh"):
                yield path


def _executed(text):
    """The lines a runner runs, without the ones explaining them.

    The thirteenth instance of the self-matching guard in this
    repository: the first draft failed on the comment that this fix
    wrote - the sentence saying "this step asserted `analyze/v1` and
    went red" is not an assertion, and a guard that cannot tell the
    subject from the argument stops being about the subject (`UX-239`).
    A `#` line is a comment in YAML and a comment in the shell inside a
    `run: |` block, so one rule covers both.
    """
    return "\n".join(line for line in text.splitlines()
                      if not line.lstrip().startswith("#"))


def _pins(text):
    """Contract-shaped literals in what runs, and only those naming a
    contract this tool owns. `python/v3` and `actions/checkout@v4` are
    not contracts, and a check that flagged them would be noise nobody
    reads."""
    names = {name.split("/")[0] for name in _declared()}
    return {found for found in _LITERAL.findall(_executed(text))
            if found.split("/")[0] in names}


class TestNoCheckPinsAContractTheToolMoved:
    def test_the_workflows_name_only_current_contracts(self):
        declared = _declared()
        stale = {}
        for path in _checks():
            unknown = _pins(path.read_text(encoding="utf-8")) - declared
            if unknown:
                stale[path.relative_to(REPO).as_posix()] = sorted(unknown)
        assert stale == {}, (
            "CI check(s) pinning a contract version the tool no longer "
            f"declares: {stale}. The tool declares {sorted(declared)}. Read "
            "the expected version from the tree instead of writing it here.")

    def test_the_sweep_reaches_the_file_that_broke(self):
        """`UX-276`'s lesson: a sweep that finds nothing and a sweep that
        looks nowhere pass identically. The workflow this was filed for
        must be in the set, and it must be read."""
        scanned = {path.relative_to(REPO).as_posix() for path in _checks()}
        assert ".github/workflows/ci.yml" in scanned, scanned
        text = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        assert "pkgvenv" in text, (
            "the packaging job this was filed for is no longer in this file")

    def test_the_check_can_see_a_stale_pin_at_all(self):
        """The pattern fires on the shape it is written for. Without
        this, narrowing `_LITERAL` to something that matches nothing
        would leave the guard green and empty."""
        assert _pins("assert d['schema']=='analyze/v1'") == {"analyze/v1"}
        assert "analyze/v1" not in _declared(), (
            "this fixture is only a stale pin while v1 is behind us")

    def test_a_comment_naming_a_past_version_is_not_a_pin(self):
        """The other half, and the one the first draft got wrong: the
        comment explaining why the pin was removed is not itself a pin.
        Without this, the honest fix - writing down what happened - is
        what reddens the guard."""
        assert _pins("          # went red when analyze/v1 became v2") == set()
        assert _pins("  # analyze/v1\n  assert x=='analyze/v1'") == {
            "analyze/v1"}, "stripping comments must not strip the code too"

    def test_it_does_not_flag_what_is_not_a_contract(self):
        """`actions/checkout@v4` and `python/v3` are not this tool's
        contracts, and a guard that shouted about them would be one
        nobody reads."""
        assert _pins("uses: actions/checkout@v4") == set()
        assert _pins("runs on python/v3") == set()

    def test_the_packaging_step_derives_its_expectation(self):
        """The fix, pinned: the step reads the contract out of
        `bga/schemas.py` rather than carrying a copy of it."""
        text = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        step = text.split("UX-293:", 1)
        assert len(step) == 2, "the packaging step no longer explains itself"
        body = step[1].split("\n      - name:", 1)[0]
        assert "bga/schemas.py" in body, (
            "the step stopped reading the contract from the tree")
        assert "sys.argv[1]" in body, (
            "the assertion no longer compares against what it read")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
