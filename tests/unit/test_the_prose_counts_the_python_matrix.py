"""`UX-1355`: the sentences that count CI's Pythons read the `ci.yml` matrix.

`UX-1348` cut push to three cells and made the pull request's one cell the
floor; five sentences still said "all four" and "the newest Python alone".
"""

import pathlib
import re
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from test_a_run_red_for_another_reason_adopts_nothing import _jobs, _matrix_cells

REPO = pathlib.Path(__file__).resolve().parents[2]
WORDS = {2: "two", 3: "three", 4: "four", 5: "five", 6: "six"}
#: "push to main still runs all four" and "all four on push to main".
PUSH_COUNT = re.compile(r"push to main\s+(?:still\s+)?runs\s+all\s+(\w+)|all\s+(\w+)\s+on\s+push\s+to\s+main")
PR_CELL = re.compile(r"\b(newest|floor|oldest|primary)\s+Python\s+alone")


def _version_key(version):
    return tuple(int(part) for part in version.split("."))


#: Where a contributor reads the CI lanes; named, so the selector picks this file up.
PROSE = (
    "CLAUDE.md",
    ".claude/skills/decompose/SKILL.md",
    ".claude/skills/verify/SKILL.md",
    "docs/contributing/fixing-guide.md",
    "docs/contributing/rules.md",
)


def _prose():
    return {path: (REPO / path).read_text(encoding="utf-8") for path in PROSE}


def _matches(pattern):
    return [(path, m) for path, text in _prose().items() for m in pattern.finditer(text)]


def test_every_push_count_names_the_push_matrix():
    push = _matrix_cells(_jobs(), {"event_name": "push"})
    found = _matches(PUSH_COUNT)
    assert len(found) >= 4, f"only {len(found)} push-count sentences found - the pattern no longer reads the prose"
    wrong = [(path, m.group(0)) for path, m in found if (m.group(1) or m.group(2)) != WORDS[len(push)]]
    assert not wrong, f"push runs {len(push)} ({push}); these say otherwise: {wrong}"


def test_every_pull_request_cell_is_named_for_where_it_sits():
    push = sorted(_matrix_cells(_jobs(), {"event_name": "push"}), key=_version_key)
    (pr,) = _matrix_cells(_jobs(), {"event_name": "pull_request"})
    allowed = (
        {"primary"} | ({"floor", "oldest"} if pr == push[0] else set()) | ({"newest"} if pr == push[-1] else set())
    )
    found = _matches(PR_CELL)
    assert len(found) >= 5, f"only {len(found)} pull-request-cell sentences found"
    wrong = [(path, m.group(0)) for path, m in found if m.group(1) not in allowed]
    assert not wrong, f"the pull request runs {pr} of {push}; these name it otherwise: {wrong}"
