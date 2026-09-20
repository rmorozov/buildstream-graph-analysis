"""UX-903: under the build type sits the variant, and it is a matrix.

`UX-898` made the build *type* - night, review, guard - half of what
makes two runs comparable. The other half is the **variant**: the
owner's pipeline builds per instruction set, and separately as
release-with-symbols, under an address sanitizer, and for coverage.

These are not the same build measured twice. A sanitizer build's
elements are slower by a factor that belongs to the sanitizer. Pooled
into one population they produce a median that describes no build
anyone runs.

The two axes are genuinely different: a type says *when and why* a
build ran, a variant says *what it did*. A nightly sanitizer build and
a review sanitizer build share a variant; a review sanitizer build and
a review coverage build share a type. So the class is the **pair**, and
comparing only the type is the mutation this file exists to redden.

Named dimensions rather than one opaque string, because several are
true at once - `arch=aarch64` *and* `sanitizer=address` *and*
`coverage=on` is one build, not three.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

from bga import buildclass

GOLDEN = "tests/fixtures/golden/mixed_task_kinds"

_ASAN = {"arch": "x86_64", "sanitizer": "address"}
_COVERAGE = {"arch": "x86_64", "coverage": "on"}


def _run(tmp_path, name, build_type=None, variant=None):
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


def _row(name, declared=None, duration_us=1_000_000):
    row = {"path": f"/store/{name}", "total_duration_us": duration_us,
           "cache_hit_rate": 0.5, "host_class": "x86_64/linux",
           "snapshot": name, "stamp": f"2026-09-20T0{len(name) % 10}:00:00Z",
           "bytes": 4096}
    if declared:
        row["build_class"] = declared
    return row


def _aggregate(rows, blend=False):
    from bga.store_aggregate import aggregate

    return aggregate({"project": "/p", "snapshots": rows}, blend=blend)


class TestSeveralDimensionsAreTrueAtOnce:
    def test_a_variant_is_a_map_not_a_string(self):
        declared = buildclass.declare("review", _ASAN)
        assert declared["variant"] == {"arch": "x86_64", "sanitizer": "address"}

    def test_the_pairs_parse_from_the_command_line(self):
        assert buildclass.parse_variant(["arch=aarch64", "sanitizer=address"]) == {
            "arch": "aarch64", "sanitizer": "address"}

    def test_the_same_pairs_parse_from_the_environment(self):
        """One rule for both declaration paths, so they cannot disagree
        about what a dimension is."""
        assert buildclass.parse_variant_env("arch=aarch64,sanitizer=address") == {
            "arch": "aarch64", "sanitizer": "address"}

    def test_a_nameless_dimension_is_refused(self):
        """Inventing a name is how `asan` and `sanitizer=asan` become
        two classes."""
        with pytest.raises(ValueError) as raised:
            buildclass.parse_variant(["asan"])
        assert "asan" in str(raised.value)

    def test_the_label_is_stable_whatever_the_declaration_order(self):
        first = buildclass.label(buildclass.declare("review", _ASAN))
        second = buildclass.label(
            buildclass.declare("review", {"sanitizer": "address", "arch": "x86_64"}))
        assert first == second == "review · arch=x86_64 · sanitizer=address"


class TestTheClassIsThePair:
    def test_one_type_and_two_variants_is_a_difference(self):
        """The mutation this file exists for: comparing only the type
        would call these two runs one population."""
        out = buildclass.classify(buildclass.declare("review", _ASAN),
                                  buildclass.declare("review", _COVERAGE))
        assert out["status"] == "different"
        assert out["differing"] == ["variant"]

    def test_one_variant_and_two_types_is_a_difference(self):
        out = buildclass.classify(buildclass.declare("night", _ASAN),
                                  buildclass.declare("review", _ASAN))
        assert out["status"] == "different"
        assert out["differing"] == ["type"]

    def test_both_matching_is_one_population(self):
        out = buildclass.classify(buildclass.declare("review", _ASAN),
                                  buildclass.declare("review", dict(_ASAN)))
        assert out["status"] == "same"

    def test_a_dimension_present_on_one_side_only_is_a_difference(self):
        out = buildclass.classify(buildclass.declare("review", {"arch": "x86_64"}),
                                  buildclass.declare("review", _ASAN))
        assert out["status"] == "different"

    def test_declaring_neither_half_still_says_nothing(self):
        assert buildclass.classify(None, None)["status"] == "absent"

    def test_the_sentence_names_the_dimension_and_both_values(self):
        baseline = buildclass.declare("review", _ASAN)
        candidate = buildclass.declare("review", _COVERAGE)
        sentence = buildclass.describe(
            buildclass.classify(baseline, candidate), baseline, candidate)
        assert "sanitizer" in sentence and "address" in sentence
        assert "coverage" in sentence
        assert buildclass.NOT_DECLARED in sentence, \
            "a dimension one side never declared must read as absent, not blank"


class TestWhatTheGateDoes:
    def test_two_variants_under_one_type_refuse_with_exit_6(self, tmp_path):
        result = _compare(["compare",
                           str(_run(tmp_path, "a", "review", _ASAN)),
                           str(_run(tmp_path, "b", "review", _COVERAGE)),
                           "--fail-on-regression"])
        assert result.returncode == 6, result.stderr
        assert "sanitizer=address" in result.stderr
        assert "coverage=on" in result.stderr

    def test_blend_opts_back_in(self, tmp_path):
        result = _compare(["compare",
                           str(_run(tmp_path, "a", "review", _ASAN)),
                           str(_run(tmp_path, "b", "review", _COVERAGE)),
                           "--fail-on-regression", "--blend"])
        assert result.returncode == 0, result.stderr

    def test_a_matching_variant_pair_passes(self, tmp_path):
        result = _compare(["compare",
                           str(_run(tmp_path, "a", "review", _ASAN)),
                           str(_run(tmp_path, "b", "review", dict(_ASAN))),
                           "--fail-on-regression"])
        assert result.returncode == 0, result.stderr


class TestWhatTheAggregateDoes:
    def test_a_mixed_variant_store_refuses_and_names_both(self):
        rows = ([_row(f"a{i}", declared=buildclass.declare("review", _ASAN))
                 for i in range(3)]
                + [_row(f"c{i}", declared=buildclass.declare("review", _COVERAGE))
                   for i in range(3)])
        refusal = _aggregate(rows)["refusal"]
        assert refusal["check"] == "mixed_class_aggregate"
        assert "sanitizer=address" in refusal["sentence"]
        assert "coverage=on" in refusal["sentence"]

    def test_one_variant_is_one_population(self):
        rows = [_row(f"a{i}", declared=buildclass.declare("review", _ASAN))
                for i in range(3)]
        document = _aggregate(rows)
        assert document["refusal"] is None
        assert document["host_classes"][0]["build_class"]["variant"] == _ASAN


class TestTheReportNamesTheVariant:
    def test_the_header_says_which_build_these_durations_describe(self):
        """A reader who opens a capture has no other way to know the
        numbers in front of them are a sanitizer's."""
        from bga.report.text import _format_build_class

        line = _format_build_class(
            {"build_class": buildclass.declare("review", _ASAN)})
        assert line == "Build class: review · arch=x86_64 · sanitizer=address"

    def test_a_variant_without_a_type_still_renders(self):
        from bga.report.text import _format_build_class

        line = _format_build_class(
            {"build_class": buildclass.declare(None, {"sanitizer": "address"})})
        assert line == "Build class: sanitizer=address"

    def test_an_undeclared_capture_is_byte_identical_to_today(self):
        from bga.report.text import _format_build_class

        assert _format_build_class({"build_class": None}) is None
