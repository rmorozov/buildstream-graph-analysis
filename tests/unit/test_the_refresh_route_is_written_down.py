"""UX-447: the drift gate said "re-record" and not from what.

Three items built the route by which `tests/ci_reference.json` gets
refreshed - `UX-420` the reference, `UX-427` CI printing this run's
timings, `UX-441` moving that document into an artifact - and none put
it in a document a contributor reads:

```console
$ git grep 'ci-reference-candidate' -- docs .claude
(nothing outside the two task files)
```

Meanwhile the tool's own advice on a red run was

> re-record with `--record` and commit, which is how the reference stays
> true rather than becoming an alarm nobody reads

and `--record` on a contributor's own machine writes **that machine's**
seconds, which `UX-418` established cannot be compared to CI's in any
form. The numbers the advice asked for existed only in the artifact,
whose name appeared in one workflow file and nowhere a person would
look.

**Three things have to agree**, and that is what this file holds: the
workflow's `name:`, the constant the tool's messages interpolate, and
the document that tells a contributor which artifact to download. A
rename that touches one of them is what the item's acceptance test asks
to redden.
"""
import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import dev_tier_drift as drift                      # noqa: E402

WORKFLOW = REPO / ".github/workflows/ci.yml"
VERIFY = REPO / ".claude/skills/verify/SKILL.md"


def test_the_workflow_uploads_the_artifact_the_tool_names():
    """Read out of the workflow's `name:` field rather than searched for
    anywhere in the file - a comment mentioning the old name would
    otherwise keep this green through a rename, which is fixing guide
    §5 on a YAML file.
    """
    text = WORKFLOW.read_text(encoding="utf-8")
    uploaded = set(re.findall(r"^\s+name:\s*(ci-\S+)\s*$", text, re.M))
    assert drift.CI_CANDIDATE_ARTIFACT in uploaded, (
        f"`ci.yml` uploads {sorted(uploaded)} and the drift tool's advice "
        f"names `{drift.CI_CANDIDATE_ARTIFACT}` - a contributor following "
        f"the message would look for an artifact this run does not have")


def test_the_document_names_the_same_artifact():
    """The `verify` skill's §3 is what a session reads before marking
    anything done, which is where somebody meets the red step."""
    text = VERIFY.read_text(encoding="utf-8")
    assert drift.CI_CANDIDATE_ARTIFACT in text, (
        f"the verify skill does not name `{drift.CI_CANDIDATE_ARTIFACT}`, "
        f"so the route from a red drift step to a committed reference is "
        f"in no document again")


def test_the_document_says_not_to_record_locally():
    """The half that makes the route correct rather than merely
    written. `--record` here is the mistake the messages used to invite,
    and a document that lists the artifact without saying why the local
    command is wrong leaves the invitation standing."""
    text = VERIFY.read_text(encoding="utf-8")
    section = text.split("## 3.", 1)[1].split("\n## ", 1)[0]
    assert "--record" in section and "UX-418" in section, section[-400:]
    assert re.search(r"[Dd]o not run `--record` locally", section), (
        "the skill does not warn against recording locally - which is "
        "what a reader does when told to re-record and not from where")


def _advice_expressions():
    """Every expression in the tool that tells a reader to `--record`.

    An expression, not a line and not a window. The first cut of this
    clause read 400 characters either side of the matching line, and a
    mutation putting one message back to a bare "re-record with
    --record" stayed **green** - the neighbouring message's mention of
    the constant was inside the window. A guard satisfied by a nearby
    string is a guard that cannot see the site it is about, which is
    the defect this repository keeps finding one level up.

    So the unit is the expression node: a string that says `--record`
    and the constant that says from where have to be in the same one.
    """
    import ast

    tree = ast.parse(pathlib.Path(drift.__file__).read_text(encoding="utf-8"))
    found = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        # What a reader is shown: what the tool prints, what `--help`
        # says, and the `note` a written reference carries. The module
        # docstring says `--record` too and is not advice to anybody -
        # scoping to the call sites is what keeps this reading messages
        # rather than prose about them.
        if isinstance(node.func, ast.Name) and node.func.id == "print":
            candidates = list(node.args)
        else:
            candidates = [kw.value for kw in node.keywords
                          if kw.arg in ("help", "note")]
        for argument in candidates:  # noqa: B007 - see the dict pass below

            text = "".join(
                part.value for part in ast.walk(argument)
                if isinstance(part, ast.Constant)
                and isinstance(part.value, str))
            if "--record" in text:
                found.append((argument, text))
    # And the `note` a written reference carries, which is a dict value
    # rather than a call argument - the fourth message, and the one the
    # first cut of this scan could not see. A contributor reads it in
    # `tests/ci_reference.json` itself, which is the most likely place
    # of all to meet the question.
    for node in ast.walk(tree):
        if not isinstance(node, ast.Dict):
            continue
        for key, value in zip(node.keys, node.values):
            if not (isinstance(key, ast.Constant) and key.value == "note"):
                continue
            text = "".join(
                part.value for part in ast.walk(value)
                if isinstance(part, ast.Constant)
                and isinstance(part.value, str))
            if "--record" in text:
                found.append((value, text))
    return found


def test_the_tool_says_where_from_wherever_it_says_re_record():
    """Every place the tool advises a refresh names the source.

    Read from the source rather than run, because two of the four
    messages need a stale or empty reference to reach and a guard that
    only exercised the others would pass while those still said
    "re-record" into the void.
    """
    import ast

    advice = _advice_expressions()
    assert len(advice) >= 4, (
        f"{len(advice)} `--record` message(s) found; the tool had four "
        f"when UX-447 landed, so this scan is reading less than it did")
    for node, text in advice:
        names = {part.id for part in ast.walk(node)
                 if isinstance(part, ast.Name)}
        assert "CI_CANDIDATE_ARTIFACT" in names, (
            f"this message tells a reader to re-record without saying from "
            f"what, which is the state UX-447 was filed on:\n  "
            f"{text.strip()[:120]}")
        # `UX-457`: and the second door. The artifact is the right
        # document and the wrong host for a reader behind an egress
        # policy that refuses GitHub's blob storage - a message naming
        # only the download sends that reader nowhere, which is the
        # same failure one host over.
        assert "CI_CANDIDATE_JOB" in names, (
            f"this message names the artifact and not the job whose log "
            f"carries the same bytes, so a reader who cannot download it "
            f"is told nothing (UX-457):\n  {text.strip()[:120]}")


if __name__ == "__main__":  # pragma: no cover
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
