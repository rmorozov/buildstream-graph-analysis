"""UX-235: the order the page asserts, and the order it actually has.

Round 27 ran twenty-two mutations against round 26's landing and two
stayed green. Both are order claims, and both were hollow the same way:
the harness built the expected sequence as a **literal** over separately
invoked renderers and never read the document `boot()` assembles.

    order: [panel && "decision", evidence && "evidence",
            overview && "overview"].filter(Boolean)

That is the source order of three function calls. `root.prepend(decision)`
mutated to `root.append(decision)` leaves it untouched, and it did:
26 passed before the mutation, 26 passed after.

**A fourth defect, which the round-27 filing did not name and which is
the reason the first three survived.** The one harness that boots the
real exported page implemented `prepend` as `append`:

    prepend(...xs) { this.append(...xs); },

so everything the page puts *first* landed *last* in the probe's view.
Booted through that shim, the real order read
`summary, run_instance, findings, ... , overview, evidence, decision` -
the exact reverse of the promise - and nobody noticed, because no guard
read it. With a real `prepend` the same page reads
`decision, evidence, overview, summary, ...`, which is what UX-207
promised all along. **The page was never wrong; the instrument was.**

So these guards read the booted document's own child sequence. The
pattern, for the next "X above Y" claim: boot the page, walk the root's
children in order, and compare indices - never re-state the order in the
test.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

node = shutil.which("node")
needs_node = pytest.mark.skipif(node is None, reason="node is not installed")
REPO = Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests" / "fixtures" / "golden" / "mixed_task_kinds"


def _probe_source():
    """The export probe, reused rather than re-implemented.

    `UX-235`: a second DOM shim is a second model of the browser, and
    the first one being wrong about `prepend` is exactly what this item
    is repairing. One shim, one place to be wrong.
    """
    source = (REPO / "tests/unit/test_a_report_you_can_navigate.py").read_text()
    return source.split('_PROBE = r"""', 1)[1].rsplit('"""', 1)[0]


def _boot_order(compare=None):
    """Section keys in the order the booted page actually holds them."""
    tmp = Path(tempfile.mkdtemp())
    run = tmp / "run"
    shutil.copytree(GOLDEN, run)
    os.remove(run / "expected_output.json")

    import tools.bga_view as view

    page = tmp / "report.html"
    view.export(str(run), str(page))
    html = page.read_text(encoding="utf-8")

    if compare is not None:
        # The export inlines `report`, `run` and `schemas` only, so the
        # band and the culprit strip never render in one. `load()` reads
        # an inlined block before it tries the network, so splicing one
        # in boots the real comparison path rather than a stub of it.
        block = ('<script type="application/json" id="bga-compare">'
                 + json.dumps(compare) + "</script>")
        html = html.replace("</body>", block + "</body>", 1)
        page.write_text(html, encoding="utf-8")

    module = tmp / "inline.mjs"
    module.write_text(
        re.search(r'<script type="module">(.*?)</script>', html, re.S).group(1),
        encoding="utf-8")
    probe = tmp / "probe.mjs"
    probe.write_text(_probe_source(), encoding="utf-8")
    result = subprocess.run(
        [node, str(probe)], capture_output=True, text=True, cwd=REPO, timeout=90,
        env=dict(os.environ, PAGE=str(page), MOD=str(module), PROTOCOL="file:"))
    assert result.returncode == 0, result.stderr
    out = json.loads(result.stdout)
    assert out["error"] is None, out["error"]
    return [section["key"] for section in out["sections"]]


def _comparison():
    """A minimal `compare/v1` that makes both the band and the culprit
    strip render, so their order is observable at all."""
    return {
        "schema": "compare/v1",
        "baseline_run_id": "a", "candidate_run_id": "b",
        "baseline": {"total_duration_us": 100000},
        "candidate": {"total_duration_us": 140000},
        "deltas": {"total_duration_us": 40000},
        "verdict": "regressed", "verdict_kind": "regressed",
        "low_confidence": False, "mismatches": [], "failed_runs": [],
        "attribution_deltas": {},
        "baseline_band": {"n": 3, "median_us": 100000, "scaled_mad_us": 5000,
                          "k": 3.0, "low_us": 85000, "high_us": 115000,
                          "observed_low_us": 95000, "observed_high_us": 105000,
                          "describes_its_own_set": True,
                          "widened_to_fixed_pct": False,
                          "edges_outside_band": 0, "runs_us": [95000, 100000, 105000]},
        "element_deltas": {
            "rows": [
                {"element_uid": "base.bst", "baseline_us": 10000,
                 "candidate_us": 40000, "delta_us": 30000,
                 "presence": "both", "verdict_kind": "regressed"},
                {"element_uid": "lib.bst", "baseline_us": 20000,
                 "candidate_us": 12000, "delta_us": -8000,
                 "presence": "both", "verdict_kind": "improved"},
            ],
            "counts": {"grew": 1, "shrank": 1, "unchanged": 0,
                       "appeared": 0, "disappeared": 0},
            "ranked_by": "absolute-duration-delta", "banded": False,
        },
    }


@needs_node
class TestTheOrderIsReadFromTheBootedPage:

    def test_the_decision_is_the_first_thing_in_the_document(self):
        """UX-207's promise, as the reader meets it."""
        order = _boot_order()
        assert order[0] == "decision", order[:5]

    def test_the_decision_comes_before_the_evidence_and_the_overview(self):
        order = _boot_order()
        assert order.index("decision") < order.index("evidence"), order[:5]
        assert order.index("evidence") < order.index("overview"), order[:5]

    def test_the_schema_sections_come_after_all_three(self):
        """Everything `render()` appended is evidence, and evidence
        follows the decision - that is the whole of UX-207."""
        order = _boot_order()
        assert order.index("overview") < order.index("summary"), order[:6]


@needs_node
class TestTheCulpritStripSitsAboveTheBand:
    """UX-221 clause 4, which was asserted for the *text* report and
    unguarded on the page."""

    def test_both_render_when_there_is_a_comparison(self):
        """Otherwise the ordering guard below passes over two absences."""
        order = _boot_order(_comparison())
        assert "culprits" in order, order[:8]
        assert "band" in order, order[:8]

    def test_the_culprits_come_first(self):
        order = _boot_order(_comparison())
        assert order.index("culprits") < order.index("band"), order[:8]

    def test_neither_appears_without_a_comparison(self):
        order = _boot_order()
        assert "culprits" not in order
        assert "band" not in order


class TestTheProbeShimCanSeeOrderAtAll:
    """The defect that made every guard above impossible.

    Not re-tested behaviourally here: a second DOM shim written to check
    the first one is a second model of the browser, and the first being
    wrong about `prepend` is precisely what this item repairs. The
    behaviour is covered where it matters - reverting the shim to
    `prepend(...xs) { this.append(...xs); }` reddens every boot-order
    guard above, which is the falsification recorded for this item.
    """

    def test_the_shim_does_not_define_prepend_as_append(self):
        source = (REPO / "tests/unit/test_a_report_you_can_navigate.py").read_text()
        assert "prepend(...xs) { this.append(...xs); }" not in source, (
            "the export probe cannot see document order again")

    def test_the_shim_unshifts(self):
        source = (REPO / "tests/unit/test_a_report_you_can_navigate.py").read_text()
        prepend = source.split("prepend(...xs)", 1)[1].split("},", 1)[0]
        assert "unshift" in prepend, prepend


class TestTheSkipCensus:
    """UX-235's third seam: a skip that stays quiet.

    Measured before this landed: with `jsonschema` absent — exactly what
    a plain `pip install -e .` gives you — `test_output_schemas.py`
    collapses to **26 skipped** and the run stays green.

    `BGA_EXPECT_DEV` already turned that into a red *in CI*, which sets
    it. It is opt-in, so a fresh clone is still silent, and it knows
    about jsonschema alone. The census is the general form: every skip
    tallied by reason, checked at session end.

    Tested here rather than only by the session it guards — a hook
    exercised solely by its own session is the same untested instrument
    this item exists to repair.
    """

    @staticmethod
    def _census():
        import sys
        sys.path.insert(0, str(REPO / "tests"))
        import conftest
        return conftest

    def test_a_whole_file_going_quiet_is_a_complaint(self):
        conftest = self._census()
        complaints = conftest.census_complaints(
            {"node is not installed": 26})
        assert complaints, "26 tests skipping for one reason must complain"
        assert "26" in complaints[0]

    def test_an_undeclared_reason_is_a_complaint(self):
        conftest = self._census()
        complaints = conftest.census_complaints({"because I said so": 1})
        assert complaints
        assert "never declared" in complaints[0]

    def test_the_suites_own_baseline_is_quiet(self):
        """Otherwise the census cries wolf on every run and gets muted."""
        conftest = self._census()
        baseline = {
            "not a dev environment by its own account "
            "(BGA_EXPECT_DEV is unset)": 2,
            "trace_processor_shell is not installed": 1,
        }
        assert conftest.census_complaints(baseline) == []

    def test_every_declared_reason_says_what_it_means(self):
        conftest = self._census()
        for reason, declared in conftest.KNOWN_SKIP_REASONS.items():
            meaning, measured = declared
            assert len(meaning.split()) >= 5, (reason, meaning)
            assert isinstance(measured, int) and measured >= 0, (
                f"{reason}: the baseline must be a count somebody measured")

    def test_the_cap_is_below_the_measured_collapse(self):
        """26 is what `test_output_schemas.py` skips without jsonschema.
        A cap at or above that would not have caught the thing that
        motivated this."""
        conftest = self._census()
        assert conftest.MAX_PER_REASON < 26

    def test_a_measured_baseline_does_not_switch_the_cap_off(self):
        """The repair for the CI failure is a *per-reason* baseline, not
        an exemption. A reason measured at 19 must still complain when a
        file's worth joins it - otherwise "declare it" becomes the way
        to silence the census, which is the defect wearing the fix's
        clothes."""
        conftest = self._census()
        known = {"an environmental absence somewhere": ("a measured arm "
                                                        "that runs in "
                                                        "another job", 19)}
        assert conftest.census_complaints({"an environmental absence "
                                           "somewhere": 19}, known) == []
        assert conftest.census_complaints({"an environmental absence "
                                           "somewhere": 27}, known) == []
        complaints = conftest.census_complaints(
            {"an environmental absence somewhere": 28}, known)
        assert complaints, "a file's worth past the baseline stayed quiet"
        assert "19 measured" in complaints[0]

    def test_the_baselines_cover_what_a_toolless_runner_skips(self):
        """The census was calibrated on one machine and CI failed on a
        run in which nothing was wrong: 82 skips across nine reasons,
        seven of them undeclared. This is that run's census, pinned."""
        conftest = self._census()
        measured_in_ci = {
            "bst not found on PATH": 2,
            "bst not found on PATH - see docs/spec/ingestion-pipeline.md": 12,
            "bst and/or buildstream-plugins not available - "
            "see docs/spec/ingestion-pipeline.md": 1,
            "bst/bwrap/bga not all found on PATH - "
            "see docs/spec/ingestion-pipeline.md": 2,
            "bst/bwrap/cc not all found on PATH - "
            "see docs/spec/ingestion-pipeline.md": 6,
            "bwrap not on PATH": 5,
            "bwrap/cc not both on PATH": 8,
            "no real capture here": 19,
            "the examples/06 capture is not here": 10,
        }
        assert conftest.census_complaints(measured_in_ci) == []
