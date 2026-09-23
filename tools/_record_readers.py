"""UX-942: the tests that read a changed record through a tool.

`dev_touching.select` greps for a changed path; a guard reaching
`tests/flake_ledger.json` as `dev_flake_census.load()` names neither the
path nor a changed module. This derives that edge from the tool's AST:
its constant spelling the record's path, the functions reading it on
their default path, and the tests calling one without passing a path.
"""
import ast
import functools
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]


def _spelled(node, names):
    """The repo-relative path `REPO / "tests" / "x.json"` spells, or None."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        left, right = _spelled(node.left, names), node.right
        if left is None or not (isinstance(right, ast.Constant)
                                and isinstance(right.value, str)):
            return None
        return f"{left}/{right.value}".lstrip("/")
    if isinstance(node, ast.Name):
        return names.get(node.id)
    # `Path(__file__).resolve().parents[1]`: the repository, from `tools/`.
    if (isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute)
            and node.value.attr == "parents"
            and isinstance(node.slice, ast.Constant) and node.slice.value == 1):
        return ""
    return None


def _on_default(call, param):
    """Whether `call` leaves a reader's path parameter to its default."""
    if param is None:
        return True
    index, name = param
    return len(call.args) <= index and name not in {k.arg for k in call.keywords}


@functools.cache
def _tree(source):
    # A file mid-edit that does not parse is read as empty, not a crash.
    try:
        return ast.parse(source)
    except SyntaxError:
        return ast.Module(body=[], type_ignores=[])


def _paths(tree):
    """`{module constant: the repo-relative path its chain spells}`."""
    names = {}
    for node in tree.body:
        if (isinstance(node, ast.Assign) and len(node.targets) == 1
                and isinstance(node.targets[0], ast.Name)):
            spelled = _spelled(node.value, names)
            if spelled is not None:
                names[node.targets[0].id] = spelled
    return names


def _reads_directly(fn, constants, names, record):
    """`(index, name)` for a parameter defaulting to the record, `None` for a
    parameterless body spelling it, `False` for neither."""
    a = fn.args
    positional = a.posonlyargs + a.args
    first = len(positional) - len(a.defaults)
    for i, (arg, default) in enumerate(zip(positional[first:], a.defaults)):
        if isinstance(default, ast.Name) and default.id in constants:
            return (first + i, arg.arg)
    if positional or a.kwonlyargs or a.vararg or a.kwarg:
        return False
    return None if any(
        (isinstance(n, ast.Name) and n.id in constants)
        or (isinstance(n, ast.BinOp) and _spelled(n, names) == record)
        for n in ast.walk(fn)) else False


@functools.cache
def _readers(source, record):
    """One tool's `{constants}` spelling `record`, and `{function: param}`
    for each reading it on its default path - directly, or by calling
    one that does without passing the path (`None`)."""
    tree = _tree(source)
    names = _paths(tree)
    constants = {name for name, spelled in names.items() if spelled == record}
    fns = [f for f in tree.body if isinstance(f, ast.FunctionDef)]
    readers = {}
    for fn in fns:
        param = _reads_directly(fn, constants, names, record)
        if param is not False:
            readers[fn.name] = param
    grew = True
    while grew:
        grew = False
        for fn in fns:
            if fn.name not in readers and any(
                    isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    and n.func.id in readers
                    and _on_default(n, readers[n.func.id])
                    for n in ast.walk(fn)):
                readers[fn.name] = None
                grew = True
    return constants, readers


def _reads(tree, stem, constants, readers):
    """What in one test's `tree` reads a tool's record on its default path."""
    modules, direct = set(), {}
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            modules |= {a.asname or a.name for a in n.names
                        if a.name in (stem, f"tools.{stem}")}
        elif isinstance(n, ast.ImportFrom) and n.module == "tools":
            modules |= {a.asname or a.name for a in n.names if a.name == stem}
        elif isinstance(n, ast.ImportFrom) and n.module in (stem, f"tools.{stem}"):
            direct.update({a.asname or a.name: a.name for a in n.names})
    reasons = set()
    for n in ast.walk(tree):
        target = n.func if isinstance(n, ast.Call) else n
        if (isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name)
                and target.value.id in modules):
            name = target.attr
        elif isinstance(target, ast.Name) and target.id in direct:
            name = direct[target.id]
        else:
            continue
        if n is target and name in constants:
            reasons.add(f"{stem}.{name}")
        elif n is not target and name in readers and _on_default(n, readers[name]):
            reasons.add(f"{stem}.{name}()")
    return reasons


def record_readers(record, tools, tests):
    """`UX-942`: `{test: [reasons]}` for the tests that load `record`
    through a tool - `census.load()`, `drift.CI_REFERENCE` - naming
    neither it nor a changed module. `tools` and `tests` map a name to
    its source; a call passing its own path (a `tmp_path`) is not a
    read of the committed record, so it does not select."""
    base = pathlib.PurePosixPath(record).name
    found = {}
    for stem, source in sorted(tools.items()):
        if base not in source:
            continue
        constants, readers = _readers(source, record)
        if not (constants or readers):
            continue
        for test, text in sorted(tests.items()):
            if stem in text:
                reasons = _reads(_tree(text), stem, constants, readers)
                if reasons:
                    found.setdefault(test, set()).update(reasons)
    return {test: sorted(reasons) for test, reasons in found.items()}


@functools.cache
def _tool_sources():
    return {p.stem: p.read_text(encoding="utf-8")
            for p in sorted((REPO / "tools").glob("*.py"))}


def choose(chosen, why, path, test_files, text_of):
    """Add to `dev_touching.select`'s `chosen`/`why` the tests reading `path`
    through a tool; nothing for a module, which the grep already names."""
    if path.endswith(".py"):
        return
    corpus = {c: text_of(c) for c in test_files()}
    found = record_readers(path, _tool_sources(),
                           {c: t for c, t in corpus.items() if t is not None})
    for candidate, reads in found.items():
        chosen[candidate] = True
        why.setdefault(candidate, []).append(f"{path} via {', '.join(reads)}")
