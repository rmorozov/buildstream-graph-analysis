#!/usr/bin/env python3
"""UX-956: the test files a docs-only pull request's lane runs.

    git diff --name-only REF | python3 tools/dev_docs_lane.py --list
    git diff --name-only REF | python3 tools/dev_docs_lane.py --run [pytest args]

Whether a diff is docs only is `dev_docs_only.py`'s. The lane is
`dev_touching.select(diff)` - the grep, the census, the map - plus
`doc_readers()`: the test files that read documents by a population
the grep cannot key, derived from their own AST - a walk (`glob`,
`rglob`, ...) or `git ls-files` whose receiver or arguments reach a
docs constant (`"docs"`, `".claude"`, a `.md` pattern), or a
reference to a function of `bga/`, `tools/` or a `tests/` helper
that does, closed over calls across those modules. Over-selection is
the safe direction; `test_a_docs_only_diff_runs_its_guards.py` holds
the derivation to a textual witness and the workflow to both tools.
"""
import argparse
import ast
import functools
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "tools"))

import dev_touching

FUNCTIONS = (ast.FunctionDef, ast.AsyncFunctionDef)
WALKS = {"glob", "rglob", "iglob", "iterdir", "walk", "listdir", "scandir"}
SHELLS = {"run", "check_output", "check_call", "call", "Popen"}


def _docsish(value) -> bool:
    return isinstance(value, str) and (
        value == "docs" or value.startswith(("docs/", ".claude"))
        or ".md" in value)


def _nodes(scope):
    """`ast.walk`, except that a module does not descend into a function."""
    if not isinstance(scope, ast.Module):
        yield from ast.walk(scope)
        return
    todo: list[ast.AST] = list(scope.body)
    while todo:
        node = todo.pop()
        yield node
        if not isinstance(node, FUNCTIONS):
            todo.extend(ast.iter_child_nodes(node))


def _bound_by(node):
    """`(target, value)` pairs one statement binds."""
    if isinstance(node, ast.Assign):
        return [(target, node.value) for target in node.targets]
    if isinstance(node, (ast.AnnAssign, ast.NamedExpr)) and node.value:
        return [(node.target, node.value)]
    if isinstance(node, (ast.For, ast.AsyncFor, ast.comprehension)):
        return [(node.target, node.iter)]
    if isinstance(node, FUNCTIONS):
        args = node.args.args[len(node.args.args) - len(node.args.defaults):]
        return list(zip(args, node.args.defaults))
    return []


def _bindings(scope):
    """`{name: [expr]}` for every binding a walk's receiver could be in
    `scope`: assignments, loop targets and argument defaults."""
    bound = {}
    for node in _nodes(scope):
        for target, value in _bound_by(node):
            for name in ast.walk(target):
                if isinstance(name, (ast.Name, ast.arg)):
                    key = name.id if isinstance(name, ast.Name) else name.arg
                    bound.setdefault(key, []).append(value)
    return bound


def _scopes(tree):
    """`(scope, bindings)`: the module, then each function with the
    module's bindings under its own."""
    module = _bindings(tree)
    yield tree, module
    for fn in ast.walk(tree):
        if isinstance(fn, FUNCTIONS):
            own = _bindings(fn)
            yield fn, {k: own.get(k, []) + module.get(k, [])
                       for k in {*own, *module}}


def _reaches_docs(expr, bound, seen):
    for node in ast.walk(expr):
        if isinstance(node, ast.Constant) and _docsish(node.value):
            return True
        if isinstance(node, ast.Name) and node.id not in seen:
            seen.add(node.id)
            if any(_reaches_docs(e, bound, seen) for e in bound.get(node.id, ())):
                return True
    return False


def _walks_docs(node, bound) -> bool:
    """A walk or a `git ls-files` in `node`'s scope that can reach a doc."""
    for call in _nodes(node):
        if not isinstance(call, ast.Call) or not isinstance(call.func, ast.Attribute):
            continue
        if call.func.attr in WALKS:
            parts = [call.func.value, *call.args, *(k.value for k in call.keywords)]
            if any(_reaches_docs(part, bound, set()) for part in parts):
                return True
        elif (call.func.attr in SHELLS and call.args
              and isinstance(call.args[0], (ast.List, ast.Tuple))):
            argv = [e.value if isinstance(e, ast.Constant)
                    and isinstance(e.value, str) else "" for e in call.args[0].elts]
            spec = [a for a in argv[2:] if a and not a.startswith("-")]
            if (argv[:2] == ["git", "ls-files"] and "--error-unmatch" not in argv
                    and (not spec or any(map(_docsish, spec)))):
                return True
    return False


def _parse(path):
    try:
        return ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError, ValueError):
        return None


def _imports(tree):
    """`({local alias: module stem}, {local name: (stem, function)})`."""
    modules, functions = {}, {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                stem = alias.name.split(".")[-1]
                modules[alias.asname or stem] = stem
        elif isinstance(node, ast.ImportFrom):
            base = (node.module or "").split(".")[-1]
            for alias in node.names:
                local = alias.asname or alias.name
                modules[local] = alias.name
                functions[local] = (base, alias.name)
    return modules, functions


def _reaches_a_walker(node, imports, found, local=frozenset()) -> bool:
    """A reference in `node` to a doc-walking function: a same-module
    name in `local`, `module.function`, or a function imported by name."""
    modules, functions = imports
    for ref in ast.walk(node):
        if isinstance(ref, ast.Name):
            stem, name = functions.get(ref.id, (None, None))
            if ref.id in local or name in found.get(stem, ()):
                return True
        elif isinstance(ref, ast.Attribute) and (ref.attr in local or (
                isinstance(ref.value, ast.Name)
                and ref.attr in found.get(modules.get(ref.value.id), ()))):
            return True
    return False


@functools.cache
def walkers():
    """`{module stem: {function}}` over `bga/`, `tools/` and the `tests/`
    helpers: a function that walks docs, or reaches one that does."""
    helpers = [p for p in (REPO / "tests").glob("*.py")
               if not p.name.startswith("test_")]
    trees = {path: _parse(path) for path in [
        *(REPO / "bga").rglob("*.py"), *(REPO / "tools").glob("*.py"), *helpers]
        if "__pycache__" not in path.parts}
    trees = {path: tree for path, tree in trees.items() if tree}
    found = {}
    for path, tree in trees.items():
        found.setdefault(path.stem, set()).update(
            scope.name for scope, bound in _scopes(tree)
            if scope is not tree and _walks_docs(scope, bound))
    imports = {path: _imports(tree) for path, tree in trees.items()}
    grew = True
    while grew:
        grew = False
        for path, tree in trees.items():
            hit = found[path.stem]
            for fn in ast.walk(tree):
                if (isinstance(fn, FUNCTIONS)
                        and fn.name not in hit
                        and _reaches_a_walker(fn, imports[path], found, hit)):
                    hit.add(fn.name)
                    grew = True
    return {stem: names for stem, names in found.items() if names}


@functools.cache
def doc_readers():
    """The test files that read documents by a population, sorted."""
    found, chosen = walkers(), []
    for name in dev_touching.test_files():
        path = REPO / name
        tree = _parse(path)
        if tree is None:
            continue
        text = path.read_text(encoding="utf-8")
        if (any(_walks_docs(*scope) for scope in _scopes(tree))
                or _reaches_a_walker(tree, _imports(tree), found)
                or any(f"{stem}.py" in text or f"tools.{stem}" in text
                       for stem in found)):
            chosen.append(name)
    return tuple(chosen)


def lane(paths):
    """What the lane runs for `paths`: the selector's set and the readers."""
    selected, _why = dev_touching.select(paths)
    return sorted(set(selected) | set(doc_readers()))


def main(argv=None, stdin=None) -> int:
    parser = argparse.ArgumentParser(description="the docs lane's test files")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--list", action="store_true")
    mode.add_argument("--run", action="store_true")
    args, rest = parser.parse_known_args(argv)
    paths = [p.strip() for p in (stdin or sys.stdin).read().splitlines() if p.strip()]
    chosen = lane(paths)
    if args.list:
        print("\n".join(chosen))
        return 0
    print(f"{len(chosen)} test file(s) in the docs lane", file=sys.stderr)
    import pytest

    return int(pytest.main([*(str(REPO / c) for c in chosen), "-q", "-n", "auto",
                            *rest]))


if __name__ == "__main__":
    sys.exit(main())
