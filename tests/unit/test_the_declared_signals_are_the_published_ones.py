"""UX-564: Parts 23 and 27 exist in the spec and nowhere else.

Measured when this was filed, and re-measured in round 83:

```text
$ git grep -il "resource_mix|CACHE_IO|wait_to_execution|wait_share" -- bga tests docs/backlog
bga/findings.py  bga/schemas.py          both `largest_wait_share`, a different quantity
specification.md:1175-1202   Part 23, wait-to-execution ratio
specification.md:1338-1370   Part 27, resource mix
specification.md:1619-1625   both listed as `signals` keys of analysis/v9
```

Part 32.7.2 declines both and maps every one of 32.4's ten declared
keys to what the tool actually publishes. This reads that mapping
against the block above it and against a real run's key set - the
population is the analyzer's own output, not a list.
"""
import ast
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

SPEC = REPO / "docs/spec/specification.md"
RUN = REPO / "tests/fixtures/macro_micro/run"

DECLINED = "declined"


def _declared_keys():
    """32.4's `signals` object, in the order the block writes them."""
    text = SPEC.read_text(encoding="utf-8")
    start = text.index('  "signals": {', text.index("## 32.4 analysis/v9"))
    block = text[start:text.index("\n  },", start)]
    return re.findall(r'^    "([a-z_]+)":', block, re.M)


def _mapping_rows():
    """32.7.2's table, as (declared key, part, published-as cell)."""
    text = SPEC.read_text(encoding="utf-8")
    start = text.index("| 32.4 `signals` key | Part | published as |")
    table = text[start:text.index("\n\n", start)]
    rows = []
    for line in table.splitlines()[2:]:
        cells = [c.strip() for c in line.split("|")[1:-1]]
        rows.append((cells[0].strip("`"), cells[1], cells[2]))
    return rows


def _published():
    """What the tool writes under `signals`, two ways.

    A real run is the population, because a key set read off the source
    is a proxy for one; the AST half only adds the sites a run of this
    shape does not reach (`fetch_build_overlap` is conditional on an
    overlap existing, and the golden run has none).
    """
    from bga.analyzer import analyze_run

    live = set(analyze_run(RUN).signals)
    stored = set()
    for path in sorted((REPO / "bga").rglob("*.py")):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                base = getattr(target, "value", None)
                if (isinstance(target, ast.Subscript)
                        and (getattr(base, "id", None)
                             or getattr(base, "attr", None)) == "signals"
                        and isinstance(target.slice, ast.Constant)):
                    stored.add(target.slice.value)
    return live | stored


class TestTheTableIsTheDeclaredBlock:
    """A key added to 32.4 and not to 32.7.2 would leave the mapping
    silently partial - which is how Parts 23 and 27 survived."""

    def test_every_declared_key_has_a_row_in_the_registry_order(self):
        declared = _declared_keys()
        assert len(declared) == 10, (
            "32.4's signals block no longer declares ten keys; 32.7.2's "
            "table is per declared key and must move with it", declared)
        rows = [key for key, _, _ in _mapping_rows()]
        assert rows == declared, (
            "32.7.2's table is not one row per 32.4 key in 32.4's own "
            "order", rows, declared)


class TestEveryPublishedRowNamesAKeyTheToolWrites:
    """The half that catches a row that ages: a mapping cell naming a
    `signals` key nothing writes."""

    def test_each_row_pointing_at_signals_points_at_a_real_key(self):
        published = _published()
        assert len(published) > 10, (
            "the analyzer published almost nothing - the fixture or the "
            "walk broke, and every claim below would pass vacuously",
            sorted(published))
        missing = []
        for key, _, cell in _mapping_rows():
            for named in re.findall(r"`signals\['([a-z_]+)'\]`", cell):
                if named not in published:
                    missing.append((key, named))
        assert not missing, (
            "32.7.2 maps a declared key onto a `signals` key the tool "
            "does not write", missing, sorted(published))


class TestTheDeclinedPartsReachNothing:
    """`UX-564`'s finding itself. A declined Part that later grows an
    implementation must redden here rather than leave the spec saying
    it was declined."""

    def test_no_module_computes_a_declined_signal(self):
        declined = [key for key, _, cell in _mapping_rows() if cell == DECLINED]
        assert sorted(declined) == ["critical_path_resource_mix",
                                    "wait_to_execution_top"], (
            "32.7.2 declines a different set than UX-564 decided", declined)
        sightings = []
        for path in sorted((REPO / "bga").rglob("*")):
            if path.suffix not in {".py", ".js"} or "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8")
            for key in declined:
                if key in text:
                    sightings.append((str(path.relative_to(REPO)), key))
        assert not sightings, (
            "a Part 32.7.2 declines is implemented after all - the note is "
            "now wrong and the decision has to be retaken", sightings)

    def test_neither_declined_key_is_published(self):
        published = _published()
        declined = {key for key, _, cell in _mapping_rows() if cell == DECLINED}
        assert not (declined & published), (
            "a declined key is in the published signals set",
            sorted(declined & published))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
