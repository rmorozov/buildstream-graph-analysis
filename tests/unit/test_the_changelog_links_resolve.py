"""UX-1294: every relative link in CHANGELOG.md resolves from the repository root."""

import pathlib
import re

REPO = pathlib.Path(__file__).resolve().parents[2]
_LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def unresolved(text, root=REPO):
    return [
        target for target in _LINK.findall(text) if not re.match(r"[a-z]+:", target) and not (root / target).exists()
    ]


def test_every_relative_link_in_the_changelog_resolves():
    bad = unresolved((REPO / "CHANGELOG.md").read_text(encoding="utf-8"))
    assert not bad, f"{len(bad)} unresolved, first: {bad[:3]}"


def test_a_fresh_release_body_resolves_from_the_root():
    from tools import bga_release_notes as notes

    body = notes.render(230, 238)
    assert body.count("](") >= 8
    assert unresolved(body) == []


def test_the_resolver_flags_a_scenario_relative_link():
    assert unresolved("[x](UX-0001-run-comparison-command.md)") == ["UX-0001-run-comparison-command.md"]
