"""UX-380: the trace said what an element is, never where it sits.

Half the question was already answered: `analyze/v4` publishes
`elements.unweighted_depth`, `parallelism.levels` and
`width_at_level`, and the element table has a `Depth` column.

The other half was not. The trace dictionary is the complete list of
what a slice carries, and every structural fact was missing from it -
a Plane 1 slice knew `element`, `element_kind`, `task_type` and
`outcome` and nothing about the graph. So in Perfetto, the tool
`UX-198` put one click away precisely so a reader could ask their own
questions, every question about the *shape* of the build was
unanswerable while every question about its timing was answerable: no
selecting level 3, no filtering to the critical path.

**Read, not recomputed.** All three values are the analyzer's, taken
from the `analyze.json` the capture already wrote beside the run. A
second implementation in the emitter is exactly how the timeline and
the report come to disagree about one element - and `UX-41` is on
record for how easy the depth recurrence is to get subtly wrong.

**Absent, not defaulted.** A snapshot with no analysis emits none of
the three. A `depth` of 0 written for an element nobody analysed would
put every unanalysed task at the graph's root, which is a claim rather
than a gap - `UX-308`'s rule, and the reason `_plane1_annotations`
filters on `is not None` rather than on truthiness.
"""
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga.viewer import __name__ as _viewer  # noqa: F401
from tools.bga_timeline import (
    IDENTITY_ANNOTATIONS,
    PLANE1_ANNOTATIONS,
    _plane1_annotations,
    element_structure,
    run_identity,
)

DICTIONARY = REPO / "docs/spec/trace-dictionary.md"
QUESTIONS = REPO / "bga/viewer/questions.js"
STRUCTURAL = ("depth", "on_critical_path", "downstream_count")


def _analysis(tmp_path, **payload):
    (tmp_path / "analyze.json").write_text(json.dumps(payload),
                                           encoding="utf-8")
    return str(tmp_path)


class TestTheStructureIsReadFromTheAnalysis:
    def test_all_three_come_back(self, tmp_path):
        snapshot = _analysis(
            tmp_path,
            elements={"unweighted_depth": {"a.bst": 2},
                      "downstream_count": {"a.bst": 7}},
            element_join=[{"element": "a.bst", "on_critical_path": True}])
        assert element_structure(snapshot)["a.bst"] == {
            "depth": 2, "downstream_count": 7, "on_critical_path": True}

    def test_a_snapshot_without_an_analysis_says_nothing(self, tmp_path):
        assert element_structure(str(tmp_path)) == {}

    def test_a_partial_analysis_yields_what_it_has(self, tmp_path):
        """An older `analyze.json` with no `element_join` still gives
        depth - the keys are independent, and demanding all three would
        lose two facts to the absence of a third."""
        snapshot = _analysis(
            tmp_path, elements={"unweighted_depth": {"a.bst": 1}})
        assert element_structure(snapshot) == {"a.bst": {"depth": 1}}

    def test_an_unreadable_analysis_does_not_raise(self, tmp_path):
        (tmp_path / "analyze.json").write_text("{not json", encoding="utf-8")
        assert element_structure(str(tmp_path)) == {}


class TestASliceCarriesIt:
    def _event(self, element="a.bst"):
        return {"args": {"element": element, "action": "build"}}

    def test_the_keys_are_documented_in_the_annotation_list(self):
        named = {key for key, _ in PLANE1_ANNOTATIONS}
        for key in STRUCTURAL:
            assert key in named, f"{key} is on no Plane 1 slice"

    def test_a_slice_carries_the_three(self):
        args = dict(_plane1_annotations(
            self._event(), {"a.bst": "cmake"}, "SUCCESS",
            {"a.bst": {"depth": 3, "on_critical_path": True,
                       "downstream_count": 9}}))
        assert args["depth"] == 3
        assert args["on_critical_path"] is True
        assert args["downstream_count"] == 9

    def test_depth_zero_and_false_survive(self):
        """The root of the graph and an element off the critical path
        are both real answers, and both are falsy - which is why the
        emitter filters on `is not None`."""
        args = dict(_plane1_annotations(
            self._event(), {}, None,
            {"a.bst": {"depth": 0, "on_critical_path": False,
                       "downstream_count": 0}}))
        assert args["depth"] == 0
        assert args["on_critical_path"] is False
        assert args["downstream_count"] == 0

    def test_no_structure_means_no_key(self):
        args = dict(_plane1_annotations(self._event(), {}, None, {}))
        for key in STRUCTURAL:
            assert key not in args, (
                f"{key} written for an element nobody analysed - a depth of 0 "
                f"there puts every unanalysed task at the graph's root")

    def test_an_element_the_analysis_missed_gets_none_of_them(self):
        args = dict(_plane1_annotations(
            self._event("b.bst"), {}, None, {"a.bst": {"depth": 1}}))
        assert "depth" not in args


class TestTheRunSaysBothFactors:
    """The Required Fix's third bullet. `builders` was on the run slice
    and the per-element concurrency was not, so a reader in Perfetto
    could see one of the two numbers whose product bounds the process
    count the trace is showing them - `UX-116`'s question, half
    answered."""

    def _context(self, tmp_path, **fields):
        (tmp_path / "run").mkdir(exist_ok=True)
        (tmp_path / "run" / "run-context.json").write_text(
            json.dumps(dict({"run_identity": {"scheduler": {"builders": 4}}},
                            **fields)), encoding="utf-8")
        return str(tmp_path)

    def test_both_factors_ride_the_run_slice(self, tmp_path):
        identity = run_identity(self._context(
            tmp_path, native_max_jobs=8,
            native_max_jobs_source="resolved_from_graph"))
        assert identity["builders"] == 4
        assert identity["native_max_jobs"] == 8

    def test_the_number_says_where_it_came_from(self, tmp_path):
        """`UX-377` gave it three tiers and `UX-357`'s rule is that a
        published number names the rule that produced it."""
        identity = run_identity(self._context(
            tmp_path, native_max_jobs=8,
            native_max_jobs_source="parsed_from_invocation"))
        assert identity["native_max_jobs_source"] == "parsed_from_invocation"

    def test_a_capture_that_established_neither_says_neither(self, tmp_path):
        identity = run_identity(self._context(tmp_path))
        assert identity["native_max_jobs"] is None
        assert identity["native_max_jobs_source"] is None

    def test_it_is_read_and_not_re_resolved(self, tmp_path):
        """The three-tier rule lives in `_run_context_common`. A second
        implementation here is how the trace and the report come to
        disagree about the number the whole capacity chain is keyed on -
        so an unexpected value is copied through, not corrected."""
        identity = run_identity(self._context(
            tmp_path, native_max_jobs=999, native_max_jobs_source="whatever"))
        assert identity["native_max_jobs"] == 999
        assert identity["native_max_jobs_source"] == "whatever"

    def test_the_keys_are_on_the_run_scope(self):
        named = {key for key, _ in IDENTITY_ANNOTATIONS}
        for key in ("native_max_jobs", "native_max_jobs_source"):
            assert key in named, f"{key} rides no run slice"


class TestTheDocumentationAndTheLibraryKeepUp:
    def test_the_dictionary_has_a_row_for_each(self):
        text = DICTIONARY.read_text(encoding="utf-8")
        for key in STRUCTURAL + ("native_max_jobs", "native_max_jobs_source"):
            assert f"| `{key}` |" in text, f"{key} has no dictionary row"

    def test_a_question_uses_them(self):
        """`UX-368`'s rule: a key nothing asks about is a key nobody
        finds. The library gets one question that groups on `depth`."""
        text = QUESTIONS.read_text(encoding="utf-8")
        assert "graph-levels" in text, "no question asks about the levels"
        assert "debug.depth" in text, (
            "the new keys are documented and no canned query reads one")

    def test_that_question_scopes_itself_to_plane_one(self):
        """`UX-308`'s correction: these ride Plane 1 only, and a query
        that did not say so would match Plane 2 slices on a key they do
        not have and return zero rows in silence."""
        text = QUESTIONS.read_text(encoding="utf-8")
        block = text[text.index('id: "graph-levels"'):]
        block = block[:block.index("},")]
        assert "bst-builder" in block, block[:400]


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
