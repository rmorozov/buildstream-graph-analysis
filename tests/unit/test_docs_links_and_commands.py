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
import subprocess
import sys
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

    Counted by **collecting** the tier rather than by counting
    `@pytest.mark.bst` decorators. The two agree only while no marked
    test is parametrized, and the first one that was (`UX-119`'s
    status-parity check, three scripts) made the decorator count say 24
    where CI's own `N passed` said 26. CI greps the number pytest
    prints, so the pin has to mean what pytest means.

    `UX-480`: the number is written **twice** in that step - once in the
    `grep -qE` that decides, and once in the `echo` that explains - and
    this guard read only the echo. Round 72 raised the tier from 43 to
    45, edited the echo, missed the grep, and this stayed green over two
    commits while `bst-tests` failed on a suite where all 45 passed. Both
    are read now, and against each other as well as against pytest: the
    one that decides is the grep.
    """
    collected = subprocess.run(
        [sys.executable, "-m", "pytest", "-m", "bst", "--collect-only", "-q",
         "-p", "no:cacheprovider", str(REPO / "tests")],
        capture_output=True, text=True, cwd=REPO,
    )
    assert collected.returncode == 0, collected.stdout[-2000:] + collected.stderr[-2000:]
    # pytest's own summary, because `pyproject.toml`'s `addopts = "-v"`
    # keeps `-q` from producing the one-line-per-test form.
    summary = re.search(r"(\d+)/\d+ tests collected", collected.stdout)
    assert summary, collected.stdout[-2000:]
    marked = int(summary.group(1))
    assert marked, "collected no bst-marked tests at all - the marker or the path moved"

    workflow = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    said = re.search(r"Expected exactly (\d+) bst-gated tests to run", workflow)
    assert said, "the bst-tests job no longer pins a count - that pin is the guard"
    # The one that actually decides the step's exit status.
    asserted = re.search(r"grep -qE \"\(\^\|\[\[:space:\]=\]\)(\d+) passed",
                         workflow)
    assert asserted, (
        "the bst-tests job no longer greps for `N passed` - that grep is what "
        "fails the step, and this guard cannot read a pin that is not there"
    )
    assert int(asserted.group(1)) == int(said.group(1)), (
        f"the bst-tests job greps for {asserted.group(1)} passed and its message "
        f"says {said.group(1)}. The grep is what decides, so a reader who trusts "
        f"the message is told the wrong number - and this is exactly how round 72 "
        f"shipped a red job on a green tier (UX-480)."
    )
    assert int(asserted.group(1)) == marked, (
        f"{marked} bst-gated test(s) collect but .github/workflows/ci.yml greps for "
        f"{asserted.group(1)}. Update the pin deliberately - it is what stops a "
        f"skipped tier reading as a pass."
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


def _lint_recipe():
    """`lint-docs`'s command line, out of the Makefile rather than
    restated here - the point is that the two agree."""
    body = (REPO / "Makefile").read_text(encoding="utf-8")
    found = re.search(r"^lint-docs:\n((?:\t.*\n)+)", body, flags=re.M)
    assert found, "no lint-docs recipe in the Makefile any more"
    return found.group(1).replace("\t", "").replace("\\\n", " ")


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
    though it holds.

    `UX-509` replaced the walk with `git ls-files`, so there is no `-r`
    to pin any more - and the behaviour is now checkable directly,
    which is better than pinning the flag that used to stand for it.
    The claim is unchanged: a document nested under each named root is
    in the set the lint really receives.
    """
    recipe = _lint_recipe()
    listing = recipe.split("|", 1)[0]
    files = subprocess.run(listing, shell=True, cwd=REPO,
                           capture_output=True, text=True).stdout.split("\0")
    files = [name for name in files if name]
    assert len(files) > 100, (
        f"the docs lint receives {len(files)} file(s) - it scanned two "
        f"before UX-109 and that is the state this guard exists to catch")
    # One *nested* document per root: a listing that reached only the
    # top of each would pass a name check and be UX-109 again.
    for deep in ("README.md", "CLAUDE.md", "REVIEW.md",
                 "docs/backlog/scenarios/README.md",
                 ".claude/skills/verify/SKILL.md"):
        assert deep in files, (
            f"the docs lint no longer reaches {deep}: it received "
            f"{len(files)} file(s)")


# `**Status:** 🟢 Done | ...` on the task file's header line, and the
# status cell of the backlog table's row for the same item.
_STATUS_EMOJI = ("🔴", "🟡", "🟢", "⚪")
_TABLE_ROW = re.compile(r"^\|\s*UX-0*(\d+)\s*\|")
_FILE_ID = re.compile(r"^UX-0*(\d+)-")


# UX-232 split the backlog by liveness: open rows in README.md, closed
# ones verbatim in closed.md. Both are the backlog, so every guard over
# it reads both - a guard that kept looking at one file would go quiet
# for 225 of the 234 rows the day the split landed.
#
# `UX-387`: that is exactly what had happened to `dev_close_task.py`,
# the *fast* check a contributor runs before committing - it read the
# open index only, so it answered for 7 rows of 386 and printed
# "0 problem(s)" for the rest. Two readings of one property is how they
# came to disagree, so there is now one: the tool's, imported here.
from tools.dev_close_task import (  # noqa: E402
    backlog_files as _backlog_files,
    close_status_line as _close_status_line,
    file_statuses as _file_statuses,
    status_marker as _status_marker,
    status_words as _status_words,
    table_statuses as _table_statuses,
)


def _rows_by_file():
    """`{item number: [file, ...]}` - for the exactly-one-of-two guard."""
    where = {}
    for path in _backlog_files():
        if not path.exists():
            continue
        name = path.relative_to(REPO).as_posix()
        for line in path.read_text(encoding="utf-8").splitlines():
            match = _TABLE_ROW.match(line)
            if match:
                where.setdefault(int(match.group(1)), []).append(name)
    return where


def test_every_task_file_declares_a_status():
    """The guard below compares two markers; a file with none would make
    it vacuously pass for that item."""
    missing = [
        name for _number, (name, line) in sorted(_file_statuses().items())
        if line is None or _status_marker(line) is None
    ]
    assert missing == [], (
        "task file(s) with no `**Status:**` marker in their first 8 lines: "
        f"{missing}"
    )


def test_every_task_file_has_a_row_in_the_table():
    """A file with no row is a scenario the backlog does not list, which
    is the same invisibility the status drift causes."""
    rows = _table_statuses()
    orphans = [
        name for number, (name, _line) in sorted(_file_statuses().items())
        if number not in rows
    ]
    assert orphans == [], f"task file(s) with no backlog table row: {orphans}"


def _in_a_linked_worktree():
    """`UX-561`: is this checkout a linked worktree rather than the
    shared one?

    `git worktree add` writes `.git` as a *file* holding `gitdir: ...`;
    the main checkout has a directory. No subprocess, so the guard
    costs nothing and works with git absent.
    """
    return (REPO / ".git").is_file()


def test_the_table_status_matches_the_task_files():
    """UX-131: two hand-maintained copies of one fact, for the third time.

    Round 11 found the table 🟢 where the file was 🔴 (`UX-85`); round 12
    found row wording drift; round 13 found **five** rows 🔴 against
    files that were 🟢 with full verification logs — the closing commit
    of a range simply never touched the table.

    The repo's own conclusion applies verbatim: every hand-maintained
    correspondence here has drifted within days, and every mechanically
    checked one has held. Only the marker is pinned — row *summaries*
    legitimately compress and stay prose.
    """
    rows = _table_statuses()
    disagreements, pending = [], []
    for number, (name, line) in sorted(_file_statuses().items()):
        if number not in rows:
            continue
        in_table = _status_marker(rows[number])
        in_file = _status_marker(line or "")
        if in_table == in_file:
            continue
        if _in_a_linked_worktree() and in_file == "🟢" and in_table == "🔴":
            # `UX-561`: a track closes its item and leaves the index
            # alone, because `decompose` makes README.md a merge hotspot
            # the orchestrator owns. In the track's tree that is the
            # instructed state, not drift - and failing on it made every
            # track disable `selector-before-commit.sh` to commit
            # correct work. Only this direction, and only here: 🟢 in
            # the table over 🔴 in the file is the drift `UX-131` found
            # three times, and it still fails everywhere.
            pending.append(f"UX-{number}: {name} is 🟢, its row not moved yet")
            continue
        disagreements.append(
            f"UX-{number}: table says {in_table}, {name} says {in_file}"
        )
    if pending:
        print("\n".join(
            ["a track's tree: these rows are the orchestrator's to move "
             "(UX-561), and `dev_close_task.py --move` is what moves them:"]
            + [f"  {one}" for one in pending]))
    assert disagreements == [], (
        "the backlog table and its task files disagree about status:\n  "
        + "\n  ".join(disagreements)
        + "\nUpdate the row in docs/backlog/scenarios/README.md in the same "
          "commit as the file (docs/contributing/fixing-guide.md)."
    )


def test_every_bga_command_the_docs_tell_you_to_type_exists():
    """UX-126 extended this: the guides now teach `bga snapshot` first,
    and a front door named in a guide but absent from the dispatch table
    is worse than an undocumented one - the reader types it and gets
    argparse's "invalid choice".

    Both halves of the CLI are checked, because a reader cannot tell
    them apart: the tool aliases in `tools_dispatch` and the analyzer's
    own subcommands.
    """
    from bga.cli import create_parser
    from bga.tools_dispatch import TOOL_ALIASES

    known = set(TOOL_ALIASES)
    for action in create_parser()._actions:
        if getattr(action, "choices", None) and action.dest == "command":
            known |= set(action.choices)

    command_re = re.compile(r"\bbga ([a-z][a-z-]*)")
    offenders = []
    for path in _instructional_files():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for name in command_re.findall(line):
                # `bga --help`, `bga doctor` and friends are commands;
                # prose like "bga refuses" is not, so only flag a word
                # that looks like one and is not known.
                if name in known or name in {"is", "does", "refuses", "says", "and", "on", "can", "it"}:
                    continue
                offenders.append(f"{path.relative_to(REPO)}:{number}: bga {name}")
    assert offenders == [], (
        "documented `bga <command>` with no such command:\n  " + "\n  ".join(offenders))


def test_the_guides_teach_the_two_line_loop():
    """UX-126's acceptance: the quick path is the loop, not the
    plumbing. Pinned because the three-command form is what three audit
    rounds actually ran, and it will drift back without a guard."""
    guide = (REPO / "docs" / "guides" / "real-project.md").read_text(encoding="utf-8")

    quick_path = guide.split("## Step 1", 1)[0]
    assert "bga snapshot -- bst build" in quick_path
    assert "bga compare @prev @last" in quick_path


def test_the_cli_reference_does_not_still_say_run_directories_only():
    """UX-134's acceptance asks for the note to be *deleted* rather than
    reworded: the seam it apologised for is closed, and a reference that
    still warns about it sends the reader to type the longer form."""
    reference = (REPO / "docs" / "guides" / "cli.md").read_text(encoding="utf-8")

    assert "Run *directories* only" not in reference
    assert "bga correlate @last\n" in reference, (
        "the short form the note was standing in for is not documented")


def test_the_guide_teaches_the_one_command_baseline_set():
    """UX-154: UX-136's log claimed this guide taught `bga baseline`
    while `grep -c` returned 0 — the claim named a file the commit did
    not touch. A guard, because prose claims about prose are exactly what
    no other test catches."""
    guide = (REPO / "docs" / "guides" / "real-project.md").read_text(encoding="utf-8")

    assert "bga baseline" in guide, (
        "the guide still teaches only the manual --baseline-run assembly")
    assert guide.index("bga baseline") < guide.index("--baseline-run"), (
        "the one-command form should lead; the explicit one is what it composes")


# ---------------------------------------------------------------------------
# UX-180: the documents that describe the verdict, the gate and the source
# axis have to keep describing what the code does.


def _verdict_strings():
    """The verdicts a *comparable* pair can receive, read out of the
    code that emits them.

    Scoped to the significance chain, so the refusal a non-comparable
    pair gets (documented with the exit codes, not with the verdicts)
    does not join the list. Read rather than pinned as literals, so that
    renaming one reddens this guard instead of leaving two documents
    quoting a string `bga` no longer prints.

    `UX-214` moved the branch this used to scrape into
    `classify_against_band`, and the sentences into `VERDICT_SENTENCES`
    keyed by the same enum - which is a better source than a slice of
    source text, and still "read rather than pinned as literals".
    """
    from bga.compare import VERDICT_SENTENCES

    verdicts = set(VERDICT_SENTENCES.values())
    assert len(verdicts) == 4, f"the significance chain now emits {sorted(verdicts)}"
    return verdicts


def test_every_verdict_the_code_emits_is_listed_where_verdicts_are_listed():
    """UX-180 item 2: `UX-170` added a fourth duration verdict and left
    both verdict lists at three, so a reader who met
    `within the baseline set's own observed range` in real output could
    not find it in either document."""
    verdicts = _verdict_strings()
    assert "within the baseline set's own observed range" in verdicts, (
        "the disputed-region verdict is gone from bga/compare.py - "
        "update this guard and the documents together")

    for name in ("README.md", "docs/guides/cli.md"):
        text = (REPO / name).read_text(encoding="utf-8")
        missing = sorted(v for v in verdicts if v not in text)
        assert not missing, f"{name} lists no {missing}"


def test_no_document_still_promises_the_gate_and_the_verdict_agree():
    """UX-180 item 3: `--fail-on-regression` has never consulted the
    band, so the claim that the gate 'fails exactly when a human reading
    the report would call it a regression' became false twice over. The
    divergence is allowed; asserting it away is not."""
    surfaces = {
        "bga/compare.py": (REPO / "bga" / "compare.py").read_text(encoding="utf-8"),
        "docs/guides/cli.md": (REPO / "docs" / "guides" / "cli.md").read_text(
            encoding="utf-8"),
    }
    for name, text in surfaces.items():
        assert "never a second, silently-different definition" not in text, (
            f"{name} still promises an equivalence UX-59 and UX-170 removed")

    assert "Where the gate and the verdict now diverge" in surfaces["bga/compare.py"], (
        "regression_exceeds_threshold's docstring should name the two divergences")


_GLOSSARY_TERMS = (
    "**resource**",
    "**blast**",
    "**keying: ref vs content**",
    "**work vs wall clock**",
    "**building vs assembling**",
)


def test_the_glossary_defines_the_terms_the_source_axis_introduced():
    """UX-180 item 6, against UX-138's rule: a word three documents use
    precisely is defined once, in the index, or it drifts."""
    index = (REPO / "docs" / "README.md").read_text(encoding="utf-8")
    glossary = index.split("## Words this project uses precisely", 1)[1]
    glossary = glossary.split("\n---", 1)[0]

    missing = [term for term in _GLOSSARY_TERMS if term not in glossary]
    assert not missing, f"the glossary defines no {missing}"


def test_the_readme_stays_inside_its_measured_line_budget():
    """UX-135 set `wc -l README.md` <= 250 and measured 420 -> 245 to
    reach it; UX-180 item 7 found it at 266. Exceeding a measured target
    is allowed - doing it silently is what turned 420 into '430'."""
    readme = (REPO / "README.md").read_text(encoding="utf-8")
    lines = len(readme.splitlines())

    if lines > 250:
        assert f"{lines} lines" in readme, (
            f"README is {lines} lines against UX-135's 250-line budget and "
            "carries no annotation restating the number and the reason")


def test_the_keying_claim_carries_the_provenance_it_was_accepted_with():
    """UX-174's acceptance asked for provenance on the `directory:`
    claim, measured preferred; UX-180 item 5 found none. The note names
    the BuildStream version, both key sites, and real `%{full-key}`
    output."""
    guide = (REPO / "docs" / "guides" / "real-project.md").read_text(encoding="utf-8")
    section = guide.split("## One repository, many elements", 1)[1]

    assert "get_unique_key()" in section
    assert 'key_dict["directory"] = source._directory' in section, (
        "the note should say where BuildStream keys the staging path, "
        "since that is the half a reader gets wrong")
    assert "BuildStream 2.7.0" in section, "the measurement names no version"
    assert "%{full-key}" in section, "no measured keys, only an argument"


# ---------------------------------------------------------------------------
# UX-192: the reference has to name the flag that changes what the answer
# contains, and the round-trip's own precondition.


def test_the_cli_reference_documents_the_blast_command():
    """`bga blast` shipped in round 18 with a one-line mention in the
    entry-point block and no entry of its own, so `--no-cost` - which
    changes what the answer contains - was documented nowhere."""
    reference = (REPO / "docs" / "guides" / "cli.md").read_text(encoding="utf-8")

    assert "## `bga blast`" in reference, "the reference has no blast entry"
    entry = reference.split("## `bga blast`", 1)[1].split("\n## ", 1)[0]
    assert "--no-cost" in entry
    assert "--project" in entry
    for reading in ("url", "path", "element"):
        assert reading in entry, f"the resolution order does not name {reading}"
    assert "exits 0" in entry, "a question, not a gate - and the entry should say so"


def test_every_flag_blast_accepts_is_in_its_entry():
    """The entry cannot fall behind the parser: a flag that exists and is
    undocumented is how `--no-cost` shipped invisible."""
    from bga.cli import create_parser

    blast = None
    for action in create_parser()._actions:
        if getattr(action, "choices", None) and hasattr(action.choices, "keys"):
            blast = action.choices.get("blast")
    assert blast is not None, "no `blast` subparser"

    entry = ((REPO / "docs" / "guides" / "cli.md").read_text(encoding="utf-8")
             .split("## `bga blast`", 1)[1].split("\n## ", 1)[0])
    flags = {option for action in blast._actions for option in action.option_strings
             if option.startswith("--")} - {"--help"}
    missing = sorted(flag for flag in flags if flag not in entry)
    assert not missing, f"cli.md's blast entry documents no {missing}"


def test_the_ci_journey_documents_the_cross_host_gate():
    """UX-186's acceptance: the journey this most affects has to name
    the flag that decides whether a CI farm's gates fire at all."""
    guide = (REPO / "docs" / "guides" / "ci-comment.md").read_text(encoding="utf-8")

    assert "--allow-cross-host" in guide
    assert "host_manifest" in guide, "the field a reader would go looking for"
    assert "exit 6" in guide, "the code a pipeline branches on"
    assert "host unknown" in guide.lower(), (
        "old captures still compare, and the guide should say so")


def test_the_fixing_guide_names_the_output_versioning_rule():
    """UX-190: a rule that lives only in a module docstring is a rule
    the next fixer does not meet. The checklist is where they look."""
    guide = (REPO / "docs" / "contributing" / "fixing-guide.md").read_text(
        encoding="utf-8")

    assert "analyze/v2" in guide
    assert "bump" in guide.lower()
    assert "additionalProperties" in guide, (
        "the rule's other half - an addition is not a breaking change")


def test_the_reference_documents_the_full_flags():
    """UX-187: a flag that restores a folded section is only useful to
    a reader who knows it exists - and the elision line names it, so
    the reference must too."""
    reference = (REPO / "docs" / "guides" / "cli.md").read_text(encoding="utf-8")

    for flag in ("--full-path", "--full-sources"):
        assert flag in reference, f"cli.md does not document {flag}"
    assert "JSON never truncates" in reference


def test_the_reference_documents_the_suspend_contract():
    """UX-185: a user whose three-hour capture just refused needs to
    find both halves - why it refused, and the flag that prevents it."""
    reference = (REPO / "docs" / "guides" / "cli.md").read_text(encoding="utf-8")

    assert "--inhibit" in reference
    assert "CLOCK_MONOTONIC" in reference, "the mechanism, not just the symptom"
    assert "spans a suspend" in reference


def test_the_reference_documents_the_timeline_command():
    """UX-188: the merge existed and worked for two rounds with no way
    to reach it. A documented command is half of the route."""
    reference = (REPO / "docs" / "guides" / "cli.md").read_text(encoding="utf-8")

    assert "bga timeline" in reference
    assert "--no-keep-raw" in reference
    assert "Perfetto" in reference


def test_the_docs_explain_how_to_turn_completion_on():
    """UX-191: completion that nobody activates is completion nobody
    has. The activation line is the feature."""
    reference = (REPO / "docs" / "guides" / "cli.md").read_text(encoding="utf-8")
    readme = (REPO / "README.md").read_text(encoding="utf-8")

    for text in (reference, readme):
        assert "register-python-argcomplete bga" in text
        assert "bga[completion]" in text
    assert "click" in reference.lower(), (
        "the declined alternative should be recorded where a reader asks")


def test_every_scenario_has_exactly_one_row_across_the_two_files():
    """UX-232 clause 5: the split must not duplicate or drop a row.

    A row moves from `README.md` to `closed.md` in the same commit that
    flips its marker. Two rows means a move that copied; zero means the
    file exists and the backlog has forgotten it (covered by
    `test_every_task_file_has_a_row_in_the_table`, which now reads
    both).
    """
    duplicated = {number: files for number, files in _rows_by_file().items()
                  if len(files) != 1}
    assert duplicated == {}, (
        f"a scenario must appear in exactly one of README.md/closed.md: "
        f"{duplicated}")


def test_open_rows_are_in_the_readme_and_closed_rows_are_not():
    """Liveness is what the split is *for*."""
    misplaced = []
    for number, files in _rows_by_file().items():
        marker = _table_statuses().get(number, "")
        in_readme = files == ["docs/backlog/scenarios/README.md"]
        if marker[:1] in ("🔴", "🟡") and not in_readme:
            misplaced.append(f"UX-{number} is {marker[:1]} but lives in closed.md")
        if marker[:1] in ("🟢", "⚪") and in_readme:
            misplaced.append(f"UX-{number} is {marker[:1]} but is still in README.md")
    assert misplaced == [], misplaced


def test_every_open_row_carries_a_topic_from_the_closed_set():
    """UX-232 clause 3. The taxonomy is a closed set so the index can be
    counted; a free-text topic is a second title."""
    topics = {"capture", "analysis", "contracts", "viewer",
              "cli", "store", "docs", "guards"}
    path = REPO / "docs/backlog/scenarios/README.md"
    rows = [line for line in path.read_text(encoding="utf-8").splitlines()
            if _TABLE_ROW.match(line)]
    # `UX-562`: 0 open rows is a backlog a round emptied, not a parser
    # that matched nothing - so the vacuity refusal stands on closed.md,
    # which only grows, and the open rows are checked however many.
    closed = [line for line in (REPO / "docs/backlog/scenarios/closed.md")
              .read_text(encoding="utf-8").splitlines()
              if _TABLE_ROW.match(line)]
    assert closed, "the row pattern matches nothing in closed.md"
    bad = []
    for line in rows:
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        if cells[2] not in topics:
            bad.append(f"{cells[0]}: {cells[2]!r}")
    assert bad == [], f"topic outside the closed set {sorted(topics)}: {bad}"


def test_the_index_counts_match_the_rows_they_index():
    """An index that has drifted from what it indexes is worse than no
    index - it is the two-hand-maintained-copies defect UX-131 filed,
    one document up."""
    path = REPO / "docs/backlog/scenarios/README.md"
    text = path.read_text(encoding="utf-8")
    rows = [line for line in text.splitlines() if _TABLE_ROW.match(line)]
    claimed = re.search(r"\*\*(\d+) open\*\*", text)
    assert claimed, "the index does not state how many are open"
    assert int(claimed.group(1)) == len(rows), (
        f"the index claims {claimed.group(1)} open rows and the table has "
        f"{len(rows)}")
    per_topic = {}
    for line in text.splitlines():
        match = re.match(r"^\| (\w+) \| (\d+) \| (\d+) \|$", line)
        if match:
            per_topic[match.group(1)] = int(match.group(2))
    counted = {}
    for line in rows:
        cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
        counted[cells[2]] = counted.get(cells[2], 0) + 1
    for topic, number in counted.items():
        assert per_topic.get(topic) == number, (
            f"the index says {per_topic.get(topic)} open {topic} rows; "
            f"the table has {number}")


def _out_of_scope_entries(path):
    """Each `Out of Scope` bullet, with wrapped continuations joined."""
    text = path.read_text(encoding="utf-8")
    if "## Out of Scope" not in text:
        return None
    body = text.split("## Out of Scope", 1)[1].split("\n## ", 1)[0]
    entries, current = [], None
    for line in body.splitlines():
        if line.strip().startswith("- "):
            if current:
                entries.append(current)
            current = line.strip()[2:]
        elif current is not None and line.strip():
            current += " " + line.strip()
    if current:
        entries.append(current)
    return entries


def test_every_out_of_scope_entry_names_a_task_or_states_a_decline():
    """UX-232 clause 4: an idea parked in `Out of Scope` has been lost
    and dug out again at least once.

    Each entry either references a task id — existing or newly stubbed —
    or says in a clause *why* it is declined. Held for filings from
    UX-227 on; earlier ones are history, and mining them was a one-time
    sweep rather than a rule applied backwards.
    """
    unjustified = []
    for path in sorted((REPO / "docs/backlog/scenarios").glob("UX-*.md")):
        match = _FILE_ID.match(path.name)
        if not match or int(match.group(1)) < 227:
            continue
        entries = _out_of_scope_entries(path)
        assert entries is not None, f"{path.name} has no Out of Scope section"
        for entry in entries:
            names_task = re.search(r"UX-\d+", entry)
            # A reason in a parenthesis, after an em-dash, after a
            # colon - or as a following sentence, which is how most of
            # them are actually written. The first three patterns were
            # derived from the three bare entries UX-232 mined, and
            # under-fit the ninth filing that used the fourth shape:
            # eight of ten round-29 entries stated their reason in a
            # second sentence and were reported as bare. A bare noun
            # phrase still cannot pass - it has no second sentence to
            # put six words in.
            gives_reason = (re.search(r"\([^)]{12,}\)", entry)
                            or re.search(r"—[^—]{12,}", entry)
                            or re.search(r":\s+\S", entry)
                            or re.search(r"\.\s+(?:\S+\s+){5,}\S", entry))
            if not (names_task or gives_reason):
                unjustified.append(f"{path.name}: {entry[:70]}")
    assert unjustified == [], (
        f"an Out of Scope entry must reference a task or state why it is "
        f"declined, or the idea is lost again: {unjustified}")


# `UX-454`. The guard above compares the two copies of the marker by
# `status_marker`, which answers with the **glyph** - the only thing the
# two halves have to agree on, and therefore blind to a line that says
# its word twice. Twenty-five files said `🟢 Done Done` under a green
# suite. These two read the other half.
#
# They are deliberately a pair, and neither alone would have caught it:
# the first sees damage in the tree and stays green under the defect
# until someone re-closes a task; the second sees the *mechanism* and
# reddens the moment the substitution stops naming the closed words.


def test_no_task_file_repeats_its_status_word():
    """The tree, read rather than parsed."""
    doubled = []
    for _number, (name, line) in sorted(_file_statuses().items()):
        words = _status_words(line or "")
        if words and len(words) > 1:
            doubled.append(f"{name}: {' '.join(words)}")
    assert doubled == [], (
        "task file(s) whose status line says its word more than once - "
        "`--move` run against a file whose own marker was already set by "
        "hand, with a substitution that did not name the word it was "
        "replacing:\n  "
        + "\n  ".join(doubled)
    )


def test_closing_a_task_twice_says_done_once():
    """The mechanism, which is what a mutation has to redden.

    Every status the tree actually uses, closed twice. A substitution
    naming only the open words passes the first line here and doubles
    the other four, which is the defect `UX-454` was filed for.
    """
    doubled = {}
    for start in ("**Status:** 🔴 Not Started |",
                  "**Status:** 🟢 Done |",
                  "**Status:** 🟢 Done. |",
                  "**Status:** 🟢 Fixed & Verified |",
                  "**Status:** 🟡 In Progress — stages 1 and 2 done |"):
        once = _close_status_line(start)
        twice = _close_status_line(once)
        if _status_words(twice) != ["Done"] or twice != once:
            doubled[start] = (once, twice)
    assert doubled == {}, (
        f"closing is not idempotent: {doubled}")


def test_the_verdict_prose_survives_a_close():
    """The other half of the same substitution, so a pattern made
    idempotent by swallowing the whole line would not pass.

    `move()` replaces the status *word* and keeps whatever verdict
    follows an em-dash - eleven closed rows carry one.
    """
    closed = _close_status_line(
        "**Status:** 🟡 In Progress — stages 1 and 2 done |")
    assert closed == "**Status:** 🟢 Done — stages 1 and 2 done |", closed
