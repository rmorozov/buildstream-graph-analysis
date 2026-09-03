"""UX-540: the registry answers for the shapes `bga` only reads.

Measured when this was filed, against the contract every capture is
laid out by:

```text
contracts.ids()                                    23
contracts.superseded()                              9
CAPTURE_LAYOUT contracts in neither    graph/v9, run-context/v9, trace/v9
```

`bga analyze` refuses without all three, and no accessor named them, so
`bga.bundle.readable_contracts()` unioned `CAPTURE_LAYOUT` in and the
registry stayed wrong for everyone else.

The clauses below are derived from the layout rather than from the
three ids, so a *fourth* input shape added to a capture and declared
nowhere reddens them the same way.
"""
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import bundle, contracts, run_store  # noqa: E402

SPEC = REPO / "docs/spec/specification.md"
ARCHITECTURE = REPO / "docs/design/architecture.md"
INDEX = REPO / "docs/README.md"


def _layout_contracts():
    return {contract for _p, _pr, contract, _w in run_store.CAPTURE_LAYOUT
            if contract}


class TestTheRegistryKnowsEveryShapeACaptureHolds:
    def test_no_contract_in_the_layout_is_unregistered(self):
        """The gap itself, derived. Not "the three are declared" - a
        fourth input would walk past that."""
        known = (set(contracts.ids()) | set(contracts.superseded())
                 | set(contracts.reads()))
        unregistered = sorted(_layout_contracts() - known)
        assert unregistered == [], (
            f"`capture-layout/v1` names contract(s) no accessor answers "
            f"for: {unregistered}. Declare them - `SCHEMA` if this tool "
            f"stamps them, `READS` on the module that reads them")

    def test_reads_names_the_input_shapes(self):
        assert contracts.reads() == ["graph/v9", "run-context/v9",
                                     "trace/v9"]

    def test_an_input_is_declared_by_the_module_that_reads_it(self):
        from bga import ingest

        assert set(contracts.reads()) <= set(ingest.READS)


class TestEmitsAndAcceptsStayDifferentQuestions:
    """The distinction is the reason this is a new accessor and not a
    wider `ids()`: a release that *emits* `graph/v9` would be a
    different tool."""

    def test_an_input_is_not_in_the_emitted_set(self):
        overlap = sorted(set(contracts.reads()) & set(contracts.ids()))
        assert overlap == [], (
            f"{overlap} is both emitted and declared as an input; one of "
            f"the two declarations is wrong")

    def test_an_input_is_not_retired(self):
        overlap = sorted(set(contracts.reads()) & set(contracts.superseded()))
        assert overlap == [], (
            f"{overlap} is declared both as an input and as superseded - "
            f"`superseded()` means *this tool* stopped writing it")

    def test_the_three_kinds_partition_what_a_bundle_can_read(self):
        """`UX-520`'s regression: `readable_contracts()` was
        `ids() | superseded()` and the first real bundle of a healthy
        capture was refused for carrying all three inputs."""
        assert _layout_contracts() <= bundle.readable_contracts()

    def test_readable_contracts_reads_the_registry_not_the_layout(self):
        assert bundle.readable_contracts() == (
            set(contracts.ids()) | set(contracts.superseded())
            | set(contracts.reads()))


class TestEveryInputHasAHomeInTheDocuments:
    """Same rule `UX-233` put on the emitted set. An input a consumer
    cannot look up is the gap this item is about, one document over."""

    def test_part_32_5_names_every_input(self):
        """The rows of 32.5's input table, not the part's text.

        The first draft read the whole part and stayed green when the
        `graph/v9` row was deleted, because the paragraph that argues
        for the table names all three ids. Subject, not argument.
        """
        part = SPEC.read_text(encoding="utf-8").split(
            "## 32.5 The published output schemas", 1)[1].split("\n## ", 1)[0]
        table = part.split("**The inputs are a third kind**", 1)
        assert len(table) == 2, "Part 32.5 no longer has an input table"
        rows = set(re.findall(r"^\|[^|]*\| `([a-z][a-z0-9-]*/v\d+)` \|",
                              table[1], re.M))
        missing = [name for name in contracts.reads() if name not in rows]
        assert missing == [], (
            f"input contract(s) spec Part 32.5 does not list: {missing}")

    def test_the_architecture_names_every_input(self):
        text = ARCHITECTURE.read_text(encoding="utf-8")
        assert "## The contracts it reads" in text, (
            "architecture.md has no chapter for the shapes `bga` reads "
            "and never writes")
        body = text.split("## The contracts it reads", 1)[1].split(
            "\n## ", 1)[0]
        missing = [name for name in contracts.reads() if name not in body]
        assert missing == [], (
            f"input contract(s) missing from the architecture: {missing}")

    def test_that_chapter_names_no_input_the_code_does_not_read(self):
        """The other direction: a chapter left behind documents nothing.

        The table is the subject and the prose around it is the
        argument - a row is what a reader takes the claim from, and
        matching the prose would find every id the chapter mentions in
        order to say it is *not* one of these.
        """
        body = ARCHITECTURE.read_text(encoding="utf-8").split(
            "## The contracts it reads", 1)[-1].split("\n## ", 1)[0]
        listed = set(re.findall(r"^\| `([a-z][a-z0-9-]*/v\d+)` \|", body,
                               re.M))
        stale = sorted(listed - set(contracts.reads()))
        assert stale == [], (
            f"the chapter names input(s) nothing reads: {stale}")

    def test_the_index_names_every_input(self):
        text = INDEX.read_text(encoding="utf-8")
        assert "## What it reads" in text, (
            "docs/README.md answers what `bga` emits and not what it "
            "accepts")
        body = text.split("## What it reads", 1)[1].split("\n## ", 1)[0]
        missing = [name for name in contracts.reads() if name not in body]
        assert missing == [], (
            f"input contract(s) docs/README.md does not name: {missing}")


class TestAnalysisV9IsNotAFourthInput:
    """`UX-540`'s Out of Scope asked which it is. Measured: it is the
    analyzer's in-memory result shape - no artifact carries it, no
    loader parses it - so it is not an unregistered input."""

    def test_nothing_stamps_or_reads_analysis_v9(self):
        assert "analysis/v9" not in _layout_contracts()
        assert "analysis/v9" not in contracts.ids()
        assert "analysis/v9" not in contracts.reads()

    def test_the_registry_says_so_where_a_reader_meets_it(self):
        body = SPEC.read_text(encoding="utf-8").split(
            "## 32.5 The published output schemas", 1)[1].split("\n## ", 1)[0]
        assert "analysis/v9" in body and "not a fourth input" in body, (
            "Part 32.5 names `analysis/v9` beside the inputs without "
            "saying it is not one of them")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
