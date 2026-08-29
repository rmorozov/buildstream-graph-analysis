"""UX-398: the library question, answered against the factory.

`UX-397` filed the Tabulator question with one argument for adoption -
a library would answer sorting, filtering and virtual scrolling "in one
dependency rather than in twenty-one modules". Measured, the premise is
false, and the measurement is the whole answer:

```text
$ grep -rn 'el("table"' bga/viewer/*.js
bga/viewer/structured.js:435

viewer modules                21
modules that construct a table 1
```

Every table on the page - 31 of them on the round-63 export - is built
by one factory, which already owns the column specs, the sorting, the
preset menus, Top-N, fold-the-middle, the density strip, the copy
control and `interrogable`'s filter bar. So a behaviour wanted on all
31 tables is one change to one function, which is the economics a
library is adopted for, already owned.

That premise is what styleguide §6b's dependency rule rests on, and a
premise nothing holds is a premise that rots: the second module to
hand-roll a `<table>` would falsify the rule silently, and the next
person to ask the question would be argued at with a stale number.

**This file holds the premise, not the conclusion.** It does not assert
that no library may ever be adopted - §6b prices candidates rather than
blacklisting them. It asserts that the sentence the price is computed
from is still true.
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

VIEWER = REPO / "bga/viewer"
STYLEGUIDE = REPO / "docs/design/styleguide.md"

#: The one module allowed to construct a table element.
THE_FACTORY = "structured.js"

#: The factory's two entry points. `buildTable` returns a table for a
#: cell; `renderTable` wraps one in a section. `UX-292` split them and
#: the split is why a nested table stopped being listed as a section.
ENTRY_POINTS = ("buildTable", "renderTable")


def _modules():
    return sorted(VIEWER.glob("*.js"))


def _section_6b():
    text = STYLEGUIDE.read_text(encoding="utf-8")
    body = text.split("## 6b.", 1)
    assert len(body) == 2, "styleguide §6b is gone"
    return "## 6b." + body[1].split("\n## ", 1)[0]


def test_one_module_constructs_a_table():
    """The premise, measured the way the styleguide states it."""
    builders = [path.name for path in _modules()
                if re.search(r'el\(\s*["\']table["\']', path.read_text("utf-8"))]
    assert builders == [THE_FACTORY], (
        "styleguide §6b prices a JS dependency against a single table "
        "factory. These modules construct a table of their own, so the "
        f"rule's premise no longer holds: {builders}")


def test_the_factory_publishes_the_entry_points_the_page_uses():
    """A caller outside the factory reaches it by name, not by copy."""
    source = (VIEWER / THE_FACTORY).read_text(encoding="utf-8")
    for name in ENTRY_POINTS:
        assert f"export function {name}" in source, (
            f"{name} is the factory's entry point named in styleguide "
            f"§6b; it is no longer exported from {THE_FACTORY}")

    callers = [path.name for path in _modules()
               if path.name != THE_FACTORY
               and any(f"{name}(" in path.read_text("utf-8")
                       for name in ENTRY_POINTS)]
    assert callers, (
        "no module outside the factory calls it, which would mean the "
        "page's tables are built somewhere this guard is not looking")


def test_the_dependency_rule_states_both_of_its_conditions():
    """§6b is a rule with two clauses; one clause is not the rule.

    A dependency admitted on bytes alone, or on convenience alone, is
    the decision this section exists to prevent - so both halves have to
    survive an edit of the section, not just its heading.
    """
    section = _section_6b()
    for clause, what in (
            ("volume budget", "the export-size half of the rule"),
            ("undercuts", "the wiring-plus-conformance half of the rule"),
            ("trackevent", "the named prior the rule is drawn from"),
            ("buildTable", "the factory the price is measured against")):
        assert clause in section, (
            f"styleguide §6b no longer states {what} ({clause!r})")


def test_the_rule_carries_the_measurement_it_was_written_from():
    """A rule quoting no number is an opinion.

    `UX-398`'s whole content is that the argument for a library was
    checked rather than weighed, so the section keeps the command that
    produced the check.
    """
    section = _section_6b()
    assert 'el("table"' in section, (
        "styleguide §6b no longer pastes the command that measured the "
        "factory; the next person to ask the question would have to "
        "re-derive it, which is how the false premise got in")
