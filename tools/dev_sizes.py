"""UX-712: the size ledger - counts for what has no finding identity.

    python3 tools/dev_sizes.py --check           # the ratchet
    python3 tools/dev_sizes.py --adopt           # writes only shrunk cells
    python3 tools/dev_sizes.py --adopt --force   # a moved-up cell too

Three counts per file under `bga`, `tools`, `.claude/hooks` (`tests/**`
is `UX-690`'s own ledger): the longest function's lines (`ast`), the
file's own line count, and pylint's `duplicate-code` (R0801) block
count - the one pip-installable measure with no finding identity of
its own. Counts only, never seconds (`UX-702` is the timing ledger).
`tests/quality_reference.json` holds one row per file, sorted; a cell
may only shrink. `--adopt` writes a shrunk cell and adds a file's first
row; it refuses to move any cell up without `--force`.
"""
import argparse
import ast
import collections
import json
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]
DEFAULT_PATHS = ("bga", "tools", ".claude/hooks")
DEFAULT_REFERENCE = REPO / "tests" / "quality_reference.json"
CELLS = ("longest_function", "file_lines", "duplicate_blocks")

#: A `duplicate-code` message's own participant lines: `==module:[a:b]`.
DUP_LINE = re.compile(r"^==([\w.]+):\[(\d+):(\d+)\]$")

#: pylint's exit code is a bitmask; 8 is the `refactor` category R0801
#: sets and nothing else can, since every other check is disabled.
PYLINT_OK_CODES = (0, 8)


class PylintFailure(Exception):
    """pylint's answer cannot be trusted: a bad exit or unreadable output."""


def iter_py_files(root, paths):
    root = pathlib.Path(root)
    for rel in paths:
        base = root / rel
        if base.is_file() and base.suffix == ".py":
            yield base
        elif base.is_dir():
            yield from sorted(base.rglob("*.py"))


def longest_function_lines(text):
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return 0
    longest = 0
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            end = getattr(node, "end_lineno", None)
            if end is not None:
                longest = max(longest, end - node.lineno + 1)
    return longest


def module_index(root, files):
    """Both ways pylint names a file - the full dotted path from
    `root` (`bga.ingest.__init__`, and `bga` for the package's own
    `__init__.py`), and the bare stem it falls back to for a directory
    with no `__init__.py` of its own (`.claude/hooks`, in this repo).
    A bare stem shared by more than one file maps to nothing rather
    than to either."""
    dotted, bare = {}, collections.defaultdict(set)
    for path in files:
        parts = path.relative_to(root).with_suffix("").parts
        rel = path.relative_to(root).as_posix()
        dotted[".".join(parts)] = rel
        stem_parts = parts[:-1] if parts[-1] == "__init__" else parts
        if stem_parts:
            dotted[".".join(stem_parts)] = rel
            bare[stem_parts[-1]].add(rel)
    return dotted, {stem: rel for stem, rels in bare.items()
                    if len(rels) == 1 for rel in rels}


def duplicate_blocks(root, paths, files):
    """Per-file R0801 count. pylint attributes every finding in a run
    to whichever module it happened to be analysing last, not to the
    files the duplication is actually in - a proxy this reads around
    by parsing the `==module:[start:end]` lines out of the message
    body instead, which name the real participants, and resolving
    those against `module_index` rather than the filesystem."""
    root = pathlib.Path(root).resolve()
    dotted, bare = module_index(root, files)
    cmd = ["pylint", "--disable=all", "--enable=duplicate-code",
           "--output-format=json", *paths]
    run = subprocess.run(cmd, cwd=root, capture_output=True, text=True,
                         check=False)
    if run.returncode not in PYLINT_OK_CODES:
        raise PylintFailure(f"pylint exited {run.returncode}: {run.stderr.strip()}")
    try:
        raw = json.loads(run.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise PylintFailure(f"pylint did not print JSON: {exc}") from exc
    counts = collections.Counter()
    for item in raw:
        if item.get("symbol") != "duplicate-code":
            continue
        files_in_group = set()
        for line in item.get("message", "").splitlines():
            match = DUP_LINE.match(line.strip())
            if not match:
                continue
            module = match.group(1)
            rel = dotted.get(module) or bare.get(module.split(".")[-1])
            if rel is not None:
                files_in_group.add(rel)
        for rel in files_in_group:
            counts[rel] += 1
    return counts


def measure(root, paths):
    root = pathlib.Path(root).resolve()
    paths_found = list(iter_py_files(root, paths))
    dup = duplicate_blocks(root, paths, paths_found)
    files = {}
    for path in paths_found:
        rel = path.relative_to(root).as_posix()
        text = path.read_text(encoding="utf-8", errors="replace")
        files[rel] = {
            "longest_function": longest_function_lines(text),
            "file_lines": len(text.splitlines()),
            "duplicate_blocks": dup.get(rel, 0),
        }
    return files


def load_reference(path):
    path = pathlib.Path(path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_reference(path, files, paths):
    body = ",\n".join(
        f"    {json.dumps(rel)}: {json.dumps(files[rel], sort_keys=True)}"
        for rel in sorted(files))
    text = ("{\n"
            f'  "paths": {json.dumps(sorted(set(paths)))},\n'
            '  "files": {\n' + (body + "\n" if body else "") + "  }\n"
            "}\n")
    pathlib.Path(path).write_text(text, encoding="utf-8")


def grown_cells(current, reference):
    """`(file, cell, old, new)` for every cell present in `reference`
    that reads higher now - files new to `current` are not judged, the
    same "recorded, not judged" shape `UX-503` gave a reference this
    tool otherwise follows."""
    grown = []
    for rel, before in sorted(reference.items()):
        after = current.get(rel)
        if after is None:
            continue
        for cell in CELLS:
            if after[cell] > before.get(cell, 0):
                grown.append((rel, cell, before.get(cell, 0), after[cell]))
    return grown


def do_check(args, current, existing):
    if existing is None:
        print(f"no reference at {args.reference} - run --adopt first")
        return 1
    grown = grown_cells(current, existing["files"])
    for rel, cell, before, after in grown:
        print(f"grew: {rel} {cell} {before} -> {after}")
    if grown:
        return 1
    print(f"sizes ok: {len(current)} file(s) measured, "
          f"none above the cell {args.reference} records")
    return 0


def do_adopt(args, current, existing):
    before_files = (existing or {}).get("files", {})
    merged = dict(before_files)
    changed = 0
    blocked = []
    for rel, after in sorted(current.items()):
        before = before_files.get(rel)
        if before is None:
            merged[rel] = after
            changed += 1
            continue
        row = dict(before)
        for cell in CELLS:
            if after[cell] < before.get(cell, 0):
                row[cell] = after[cell]
                changed += 1
            elif after[cell] > before.get(cell, 0):
                if args.force:
                    row[cell] = after[cell]
                    changed += 1
                else:
                    blocked.append((rel, cell, before.get(cell, 0), after[cell]))
        merged[rel] = row
    if blocked and not args.force:
        for rel, cell, before, after in blocked:
            print(f"refused: {rel} {cell} {before} -> {after} - rerun with "
                  "--force to move a cell upward")
        return 1
    write_reference(args.reference, merged, args.paths or list(DEFAULT_PATHS))
    print(f"wrote {len(merged)} file(s) to {args.reference} "
          f"({changed} cell(s) changed)")
    return 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--adopt", action="store_true")
    parser.add_argument("--force", action="store_true",
                         help="with --adopt, allow moving a cell upward")
    parser.add_argument("--reference", type=pathlib.Path, default=DEFAULT_REFERENCE)
    parser.add_argument("--root", type=pathlib.Path, default=REPO)
    parser.add_argument("--paths", nargs="+", default=None)
    args = parser.parse_args(argv)
    if sum((args.check, args.adopt)) != 1:
        parser.error("exactly one of --check, --adopt")

    paths = args.paths or list(DEFAULT_PATHS)
    try:
        current = measure(args.root, paths)
    except PylintFailure as exc:
        print(f"error: {exc}")
        return 2
    existing = load_reference(args.reference)

    if args.adopt:
        return do_adopt(args, current, existing)
    return do_check(args, current, existing)


if __name__ == "__main__":
    sys.exit(main())
