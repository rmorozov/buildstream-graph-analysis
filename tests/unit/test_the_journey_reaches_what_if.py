"""UX-246: the journey walks past the command that prices its own act
step.

`docs/guides/real-project.md` is the end-to-end journey — capture →
read → go inside → join → **act** → gate — and it is the document
`README.md` points at six times. Step 7 is where a reader decides what
to change. Measured when this was filed:

```text
subcommands absent from docs/guides/real-project.md:
  whatif, cache-trend, diagnostics, floors, graph, utilisation
```

Five of those six are correct absences: a journey is not a reference,
and `floors`/`graph`/`utilisation`/`diagnostics` are `analyze`'s own
sections with `cli.md` as their home. `whatif` is not — it is a step in
the journey the guide walks.

So this guard is deliberately narrow. It does **not** check that every
subcommand appears in every guide, which would be wrong in a way the
item spells out: it would force `ci-comment.md` to name `sweep`. It
checks one step of one guide for one command, plus the two things that
make the pasted figures worth anything — that they are the numbers the
tool produces today, and that the convention travels with them.
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
GUIDE = REPO / "docs/guides/real-project.md"
STEP = "## Step 7 — change something, then prove it"
RUN = REPO / "examples/06-macro-micro-optimization/.bga/runs/20260821T170127Z/run"

# The selections the guide projects, between the act step and the
# appendix. Every projection line pasted anywhere in the guide has to be
# a line one of these produces - which is what makes the figures
# checkable rather than historical.
SELECTIONS = (("core.bst",), ("codegen.bst",), ("core.bst", "codegen.bst"))
SELECTION = list(SELECTIONS[-1])


def _flat(text):
    """Whitespace-insensitive, for the reason `UX-244` measured: this
    repository's prose is hard-wrapped at 72 columns, so a phrase long
    enough to be worth checking can wrap and read as absent."""
    return re.sub(r"\s+", " ", text).replace("—", "-").lower()


def _appendix():
    return GUIDE.read_text(encoding="utf-8").split(
        "## Appendix: where these numbers came from", 1)[-1]


def _act_step():
    text = GUIDE.read_text(encoding="utf-8")
    assert STEP in text, f"the journey guide has no {STEP!r}"
    return text.split(STEP, 1)[1].split("\n## ", 1)[0]


def _render(selection):
    """What the tool says about the committed run, right now."""
    from bga.analyzer import BuildEfficiencyAnalyzer
    from bga.whatif import project, render

    analyzer = BuildEfficiencyAnalyzer(verbose=False)
    analyzer.load(RUN)
    document = project(analyzer.analyze(RUN), analyzer.graph, list(selection))
    return "\n".join(render(document))


def _projection():
    return _render(SELECTION)


# The two rendered forms that carry a number. Matched as *forms* rather
# than as whole lines, and on flattened text, for two reasons this
# repository has already paid for:
#
#   - the guide reflows pasted output to 72 columns, so `Their
#     individual savings add up to ...` spans two lines in the document
#     and one in the terminal (`UX-244`'s lesson, one guide over);
#   - the prose around the block repeats both figures in bold, so a
#     check for "the number appears in this section" is satisfied by the
#     sentence *discussing* the number. The first draft of this guard did
#     exactly that and stayed green when the pasted block was deleted and
#     when its figures were edited.
#
# These patterns match the renderer's output and nothing a sentence can
# say.
FIGURE_FORMS = (
    re.compile(r"Makespan ([0-9.]+s) -> ([0-9.]+s) \(saves ([0-9.]+s)\)"),
    re.compile(r"add up to ([0-9.]+s), which is not what they are worth "
               r"together \(([0-9.]+s)\)"),
)


def _figures(text):
    flat = re.sub(r"\s+", " ", text)
    return {(index, match.groups())
            for index, pattern in enumerate(FIGURE_FORMS)
            for match in pattern.finditer(flat)}


def _produced_figures():
    produced = set()
    for selection in SELECTIONS:
        produced |= _figures(_render(selection))
    return produced


class TestTheActStepReachesTheCommand:
    def test_the_step_names_whatif(self):
        assert "bga whatif" in _act_step(), (
            "the act step of the journey guide does not name `bga whatif`, "
            "the command that prices the decision it is about")

    def test_the_step_shows_output_and_not_only_a_command(self):
        """Every other step in this guide pastes what it got. A command
        with no output is an instruction to go and find out.

        Checked on the lines that carry a *number*, not on the heading:
        the step also pastes a refusal, and a refusal has no makespan in
        it, so matching "What if these were fixed" would let the worked
        example be deleted as long as the refusal stayed."""
        assert _figures(_act_step()), (
            "the act step names `bga whatif` and pastes no projection "
            "output - no makespan line, no summed-against-joint line")

    def test_the_step_says_what_the_number_is_not(self):
        """`UX-244`'s convention, in the guide's own register. A
        projected makespan quoted without it is a forecast in the
        reader's hands."""
        step = _flat(_act_step())
        for phrase in ("upper bound", "not a forecast", "instant"):
            assert phrase in step, (
                f"the act step quotes a projected saving without {phrase!r}")


class TestThePastedFiguresAreStillTrue:
    """A pasted number is a claim about the tool, and this repository has
    already been bitten by figures a later round moved (`UX-132`). The
    run is committed, so the claim is checkable rather than historical."""

    def test_the_run_the_guide_quotes_still_exists(self):
        assert RUN.is_dir(), (
            f"the journey guide's act step quotes {RUN}, which is not a "
            f"run directory")

    @pytest.mark.parametrize("where", ["act step", "appendix"])
    def test_every_pasted_figure_is_one_the_tool_produces(self, where):
        """Line by line, against the tool. A pasted figure nothing
        produces is the defect `UX-132` named, and the run is committed,
        so it is checkable rather than historical."""
        section = _act_step() if where == "act step" else _appendix()
        produced = _produced_figures()
        stale = sorted(_figures(section) - produced)
        assert stale == [], (
            f"the {where} pastes projection figure(s) `bga whatif` does not "
            f"produce today: {stale}. Produced: {sorted(produced)}")

    def test_the_run_still_discriminates_summed_from_joint(self):
        """The line the act step is *for*. If the two ever stop
        differing on this run, the step's whole argument goes with it
        and the example has to move to a run where it holds."""
        produced = _projection()
        assert "individual savings add up to" in produced, (
            "the committed run no longer discriminates between summed and "
            "joint savings, so the act step's example proves nothing:\n"
            + produced)

    def test_the_appendix_says_where_the_figures_came_from(self):
        """The guide's own rule, stated in its appendix: every number
        names its capture."""
        assert "whatif" in _appendix(), (
            "the appendix accounts for every other figure in the guide and "
            "not for the act step's")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
