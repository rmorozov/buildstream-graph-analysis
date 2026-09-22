"""`UX-939`: the version CI installs and the version the facts claim.

`docs/spec/ingestion-pipeline.md`'s "Last exercised on" line used to
name two versions because the tier ran in two environments and nothing
pinned either. `UX-571`'s guard reads the binary, so it only fires
where a binary exists - a container without `bst` skips it, which is
every session container, so a runner image moving the version reddened
CI and nothing else.

`ci.yml` pins `BST_VERSION` now. This asks the one question that needs
no binary: does the pin say what the document says. Both move together
or neither moves.
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DOC = REPO / "docs" / "spec" / "ingestion-pipeline.md"
WORKFLOW = REPO / ".github" / "workflows" / "ci.yml"

PINNED = re.compile(r'^\s*BST_VERSION:\s*"(?P<version>[0-9]+(?:\.[0-9]+)*)"\s*$', re.M)
EXERCISED = re.compile(r"\*\*Last exercised on `bst` (?P<version>[0-9]+(?:\.[0-9]+)*), ")


def pinned():
    found = PINNED.findall(WORKFLOW.read_text(encoding="utf-8"))
    assert found, "ci.yml declares no BST_VERSION"
    assert len(set(found)) == 1, f"ci.yml pins more than one version: {found}"
    return found[0]


def documented():
    found = EXERCISED.findall(DOC.read_text(encoding="utf-8"))
    assert found, "the document has no 'Last exercised on' line"
    return found


def test_the_workflow_pins_one_bst_version():
    assert pinned()


def test_every_exercised_line_names_the_pinned_version():
    """One version, not a set: `UX-939`'s finding is that a second
    entry named an environment nothing could read."""
    assert documented(), "no exercised line"
    assert set(documented()) == {pinned()}, (
        f"ci.yml pins {pinned()}; the document says {sorted(set(documented()))}. "
        f"Bump both - they are one decision")


def test_every_install_uses_the_pin_rather_than_a_floor():
    """A `pip install buildstream` with no version is what let the
    runner move: the floor in `pyproject.toml`'s extras resolves to
    whatever is newest that day."""
    body = WORKFLOW.read_text(encoding="utf-8")
    loose = [line.strip() for line in body.splitlines()
             if re.search(r"pip install\b.*\bbuildstream(-plugins)?\b", line, re.I)
             and "==" not in line]
    assert loose == [], f"unpinned buildstream install(s) in ci.yml: {loose}"
