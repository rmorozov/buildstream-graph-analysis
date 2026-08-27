#!/usr/bin/env python3
"""UX-340: the viewer's dependency graph, derived rather than guessed.

`UX-337` moved half the viewer between modules, and its Required Fix
opens *"the dependency graph between the chapters is derived (not
guessed) before anything moves"*. The first derivation was wrong, and it
was wrong in the way that does not announce itself: it reported a
**cleaner** answer than the truth.

Counting which symbols cross a proposed cut means ignoring the ones that
only appear in a comment or a string - a docstring naming `render` is
not a call to `render`. That was done with regexes, and the
template-literal pattern, written to skip `${…}` so an interpolated
expression stayed visible, failed to match any template that had one.
Its opening backtick then paired with some later backtick and everything
between vanished:

```text
app.js's declarations, raw   1,124 lines
after block comments         1,024
after line comments          1,024
after template literals        148     <- 87% of the file, silently
```

Three real crossings were missing - `PRESETS`, `elementColumn` and
`safeStorage` - each a `ReferenceError` in the concatenated export,
which is `UX-199`'s empty page.

So the scanner below is a character scanner, not a pattern. It exists as
a tool rather than as a scratch file because the next round to move a
function between viewer modules will reach for regexes too.

**What it reads.** The subset this repository writes: ES modules whose
top-level declarations are `function` / `const` / `let` / `var` /
`class`, one per seam, each owning the comment block above it. It is not
a JavaScript parser and does not pretend to be one - a module that
stopped looking like this would need a real one, and the failure would
be visible rather than silent, because `--order` is asserted equal to
the function the export actually uses.
"""
import argparse
import json
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[1]

# A `/` here opens a regex literal rather than dividing. The standard
# heuristic: what can precede a division is a value, and what can
# precede a regex is not.
BEFORE_REGEX = set("(,=:[!&|?{};+-*%<>~^\n") | {""}

DECLARATION = re.compile(
    r"^(?:export\s+)?(?:async\s+)?"
    r"(?:function\s+(\w+)|(?:const|let|var|class)\s+(\w+))")
COMMENT_LINE = re.compile(r"^\s*(//|/\*|\*)")
IMPORT = re.compile(r"""^[ \t]*import\s.*?from\s+["']\./([\w.-]+)["'];?""",
                    re.M | re.S)


def strip_comments(source: str) -> str:
    """`source` with comments removed and string bodies blanked.

    A scanner, because the thing being removed can contain the thing
    that would end it: `//` inside a string is not a comment, a backtick
    inside a comment does not open a template, and a template's `${…}`
    holds real code that must survive. Interpolations are recursed into
    for exactly that reason - a symbol referenced only from inside one
    is still referenced.
    """
    out, i, n, previous = [], 0, len(source), ""
    while i < n:
        char, pair = source[i], source[i:i + 2]
        if pair == "//":
            while i < n and source[i] != "\n":
                i += 1
            continue
        if pair == "/*":
            i += 2
            while i < n and source[i:i + 2] != "*/":
                i += 1
            i, _ = i + 2, out.append(" ")
            continue
        if char in "\"'":
            out.append(" ")
            quote, i = char, i + 1
            while i < n and source[i] != quote:
                i += 2 if source[i] == "\\" else 1
            i, previous = i + 1, "x"
            continue
        if char == "`":
            i, previous = _template(source, i + 1, out), "x"
            continue
        if char == "/" and previous in BEFORE_REGEX:
            out.append(" ")
            i, previous = _regex(source, i + 1), "x"
            continue
        out.append(char)
        if not char.isspace():
            previous = char
        elif char == "\n":
            previous = "\n"
        i += 1
    return "".join(out)


def _template(source: str, i: int, out: list) -> int:
    """Past the closing backtick, keeping what `${…}` holds."""
    n = len(source)
    while i < n:
        if source[i] == "\\":
            i += 2
            continue
        if source[i:i + 2] == "${":
            out.append(" ")
            i += 2
            start, braces = i, 1
            while i < n and braces:
                if source[i] == "{":
                    braces += 1
                elif source[i] == "}":
                    braces -= 1
                i += 1
            out.append(strip_comments(source[start:i - 1]))
            out.append(" ")
            continue
        if source[i] == "`":
            return i + 1
        i += 1
    return i


def _regex(source: str, i: int) -> int:
    """Past a regex literal's closing `/`, minding its character class."""
    n, in_class = len(source), False
    while i < n:
        if source[i] == "\\":
            i += 2
            continue
        if source[i] == "[":
            in_class = True
        elif source[i] == "]":
            in_class = False
        elif source[i] == "/" and not in_class:
            return i + 1
        elif source[i] == "\n":
            return i
        i += 1
    return i


def declarations(path):
    """Every top-level declaration, with the comment block it owns.

    A block starts at the first line of the comment run immediately
    above the declaration, not at the declaration - the prose is the
    seam, and cutting on a line number instead is how a docstring ends
    up attached to the wrong function.
    """
    lines = pathlib.Path(path).read_text(encoding="utf-8").splitlines()
    found = [(m.group(1) or m.group(2), i)
             for i, line in enumerate(lines) if (m := DECLARATION.match(line))]
    if not found:
        return []
    first = found[0][1]
    starts = []
    for name, line in found:
        start = line
        while start - 1 >= first and COMMENT_LINE.match(lines[start - 1]):
            start -= 1
        starts.append((start, name))
    blocks = []
    for k, (start, name) in enumerate(starts):
        end = starts[k + 1][0] if k + 1 < len(starts) else len(lines)
        blocks.append({"name": name, "start": start + 1, "end": end,
                       "exported": lines[found[k][1]].startswith("export "),
                       "text": "\n".join(lines[start:end])})
    return blocks


def imports_of(path):
    text = pathlib.Path(path).read_text(encoding="utf-8")
    return [m.group(1) for m in IMPORT.finditer(text)]


def graph(directory):
    """Every module in `directory` and what it imports."""
    modules = sorted(p.name for p in pathlib.Path(directory).iterdir()
                     if p.suffix == ".js")
    return {name: imports_of(pathlib.Path(directory) / name)
            for name in modules}


def order(directory, entry="app.js"):
    """`entry`'s dependencies first, the way the export inlines them.

    Deliberately the same walk as `tools/bga_view.py::_module_order`,
    and asserted equal to it: an instrument that agrees with the thing
    it describes only by coincidence is not an instrument.
    """
    edges, seen, out = graph(directory), set(), []

    def walk(name):
        if name in seen:
            return
        seen.add(name)
        for needed in edges.get(name, ()):
            walk(needed)
        out.append(name)

    walk(entry)
    return out


def cycles(directory):
    """Every import cycle, as the list of modules that closes it."""
    edges, found = graph(directory), []
    colour = {}

    def walk(name, path):
        if colour.get(name) == "done":
            return
        if colour.get(name) == "open":
            found.append(path[path.index(name):] + [name])
            return
        colour[name] = "open"
        for needed in edges.get(name, ()):
            walk(needed, path + [name])
        colour[name] = "done"

    for name in edges:
        walk(name, [])
    return found


PARAMETERS = re.compile(
    r"^(?:export\s+)?(?:async\s+)?(?:function\s+\w+\s*|"
    r"(?:const|let|var)\s+\w+\s*=\s*(?:async\s*)?)\((.*?)\)", re.S)


def bound_names(text: str):
    """The names the declaration's own parameter list binds.

    `expandControl(path, label, render, breadcrumb)` reads `render()` in
    its body and means its parameter, not the top-level `render`.
    `UX-337` had to notice that by eye and write it down; here it is
    subtracted. Only the declaration's own list - this is not a scope
    analysis, and a name shadowed by an inner `const` still counts as a
    reference. That limit is worth stating rather than papering over:
    the tool removes comments, strings and parameters, and what is left
    is a superset of the real edges, not the exact set.
    """
    found = PARAMETERS.match(strip_comments(text))
    if not found:
        return set()
    return set(re.findall(r"\b([A-Za-z_$][\w$]*)\b", found.group(1)))


def crossings(path, groups):
    """Which symbols each group would have to import from which other.

    `groups` maps a group name to the declaration names in it. Comments
    and string bodies are gone before a name is counted, so a docstring
    mentioning `render` and a parameter called `render` both stay out of
    the answer - both were false edges in `UX-337`'s first derivation.
    """
    blocks = {b["name"]: b for b in declarations(path)}
    home = {name: group for group, names in groups.items() for name in names}
    unplaced = sorted(set(blocks) - set(home))
    needed = {}
    for name, block in blocks.items():
        body = strip_comments(block["text"])
        bound = bound_names(block["text"])
        for word in sorted(set(re.findall(r"\b(\w+)\b", body)) - bound):
            if word in home and home[word] != home.get(name):
                needed.setdefault((home.get(name), home[word]), []).append(word)
    return {"unplaced": unplaced,
            "crossings": {f"{a} <- {b}": sorted(v)
                          for (a, b), v in sorted(needed.items())}}


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--order", metavar="DIR",
                        help="the order the export inlines DIR's modules in")
    parser.add_argument("--graph", metavar="DIR",
                        help="every module and what it imports, plus cycles")
    parser.add_argument("--declarations", metavar="FILE",
                        help="FILE's top-level declarations and their spans")
    parser.add_argument("--crossings", metavar="FILE",
                        help="which symbols would cross a proposed cut of FILE")
    parser.add_argument("--groups", metavar="JSON",
                        help="the proposed grouping: {group: [names]}, a file "
                             "or a literal. Required by --crossings")
    parser.add_argument("--entry", default="app.js",
                        help="the module --order walks from (default app.js)")
    parser.add_argument("--json", action="store_true",
                        help="machine-readable output")
    args = parser.parse_args(argv)

    if args.order:
        names = order(args.order, args.entry)
        loops = cycles(args.order)
        if args.json:
            print(json.dumps({"order": names, "cycles": loops}))
        else:
            print(" ".join(names))
            for loop in loops:
                print(f"CYCLE: {' -> '.join(loop)}", file=sys.stderr)
        return 1 if loops else 0

    if args.graph:
        edges = graph(args.graph)
        loops = cycles(args.graph)
        if args.json:
            print(json.dumps({"imports": edges, "cycles": loops}))
        else:
            for name in sorted(edges):
                print(f"{name:<20} {' '.join(edges[name]) or '-'}")
            for loop in loops:
                print(f"CYCLE: {' -> '.join(loop)}", file=sys.stderr)
        return 1 if loops else 0

    if args.declarations:
        blocks = declarations(args.declarations)
        if args.json:
            print(json.dumps([{k: v for k, v in b.items() if k != "text"}
                              for b in blocks]))
        else:
            for b in blocks:
                mark = "export" if b["exported"] else "     "
                print(f"{b['start']:>6}-{b['end']:<6} {mark} {b['name']}")
        return 0

    if args.crossings:
        if not args.groups:
            parser.error("--crossings needs --groups")
        raw = args.groups
        if pathlib.Path(raw).exists():
            raw = pathlib.Path(raw).read_text(encoding="utf-8")
        result = crossings(args.crossings, json.loads(raw))
        if args.json:
            print(json.dumps(result))
        else:
            for name in result["unplaced"]:
                print(f"UNPLACED: {name}", file=sys.stderr)
            for pair, names in result["crossings"].items():
                print(f"{pair:<28} {' '.join(names)}")
        return 1 if result["unplaced"] else 0

    parser.error("nothing asked for: try --order, --graph, --declarations "
                 "or --crossings")


if __name__ == "__main__":
    sys.exit(main())
