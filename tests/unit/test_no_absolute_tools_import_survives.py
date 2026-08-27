"""UX-325: `bga/` may not import `tools.` by name, and the sweep is honest.

Three times now the same defect has shipped: `UX-77` (`bga wrap`),
`UX-203` (the viewer's assets), `UX-325` (`bga snapshot --aggregate`).
Every one is a line in `bga/` that reads

    from tools.something import a_name

which resolves in a checkout - where the repository root is on
`sys.path` and `tools/` is a directory beside `bga/` - and raises
`ModuleNotFoundError` in a wheel, where the same directory installs as
`bga._tools` (`UX-94`). A test suite run from the repository root can
never see the difference.

Two guards, deliberately different in kind:

* **The static one, here.** No module under `bga/` names `tools` in an
  `import` statement. It costs nothing, it covers every line rather
  than every reachable line, and it is the only thing standing between
  the next such import and a user - because two of the three sites
  `UX-325` fixed (`hostinfo.collect`, `cli._element_completer`) are not
  reachable from any command a CI runner can invoke.
* **The behavioural one**, `tests/installed_command_sweep.py`, run by
  the packaging job against a wheel in a clean venv. It cannot cover
  everything; what it covers, it covers for real.

This file also holds the sweep's *coverage* honest, because a sweep
that quietly stops naming a command is the failure mode the hand-written
list had.
"""
import ast
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tests.installed_command_sweep import (  # noqa: E402
    OK, PARSE_ONLY, REFUSES, Fixtures, documented_commands, invocations)

PACKAGE = REPO / "bga"


def _tools_imports(path: pathlib.Path):
    """Every `import tools…` / `from tools… import …` in one module.

    An AST walk, not a grep: `_import_tool("tools.bga_snapshot")` passes
    the same text as a *string*, and that one is the fix rather than the
    defect. Only the import statements count.
    """
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "tools" or alias.name.startswith("tools."):
                    found.append((node.lineno, f"import {alias.name}"))
        elif isinstance(node, ast.ImportFrom):
            # `level > 0` is a relative import: `from .tools_dispatch`
            # is fine and is what the fix uses.
            if node.level == 0 and node.module and (
                    node.module == "tools" or node.module.startswith("tools.")):
                found.append((node.lineno, f"from {node.module} import …"))
    return found


class TestThePackageNeverNamesTools:

    def test_no_module_under_bga_imports_tools_absolutely(self):
        offenders = []
        for path in sorted(PACKAGE.rglob("*.py")):
            for lineno, text in _tools_imports(path):
                offenders.append(f"{path.relative_to(REPO)}:{lineno}  {text}")
        assert not offenders, (
            "an absolute `tools.` import is back in the shipped package. It "
            "works in this checkout and raises ModuleNotFoundError on every "
            "`pip install` - UX-77, UX-203 and UX-325 were each one of "
            "these. Route it through `bga.tools_dispatch._import_tool`, "
            "which tries `tools.X` and then `bga._tools.X`:\n  "
            + "\n  ".join(offenders))

    def test_the_scan_actually_reads_modules(self):
        """A walk that found no files would pass the clause above."""
        modules = list(PACKAGE.rglob("*.py"))
        assert len(modules) >= 20, (
            f"only {len(modules)} modules under bga/; the package had 40-odd "
            "when this was written and a near-empty scan asserts nothing")

    def test_the_dispatcher_is_the_one_place_that_may(self):
        """`_import_tool` exists precisely to hold the fallback once."""
        from bga.tools_dispatch import _import_tool

        module = _import_tool("tools.bga_snapshot")
        assert module.__name__ in ("tools.bga_snapshot", "bga._tools.bga_snapshot"), (
            f"_import_tool resolved to {module.__name__}, which is neither "
            "shape it exists to bridge")


class TestTheSweepCoversWhatTheDocsPromise:

    def test_every_documented_command_has_a_sweep_entry(self, tmp_path):
        plan = invocations(Fixtures(tmp_path))
        missing = sorted(documented_commands() - set(plan))
        assert not missing, (
            f"{missing} have a row in the architecture's command table and no "
            "entry in the sweep. That is the round-12 hand-list defect: the "
            "documented surface grew and the installed-mode exercise did not.")

    def test_no_sweep_entry_names_an_undocumented_command(self, tmp_path):
        plan = invocations(Fixtures(tmp_path))
        stale = sorted(set(plan) - documented_commands())
        assert not stale, (
            f"the sweep invokes {stale}, which the command table does not "
            "list - either the row was dropped or the entry has rotted")

    def test_every_parse_only_entry_says_why(self, tmp_path):
        plan = invocations(Fixtures(tmp_path))
        for command, (verdict, detail) in sorted(plan.items()):
            if verdict == PARSE_ONLY:
                assert isinstance(detail, str) and len(detail) > 40, (
                    f"{command} is parse-only with no written reason. "
                    "Parse-only is the sweep's one judgement and it is the "
                    "shape the old hand-list had for every command.")
            else:
                assert isinstance(detail, list) and detail[0] == command, (
                    f"{command}'s argv does not start with the command")

    def test_parse_only_stays_a_small_minority(self, tmp_path):
        """If most commands end up parse-only the sweep has become the
        `--help` loop it replaced."""
        plan = invocations(Fixtures(tmp_path))
        parse_only = [c for c, (v, _) in plan.items() if v == PARSE_ONLY]
        assert len(parse_only) <= len(plan) // 4, (
            f"{len(parse_only)} of {len(plan)} documented commands are "
            f"parse-only ({sorted(parse_only)}); the sweep was 3 of 21 when "
            "it was written, and it is a real-invocation sweep or it is "
            "nothing")

    def test_the_aggregate_is_swept_for_real(self, tmp_path):
        """The defect UX-325 was filed for, named rather than counted."""
        verdict, argv = invocations(Fixtures(tmp_path)).get(
            "snapshot", (PARSE_ONLY, "no entry at all"))
        assert verdict == OK and "--aggregate" in argv, (
            "`bga snapshot --aggregate` is no longer really invoked by the "
            "sweep. It is the command that shipped broken to every user for "
            "eleven rounds, and a `--help` does not touch its import.")

    def test_the_refusals_are_refusals(self, tmp_path):
        """A REFUSES entry that starts succeeding is a stale entry, not a
        pass - so at least one exists to keep the branch exercised."""
        plan = invocations(Fixtures(tmp_path))
        refusals = [c for c, (v, _) in plan.items() if v == REFUSES]
        assert refusals, (
            "no command is swept through its refusal path any more; a clean "
            "one-line refusal is the other half of 'the module loaded'")
