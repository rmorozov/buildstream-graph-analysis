"""UX-687: the design-stage question, answered by one tool.

`dev_touching` says which guards run. This says what a change *reaches*
- contracts, findings, guides, styleguide sections, guards, open
filings - and each row names one source, so a row that stops being
derived is a row that reddens here.

The contract row is the one that had to be argued. Three sources were
tried: `inventory()` answers where a `SCHEMA` constant is declared
(`bga.schemas` for 24 of 25), the module's own text does not name its
id at all, and what is left is the name. So the join is by name, it
places 14 of 25, and `unplaced()` names the rest rather than letting a
partial row read as a complete one - `UX-376`'s rule.
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

import dev_impact

from bga import contracts

SKILL = REPO / ".claude/skills/decompose/SKILL.md"


class TestTheSetNamesWhatTheChangeReaches:
    """`UX-687`'s acceptance, on the module it names."""

    def _report(self):
        return dev_impact.report("bga/correlate.py")

    def test_the_contract_the_module_serves_is_named(self):
        assert "correlate/v2" in self._report()["contracts"]

    def test_the_guide_that_walks_the_command_is_named(self):
        rows = self._report()["guides"]
        assert any("real-project" in row for row in rows), rows[:5]

    def test_the_join_guard_is_named(self):
        rows = self._report()["guards"]
        assert any("test_correlate" in row for row in rows), rows[:5]

    def test_an_open_filing_on_the_same_topic_is_named(self):
        assert self._report()["filings"], "no open row on the module's topic"


class TestTheContractRowSaysWhatItCannotPlace:
    """A partial row that reads as complete is the defect `UX-376`
    named: the census that does not say what it could not assess."""

    def test_every_contract_is_placed_or_named_unplaced(self):
        placed = set()
        for module in (REPO / "bga").rglob("*.py"):
            placed |= set(dev_impact.contracts_of(
                str(module.relative_to(REPO))))
        assert placed | set(dev_impact.unplaced()) == set(
            contracts.inventory()), "a contract is neither placed nor named"

    def test_the_unplaced_set_is_not_everything(self):
        """A join that places nothing would pass the clause above."""
        assert len(dev_impact.unplaced()) < len(contracts.inventory()) / 2


class TestTheSkillSendsTheReaderToTheTool:
    """`UX-687`: decompose's surfaces step becomes run-and-paste."""

    def test_decompose_names_the_tool(self):
        assert "dev_impact.py" in SKILL.read_text(encoding="utf-8")
