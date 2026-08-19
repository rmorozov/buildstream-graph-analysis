"""UX-114 item 2: what `captures/fdsdk-latest` is allowed to point at.

The pointer means "the current state of the project", and every document
that reads it takes it that way. `UX-86` already gave cold its own
pointer so two *kinds of build* could not mix through one ref. Nothing
gave the same treatment to two *kinds of measurement*: a dispatch with
`trace_spine=true` moved `fdsdk-latest` onto a spine capture
(run 32223468993, `bga_ref=7bdb7e6f`), which is a different instrument
reading the same build.

The workflow keeps that decision in a `publish_decision` shell function
for one reason: so this file can extract it and *run* it, rather than
assert on prose about it. A test that re-implemented the rule would pass
against a workflow that had stopped following it.
"""
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github/workflows/real-project-capture.yml"

# The function definition, from `publish_decision() {` to its closing
# brace at the same indentation.
DECISION = re.compile(
    r"^(?P<indent>\s*)publish_decision\(\) \{\n(?P<body>.*?)^(?P=indent)\}$",
    re.MULTILINE | re.DOTALL,
)


def _decision_source() -> str:
    match = DECISION.search(WORKFLOW.read_text())
    assert match, "the workflow no longer defines publish_decision the way this test reads it"
    indent = match.group("indent")
    lines = ["publish_decision() {"]
    for line in match.group("body").splitlines():
        lines.append(line[len(indent):] if line.startswith(indent) else line)
    lines.append("}")
    return "\n".join(lines)


def decide(traced_exit="0", trace_spine="false", trace_opens="true") -> str:
    """The workflow's own decision, run under a real shell."""
    script = f'{_decision_source()}\npublish_decision "{traced_exit}"\n'
    result = subprocess.run(
        ["bash", "-c", script],
        capture_output=True, text=True,
        env={"TRACE_SPINE": trace_spine, "TRACE_OPENS": trace_opens, "PATH": "/usr/bin:/bin"},
    )
    assert result.returncode == 0, result.stderr
    return result.stdout.strip()


class TestWhatMovesThePointer:
    def test_the_scheduled_default_moves_it(self):
        """Hook-only, opens on, build succeeded - the configuration the
        cron actually runs, and the only one `-latest` describes."""
        assert decide() == "move-latest"

    def test_a_spine_capture_does_not(self):
        """The case that was filed: a different instrument reading the
        same build must not become the project's current state."""
        assert decide(trace_spine="true") == "non-default-instrumentation"

    def test_an_opens_off_capture_does_not_either(self):
        """`trace_opens` is the other half of the instrumentation, and it
        is off-by-request the same way the spine is on-by-request."""
        assert decide(trace_opens="false") == "non-default-instrumentation"

    def test_a_failed_build_still_does_not(self):
        """UX-81's rule, unchanged - checked here because this is the
        rewrite that could have dropped it."""
        assert decide(traced_exit="1") == "failed-build"

    def test_a_failed_spine_build_reports_the_failure_first(self):
        """Two reasons to withhold the pointer is not two messages. The
        build failing is the more fundamental one and the one a reader
        needs, so it wins."""
        assert decide(traced_exit="1", trace_spine="true") == "failed-build"

    @pytest.mark.parametrize("spine", ["auto", "on", "TRUE", ""])
    def test_anything_that_is_not_the_literal_default_withholds_it(self, spine):
        """UX-113 added `auto` as a third value, and the guard is written
        against the default rather than against a list of known
        non-defaults - so a value invented after this test was written
        withholds the pointer rather than silently moving it."""
        assert decide(trace_spine=spine) == "non-default-instrumentation"


def test_the_pointer_push_is_reachable_only_from_the_move_branch():
    """The guard is only worth as much as its wiring: a `git push --force`
    to `$LATEST_REF` sitting outside the `move-latest` branch would make
    every test above decorative."""
    text = WORKFLOW.read_text()
    pushes = [
        line.strip() for line in text.splitlines()
        if "LATEST_REF" in line and "git push" in line
    ]
    assert len(pushes) == 1, pushes

    case_body = text.split("case \"$(publish_decision")[1]
    move_branch = case_body.split("move-latest)")[1].split(";;")[0]
    assert pushes[0] in move_branch, "the pointer push is not inside the move-latest branch"
