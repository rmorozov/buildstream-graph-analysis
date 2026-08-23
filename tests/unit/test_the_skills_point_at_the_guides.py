"""UX-240: a skill is an entry point, never a second copy of a rule.

Three procedures get re-derived every session - how to close a task,
how to falsify a guard, how to regenerate the golden snapshot - and all
three are already prose in a guide. `.claude/skills/` makes them
runnable. The danger is the one this repository has fixed more often
than any other: two copies of one rule, drifting.

So a skill is held to three things. Its commands exist. It points at
the guide that owns its rule rather than restating it. And nothing in
it names a file that is not there.
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
SKILLS = REPO / ".claude/skills"

# Each skill and the guide whose rule it is the entry point for. A
# skill with no owning guide is a rule with one copy in the wrong
# place, which is what the Out of Scope section of UX-240 declines.
OWNERS = {
    "verify": "docs/contributing/fixing-guide.md",
    "falsify": "docs/contributing/fixing-guide.md",
    "measure": "docs/contributing/style-guide.md",
}

_FRONTMATTER = re.compile(r"\A---\n(.*?)\n---\n", re.S)


def _skill(name):
    return (SKILLS / name / "SKILL.md").read_text(encoding="utf-8")


def _body(name):
    text = _skill(name)
    match = _FRONTMATTER.match(text)
    return text[match.end():] if match else text


def _commands(name):
    """Only what the skill presents *as* a command - fenced blocks and
    inline code spans.

    Scanning the prose too made the make-target check report a target
    called `a`, out of the sentence "make a document wrong". A guard
    that reads English as shell finds commands nobody wrote.
    """
    body = _body(name)
    fenced = body.split("```")[1::2]
    inline = re.findall(r"`([^`\n]+)`", re.sub(r"```.*?```", "", body, flags=re.S))
    return "\n".join([*fenced, *inline])


class TestEverySkillIsWellFormed:
    def test_the_skills_exist(self):
        found = sorted(p.parent.name for p in SKILLS.glob("*/SKILL.md"))
        assert found == sorted(OWNERS), (
            f"skills on disk {found}, skills this guard knows {sorted(OWNERS)}")

    @pytest.mark.parametrize("name", sorted(OWNERS))
    def test_it_has_a_name_and_a_description(self, name):
        """The description is what decides whether the skill is reached
        at all, so an empty one makes the file dead weight."""
        match = _FRONTMATTER.match(_skill(name))
        assert match, f"{name}: no YAML frontmatter"
        front = match.group(1)
        assert re.search(rf"^name:\s*{name}\s*$", front, re.M), front
        described = re.search(r"^description:\s*(\S.*)$", front, re.M)
        assert described and len(described.group(1)) > 40, (
            f"{name}: description is missing or too short to route on")

    @pytest.mark.parametrize("name", sorted(OWNERS))
    def test_it_points_at_the_guide_that_owns_the_rule(self, name):
        assert OWNERS[name].rsplit("/", 1)[-1] in _body(name), (
            f"{name} does not name {OWNERS[name]}, so it is a second copy "
            f"of the rule rather than an entry point to it")


class TestEverySkillSaysThingsThatAreTrue:
    """The same two checks `test_docs_links_and_commands.py` makes for
    the guides, because a skill is read the same way and mis-typed the
    same way."""

    @pytest.mark.parametrize("name", sorted(OWNERS))
    def test_every_relative_link_resolves(self, name):
        base = SKILLS / name
        broken = []
        for target in re.findall(r"\]\((\.\./[^)#]+)\)", _body(name)):
            if not (base / target).resolve().exists():
                broken.append(target)
        assert broken == [], f"{name}: dangling link(s) {broken}"

    @pytest.mark.parametrize("name", sorted(OWNERS))
    def test_every_make_target_it_names_exists(self, name):
        makefile = (REPO / "Makefile").read_text(encoding="utf-8")
        targets = {line.split(":", 1)[0]
                   for line in makefile.splitlines()
                   if re.match(r"^[a-z][\w-]*:", line)}
        named = set(re.findall(r"\bmake ([a-z][\w-]*)", _commands(name)))
        missing = sorted(named - targets)
        assert missing == [], f"{name}: no such make target(s) {missing}"

    @pytest.mark.parametrize("name", sorted(OWNERS))
    def test_every_bga_subcommand_it_names_exists(self, name):
        from bga import cli, tools_dispatch

        known = set(tools_dispatch.TOOL_ALIASES)
        for action in cli.create_parser()._subparsers._group_actions:
            if getattr(action, "choices", None):
                known |= set(action.choices)
        named = set(re.findall(r"\bbga ([a-z][\w-]*)", _commands(name)))
        # `bga --schema`-style flags and the placeholders a recipe uses
        # are not subcommands; only bare words are checked.
        missing = sorted(n for n in named if n not in known)
        assert missing == [], f"{name}: no such bga subcommand(s) {missing}"

    @pytest.mark.parametrize("name", sorted(OWNERS))
    def test_every_repository_path_it_names_exists(self, name):
        paths = set(re.findall(
            r"`((?:tests|bga|tools|docs)/[\w./-]+)`", _body(name)))
        # A path with a `<placeholder>` segment is a recipe, not a file.
        missing = sorted(p for p in paths
                         if "<" not in p and not (REPO / p).exists())
        assert missing == [], f"{name}: names path(s) that do not exist {missing}"


class TestTheSkillsDoNotBecomeTheRule:
    def test_the_fixing_guide_still_owns_the_definition_of_done(self):
        """If a session can follow the skill and skip the guide, the
        guide stops being maintained. The skill says so out loud, and
        this pins the sentence that says it."""
        body = _body("verify")
        assert "the guide is right and this file is a bug" in body, (
            "the verify skill does not say which document wins")

    def test_falsify_carries_the_failure_modes_that_cost_something(self):
        """A falsification procedure without them is the procedure this
        repository already followed while getting it wrong five times."""
        body = _body("falsify")
        for phrase in ("does not discriminate",
                       "matches its own explanation",
                       "resets past your own work"):
            assert phrase in body, f"falsify does not name {phrase!r}"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
