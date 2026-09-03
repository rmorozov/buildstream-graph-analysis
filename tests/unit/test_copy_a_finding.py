"""UX-224: a finding as something you can paste.

The report ends its life in a pull request, a chat message or a ticket,
and getting it there was manual: select the finding, lose the evidence,
retype the numbers, re-find the element name.

**The text is rendered in the pipeline and published**, and that is the
whole design. Clause 2 asks for one renderer shared with
`--format ci-comment`; the CI comment is Python and the viewer is
JavaScript, so across that boundary the only honest way to have *one*
renderer is for the page to copy a published string rather than word
one. The same reason UX-218's commands are decided in the pipeline and
UX-207's diagnosis is.

The line that matters as much as the first is the last: a pasted finding
without the run identity is an assertion nobody can check, and UX-178
established that the identity must round-trip.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

from bga import schemas

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")
REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN = os.path.join(REPO, "tests", "fixtures", "golden", "mixed_task_kinds")
# `UX-477`: the clauses about `blast-radius-ranking` need a run that
# takes the ranking branch, and the golden run stopped taking it. Not
# because anything about the ranking changed - because the golden run
# was only ever `scheduler_bound` thanks to BuildStream's startup
# sitting in `chain_share`'s denominator, and four back-to-back tasks
# are a chain.
#
# `UX-474` moved it one fixture further along. It was
# `shared_base_wide`, whose six modules over one base are
# scheduler-bound by shape - but every one of those modules reaches
# nothing, and the ranking there was an ordering of three zeros, which
# is the defect that row closed. The copy text those clauses read was
# the copy text of a finding that should not have been published.
# `a_chain_beside_a_crowd` is the shape a ranking is worth reading on:
# `lib0.bst` reaches nine, `lib1.bst` two, `lib2.bst` one.
RANKING = os.path.join(REPO, "tests", "fixtures",
                       "a_chain_beside_a_crowd", "run")


def _analyze(run):
    proc = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", run,
         "--format", "json", "--diagnostics"],
        capture_output=True, text=True, cwd=REPO)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


@pytest.fixture(scope="module")
def report():
    return _analyze(GOLDEN)


@pytest.fixture(scope="module")
def ranking():
    """A run that takes the blast-radius branch - see `RANKING`."""
    return _analyze(RANKING)


def _finding(report, uid):
    for finding in report["findings"]:
        if finding["id"] == uid:
            return finding
    raise AssertionError(f"{uid} is not in this report")


class TestEveryFindingCarriesItsText:

    def test_every_finding_publishes_one(self, report):
        assert report["findings"]
        for finding in report["findings"]:
            assert finding.get("copy_text"), finding["id"]

    def test_the_schema_declares_it(self):
        items = (schemas.schema(schemas.ANALYZE)["properties"]["findings"]
                 ["items"]["properties"])
        assert "copy_text" in items
        assert items["copy_text"]["description"]

    def test_it_opens_with_the_finding(self, ranking):
        finding = _finding(ranking, "blast-radius-ranking")
        assert finding["copy_text"].startswith("BGA finding: ")
        assert finding["title"].splitlines()[0] in finding["copy_text"]


class TestTheEvidenceIsInItsDeclaredUnit:

    def test_a_duration_reads_as_seconds(self, report):
        """Asserted against the payload's own number, not a literal."""
        finding = _finding(report, "wait-category")
        published = finding["evidence"]["category_us"]
        assert f"category_us {published / 1e6:.1f}s" in finding["copy_text"]

    def test_a_share_reads_as_a_percentage(self, report):
        finding = _finding(report, "wait-category")
        published = finding["evidence"]["share"]
        assert f"share {published * 100:.0f}%" in finding["copy_text"]

    def test_two_keys_are_never_reduced_to_one_label(self, report):
        """`category` and `category_us` are different numbers. A first
        draft stripped `_us` from every label and printed both as
        "category" - two numbers under one name is worse than an ugly
        one."""
        text = _finding(report, "wait-category")["copy_text"]
        assert "category_us " in text
        assert "\n  category " in text
        assert text.count("category") >= 2

    def test_a_nested_value_is_left_out_rather_than_dumped(self, ranking):
        """`blast_radius` is a dict of dicts. A first draft rendered it
        as 400 characters of `repr` into the middle of a paste."""
        text = _finding(ranking, "blast-radius-ranking")["copy_text"]
        assert "blast_radius" not in text
        assert "{" not in text and "}" not in text

    def test_the_declared_units_come_from_the_schema(self):
        """Not a table in `findings.py`: `EVIDENCE_QUANTITIES` is where
        UX-217 declared what each evidence key is."""
        source = open(os.path.join(REPO, "bga", "findings.py"),
                      encoding="utf-8").read()
        body = source.split("def _evidence_line", 1)[1].split("\ndef ", 1)[0]
        assert "EVIDENCE_QUANTITIES" in body


class TestItCarriesWhatAReaderWouldRetype:

    def test_the_elements_it_names(self, ranking):
        finding = _finding(ranking, "blast-radius-ranking")
        assert finding["elements"]
        for uid in finding["elements"]:
            assert uid in finding["copy_text"]

    def test_the_published_next_step_for_that_finding(self, ranking):
        finding = _finding(ranking, "blast-radius-ranking")
        step = next(s for s in ranking["next_steps"]
                    if s["follows_from"] == "blast-radius-ranking")
        assert f"Next: {' '.join(step['argv'])}" in finding["copy_text"]

    def test_a_finding_with_no_step_gets_no_next_line(self, report):
        finding = _finding(report, "confidence")
        assert not any(s["follows_from"] == "confidence"
                       for s in report["next_steps"])
        assert "Next:" not in finding["copy_text"]

    def test_the_run_identity_is_there(self, report):
        """UX-178: a pasted finding without it cannot be checked."""
        for finding in report["findings"]:
            assert f"Run: {report['run_id']}" in finding["copy_text"]


class TestThePageCopiesRatherThanWords:

    def test_the_viewer_never_builds_the_text(self):
        """Clause 2, asserted by reading the source rather than by the
        two happening to agree today - UX-214's lesson."""
        # `UX-450`: the section walk moved to `sections.js`.
        source = open(os.path.join(REPO, "bga/viewer/sections.js"),
                      encoding="utf-8").read()
        assert "finding.copy_text" in source
        assert "BGA finding:" not in source, (
            "the page is wording a finding; the text is published and "
            "must only be copied")

    def test_no_other_module_words_one_either(self):
        for name in ("views.js", "questions.js", "nav.js", "tables.js"):
            source = open(os.path.join(REPO, "bga/viewer", name),
                          encoding="utf-8").read()
            assert "BGA finding:" not in source, name

    @needs_node
    def test_the_button_carries_the_published_string(self, ranking):
        finding = _finding(ranking, "blast-radius-ranking")
        out = subprocess.run(
            [node, "--input-type=module", "-e", '''
              const shim = await import(process.env.BGA_DOM_SHIM);
              const { copyButton } = await import("./bga/viewer/questions.js");
              const text = %s;
              const button = copyButton((t, a = {}) => {
                const n = shim.makeNode(t);
                for (const [k, v] of Object.entries(a)) n.setAttribute(k, v);
                return n;
              }, text);
              button.listeners.click[0]();
              console.log(JSON.stringify({ copy: button.attrs["data-copy"] }));
            ''' % json.dumps(finding["copy_text"])],
            capture_output=True, text=True, cwd=REPO, timeout=60,
            env=dict(os.environ, BGA_DOM_SHIM=os.path.join(REPO, "tests", "dom_shim.mjs")))
        assert out.returncode == 0, out.stderr
        assert json.loads(out.stdout)["copy"] == finding["copy_text"]
