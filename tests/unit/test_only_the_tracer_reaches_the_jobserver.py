"""UX-901: the jobserver is a subtool behind an import boundary.

An AST walk, the same shape as `test_no_absolute_tools_import_survives`:
only `tools/bst_native_build_tracer.py` may import `tools.jobserver`,
only a name in its `__all__` (never a submodule reached directly), and
`bga/**` and the package itself may never import it or reach back into
the tracer/`bga`. The shim is the one exception, named below.
"""
import ast
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[2]
JOBSERVER_PKG = REPO / "tools" / "jobserver"
TRACER = REPO / "tools" / "bst_native_build_tracer.py"
#: This guard itself reads `__all__` to check the tracer's own import -
#: the one other legitimate import, named so the sweep does not flag it.
THIS_FILE = pathlib.Path(__file__).resolve()

#: The shim names the tracer's own `Broker` may import - `bwrap_shim.py`
#: is the one thing besides stdlib `tools/jobserver/` may reach.
SHIM_ALLOWED_NAMES = {"JOBSERVER_PINNED"}


def _all_names() -> set:
    import tools.jobserver as jobserver
    return set(jobserver.__all__)


def _module_paths() -> list:
    """The product code the Decision bounds: `bga/` and `tools/`, never a
    stale agent worktree under `.claude/worktrees/`."""
    return sorted(p for root in ("bga", "tools") for p in (REPO / root).rglob("*.py"))


def _jobserver_import_sites(path: pathlib.Path):
    """`(lineno, kind, detail)` for every way `path` reaches
    `tools.jobserver` - a whole-package import, a submodule import, or
    a `from tools.jobserver import NAME` naming something outside
    `__all__`."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    all_names = _all_names()
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "tools.jobserver":
                    found.append((node.lineno, "package", alias.name))
                elif alias.name.startswith("tools.jobserver."):
                    found.append((node.lineno, "submodule", alias.name))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            is_absolute_pkg = module == "tools.jobserver"
            is_absolute_submodule = module.startswith("tools.jobserver.")
            is_relative_submodule = (
                node.level > 0 and module in ("pool", "ledger")
                and path.is_relative_to(JOBSERVER_PKG))
            if is_absolute_submodule:
                found.append((node.lineno, "submodule", module))
            elif is_absolute_pkg and not is_relative_submodule:
                for alias in node.names:
                    if alias.name not in all_names:
                        found.append(
                            (node.lineno, "undeclared", f"{module}.{alias.name}"))
    return found


class TestOnlyTheTracerImportsTheJobserver:

    def test_no_module_but_the_tracer_imports_it(self):
        offenders = []
        for path in _module_paths():
            if path in (TRACER, THIS_FILE) or path.is_relative_to(JOBSERVER_PKG):
                continue
            for lineno, kind, detail in _jobserver_import_sites(path):
                offenders.append(f"{path.relative_to(REPO)}:{lineno} {kind} {detail}")
        assert not offenders, (
            "only tools/bst_native_build_tracer.py may import "
            "tools.jobserver (UX-901's import boundary):\n  "
            + "\n  ".join(offenders))

    def test_the_tracer_reaches_no_submodule_and_no_undeclared_name(self):
        offenders = [
            f"{TRACER.relative_to(REPO)}:{lineno} {kind} {detail}"
            for lineno, kind, detail in _jobserver_import_sites(TRACER)
            if kind != "package"]
        assert not offenders, (
            "the tracer must reach tools.jobserver only through its "
            "declared __all__, never a submodule directly:\n  "
            + "\n  ".join(offenders))

    def test_bga_never_imports_the_jobserver(self):
        offenders = []
        for path in sorted((REPO / "bga").rglob("*.py")):
            for lineno, kind, detail in _jobserver_import_sites(path):
                offenders.append(f"{path.relative_to(REPO)}:{lineno} {kind} {detail}")
        assert not offenders, (
            "bga/** must never import tools.jobserver:\n  " + "\n  ".join(offenders))


def _package_import_sites(path: pathlib.Path):
    """Every `import`/`from` in one `tools/jobserver/*.py` module naming
    the tracer or `bga` - the boundary's other direction."""
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "bga" or alias.name.startswith("bga."):
                    found.append((node.lineno, f"import {alias.name}"))
                if "bst_native_build_tracer" in alias.name:
                    found.append((node.lineno, f"import {alias.name}"))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level == 0 and (module == "bga" or module.startswith("bga.")):
                found.append((node.lineno, f"from {module} import ..."))
            if "bst_native_build_tracer" in module:
                found.append((node.lineno, f"from {module} import ..."))
    return found


class TestThePackageReachesNeitherTracerNorBga:

    def test_no_jobserver_module_imports_the_tracer_or_bga(self):
        offenders = []
        for path in sorted(JOBSERVER_PKG.glob("*.py")):
            for lineno, detail in _package_import_sites(path):
                offenders.append(f"{path.relative_to(REPO)}:{lineno} {detail}")
        assert not offenders, (
            "tools/jobserver/ imports stdlib and the shim only, never the "
            "tracer or bga (UX-901's Decision):\n  " + "\n  ".join(offenders))

    def test_the_shim_names_the_package_may_import_are_declared(self):
        """`bwrap_shim` is the one non-stdlib import the package may make
        - only the names this file declares, from `pool.py` alone."""
        import ast as _ast

        pool = JOBSERVER_PKG / "pool.py"
        tree = _ast.parse(pool.read_text(encoding="utf-8"), filename=str(pool))
        shim_names = set()
        for node in _ast.walk(tree):
            if isinstance(node, _ast.ImportFrom) and node.module and (
                    node.module.endswith("bwrap_shim")):
                shim_names.update(alias.name for alias in node.names)
        assert shim_names == SHIM_ALLOWED_NAMES, (
            f"pool.py imports {shim_names or 'nothing'} from the shim; the "
            f"declared list is {SHIM_ALLOWED_NAMES}")

    def test_the_scan_actually_reads_modules(self):
        """A walk that found no files would pass every clause above."""
        modules = list(JOBSERVER_PKG.glob("*.py"))
        assert len(modules) >= 3, (
            f"only {len(modules)} modules under tools/jobserver/ - the "
            "package had 3 (__init__, pool, ledger) when this was written")


def test_the_tracer_binds_both_readers():
    """An unbound reader degrades silently (no busy-core signal, no live
    pid refresh), so importing the tracer must leave both bound to its own."""
    from tools import bst_native_build_tracer as tracer
    from tools.jobserver import pool
    assert pool.cpu_sampler is tracer.read_cpu_sample
    assert pool.pid_to_element_reader is tracer.read_pid_to_element
