"""UX-354: the workflow reads the payload, and no guard reads the workflow.

Twice, a deliberate contract change was found by a red pull request
rather than by the suite, in the same expression.

`UX-288` bumped `analyze` to v2 and the packaging step asserted the
version literally. `UX-293` fixed that half by reading `ANALYZE` out of
the tree, and wrote down why:

    the one file the suite does not scan

The other half of the same assertion stayed a literal - `d.get('signals')` -
and `UX-344` lifted `signals` away. 4,440 guards passed and CI failed:

```text
AssertionError: the payload has no signals
```

**What this guards, and what it deliberately does not.** Not "a
workflow may not mention a key": the workflows are full of prose that
names `signals` and `structural` as history, and a comment recording
why a step exists is not a claim about today's payload. The property
is narrower and mechanical: **a step that parses a JSON document this
repository produces must not name that document's keys itself.** The
producing module publishes them - `schemas.VERSION_KEY`,
`schemas.ANALYZE_FULL_KEYS`, `bst_baseline_set.trend_order` - and a
step that goes through the publisher cannot drift from it, which is
the whole of `UX-293`'s argument applied to the other half of the
expression it fixed.

Two sites existed when this was written, and both are now indirect:

```text
ci.yml                     d['schema'], d.get('signals')
real-project-capture.yml   json.load(...)["members"], m["run_dir"]
```
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
WORKFLOWS = sorted((REPO / ".github/workflows").glob("*.yml"))

#: A `run:` line that parses JSON. The whole block is then read, because
#: the subscript is usually a line or two below the `json.load`.
_PARSES = re.compile(r"\bjson\.loads?\s*\(")

#: `x['k']`, `x["k"]`, `.get('k')` - a string literal standing where a
#: key goes. Not `sys.argv[1]`, which is a position rather than a key,
#: and not a bare `[0]`. This is the *shape* rule, and it catches a key
#: this repository has never heard of - `'signals'` after `UX-344`
#: removed it - which is the case the item was filed on.
_LITERAL_KEY = re.compile(r"""(?:\.get\s*\(\s*|\[\s*)(['"])([A-Za-z_][\w-]*)\1""")

#: Any quoted string at all, for the *membership* rule below.
_QUOTED = re.compile(r"""(['"])([A-Za-z_][\w/.-]*)\1""")


def _published():
    """Every contract id, and every key a published contract declares.

    The membership rule the shape rule cannot cover. `UX-288`'s defect
    was `key = 'schema'` - a plain assignment, no subscript - and a
    mutation of exactly that form passed the shape rule when this guard
    was first written. The name is not in a subscript, so the only
    thing that makes it a finding is that the package publishes it.
    """
    from bga import contracts, schemas

    names = set(contracts.ids())
    names.update(schemas.ANALYZE_FULL_KEYS)
    for contract in contracts.ids():
        try:
            node = schemas.schema(contract)
        except KeyError:
            continue    # superseded ids keep an id and no body
        names.update((node or {}).get("properties", {}))
    return names


def _run_blocks(text):
    """Every `run:` block, as `(first_line_number, [lines])`.

    Read off the indentation rather than through a YAML parser: the
    parser gives the block's *value* and loses the line numbers, and a
    finding that cannot say `file:line` sends the reader to grep.
    """
    lines = text.splitlines()
    blocks = []
    at = 0
    while at < len(lines):
        opener = re.match(r"^(\s*)(?:-\s+)?run:\s*[|>]?[-+]?\s*$", lines[at])
        if not opener:
            at += 1
            continue
        indent = len(opener.group(1))
        body, cursor = [], at + 1
        while cursor < len(lines):
            line = lines[cursor]
            if line.strip() and len(line) - len(line.lstrip()) <= indent:
                break
            body.append((cursor + 1, line))
            cursor += 1
        blocks.append(body)
        at = cursor
    return blocks


def _code(line):
    """The line with its shell comment removed.

    Crude on purpose: a `#` inside a string would be trimmed too, and
    the cost of that is a *missed* finding rather than a false one -
    which is the right way for a guard over a file nobody else reads
    to be wrong.
    """
    return line.split("#", 1)[0]


def _findings():
    """`(file, line, key, text)` for every literal that names a key.

    Two rules, and the second is not redundant: the shape rule sees a
    subscript whatever the key, the membership rule sees a published
    name wherever it stands.
    """
    published = _published()
    found = []
    for path in WORKFLOWS:
        for block in _run_blocks(path.read_text(encoding="utf-8")):
            if not any(_PARSES.search(_code(line)) for _, line in block):
                continue
            for number, line in block:
                code = _code(line)
                keys = {key for _, key in _LITERAL_KEY.findall(code)}
                keys.update(key for _, key in _QUOTED.findall(code)
                            if key in published)
                for key in sorted(keys):
                    found.append((path.name, number, key, line.strip()))
    return found


def _ids_outside_comments():
    """A published contract id anywhere in a workflow, parsing step or
    not. `UX-293` fixed one of these by reading `ANALYZE` out of the
    tree; a `grep -q "analyze/v4"` added tomorrow is the same defect
    somewhere the parsing-block rule does not look."""
    from bga import contracts

    ids = contracts.ids()
    found = []
    for path in WORKFLOWS:
        for number, line in enumerate(
                path.read_text(encoding="utf-8").splitlines(), 1):
            code = _code(line)
            for contract in ids:
                if contract in code:
                    found.append((path.name, number, contract, line.strip()))
    return found


class TestNoWorkflowNamesAPayloadsKeys:
    def test_the_workflows_are_where_this_expects_them(self):
        """A guard that walks an empty directory passes forever. The
        two files and the one parsing step are the population; if the
        walk finds no JSON-parsing step at all, the instrument has
        stopped reaching the thing it guards."""
        assert len(WORKFLOWS) >= 2, [p.name for p in WORKFLOWS]
        parsing = [path.name for path in WORKFLOWS
                   for block in _run_blocks(path.read_text(encoding="utf-8"))
                   if any(_PARSES.search(_code(line)) for _, line in block)]
        assert parsing, "no workflow step parses JSON - has the walk broken?"

    def test_no_parsing_step_names_a_key_itself(self):
        """The property. `d.get('signals')` is what this is for."""
        bad = _findings()
        assert bad == [], (
            "a workflow step names the keys of a document this repository "
            "produces; the producing module publishes them:\n"
            + "\n".join(f"  {name}:{line}  {key!r}  in  {text}"
                        for name, line, key, text in bad))

    def test_no_step_spells_a_contract_id(self):
        """`UX-288`'s half, at the file's scale rather than the block's:
        `EXPECTED` reads `ANALYZE` from the tree precisely so that no
        version literal sits here to go stale."""
        bad = _ids_outside_comments()
        assert bad == [], (
            "a workflow names a published contract id; read it from the "
            "package or the tree, as the packaging step does:\n"
            + "\n".join(f"  {name}:{line}  {cid}  in  {text}"
                        for name, line, cid, text in bad))


class TestTheIndirectionsExist:
    """The other direction: the step went through a publisher, so the
    publisher has to be there. Without this, deleting `VERSION_KEY` and
    inlining `"schema"` again would trade one guard's red for another's
    silence."""

    def test_the_version_key_is_published(self):
        from bga import schemas

        assert schemas.VERSION_KEY == "schema"

    def test_the_always_present_keys_are_published(self):
        from bga import schemas

        assert len(schemas.ANALYZE_FULL_KEYS) > 20

    def test_the_baseline_set_reads_its_own_document(self, tmp_path):
        """`trend_order` is the module that *writes* the set reading it
        back, and the newest-first to forwards-in-time reversal is the
        rule that used to live in a shell one-liner."""
        import json
        import sys

        sys.path.insert(0, str(REPO))
        from tools.bst_baseline_set import trend_order

        document = tmp_path / "set.json"
        document.write_text(json.dumps({"members": [
            {"run_dir": "/runs/newest"},
            {"run_dir": "/runs/middle"},
            {"run_dir": "/runs/oldest"},
        ]}))
        assert trend_order(str(document)) == [
            "/runs/oldest", "/runs/middle", "/runs/newest"]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
