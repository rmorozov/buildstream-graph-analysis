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
    # through the `_finding(...)` helper the pattern above matches.
    ids |= set(
        re.findall(r"'id': '([a-z0-9-]+)'", (REPO / "bga/correlate.py").read_text(encoding="utf-8"))
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
