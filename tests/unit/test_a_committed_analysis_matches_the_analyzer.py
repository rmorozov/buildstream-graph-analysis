"""UX-486: a committed analysis is what the analyzer emits, or it is
a document about a version of bga that no longer exists.

`tests/fixtures/with_timeline/analyze.json` is read by several guards
as if it were the analyzer's output. It was one old run of it, frozen,
and it drifted **four findings** behind before anything spoke:

```text
committed   ... mesh-graph, joint-saving, ...
analyzer    ... chain-graph, blast-radius-reach, blast-radius-structural,
                graph-width, joint-saving, ...
```

Three findings round 73 added reached this fixture and were not in it,
and one it carried - `mesh-graph` - is a verdict `UX-475` re-decided;
on this run the analyzer says `chain-graph`. The clause that finally
spoke was in another file entirely and only because `UX-469` changed a
*field* it compares against live code. Nothing compared the document's
**shape** with what the analyzer emits.

`tests/fixtures/golden/mixed_task_kinds/expected_output.json` has had
that comparison since P3-08. This file gives the other fixture the same
one, and `tools/dev_refresh_analysis.py` is where the rule that makes
either reproducible now lives - once, rather than in a docstring, a
test helper and a skill.
"""
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import dev_refresh_analysis as refresh


@pytest.mark.parametrize(
    "fixture", refresh.FIXTURES, ids=lambda f: f.name.split("/")[-1])
def test_the_committed_document_is_the_one_the_analyzer_emits(fixture):
    found = refresh.differences(fixture)
    assert found == [], (
        f"{fixture.name} disagrees with a fresh analysis:\n"
        + "\n".join(f"  {where}: {what}" for where, what in found)
        + f"\n\nRefresh it with:\n"
        f"    python3 tools/dev_refresh_analysis.py --write {fixture.name}\n"
        f"and read `git diff` to confirm the change you intended is the "
        f"only one.")


class TestTheRuleIsOneRuleAndItIsStated:
    """What a committed analysis may hold, held. Three keys of the
    analyzer's output are properties of the *machine*, and a fixture
    that carried them would fail on the first release rather than on
    the first regression."""

    def test_no_committed_document_carries_the_machine(self):
        for fixture in refresh.FIXTURES:
            held = fixture.committed()
            for key in refresh.MACHINE_KEYS:
                assert key not in held, (
                    f"{fixture.name} carries `{key}`, which names the "
                    f"machine or the build rather than the analysis")

    def test_no_committed_document_carries_an_absolute_path(self):
        """`UX-218`'s next-step commands name the run directory,
        because a command that did not name it would not be runnable -
        so the directory is rewritten to a token and the commands
        themselves are still compared."""
        for fixture in refresh.FIXTURES:
            text = fixture.into.read_text(encoding="utf-8")
            assert str(REPO) not in text, (
                f"{fixture.name} carries this machine's checkout path, so "
                f"it can only match on this machine")
            assert fixture.token in text, (
                f"{fixture.name} carries neither the path nor the "
                f"{fixture.token} token, so the rewrite is not being "
                f"applied and the commands name nothing")

    def test_the_rule_is_written_where_a_regenerating_reader_looks(self):
        """The recipe was in a docstring, a test helper and a skill, and
        the fixture with no recipe is the one that drifted. It is a
        command now, and the command says what it drops and why."""
        text = (REPO / "tools/dev_refresh_analysis.py").read_text(
            encoding="utf-8")
        for key in refresh.MACHINE_KEYS:
            assert key in text, key
        assert "--write" in text and "git diff" in text, (
            "the tool does not tell a reader to check the diff it wrote, "
            "which is the step that turns a refresh into a decision")


class TestTheDifferenceIsLegibleBeforeItIsFixed:
    """A guard that says "the document differs" and not *how* sends a
    reader to a 3,000-line diff. The finding ids are the shape of the
    document, and they are what this reports first."""

    def test_a_missing_finding_is_named_rather_than_counted(self):
        fixture = refresh.FIXTURES[-1]
        real = fixture.analysed()

        class Trimmed:
            name, token, into = fixture.name, fixture.token, fixture.into
            analysed = staticmethod(lambda: real)

            @staticmethod
            def committed():
                held = dict(real)
                held["findings"] = [f for f in real["findings"]
                                    if f["id"] != "graph-width"]
                return held

        found = dict(refresh.differences(Trimmed))
        assert "findings" in found, found
        assert "graph-width" in found["findings"], found["findings"]
