"""UX-905: Direction 20's status block cites a real-core reading with no
committed capture behind it - the Graviton runs are not fixtures. So the
guard is on what *can* be checked from a clone: the paragraph names a
`run <id>`, names the two files that reproduce it, and every leg name it
cites is a case the script still handles and the workflow can still
select - a renamed or deleted leg reddens even though the run itself
never will.
"""
import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
DIRECTIONS = REPO / "docs/design/directions.md"
SCRIPT = REPO / "examples/11-serial-giant/graviton_arms.sh"
WORKFLOW = REPO / ".github/workflows/codspeed-probe.yml"

ANCHOR = "The real-core reading (`UX-905`"
RUN_ID = re.compile(r"\brun (\d{5,})\b")
LEG = re.compile(r"`(pairs|cap3|overhead|diag)`")


def _paragraph():
    """The reading's own sentence run, to the end of the Status line it
    lives in - the whole status is one un-wrapped paragraph."""
    text = DIRECTIONS.read_text(encoding="utf-8")
    start = text.index(ANCHOR)
    end = text.index("\n", start)
    return text[start:end]


def _script_legs():
    """The case arms `graviton_arms.sh` actually dispatches on, from its
    own `case $MODE in` block - not a copy of the list, so a renamed or
    removed arm reddens this rather than a second literal."""
    text = SCRIPT.read_text(encoding="utf-8")
    start = text.index("case $MODE in")
    block = text[start:text.index("esac", start)]
    legs = set()
    for match in re.finditer(r"^\s*([a-z0-9|]+)\)", block, re.M):
        pattern = match.group(1)
        if pattern == "*":
            continue
        legs.update(pattern.split("|"))
    return legs


def test_the_paragraph_exists():
    assert ANCHOR in DIRECTIONS.read_text(encoding="utf-8"), (
        "Direction 20's real-core reading has moved or was removed")


def test_it_names_a_run_id():
    assert RUN_ID.search(_paragraph()), (
        "the real-core reading names no `run <id>` - it would be a "
        "measurement with no way back to what produced it")


def test_it_names_the_procedure_that_reproduces_it():
    para = _paragraph()
    assert "graviton_arms.sh" in para, (
        "the reading names no script - not reproducible from the prose alone")
    assert "codspeed-probe.yml" in para, (
        "the reading names no workflow - nothing says how the script is invoked")


def test_every_leg_it_cites_is_one_the_script_still_handles():
    cited = set(LEG.findall(_paragraph()))
    assert cited, "no leg name found in the reading - nothing to check"
    handled = _script_legs()
    missing = sorted(cited - handled)
    assert missing == [], (
        f"the reading cites leg(s) {missing} that graviton_arms.sh's own "
        f"case arms no longer handle: {sorted(handled)}")


def test_the_workflow_selects_its_leg_from_the_matrix_not_a_literal():
    """Reads the dispatch generically - `${{ matrix.leg }}` - rather than
    pinning today's `[pairs, cap3]`, so adding or renaming a matrix leg
    does not require touching this guard."""
    text = WORKFLOW.read_text(encoding="utf-8")
    assert "graviton_arms.sh" in text
    assert re.search(r"graviton_arms\.sh\s+\$\{\{\s*matrix\.leg\s*\}\}", text), (
        "the workflow's Arms step no longer passes matrix.leg through - "
        "a leg the reading names could be one the job never runs")
