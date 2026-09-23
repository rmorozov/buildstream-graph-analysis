"""UX-701: the review that runs before the pull request opens.

`REVIEW.md` has the four passes, the finding shape, the nit cap and
the exclusions; `rules.md` has the rules. The skill added here is the
**procedure** - what to read, where to route, what to write down - and
carries no second copy of either, because two checklists drift
(`UX-240`, and four of round 96's own rows).

The routing rule is `dev_impact.route()` rather than a sentence, so a
diff that reaches a contract, the spec, a hook or a skill is sent on by
something that can be run and mutated: to `design-review` with a page
in it, to `review` without one (`UX-928`).
"""
import pathlib
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))

import dev_impact

SKILL = REPO / ".claude/skills/self-review/SKILL.md"
REVIEW = REPO / "REVIEW.md"


class TestTheRoutingRuleIsRunNotRemembered:
    """`UX-701`'s two mutations, as clauses."""

    def test_a_contract_diff_is_sent_on(self):
        where, why = dev_impact.route(["bga/schemas.py"])
        assert where == "review" and "a contract" in why

    def test_a_docs_only_diff_stops_at_self_review(self):
        where, why = dev_impact.route(["docs/guides/cli.md", "README.md"])
        assert where == "self-review" and why == []

    def test_every_named_surface_routes(self):
        """A rule that fires on one surface and not the others reads as
        complete and is not."""
        for path in ("bga/schemas.py", "docs/spec/specification.md",
                     ".claude/hooks/no-bulk-add.sh",
                     ".claude/skills/verify/SKILL.md"):
            assert dev_impact.route([path])[0] != "self-review", path


class TestASurfaceDiffWithNoPageIsNotSentToThePage:
    """`UX-928`: 165 of 254 surface commits since 2026-08-01 touch no
    page, and `design-review`'s protocol opens on a served one."""

    def test_a_skill_only_diff_goes_to_a_protocol_with_no_page(self):
        where, why = dev_impact.route([".claude/skills/verify/SKILL.md"])
        assert (where, why) == ("review", ["a skill"])

    def test_a_surface_diff_with_a_page_in_it_still_goes_to_the_page(self):
        for page in ("bga/viewer/app.js", "bga/viewer/style.css",
                     "tests/viewer.mjs"):
            where, _ = dev_impact.route(["bga/schemas.py", page])
            assert where == "design-review", page

    def test_a_page_only_diff_is_not_a_surface_diff(self):
        assert dev_impact.route(["bga/viewer/app.js"]) == ("self-review", [])

    def test_every_destination_is_a_skill_that_exists(self):
        for paths in ([".claude/hooks/no-bulk-add.sh"],
                      ["bga/schemas.py", "bga/viewer/app.js"]):
            where, _ = dev_impact.route(paths)
            assert (REPO / ".claude/skills" / where / "SKILL.md").is_file(), where

    def test_the_no_page_destination_answers_every_surface(self):
        """A surface added to `DESIGN_SURFACES` with no row in the
        destination's clause is routed to a protocol with nothing to run."""
        where, _ = dev_impact.route(["docs/spec/specification.md"])
        text = (REPO / ".claude/skills" / where / "SKILL.md").read_text(
            encoding="utf-8")
        clause = text.split("routed here", 1)[-1]
        for name, _ in dev_impact.DESIGN_SURFACES:
            assert f"| {name} |" in clause, name


class TestTheSkillPointsRatherThanRestates:
    """The defect this round kept finding: a figure written twice."""

    def test_it_sends_the_reader_to_both_documents(self):
        text = SKILL.read_text(encoding="utf-8")
        assert "REVIEW.md" in text
        assert "docs/contributing/rules.md" in text

    def test_it_does_not_carry_its_own_nit_cap(self):
        """`REVIEW.md` owns the number. A copy here is a copy to drift."""
        text = SKILL.read_text(encoding="utf-8").lower()
        assert "five nits" not in text, (
            "the skill restates REVIEW.md's cap instead of citing it")

    def test_it_names_the_model_the_round_advised(self):
        assert "sonnet" in SKILL.read_text(encoding="utf-8")

    def test_it_says_not_to_report_what_the_gate_holds(self):
        text = SKILL.read_text(encoding="utf-8")
        assert "make lint" in text and "wrong layer" in text
