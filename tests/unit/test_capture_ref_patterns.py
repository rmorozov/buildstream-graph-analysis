"""UX-122: every `captures/…` pattern in the docs has to match a ref the
workflow can actually publish.

`UX-97` fixed a mode-less glob once and automated the two *counts* that
had drifted beside it. The ref-name patterns stayed hand-maintained
prose, and drifted again within two days — in the same file, producing a
documented `git fetch` that matches no ref that exists. Prose that
describes a generated name needs what the counts got: a test that reads
the generator.
"""
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github/workflows/real-project-capture.yml"

# The one shell assignment the workflow builds every per-run ref from.
REF_EXPRESSION = re.compile(r'RUN_REF="(captures/[^"]*)"')
# A `captures/...` token as it appears in prose, a glob or a command.
DOC_PATTERN = re.compile(r"captures/[A-Za-z0-9_./<>*${}-]+")
# The moving pointers. Enumerated rather than pattern-matched: a pointer
# is a different kind of name from a capture, and a test that blurred
# them would stop catching the drift it exists for.
POINTER_REFS = ("captures/fdsdk-latest", "captures/fdsdk-cold-latest")
# What a documentation writer may legitimately put where the workflow
# substitutes a variable: a real value, a <prose placeholder>, a `*`
# glob, or an unexpanded shell variable. Anything is allowed there
# *except* nothing, which is what dropping a segment looks like.
SEGMENT = r"(?:[A-Za-z0-9_.]+|<[^>]+>|\*|\$\{?\w+\}?)"
# `${SHORT_REF}` and `${{ github.run_id }}` in the raw template.
VARIABLE = re.compile(r"\$\{\{.*?\}\}|\$\{\w+\}")


def _run_ref_template() -> str:
    match = REF_EXPRESSION.search(WORKFLOW.read_text())
    assert match, "the workflow no longer builds RUN_REF the way this test reads it"
    return match.group(1)


def _example_ref() -> str:
    """One concrete name the workflow would really publish."""
    ref = _run_ref_template()
    for name, value in (("SHORT_REF", "953683fb"), ("CAPTURE_MODE", "incremental"),
                        ("BUILDERS", "4"), ("MAX_JOBS", "4")):
        ref = ref.replace("${" + name + "}", value)
    ref = re.sub(r"\$\{\{.*?\}\}", "32223468993", ref)   # github.run_id
    assert "$" not in ref, f"unsubstituted variable in {ref}"
    return ref


def _ref_shape() -> "re.Pattern":
    """A regex for the *shape* the template generates - built from the
    template rather than written out, so what is checked is the
    generator and not a second copy of it.

    Assembled from the literal pieces between the variables, because a
    substitution into an escaped string has to survive both `re.escape`'s
    quoting and `re.sub`'s replacement-template parsing, and getting
    either wrong yields a regex that matches nothing while looking
    plausible.
    """
    template = _run_ref_template()
    # The project segment is a literal in the workflow (`fdsdk`) and a
    # placeholder in any doc describing the scheme in general
    # (`captures/<project>/…`), so it is as variable as the rest.
    template = re.sub(r"^captures/[^/]+/", "captures/${PROJECT}/", template)
    parts, last = [], 0
    for match in VARIABLE.finditer(template):
        parts.append(re.escape(template[last:match.start()]))
        parts.append(SEGMENT)
        last = match.end()
    parts.append(re.escape(template[last:]))
    return re.compile("^" + "".join(parts) + "$")


# Where a `captures/…` token is an *instruction* rather than a record.
#
# `docs/backlog/` and `docs/audits/` are append-only history: UX-81's file
# quotes the ref shape as it was the day it shipped, before the mode
# segment existed, and UX-122's own file quotes the broken glob *as the
# defect*. Forcing those to match today's generator would either rewrite
# history or forbid a task from quoting the bug it fixed. A reader only
# types what the guides and the README tell them to.
INSTRUCTION_DOCS = ("docs/guides", "docs/spec", "README.md")


def _documented_patterns():
    candidates = sorted(REPO.joinpath("docs/guides").rglob("*.md")) \
        + sorted(REPO.joinpath("docs/spec").rglob("*.md")) \
        + [REPO / "README.md"]
    for path in candidates:
        for raw in DOC_PATTERN.findall(path.read_text(errors="replace")):
            token = raw.rstrip("'\"`,.);:")
            if token.startswith(POINTER_REFS):
                continue
            if "/" not in token[len("captures/"):]:
                continue          # `captures/<project>` alone, not a ref name
            yield path.relative_to(REPO), token


def test_the_workflow_still_builds_refs_the_documented_way():
    ref = _example_ref()

    assert ref.startswith("captures/")
    # The segment that has now gone missing twice.
    assert "-incremental-" in ref, ref
    assert ref.endswith("-32223468993"), ref


@pytest.mark.parametrize("where,token", list(_documented_patterns()))
def test_every_documented_ref_pattern_has_the_shape_the_workflow_publishes(where, token):
    """A pattern missing a segment is a command a reader will run and get
    nothing back from - which is exactly what shipped, twice."""
    assert _ref_shape().match(token), (
        f"{where} documents `{token}`, which is not the shape the workflow "
        f"publishes (`{_run_ref_template()}`, e.g. `{_example_ref()}`)"
    )


def test_the_check_would_catch_the_drift_it_was_written_for():
    """The exact pattern that shipped: the mode segment dropped."""
    shape = _ref_shape()

    assert shape.match("captures/fdsdk/953683fb-incremental-b4j4-32064333551")
    assert shape.match("captures/fdsdk/<commit>-<mode>-b<N>j<M>-*")
    assert shape.match("captures/<project>/<commit>-<mode>-b<N>j<M>-*")
    assert not shape.match("captures/fdsdk/953683fb-b4j4-32064333551")
    assert not shape.match("captures/fdsdk/953683fb-b4j4-*")
