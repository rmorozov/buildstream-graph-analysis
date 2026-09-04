"""UX-609: the invariants docstring listed five of six gates.

Measured when this was filed, at `d4a3d04`:

```text
$ hard_gates dict literal, bga/validation/invariants.py:191      6 keys
$ module docstring, gates named                                  5
$ missing                          run_identity_consistent  (no
  "run_identity", "manifest", "identity" or "I8" anywhere in it)
```

`UX-602` gave the same defect one layer out a derived table; its guard
reads spec 32.7.5 against a run's published `hard_gates` and passes
here, because the docstring is neither. This reads the docstring's
block against that same population, both directions and in order. The
population is the analyzer's own output, never a list restated here.
"""
import ast
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

MODULE = REPO / "bga/validation/invariants.py"
RUN = REPO / "tests/fixtures/macro_micro/run"
STORED = REPO / "tests/fixtures/with_timeline/analyze.json"

HEADER = re.compile(r"^Hard gates\b.*:$", re.M)
#: A gate key, not a word: every published key is snake_case, so
#: requiring the underscore keeps lowercase prose out of the block too.
KEY = re.compile(r"^[a-z][a-z0-9]*(?:_[a-z0-9]+)+$")


def _docstring_gates():
    """The keys the module docstring lists, in the order it lists them.

    Bounded to the indented block under the `Hard gates ...:` header, so
    the prose around it cannot be mistaken for the list - and so a list
    that is deleted parses to nothing rather than to the paragraph below.
    """
    doc = ast.get_docstring(ast.parse(MODULE.read_text(encoding="utf-8"))) or ""
    header = HEADER.search(doc)
    if not header:
        return None
    listed = []
    for line in doc[header.end():].splitlines()[1:]:
        if not line.startswith("    "):
            break
        listed.extend(line.split())
    return listed


def _published():
    """`confidence.hard_gates`, from a live run and from a stored one.

    Two runs of different shape, because a key only one run publishes
    would make the docstring look wrong when it is the gate that is
    conditional.
    """
    import json

    from bga.analyzer import analyze_run

    live = analyze_run(RUN).confidence["hard_gates"]
    stored = json.loads(STORED.read_text(encoding="utf-8"))
    return live, stored["confidence"]["hard_gates"]


class TestTheListIsReadable:
    """Anti-vacuity: both populations exist and parsed to something of
    the right shape. Without these, the two directions below can agree
    by both being empty."""

    def test_the_run_publishes_gates_at_all(self):
        live, stored = _published()
        assert len(live) >= 4 and live.keys() == stored.keys(), (
            "the two runs do not publish the same gate keys, or the "
            "fixture broke - every claim below would pass vacuously",
            sorted(live), sorted(stored))

    def test_the_docstring_block_parses_to_gate_shaped_names(self):
        listed = _docstring_gates()
        assert listed, (
            "bga/validation/invariants.py's docstring has no `Hard "
            "gates ...:` header with an indented block under it; the "
            "list this holds to the registry is gone", listed)
        odd = [tok for tok in listed if not KEY.match(tok)]
        assert not odd, (
            "the docstring's hard-gate block holds a token that is not "
            "a bare gate key - prose has leaked into the list", odd)


class TestTheDocstringIsThePublishedSet:
    """The finding itself, both directions: each has its own failure."""

    def test_the_docstring_names_every_published_gate(self):
        live, stored = _published()
        listed = set(_docstring_gates() or [])
        unnamed = sorted((live.keys() | stored.keys()) - listed)
        assert not unnamed, (
            "a hard gate is published and bga/validation/invariants.py's "
            "module docstring does not name it - this is UX-609's defect "
            "arriving again", unnamed)

    def test_the_docstring_names_no_gate_a_run_does_not_publish(self):
        live, stored = _published()
        listed = set(_docstring_gates() or [])
        stale = sorted(listed - (live.keys() | stored.keys()))
        assert not stale, (
            "bga/validation/invariants.py's module docstring names a "
            "hard gate no run publishes; the line outlived its gate",
            stale, sorted(live))

    def test_the_list_is_in_the_order_the_code_writes_them(self):
        """The docstring says "in written order", which is the
        `hard_gates` dict's own order - so a reader can diff the list
        against the literal without re-sorting either."""
        live, _ = _published()
        assert _docstring_gates() == list(live), (
            "bga/validation/invariants.py's module docstring lists the "
            "gates in an order no run writes them in",
            _docstring_gates(), list(live))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
