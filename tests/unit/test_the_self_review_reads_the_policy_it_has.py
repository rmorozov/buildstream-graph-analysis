"""UX-701: the review that runs before the pull request opens.

`REVIEW.md` has the four passes, the finding shape, the nit cap and
the exclusions; `rules.md` has the rules. The skill added here is the
**procedure** - what to read, where to route, what to write down - and
carries no second copy of either, because two checklists drift
(`UX-240`, and four of round 96's own rows).

The routing rule is `dev_impact.route()` rather than a sentence, so a
diff that reaches a contract, the spec, a hook or a skill is sent to
`design-review` by something that can be run and mutated.
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

    def test_a_contract_diff_goes_to_design_review(self):
        where, why = dev_impact.route(["bga/schemas.py"])
        assert where == "design-review" and "a contract" in why

    def test_a_docs_only_diff_stops_at_self_review(self):
        where, why = dev_impact.route(["docs/guides/cli.md", "README.md"])
        assert where == "self-review" and why == []

    def test_every_named_surface_routes(self):
        """A rule that fires on one surface and not the others reads as
        complete and is not."""
        for path in ("bga/schemas.py", "docs/spec/specification.md",
                     ".claude/hooks/no-bulk-add.sh",
                     ".claude/skills/verify/SKILL.md"):
            assert dev_impact.route([path])[0] == "design-review", path


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
