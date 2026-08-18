"""UX-85: the findings layer is decided once, and nothing may quietly
re-decide it.

`UX-75` moved every "what is worth saying" judgement into
`bga.findings`, leaving `bga.report.text` importing it under the historic
private names. The imports stayed, and a full duplicate of four of them
was left below in the same module, shadowing them - production went
through `bga.findings`, while `tests/unit/test_correlate.py` and
`tests/unit/test_realizable_saving.py` imported the *shadow* to guard
`UX-71`'s "analyze and correlate cannot name different elements first"
invariant. Two implementations, one guarded, free to drift: exactly the
failure mode `UX-75` shipped to remove, and exactly how `UX-76`'s
regression happened the first time.

These tests are cheap and they fail loudly the moment a convenience copy
reappears - which is the only reason they exist.
"""
import ast

from bga import findings
from bga.report import text


def test_the_report_aliases_are_the_findings_objects_themselves():
    """Not "equal to" - *the same object*. A re-implementation that
    happens to agree today passes an equality check and fails this one,
    which is the point."""
    assert text._heaviest_on_path is findings.heaviest_on_path
    assert text._path_elements_by_duration is findings.path_elements_by_duration
    assert text._confidence_band is findings.confidence_band
    assert text._efficiency_band is findings.efficiency_band
    assert text._structural_kind_tag is findings.structural_kind_tag
    assert text._OPPORTUNITY_FLOOR_PCT is findings.OPPORTUNITY_FLOOR_PCT
    assert text._CHAIN_BOUND_RATIO is findings.CHAIN_BOUND_RATIO


def _module_level_bindings(module_path: str):
    """Every name bound at module scope, with the count of bindings.

    Parsed rather than imported: after import, a shadow is invisible -
    the module object holds whichever binding ran last, and `is`-identity
    against `bga.findings` is the only trace. The source is where a
    second binding is still visible.
    """
    tree = ast.parse(open(module_path).read())
    counts: dict = {}
    for node in tree.body:
        names = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names = [node.name]
        elif isinstance(node, ast.Assign):
            names = [t.id for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names = [node.target.id]
        for name in names:
            counts[name] = counts.get(name, 0) + 1
    return counts


def test_no_name_is_bound_twice_at_module_scope_in_the_renderer():
    """The general form of the bug, not the four instances of it: any
    module-level name bound twice in `bga/report/text.py` is either a
    shadow or a typo, and both are worth failing on."""
    counts = _module_level_bindings(text.__file__)
    duplicated = sorted(name for name, n in counts.items() if n > 1)
    assert duplicated == [], (
        "re-bound at module scope in bga/report/text.py: "
        f"{duplicated}. If it is imported from bga.findings at the top of "
        "the file, do not redefine it below - that is UX-85."
    )
