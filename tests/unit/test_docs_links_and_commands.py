"""Documentation checks that a reader would otherwise have to perform.

Two failures this repository has actually shipped, both cheap to catch
mechanically and neither catchable by reading:

- **A link that does not resolve.** `UX-88` found a code comment whose
  scenario reference had a literal `...` where the filename should have
  been, and a stderr message naming a file that did not exist. Reorganising
  the docs tree into folders makes that failure mode routine rather than
  rare, so it is checked instead of watched for.

- **An instruction telling a user to run the wrong thing.** `UX-77`
  established `bga <alias>` as the front door and shipped a CI job that
  proves every alias runs from a clean install. Documentation then went
  on telling people to run `python3 -m tools.<module>`, which works only
  from a source checkout with the repository root on `sys.path` - so the
  documented command fails for exactly the user who installed the
  package as documented.

Both are style-guide rules (`docs/contributing/style-guide.md`); these are
that can be enforced rather than asked for.
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# `[text](target)` where the target is a repo file, not a URL or a bare
# anchor. Angle-bracket and title forms are not used in this repo.
_LINK_RE = re.compile(r'\[[^\]]*\]\(([^)\s]+)(?:\s+"[^"]*")?\)')

# Instructional documents - the ones that tell a reader what to type.
# `docs/spec/` and the backlog are excluded deliberately: a scenario
# file quoting the command a past round actually ran is a record of what
# happened, and rewriting history to match current style would make it
# false.
INSTRUCTIONAL = [
    "README.md",
    "docs/README.md",
    "docs/contributing",
    "docs/guides",
]


def _markdown_files():
    files = [REPO / "README.md"]
    files += sorted((REPO / "docs").rglob("*.md"))
    return [f for f in files if f.exists()]


def _links(path: Path):
    for match in _LINK_RE.finditer(path.read_text(encoding="utf-8")):
        target = match.group(1)
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        yield target


def test_every_relative_documentation_link_resolves():
    """A dangling link is a promise the docs cannot keep, and after a
    reorganisation it is the default outcome rather than an accident."""
    broken = []
    for path in _markdown_files():
        for target in _links(path):
            # Strip any `#anchor`; the file is what must exist.
            resolved = (path.parent / target.split("#", 1)[0]).resolve()
            if not resolved.exists():
                broken.append(f"{path.relative_to(REPO)} -> {target}")
    assert broken == [], "dangling documentation link(s):\n  " + "\n  ".join(broken)


def _instructional_files():
    files = []
    for entry in INSTRUCTIONAL:
        path = REPO / entry
        if path.is_dir():
            files.extend(sorted(path.rglob("*.md")))
        elif path.exists():
            files.append(path)
    return files


def test_no_instructional_doc_tells_a_user_to_run_python_dash_m_tools():
    """`bga <alias>` is the front door (`UX-77`).

    `python3 -m tools.<module>` works only from a source checkout with
    the repo root on `sys.path`. Telling an installed user to run it
    hands them a `ModuleNotFoundError` - the precise failure `UX-77` was
    filed for, in the document that was supposed to help.

    `docs/guides/cli.md` is where the direct-module form is *documented*
    as still supported, and `docs/contributing/style-guide.md` shows it
    as the anti-pattern. Both carry the `docs-style: allow-direct-module`
    marker; anywhere else is a failure.
    """
    offenders = []
    for path in _instructional_files():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "python3 -m tools." not in line and "python -m tools." not in line:
                continue
            if "docs-style: allow-direct-module" in line:
                continue
            offenders.append(f"{path.relative_to(REPO)}:{number}: {line.strip()}")
    assert offenders == [], (
        "instructional docs must use the `bga <alias>` form, not the direct module "
        "(see docs/contributing/style-guide.md):\n  " + "\n  ".join(offenders)
    )


@pytest.mark.parametrize(
    "required", ["docs/README.md", "docs/contributing/style-guide.md"],
)
def test_the_navigational_documents_exist(required):
    """The index and the style guide are load-bearing: the first is how
    a reader finds anything after the reorganisation, the second is what
    the two tests above enforce."""
    assert (REPO / required).exists()

# --- UX-97: the two counts that drifted within one commit range -------
#
# Both of these were shipped correct and falsified by a later commit in
# the same twenty-commit range, because both were checked once by a
# one-off script and then hand-maintained. A number a human has to
# remember to update is a number that goes stale; these make the
# checking automatic.

FINDINGS_ID_RE = re.compile(r"^\s+'([a-z0-9-]+)', SEVERITY", re.M)


def _declared_finding_ids():
    """Every `id` `bga` can put in `findings[]` or a correlate row."""
    ids = set()
    for module in ("bga/findings.py", "bga/correlate.py"):
        ids |= set(FINDINGS_ID_RE.findall((REPO / module).read_text(encoding="utf-8")))
    # `find_restructuring_findings` builds its dict literally rather than
    # through the `_finding(...)` helper the pattern above matches, and
    # `UX-102`'s Plane 3 finding is built in the tool because it reads
    # BuildStream's own logs, which the analyzer never sees.
    for module in ("bga/correlate.py", "tools/bst_cache_logs.py", "bga/cache_trend.py"):
        ids |= set(
            re.findall(r"'id': '([a-z0-9-]+)'", (REPO / module).read_text(encoding="utf-8"))
        )
    return ids


def test_every_finding_id_appears_in_the_published_table():
    """`docs/guides/cli.md` publishes the id set as the contract a CI
    gate keys on, so an id missing from it is a documented contract that
    does not match the code.

    `UX-88` shipped that table with 15 ids and verified it with a
    throwaway script. `UX-92` added `cache-hit-ratio` and
    `cache-transfer-cost` days later and the table stayed at 15 - the
    same drift, inside one commit range. This is that script, kept.
    """
    published = (REPO / "docs/guides/cli.md").read_text(encoding="utf-8")
    missing = sorted(i for i in _declared_finding_ids() if f"`{i}`" not in published)
    assert missing == [], (
        "finding id(s) declared in code but absent from the table in "
        f"docs/guides/cli.md: {missing}"
    )


def test_the_pinned_bst_tier_count_matches_the_number_of_marked_tests():
    """CI pins how many `bst`-marked tests must run, so that a *skip*
    cannot read as a pass. The pin is the one hand-written copy of that
    number; this asserts it against the tests themselves.

    `UX-91` added the fifteenth marked test and moved the pin. Four
    documents still said fourteen. The fix for that is not to update
    four numbers - it is to stop writing the number down anywhere a
    check cannot reach.
    """
    marked = 0
    for path in (REPO / "tests").rglob("test_*.py"):
        marked += len(re.findall(r"^\s*@pytest\.mark\.bst\b", path.read_text(encoding="utf-8"), re.M))

    workflow = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    pinned = re.search(r"Expected exactly (\d+) bst-gated tests to run", workflow)
    assert pinned, "the bst-tests job no longer pins a count - that pin is the guard"
    assert int(pinned.group(1)) == marked, (
        f"{marked} test(s) carry @pytest.mark.bst but .github/workflows/ci.yml pins "
        f"{pinned.group(1)}. Update the pin deliberately - it is what stops a skipped "
        f"tier reading as a pass."
    )


def test_the_packaging_config_keeps_tools_out_of_the_top_level():
    """UX-94: the wheel must own exactly one top-level name.

    `UX-77` made the aliases work from an installed wheel by packaging
    `tools*`, which shipped a top-level package called `tools` into
    site-packages - about the most generic importable name in Python.
    Two distributions that both ship `tools/` overwrite each other's
    files, and pip does it silently.

    The directory stays `tools/` in the repository and installs as
    `bga._tools`, so nothing in the checkout had to move. This asserts
    the mapping is still declared; CI's `packaging` job asserts the
    built wheel actually behaves (every alias from an empty directory in
    a clean venv, `hook.c` present, and nothing importable as `tools`).
    """
    try:
        import tomllib
    except ModuleNotFoundError:  # pragma: no cover - Python 3.9/3.10
        pytest.skip("tomllib is 3.11+; CI's packaging job covers this everywhere")

    config = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    setuptools = config["tool"]["setuptools"]

    assert setuptools["package-dir"] == {"bga._tools": "tools"}
    packages = setuptools["packages"]
    top_level = {name.split(".")[0] for name in packages}
    assert top_level == {"bga"}, f"the wheel would ship top-level {sorted(top_level)}"
    assert "bga._tools" in packages and "bga._tools.native_trace" in packages
    assert "bga._tools.native_trace" in setuptools["package-data"]


# --- UX-98: table rows GitHub will render as written ------------------
#
# The one markdown defect this repository has actually shipped, five
# times across three files, one of them broken since the P-task era: a
# table row whose cell count does not match its header, because a
# literal `|` inside the row was not escaped. GitHub splits table rows
# on `|` *even inside backtick spans*, so a quoted jq pipeline turns a
# 6-column row into 8 cells and the table collapses.
#
# This is checked here rather than by the markdown linter because
# `pymarkdownlnt` cannot see it: it implements MD001-MD048, and the
# table rules (MD055 pipe style, MD056 column count) are markdownlint
# v0.34+ additions with no PyMarkdown equivalent. Measured, not assumed
# - see UX-98. `make lint-docs` covers the rest of the correctness
# class; this covers the part that actually broke.


def _tables(text: str):
    """Yield each pipe table as a list of (line number, row).

    A table is a *contiguous* run of rows starting with `|`; anything
    else ends it. Tracking that matters — two tables of different widths
    in one file are normal, and treating the file as one table would
    fail on every document here.

    Fenced code blocks are skipped entirely: a `|` in a shell pipeline
    inside a fence is not a table row.
    """
    in_fence = False
    current = []
    for number, line in enumerate(text.splitlines(), 1):
        stripped = line.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_fence = not in_fence
            if current:
                yield current
                current = []
            continue
        if in_fence:
            continue
        if stripped.startswith("|"):
            current.append((number, stripped))
        elif current:
            yield current
            current = []
    if current:
        yield current


def _cell_count(row: str) -> int:
    """Cells in a table row, counted the way a renderer counts them.

    A backslash-escaped pipe does not split a cell; a leading and
    trailing pipe are delimiters rather than empty cells.
    """
    without_escapes = row.replace("\\|", "\x00")
    inner = without_escapes.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return len(inner.split("|"))


def _is_separator(row: str) -> bool:
    return not row.replace("|", "").replace("-", "").replace(":", "").strip()


def test_every_table_row_has_its_header_cell_count():
    """A row that does not match its header renders as a broken table.

    The failure is invisible in every editor that renders leniently,
    which is how it survived in three files at once - including one
    broken since the P-task era.
    """
    broken = []
    for path in _markdown_files():
        for table in _tables(path.read_text(encoding="utf-8")):
            header_cells = _cell_count(table[0][1])
            for number, row in table[1:]:
                if _is_separator(row):
                    continue
                cells = _cell_count(row)
                if cells != header_cells:
                    broken.append(
                        f"{path.relative_to(REPO)}:{number}: {cells} cells against a "
                        f"{header_cells}-cell header - an unescaped pipe splits a cell"
                    )
    assert broken == [], "malformed markdown table row(s):\n  " + "\n  ".join(broken)


def test_no_table_is_split_by_a_blank_line():
    """A blank line inside a table ends it, and GitHub renders whatever
    follows as a second, headerless table.

    The rule is exact rather than heuristic: a well-formed table is a
    header row, a `|---|` separator, then body rows. So a run of table
    rows whose *second* row is not a separator is not a table at all —
    it is the tail of one that a blank line cut in half. The author sees
    one table in their editor; the reader sees two, the second with the
    first body row promoted to a header.

    Found three of these on first run — two in the backlog status table,
    one in `architecture.md` — after a report that the previewer was
    breaking at `docs/backlog/scenarios/README.md:111`.
    """
    fragments = []
    for path in _markdown_files():
        for table in _tables(path.read_text(encoding="utf-8")):
            if len(table) >= 2 and _is_separator(table[1][1]):
                continue
            number, row = table[0]
            fragments.append(
                f"{path.relative_to(REPO)}:{number}: table rows with no `|---|` "
                f"header separator — a blank line above split a table: {row[:60]}"
            )
    assert fragments == [], "split markdown table(s):\n  " + "\n  ".join(fragments)


def test_scenario_filenames_are_zero_padded_so_they_sort():
    """Backlog filenames sort the way a reader expects in `ls`.

    Lexicographic sort is what every directory listing, file picker and
    `git status` uses, and it puts `UX-100` between `UX-10` and `UX-11`.
    With 103 scenarios that interleaving makes the listing unreadable.
    Four digits give room the project will not reach.

    The *identifier* stays unpadded — `UX-97` in prose, `UX-0097-…md` as
    a filename — because the id is what people say and write, and
    renaming it would invalidate every reference in every commit message
    and audit already written.
    """
    offenders = [
        path.name
        for path in sorted((REPO / "docs/backlog/scenarios").glob("UX-*.md"))
        if not re.match(r"^UX-\d{4}-", path.name)
    ]
    assert offenders == [], (
        "scenario filenames must be zero-padded to four digits so they sort "
        f"lexicographically: {offenders}"
    )


def test_the_docs_lint_scans_the_tree_it_names():
    """UX-109: `make lint-docs` ran PyMarkdown without `-r`, which does
    not recurse - so the gate scanned exactly two files, `README.md` and
    `docs/README.md`, while naming `docs/`. Every other document was
    unlinted, and with `-r` the same configuration reported **1300**
    violations across ~150 of them.

    Same shape as `UX-84` (a whole test tier gated on a binary CI did
    not have) and `UX-97` (a count grep anchored at a column the output
    never used): a gate that cannot fail, in a repository written as
    though it holds. This pins the flag rather than the behaviour
    because the behaviour is what the flag *is*.
    """
    makefile = (REPO / "Makefile").read_text(encoding="utf-8")
    lint_line = next(
        line for line in makefile.splitlines() if "pymarkdown" in line and "scan" in line
    )
    assert " -r " in lint_line, (
        "the docs lint must recurse, or it scans README.md and docs/README.md "
        f"and nothing else: {lint_line.strip()}"
    )
    # And it must still name both roots, so a future edit cannot narrow
    # the scope by dropping one instead of the flag.
    assert "README.md" in lint_line and "docs/" in lint_line
