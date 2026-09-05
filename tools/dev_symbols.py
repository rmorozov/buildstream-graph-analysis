#!/usr/bin/env python3
"""`UX-700`: the symbol index, read from the AST rather than grepped.

`orient`'s five lookups return raw lines the session then re-reads.
CodeQL was measured and declined - no `codeql` on PATH, a database
build is minutes for a question `grep -w` mostly answers in
milliseconds. What is left over grep: a string literal or a docstring
that happens to spell a name is not a call (`UX-403`'s shape), and
`ast` tells the two apart for free.

    python3 tools/dev_symbols.py def compute_confidence
    python3 tools/dev_symbols.py callers compute_confidence
    python3 tools/dev_symbols.py importers bga.schemas
    python3 tools/dev_symbols.py fanin bga.schemas
    python3 tools/dev_symbols.py dead --js

Walks `bga/` and `tools/` only; `--tests` adds `tests/`. No index is
kept between runs - the walk is under two seconds, and a cache would
be a second source of truth (`UX-700`'s Out of Scope).
"""
import argparse
import ast
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
DIRS = ("bga", "tools")


def source_files(include_tests):
    """Every `.py` file under the walked directories, sorted."""
    dirs = DIRS + (("tests",) if include_tests else ())
    files = []
    for d in dirs:
        files.extend(sorted((REPO / d).rglob("*.py")))
    return files


def parse(path):
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError:
        return None


def rel(path):
    return str(path.relative_to(REPO))


def module_dotted(path):
    """The dotted module name a file would be imported as."""
    parts = path.relative_to(REPO).with_suffix("").parts
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def package_of(path):
    if path.name == "__init__.py":
        return module_dotted(path)
    dotted = module_dotted(path)
    return dotted.rpartition(".")[0]


def relative_base(path, level):
    pkg = package_of(path).split(".") if package_of(path) else []
    drop = level - 1
    if drop:
        pkg = pkg[:-drop] if drop < len(pkg) else []
    return pkg


def module_to_path(module):
    parts = module.split(".")
    candidate = REPO.joinpath(*parts).with_suffix(".py")
    if candidate.is_file():
        return candidate
    package = REPO.joinpath(*parts, "__init__.py")
    if package.is_file():
        return package
    return None


# ---------------------------------------------------------------- def


def find_definitions(name, include_tests):
    rows = []
    for path in source_files(include_tests):
        tree = parse(path)
        if tree is None:
            continue
        parents = {}
        for node in ast.walk(tree):
            for child in ast.iter_child_nodes(node):
                parents[child] = node
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                continue
            if node.name != name:
                continue
            enclosing = parents.get(node)
            cls = enclosing.name if isinstance(enclosing, ast.ClassDef) else "-"
            kind = ("class" if isinstance(node, ast.ClassDef)
                    else "async def" if isinstance(node, ast.AsyncFunctionDef)
                    else "def")
            rows.append((f"{rel(path)}:{node.lineno}", kind, cls))
    return rows


# ------------------------------------------------------------- callers


def find_callers(name, include_tests):
    """Call nodes whose func name or attribute matches `name`.

    `ast.Call` only - a string literal or a docstring is a `Constant`,
    never a `Call`, so neither can appear here (`UX-403`'s shape).
    """
    rows = []
    for path in source_files(include_tests):
        tree = parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            hit = ((isinstance(func, ast.Name) and func.id == name)
                   or (isinstance(func, ast.Attribute) and func.attr == name))
            if hit:
                rows.append((f"{rel(path)}:{node.lineno}",))
    return rows


# ------------------------------------------------------------ importers


def imported_names(path, node):
    """Every dotted name `node` (an Import/ImportFrom) brings into scope."""
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names]
    base = relative_base(path, node.level) if node.level else []
    if node.module:
        base = [*base, *node.module.split(".")]
    base_str = ".".join(base)
    names = [base_str] if base_str else []
    names += [f"{base_str}.{alias.name}" if base_str else alias.name
              for alias in node.names]
    return names


def find_importers(module, include_tests):
    rows = []
    for path in source_files(include_tests):
        tree = parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)) and module in imported_names(path, node):
                rows.append((rel(path),))
                break
    return rows


def find_fanout(module, include_tests):
    target = module_to_path(module)
    if target is None:
        return []
    tree = parse(target)
    if tree is None:
        return []
    seen = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.Import, ast.ImportFrom)):
            continue
        for name in imported_names(target, node):
            if name.split(".")[0] in DIRS and module_to_path(name) and name not in seen:
                seen.append(name)
    return [(name,) for name in sorted(seen)]


# ----------------------------------------------------------------- dead


def top_level_names(path, tree):
    names = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.append((node.name, node.lineno))
        elif isinstance(node, ast.Assign):
            names += [(t.id, node.lineno) for t in node.targets if isinstance(t, ast.Name)]
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.append((node.target.id, node.lineno))
    # `__all__` and friends are read by tooling, never by name - not an export.
    return [(n, ln) for n, ln in names if not (n.startswith("__") and n.endswith("__"))]


def referenced_names(include_tests):
    """Every identifier used (not merely bound) anywhere in the walk."""
    used = set()
    for path in source_files(include_tests):
        tree = parse(path)
        if tree is None:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
                used.add(node.id)
            elif isinstance(node, ast.Attribute):
                used.add(node.attr)
            elif isinstance(node, ast.ImportFrom):
                used.update(alias.name for alias in node.names)
    return used


def find_dead(include_tests):
    used = referenced_names(include_tests)
    rows = []
    for path in source_files(include_tests):
        if rel(path).split("/")[0] not in DIRS:
            continue
        tree = parse(path)
        if tree is None:
            continue
        for name, lineno in top_level_names(path, tree):
            if name not in used:
                rows.append((f"{rel(path)}:{lineno}", name))
    return rows


def find_dead_js():
    sys.path.insert(0, str(REPO / "tools"))
    import dev_js_deps
    viewer = REPO / "bga" / "viewer"
    js_files = sorted(viewer.glob("*.js"))
    stripped = {p: dev_js_deps.strip_comments(p.read_text(encoding="utf-8")) for p in js_files}
    rows = []
    for path in js_files:
        for block in dev_js_deps.declarations(path):
            if not block["exported"]:
                continue
            pattern = re.compile(rf"\b{re.escape(block['name'])}\b")
            own_text = "\n".join(stripped[path].splitlines()[block["start"] - 1:block["end"]])
            elsewhere = stripped[path].replace(own_text, "", 1)
            hit = pattern.search(elsewhere) or any(
                pattern.search(stripped[p]) for p in js_files if p != path)
            if not hit:
                rows.append((f"{path.relative_to(REPO)}:{block['start']}", block["name"]))
    return rows


# ---------------------------------------------------------------- output


def render(headers, rows, as_json):
    if as_json:
        print(json.dumps([dict(zip(headers, row, strict=True)) for row in rows]))
        return
    widths = [max(len(h), *(len(str(r[i])) for r in rows)) if rows else len(h)
              for i, h in enumerate(headers)]
    print("  ".join(h.ljust(w) for h, w in zip(headers, widths, strict=True)))
    for row in rows:
        print("  ".join(str(c).ljust(w) for c, w in zip(row, widths, strict=True)))


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tests", action="store_true", help="include tests/ in the walk")
    parser.add_argument("--json", action="store_true", help="print JSON instead of a table")
    sub = parser.add_subparsers(dest="command", required=True)
    for cmd in ("def", "callers", "importers", "fanin", "fanout"):
        p = sub.add_parser(cmd)
        p.add_argument("name")
    dead = sub.add_parser("dead")
    dead.add_argument("--js", action="store_true", help="viewer exports, not Python")
    args = parser.parse_args()

    if args.command == "def":
        render(["location", "kind", "class"], find_definitions(args.name, args.tests), args.json)
    elif args.command == "callers":
        render(["location"], find_callers(args.name, args.tests), args.json)
    elif args.command == "importers":
        render(["file"], find_importers(args.name, args.tests), args.json)
    elif args.command == "fanin":
        rows = find_importers(args.name, args.tests)
        if args.json:
            print(json.dumps({"count": len(rows), "files": [r[0] for r in rows]}))
        else:
            print(f"fanin({args.name}) = {len(rows)}")
            render(["file"], rows, False)
    elif args.command == "fanout":
        rows = find_fanout(args.name, args.tests)
        if args.json:
            print(json.dumps({"count": len(rows), "modules": [r[0] for r in rows]}))
        else:
            print(f"fanout({args.name}) = {len(rows)}")
            render(["module"], rows, False)
    elif args.command == "dead":
        rows = find_dead_js() if args.js else find_dead(args.tests)
        render(["location", "name"], rows, args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
