"""UX-906: the shim's own policies are the ground truth for section 7a's
register, derived from its ast rather than a hand-kept set - a new
`return ..., "x"` in `kind_job_env`/`_ninja_aware_env` is a policy the
register has to carry a row for, or this reddens.

holds: docs/design/continuous-build-improvement.md#7a
"""
import ast
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SHIM = REPO / "tools" / "native_trace" / "bwrap_shim.py"
DESIGN_DOC = REPO / "docs" / "design" / "continuous-build-improvement.md"
STATES = {"guarded", "known-unguarded", "unexamined"}


def _derive_policies() -> set:
    """The third element of every `return (pairs, unsets, policy)` tuple
    in `kind_job_env`/`_ninja_aware_env`, with a bare `Name` resolved
    either against a module-level string constant or, for `base_policy`,
    against the literal each call site passes."""
    tree = ast.parse(SHIM.read_text(encoding="utf-8"))
    module_consts = {
        node.targets[0].id: node.value.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Assign) and len(node.targets) == 1
        and isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, ast.Constant) and isinstance(node.value.value, str)
    }
    funcs = {
        node.name: node for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef)
        and node.name in ("kind_job_env", "_ninja_aware_env")
    }
    assert set(funcs) == {"kind_job_env", "_ninja_aware_env"}, \
        "the two functions the Decision names must both exist"

    policies = set()
    for func in funcs.values():
        for node in ast.walk(func):
            if isinstance(node, ast.Return) and isinstance(node.value, ast.Tuple) \
                    and len(node.value.elts) == 3:
                third = node.value.elts[2]
                if isinstance(third, ast.Constant) and isinstance(third.value, str):
                    policies.add(third.value)
                elif isinstance(third, ast.Name) and third.id in module_consts:
                    policies.add(module_consts[third.id])
                # else: a bare parameter (`base_policy`) - resolved below,
                # from what each call site actually passes.

    for node in ast.walk(funcs["kind_job_env"]):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id == "_ninja_aware_env":
            arg = node.args[3] if len(node.args) > 3 else next(
                (kw.value for kw in node.keywords if kw.arg == "base_policy"), None)
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                policies.add(arg.value)

    return policies


def _register_rows() -> list:
    """The `## 7a.` section's table rows as dicts, keyed by header cell."""
    text = DESIGN_DOC.read_text(encoding="utf-8")
    start = text.index("## 7a.")
    end = text.index("\n## 8.", start)
    section = text[start:end]
    lines = [ln for ln in section.splitlines() if ln.strip().startswith("|")]
    assert len(lines) >= 3, "the register table must have a header and rows"
    header = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = []
    for line in lines[2:]:
        cells = [c.strip() for c in line.strip("|").split("|")]
        rows.append(dict(zip(header, cells)))
    return rows


def _strip_md(cell: str) -> str:
    return re.sub(r"[`*]", "", cell).strip()


def test_every_derived_policy_appears_in_some_row():
    policies = _derive_policies()
    row_policies = {_strip_md(row["policy"]) for row in _register_rows()}
    missing = policies - row_policies
    assert not missing, f"policies with no register row: {sorted(missing)}"


def test_every_state_cell_is_one_of_the_three_words():
    for row in _register_rows():
        state = _strip_md(row["state"])
        assert state in STATES, f"{row['corner case']!r} has an unknown state {state!r}"


def test_every_guarded_rows_evidence_path_exists():
    for row in _register_rows():
        if _strip_md(row["state"]) == "guarded":
            evidence = _strip_md(row["evidence"])
            assert evidence != "-", f"{row['corner case']!r} is guarded with no evidence"
            assert (REPO / evidence).exists(), \
                f"{row['corner case']!r} names a guard that does not exist: {evidence}"


def test_every_known_unguarded_rows_ux_id_has_a_task_file():
    for row in _register_rows():
        if _strip_md(row["state"]) == "known-unguarded":
            ux_id = _strip_md(row["evidence"])
            number = ux_id.removeprefix("UX-")
            padded = f"UX-{int(number):04d}"
            matches = list((REPO / "docs" / "backlog" / "scenarios").glob(f"{padded}-*.md"))
            assert matches, f"{row['corner case']!r} names {ux_id!r}, no task file matches"


def test_every_unexamined_row_carries_no_evidence():
    for row in _register_rows():
        if _strip_md(row["state"]) == "unexamined":
            assert _strip_md(row["evidence"]) == "-", \
                f"{row['corner case']!r} is unexamined but carries evidence"
