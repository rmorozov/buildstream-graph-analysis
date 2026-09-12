"""UX-821: a CI job that runs a dev tool installs what the tool imports.

`UX-698` gave the two junit readers a `defusedxml` import; the three
adopt jobs on the default branch run them on a bare interpreter, and
had been red on `ModuleNotFoundError` at every push since 2026-09-08.
The gate is on pull requests, where those jobs never run, so nothing
saw it. This reads `ci.yml`: every `python tools/<x>.py` step whose
tool imports a third-party module sits after a `pip install` step in
the same job. The import walk follows the tool's own `tools/` imports
(`dev_touch_map` reaches `defusedxml` through `dev_tier_drift`).
"""
import ast
import importlib.util
import pathlib
import re
import sys
import sysconfig

import yaml

REPO = pathlib.Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github/workflows/ci.yml"
TOOLS = REPO / "tools"
TOOL_RUN = re.compile(r"python3?\s+tools/(dev_\w+)\.py")
INSTALL = re.compile(r"pip install .*(\[dev\]|requirements\.lock)")


def _is_stdlib(root):
    names = getattr(sys, "stdlib_module_names", None)
    if names is not None:
        return root in names
    spec = importlib.util.find_spec(root)
    if spec is None:
        return False
    origin = spec.origin or ""
    if origin in ("built-in", "frozen"):
        return True
    return (origin.startswith(sysconfig.get_paths()["stdlib"])
            and "site-packages" not in origin)


def third_party_imports(tool, seen=None):
    """Root modules `tools/<tool>.py` imports that are neither stdlib
    nor this repository's, following its `tools/` imports."""
    seen = set() if seen is None else seen
    if tool in seen:
        return set()
    seen.add(tool)
    tree = ast.parse((TOOLS / f"{tool}.py").read_text(encoding="utf-8"))
    roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            roots.add(node.module.split(".")[0])
    found = set()
    for root in roots:
        if (TOOLS / f"{root}.py").exists():
            found |= third_party_imports(root, seen)
        elif root in ("bga", "tests", "tools") or _is_stdlib(root):
            continue
        else:
            found.add(root)
    return found


def _jobs():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))["jobs"]


def _tool_steps():
    """(job, tool, installed-before) for every step running a tool."""
    for name, job in _jobs().items():
        installed = False
        for step in job.get("steps", []):
            run = str(step.get("run", ""))
            if INSTALL.search(run):
                installed = True
            for tool in TOOL_RUN.findall(run):
                yield name, tool, installed


def test_the_population_is_not_empty():
    needing = [(job, tool) for job, tool, _ in _tool_steps()
               if third_party_imports(tool)]
    assert len(needing) >= 3, (
        f"only {needing} run a tool with a third-party import; the three "
        "adopt jobs are what this guard was filed on")


def test_the_walk_follows_a_tool_into_the_tool_it_imports():
    assert "defusedxml" in third_party_imports("dev_touch_map"), (
        "dev_touch_map reaches defusedxml through dev_tier_drift; a walk "
        "that stops at the first file passes the job that failed")


def test_every_job_running_a_tool_installs_what_it_imports():
    bare = [(job, tool, sorted(third_party_imports(tool)))
            for job, tool, installed in _tool_steps()
            if not installed and third_party_imports(tool)]
    assert not bare, (
        "job(s) run a tool on a bare interpreter: "
        f"{bare} - a pip install step must come first; the adopt jobs were "
        "red on ModuleNotFoundError from 2026-09-08 to 2026-09-12")
