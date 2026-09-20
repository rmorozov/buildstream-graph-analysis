"""UX-898: a build type is half a comparison class, and nothing recorded it.

`bga` already refuses to blend host classes: a store spanning two of
them exits rather than averaging, because a queue over two service
times is two queues. A nightly and a review build differ at least as
much - different targets, a different cache state, often a different
agent - and the tool had no vocabulary for that difference at all.

The type is **declared**, free text the pipeline picks, because no enum
this repository maintains fits a pipeline nobody has seen. The cost is
that a typo makes a third class rather than an error, which is why
every refusal here names both values it saw.

The four behaviours, in the order a user meets them: the capture
records the type, the comparison says when they differ, the gate
refuses, and the aggregate refuses to pool two populations. The fifth
is the one nobody asks for and everybody depends on: a store of
captures that declared nothing behaves exactly as it did.
"""
import json
import os
import shutil
import subprocess
import sys

from bga import buildclass
from bga.compare import compare_runs

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"


def _run(tmp_path, name, build_type=None, variant=None):
    """A run directory declaring a build class, or declaring none."""
    run = tmp_path / name
    shutil.copytree(GOLDEN, run)
    os.remove(run / "expected_output.json")
    context = json.loads((run / "run-context.json").read_text())
    declared = buildclass.declare(build_type, variant)
    if declared:
        context["build_class"] = declared
    (run / "run-context.json").write_text(json.dumps(context, indent=2))
    return run


def _compare(args):
    return subprocess.run(
        [sys.executable, "-c",
         f"from bga.cli import main; raise SystemExit(main({args!r}))"],
        capture_output=True, text=True, cwd=os.getcwd())


def _row(name, host_class="x86_64/linux", declared=None, duration_us=1_000_000):
    row = {"path": f"/store/{name}", "total_duration_us": duration_us,
           "cache_hit_rate": 0.5, "host_class": host_class,
           "snapshot": name, "stamp": f"2026-09-20T0{len(name) % 10}:00:00Z",
           "bytes": 4096}
    if declared:
        row["build_class"] = declared
    return row


def _aggregate(rows, blend=False):
    from bga.store_aggregate import aggregate

    return aggregate({"project": "/p", "snapshots": rows}, blend=blend)


class TestTheCaptureRecordsIt:
    def test_a_declared_type_lands_in_the_run_context(self, tmp_path):
        from tools._run_context_common import add_build_class

        context = {}
        add_build_class(context, build_type="review")
        assert context["build_class"] == {"type": "review", "variant": {}}

    def test_the_environment_declares_it_too(self, tmp_path, monkeypatch):
        """`bga snapshot` drives the capture through two more processes,
        and a CI job has an environment before it has a command line."""
        from tools._run_context_common import add_build_class

        monkeypatch.setenv("BGA_BUILD_TYPE", "night")
        context = {}
        add_build_class(context)
        assert context["build_class"]["type"] == "night"

    def test_declaring_nothing_records_nothing(self, tmp_path, monkeypatch):
        """The discriminating case: every capture taken before this row.
        A key present and null would be a third state to reason about."""
        from tools._run_context_common import add_build_class

        monkeypatch.delenv("BGA_BUILD_TYPE", raising=False)
        monkeypatch.delenv("BGA_BUILD_VARIANT", raising=False)
        context = {}
        add_build_class(context)
        assert context == {}


class TestTheComparisonSaysWhenTheyDiffer:
    def test_two_types_are_different(self):
        out = buildclass.classify(buildclass.declare("review"),
                                  buildclass.declare("night"))
        assert out["status"] == "different"
        assert out["differing"] == ["type"]

    def test_case_is_a_difference_not_a_match(self):
        """Argued, not accidental: folding case would be `bga` deciding
        that a pipeline's two spellings mean one thing, which is a
        guess, and this module refuses rather than guesses."""
        out = buildclass.classify(buildclass.declare("Nightly"),
                                  buildclass.declare("nightly"))
        assert out["status"] == "different"

    def test_one_side_declaring_is_unknown_and_not_a_difference(self):
        """Absence is not evidence of a mismatch, so it must not refuse
        - and it must not read as agreement either."""
        out = buildclass.classify(None, buildclass.declare("review"))
        assert out["status"] == "unknown"
        assert out["differing"] == []

    def test_neither_side_declaring_is_absent_and_silent(self):
        out = buildclass.classify(None, None)
        assert out["status"] == "absent"
        assert buildclass.describe(out, None, None) is None

    def test_the_sentence_names_both_values(self):
        """A free-text declaration's one failure mode is a typo, and
        "different build type" is a sentence a reader cannot act on."""
        baseline, candidate = buildclass.declare("reveiw"), buildclass.declare("review")
        sentence = buildclass.describe(
            buildclass.classify(baseline, candidate), baseline, candidate)
        assert "reveiw" in sentence and "review" in sentence

    def test_a_mixed_pair_still_compares_and_says_so(self, tmp_path):
        """Looking is fine; gating is not."""
        result = compare_runs(_run(tmp_path, "a", "review"),
                              _run(tmp_path, "b", "night"))
        assert result.build_class_comparison["status"] == "different"
        assert "Mixed build class" in (result.comparability_warning or "")
        assert result.verdict, "the comparison itself was refused"

    def test_the_confidence_is_capped(self, tmp_path):
        result = compare_runs(_run(tmp_path, "a", "review"),
                              _run(tmp_path, "b", "night"))
        assert result.low_confidence

    def test_a_matching_pair_is_untouched(self, tmp_path):
        result = compare_runs(_run(tmp_path, "a", "review"),
                              _run(tmp_path, "b", "review"))
        assert result.build_class_comparison["status"] == "same"
        assert "Mixed build class" not in (result.comparability_warning or "")

    def test_it_is_published_in_the_json(self, tmp_path):
        result = compare_runs(_run(tmp_path, "a", "review"),
                              _run(tmp_path, "b", "night"))
        assert result.to_dict()["build_class_comparison"]["differing"] == ["type"]


class TestWhatTheGateDoes:
    """Exit codes, through the real CLI - the surface a pipeline sees."""

    def test_two_types_refuse_with_exit_6(self, tmp_path):
        result = _compare(["compare", str(_run(tmp_path, "a", "review")),
                           str(_run(tmp_path, "b", "night")),
                           "--fail-on-regression"])
        assert result.returncode == 6, result.stderr
        assert "Mixed build class gate FAILED" in result.stderr
        assert "review" in result.stderr and "night" in result.stderr, \
            "the refusal must name both values it saw"

    def test_blend_opts_back_in(self, tmp_path):
        result = _compare(["compare", str(_run(tmp_path, "a", "review")),
                           str(_run(tmp_path, "b", "night")),
                           "--fail-on-regression", "--blend"])
        assert result.returncode == 0, result.stderr

    def test_one_undeclared_side_does_not_refuse(self, tmp_path):
        """Today's behaviour, and the one every old baseline depends on."""
        result = _compare(["compare", str(_run(tmp_path, "old")),
                           str(_run(tmp_path, "a", "review")),
                           "--fail-on-regression"])
        assert result.returncode == 0, result.stderr

    def test_two_undeclared_sides_say_nothing_at_all(self, tmp_path):
        result = _compare(["compare", str(_run(tmp_path, "old")),
                           str(_run(tmp_path, "older"))])
        assert result.returncode == 0, result.stderr
        assert "build class" not in result.stdout.lower()


class TestWhatTheAggregateDoes:
    def test_a_mixed_store_refuses_and_names_both_populations(self):
        rows = ([_row(f"n{i}", declared=buildclass.declare("night"))
                 for i in range(3)]
                + [_row(f"r{i}", declared=buildclass.declare("review"))
                   for i in range(3)])
        document = _aggregate(rows)
        assert document["refusal"]["check"] == "mixed_class_aggregate"
        assert document["refusal"]["classes"] == 2
        assert "night" in document["refusal"]["sentence"]
        assert "review" in document["refusal"]["sentence"]
        assert document["blended"] is None

    def test_blend_states_the_mixed_claim(self):
        rows = ([_row(f"n{i}", declared=buildclass.declare("night"))
                 for i in range(3)]
                + [_row(f"r{i}", declared=buildclass.declare("review"))
                   for i in range(3)])
        document = _aggregate(rows, blend=True)
        assert document["blended"]["mixes"] == 2
        assert document["blended"]["runs"] == 6

    def test_one_type_is_one_population(self):
        rows = [_row(f"r{i}", declared=buildclass.declare("review"))
                for i in range(3)]
        document = _aggregate(rows)
        assert document["refusal"] is None
        assert len(document["host_classes"]) == 1
        assert document["host_classes"][0]["build_class"]["type"] == "review"

    def test_the_host_class_field_still_names_the_machine_alone(self):
        """`host_class` has meant the machine since UX-234; widening it
        silently is the drift UX-190 was filed about."""
        rows = [_row(f"r{i}", declared=buildclass.declare("review"))
                for i in range(3)]
        entry = _aggregate(rows)["host_classes"][0]
        assert entry["host_class"] == "x86_64/linux"

    def test_an_undeclared_store_is_byte_identical_to_today(self):
        """The load-bearing one: an old store still compares, and the
        document it produces is the document it always produced."""
        rows = [_row(f"s{i}") for i in range(3)]
        document = _aggregate(rows)
        entry = document["host_classes"][0]
        assert "build_class" not in entry
        assert document["refusal"] is None

    def test_an_undeclared_mixed_host_store_keeps_the_old_refusal(self):
        rows = ([_row(f"a{i}", host_class="x86_64/linux") for i in range(3)]
                + [_row(f"b{i}", host_class="aarch64/linux") for i in range(3)])
        refusal = _aggregate(rows)["refusal"]
        assert refusal["check"] == "cross_host_aggregate"
        assert "host classes" in refusal["sentence"]


class TestTheReportNamesIt:
    def test_a_declared_class_is_in_the_header(self):
        from bga.report.text import _format_build_class

        line = _format_build_class(
            {"build_class": buildclass.declare("review")})
        assert line == "Build class: review"

    def test_an_undeclared_capture_prints_no_line(self):
        from bga.report.text import _format_build_class

        assert _format_build_class({}) is None
