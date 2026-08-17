"""UX-46: detect declared build dependencies an element never read.

This was the last macro-level gap - the over-declared `codegen.bst` dep
in `examples/06` was the one problem in that project no `bga` signal
found. Round 2 established that the cheap approach (matching staged
dependency paths against traced command lines) cannot work: BuildStream
stages every dependency into one shared sandbox root, so by the time a
compiler runs, a path carries no element identity.

The mechanism that does work has two halves:
  - the hook records which absolute paths each element's sandbox opened;
  - `bst artifact list-contents` says which files each dependency staged.

An element that opened none of a dependency's staged files is a
*candidate* for removing that edge.

The tests below concentrate on the ways this can be dangerously wrong,
because the costly failure is a confident false "unused" that gets a real
dependency deleted.
"""
from tools.bst_native_build_tracer import (
    compute_declared_vs_used,
    parse_open_records,
)


def _opens(paths, dropped=0, processes=1):
    return {"paths": set(paths), "dropped": dropped, "processes": processes}


# --- parsing ------------------------------------------------------------

def test_open_records_are_unioned_across_an_elements_processes():
    text = (
        "OPENS pid=2 element=a.bst unique=2 dropped=0\n"
        "/usr/include/x.hpp\n"
        "/usr/lib/libx.a\n"
        "OPENS pid=3 element=a.bst unique=1 dropped=0\n"
        "/usr/include/y.hpp\n"
    )

    parsed = parse_open_records(text)

    assert parsed["a.bst"]["paths"] == {
        "/usr/include/x.hpp", "/usr/lib/libx.a", "/usr/include/y.hpp",
    }
    assert parsed["a.bst"]["processes"] == 2


def test_open_records_interleaved_with_lifecycle_lines():
    text = (
        "START pid=2 ppid=1 ts=1.0 element=a.bst cmd=cc1\n"
        "OPENS pid=2 element=a.bst unique=1 dropped=0\n"
        "/usr/include/x.hpp\n"
        "END pid=2 ppid=1 ts=2.0 element=a.bst cmd=cc1\n"
    )

    parsed = parse_open_records(text)

    assert parsed["a.bst"]["paths"] == {"/usr/include/x.hpp"}


def test_truncated_block_does_not_swallow_the_next_record():
    """A process killed mid-write leaves a header promising more paths
    than follow. Consuming the next header as a path would lose a whole
    element's data."""
    text = (
        "OPENS pid=2 element=a.bst unique=5 dropped=0\n"
        "/usr/include/x.hpp\n"
        "OPENS pid=3 element=b.bst unique=1 dropped=0\n"
        "/usr/include/y.hpp\n"
    )

    parsed = parse_open_records(text)

    assert parsed["a.bst"]["paths"] == {"/usr/include/x.hpp"}
    assert parsed["b.bst"]["paths"] == {"/usr/include/y.hpp"}


# --- the analysis -------------------------------------------------------

def test_dependency_whose_files_were_never_opened_is_a_candidate():
    result = compute_declared_vs_used(
        {"app.bst": _opens(["/usr/include/used.hpp"])},
        {"app.bst": ["used.bst", "unused.bst"]},
        {"used.bst": {"/usr/include/used.hpp"},
         "unused.bst": {"/usr/include/unused.hpp"}},
    )

    assert [c["dependency"] for c in result["unused_candidates"]] == ["unused.bst"]
    assert [u["dependency"] for u in result["used"]] == ["used.bst"]


def test_evidence_names_the_counts_rather_than_asserting_a_verdict():
    result = compute_declared_vs_used(
        {"app.bst": _opens(["/usr/include/other.hpp"])},
        {"app.bst": ["dep.bst"]},
        {"dep.bst": {"/a", "/b", "/c"}},
    )

    assert result["unused_candidates"][0]["evidence"] == (
        "0 of 3 files staged by dep.bst were opened during app.bst's build"
    )


def test_element_with_no_observed_opens_is_uncovered_not_all_unused():
    """The dangerous failure mode. An element built entirely by
    statically-linked processes is invisible to LD_PRELOAD and looks
    exactly like an element that used nothing - reporting all of its
    dependencies as unused would be catastrophic."""
    result = compute_declared_vs_used(
        {"other.bst": _opens(["/x"])},
        {"static.bst": ["a.bst", "b.bst"]},
        {"a.bst": {"/a"}, "b.bst": {"/b"}},
    )

    assert result["unused_candidates"] == []
    assert result["uncovered_elements"][0]["element"] == "static.bst"
    assert "statically-linked" in result["uncovered_elements"][0]["reason"]


def test_element_with_dropped_paths_is_uncovered():
    """A truncated read set is exactly the input that turns a used
    dependency into a false unused, so it refuses rather than guesses."""
    result = compute_declared_vs_used(
        {"app.bst": _opens(["/x"], dropped=17)},
        {"app.bst": ["dep.bst"]},
        {"dep.bst": {"/y"}},
    )

    assert result["unused_candidates"] == []
    assert "17 path(s) exceeded" in result["uncovered_elements"][0]["reason"]


def test_dependency_with_unreadable_artifact_is_skipped_not_unused():
    result = compute_declared_vs_used(
        {"app.bst": _opens(["/x"])},
        {"app.bst": ["missing.bst"]},
        {},
    )

    assert result["unused_candidates"] == []
    assert result["skipped"][0]["dependency"] == "missing.bst"


def test_dependency_that_staged_nothing_is_skipped_not_unused():
    result = compute_declared_vs_used(
        {"app.bst": _opens(["/x"])},
        {"app.bst": ["empty.bst"]},
        {"empty.bst": set()},
    )

    assert result["unused_candidates"] == []
    assert "staged no files" in result["skipped"][0]["reason"]


def test_partial_overlap_counts_as_used():
    """Opening even one staged file is proof the dependency was
    consumed - the real toolchain case, where 51 of 8369 staged files
    were read."""
    result = compute_declared_vs_used(
        {"app.bst": _opens(["/usr/bin/c++"])},
        {"app.bst": ["toolchain.bst"]},
        {"toolchain.bst": {f"/f{i}" for i in range(8000)} | {"/usr/bin/c++"}},
    )

    assert result["unused_candidates"] == []
    assert result["used"][0]["opened_files"] == 1


def test_no_opens_at_all_reports_unavailable():
    result = compute_declared_vs_used({}, {"a.bst": ["b.bst"]}, {"b.bst": {"/x"}})

    assert result["available"] is False
