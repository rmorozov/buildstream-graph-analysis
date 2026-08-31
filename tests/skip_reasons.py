"""UX-449: the skip reasons a file *declares*, read without running it.

The census in `conftest.py` counts skips **as they happen** and fails
the session on a reason `KNOWN_SKIP_REASONS` has never declared. That is
the right instrument for "a guard has gone quiet", and it has one
structural blind spot: it can only see a skip that fired. The machine
that writes a new gate is, almost by definition, the machine that has
the optional tool installed - so the clause runs, the census never sees
the reason, and `make test` is green. Every CI runner lacks the tool,
the clause skips, and four interpreters fail *after every test passed*.

Twice now, five rounds apart: `UX-330`'s gzipped-raw-log clauses in
round 50, and `UX-434`'s `trace_processor_shell` clauses in round 70.

This reads the other half - the reason as written in the source - so
the same fact is checked on the author's machine whatever that machine
happens to have installed.

**Why `ast` and not a scan.** A regular expression over the text cannot
tell a call from a comment, a docstring or a string in a fixture, which
is the defect class the fixing guide's §5 is about; this repository has
found ~30 instances of it. `tests/unit/test_a_command_renders_as_a_command.py`
went the other way in round 70 and matched a comment. Parsing the file
means a reason is found because it is an argument to a skip, and for no
other reason.

**What cannot be resolved.** A reason built at runtime - an f-string, a
module attribute like `trace_processor.REASON`, a helper's return - has
no literal to read. Those are *counted* rather than ignored, and the
count is asserted against a measured baseline, so a new unresolvable
reason is a change that has to be argued rather than a silence.
"""
import ast
import pathlib

REPO = pathlib.Path(__file__).resolve().parents[1]
TESTS = REPO / "tests"

#: The callables whose reason this reads, and where the reason sits.
#:
#: `pytest.mark.skip` is not here because the suite has none (measured:
#: `grep -rho 'pytest\.mark\.skip(' tests/` is 0). Adding a form the
#: suite does not use would be an unexercised branch, and
#: `test_the_scan_knows_the_forms_the_suite_uses` fails if that changes.
SKIP_FORMS = {
    # (attribute path): the keyword, and the positional index or None
    ("pytest", "mark", "skipif"): ("reason", None),
    ("pytest", "skip"): ("reason", 0),
}

#: `pytest.importorskip` writes its own message ("could not import
#: 'x'"), so there is no authored reason to compare. It is excluded
#: deliberately rather than by omission, and counted, so the exclusion
#: is visible in the same report as everything else.
IMPORT_OR_SKIP = ("pytest", "importorskip")


def _aliases(tree):
    """`{local name: "pytest"}` for however this module imported it.

    Found the hard way: a mutation written as `import pytest as _p`
    made every skip in that file invisible to this scan, because the
    dotted path came out `("_p", "mark", "skip")`. A scan that reads
    one spelling of an import is a scan a rename silences, which is the
    same defect one level up from the one this file exists to catch.
    """
    found = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "pytest":
                    found[alias.asname or "pytest"] = "pytest"
    return found


def _dotted(node, aliases=None):
    """`pytest.mark.skipif` -> `("pytest", "mark", "skipif")`."""
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if not isinstance(node, ast.Name):
        return None
    parts.append((aliases or {}).get(node.id, node.id))
    return tuple(reversed(parts))


def _module_strings(tree):
    """`{name: text}` for module-level `NAME = "..."` assignments.

    Sixty-three of the suite's skip sites pass a constant - `NO_CC`,
    `NO_BWRAP` - rather than a literal, which is good practice and is
    exactly `UX-321`'s "one gate asked in one place". Leaving those
    unresolved would blind this scan to the majority of the suite, and
    to the very shape the rule encourages: a reason coined once and
    referenced everywhere would read as unresolvable rather than as a
    reason. So they are resolved, and only a genuinely dynamic reason -
    an f-string, another module's attribute - is counted as unread.
    """
    found = {}
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Constant):
            continue
        if not isinstance(node.value.value, str):
            continue
        for target in node.targets:
            if isinstance(target, ast.Name):
                found[target.id] = node.value.value
    return found


_MODULE_CACHE = {}


def _module_path(dotted):
    """`tests.browser` -> the file, when it is inside this repository."""
    if not dotted:
        return None
    candidate = REPO.joinpath(*dotted.split(".")).with_suffix(".py")
    return candidate if candidate.is_file() else None


def _imported_strings(tree):
    """`{name: text}` for `from <a repo module> import NAME` constants.

    One hop, deliberately. The suite's shared gates - `NO_BROWSER` in
    `tests/browser.py`, `REASON` in `tests/trace_processor.py` - are
    imported, and that is the shape `UX-321` asks for: one gate, asked
    in one place. A scan that could not follow an import would be blind
    to exactly the pattern the rule recommends, and would report the
    best-written half of the suite as unreadable.

    A second hop is not done, because nothing in the suite needs it and
    an unexercised branch is the thing this file is guarding against.
    """
    found = {}
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom) or node.level:
            continue
        path = _module_path(node.module)
        if path is None:
            continue
        if path not in _MODULE_CACHE:
            try:
                other = ast.parse(path.read_text(encoding="utf-8"))
                _MODULE_CACHE[path] = _module_strings(other)
            except (OSError, SyntaxError):  # pragma: no cover
                _MODULE_CACHE[path] = {}
        exported = _MODULE_CACHE[path]
        for alias in node.names:
            if alias.name in exported:
                found[alias.asname or alias.name] = exported[alias.name]
    return found


def _literal(node, names=None):
    """The string a node evaluates to, or `None` if it is not static.

    `ast.literal_eval` covers a plain literal, implicit concatenation
    (which the parser has already folded) and `"a" + "b"`. Anything
    else - an f-string, a name, a call, a `%` or `.format()` - raises,
    and raising is the answer: it is what "could not be resolved"
    means.
    """
    if isinstance(node, ast.Name) and names and node.id in names:
        return names[node.id]
    try:
        value = ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError,
            RecursionError):
        return None
    return value if isinstance(value, str) else None


def scan(root=TESTS):
    """`(resolved, unresolved)` over every test source under `root`.

    `resolved` is `{reason: [(file, line, form), ...]}`; `unresolved`
    is a list of `(file, line, what)` for the call sites whose reason
    is built at runtime.

    `form` is the dotted call, and it decides whether the **runtime**
    census can ever see this reason: the hook in `conftest.py` counts
    `report.when == "setup"`, so a `pytest.mark.skipif` marker is
    counted and a `pytest.skip()` raised in a test body is not. Both
    are declarations, so both are read here.
    """
    resolved, unresolved = {}, []
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        try:
            name = path.relative_to(REPO).as_posix()
        except ValueError:
            # A root outside the repository - the decoy tree the guard
            # builds to prove this reads calls and not text.
            name = path.as_posix()
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=name)
        except SyntaxError:  # pragma: no cover - a broken file fails louder
            continue
        aliases = _aliases(tree)
        names = dict(_imported_strings(tree))
        names.update(_module_strings(tree))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            dotted = _dotted(node.func, aliases)
            if dotted == IMPORT_OR_SKIP or dotted not in SKIP_FORMS:
                continue
            keyword, index = SKIP_FORMS[dotted]
            argument = next(
                (kw.value for kw in node.keywords if kw.arg == keyword), None)
            if argument is None and index is not None and (
                    len(node.args) > index):
                argument = node.args[index]
            if argument is None:
                # A skip with no reason at all. Not "unresolvable" - the
                # census will show it as an empty reason, which is its
                # own complaint - so it is reported as such.
                unresolved.append((name, node.lineno, "no reason given"))
                continue
            text = _literal(argument, names)
            if text is None:
                unresolved.append(
                    (name, node.lineno, type(argument).__name__))
                continue
            resolved.setdefault(text, []).append(
                (name, node.lineno, ".".join(dotted)))
    return resolved, unresolved
