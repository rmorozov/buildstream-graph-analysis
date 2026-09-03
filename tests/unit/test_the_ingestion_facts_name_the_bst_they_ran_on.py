"""UX-571: the ingestion facts say which `bst` they were last run against.

`docs/spec/ingestion-pipeline.md` was a 2026-08-14 log of facts
"confirmed against real `bst` 2.7.0" and nothing tied that number to a
binary anyone had run. Two of the facts had also stopped being true.

The version comes from the guard now: `test_bst_extract_run.py`'s
`bst_version()` reads it off the binary, and the document's
"Last exercised on" line has to agree. Facts 9 and 11 keep their old
claim as a quotation and name what superseded it - each named `bga`
module is read here, so the correction cannot name a fiction.
"""
import re
from pathlib import Path

import pytest

from .test_bst_extract_run import BST_AVAILABLE, bst_version

# Spelled out rather than imported: tests/skip_reasons.py resolves a
# literal or a module-level constant, and an imported name counts as
# unreadable (tests/unit/test_every_skip_reason_is_declared.py).
BST_SKIP_REASON = "bst not found on PATH - see docs/spec/ingestion-pipeline.md"

REPO = Path(__file__).resolve().parents[2]
DOC = REPO / "docs" / "spec" / "ingestion-pipeline.md"

# The "Last exercised on `bst` <version>, <date>" line the headings carry.
EXERCISED = re.compile(
    r"\*\*Last exercised on `bst` (?P<version>[0-9]+(?:\.[0-9]+)*(?:, [0-9]+(?:\.[0-9]+)*)*), "
    r"(?P<date>\d{4}-\d{2}-\d{2})\.\*\*")

# `element_kind` as a value that is read, not as a fragment of a longer
# name: `by_element_kind_phase` in bga/floors/cold.py is a *task* kind
# pool and matching it would let the document name a non-consumer.
ELEMENT_KIND_READ = re.compile(r"(?<![A-Za-z0-9_])element_kinds?(?![A-Za-z0-9_])")

_QUOTED = re.compile(r'"[^"]*"')


def _doc() -> str:
    return DOC.read_text()


def _fact(number: int) -> str:
    """One numbered fact's own text - the subject, not the argument.

    A guard that greps the whole document finds the phrase in the
    sentence that supersedes it.
    """
    text = _doc()
    start = re.search(rf"^{number}\. \*\*", text, re.M)
    assert start, f"fact {number} not found"
    end = re.search(rf"^(?:{number + 1}\. |## )", text[start.end():], re.M)
    block = text[start.start():start.end() + (end.start() if end else len(text))]
    return re.sub(r"\s+", " ", block)


def _unquoted(block: str) -> str:
    return _QUOTED.sub(" ", block)


# --- the version is the guard's, not the prose's -------------------------

def test_both_facts_headings_say_which_bst_they_were_last_exercised_on():
    hits = EXERCISED.findall(_doc())
    headings = re.findall(r"^## Empirically confirmed facts.*$", _doc(), re.M)
    assert len(headings) == 2, headings
    assert len(hits) == len(headings), (
        f"{len(headings)} facts headings, {len(hits)} 'Last exercised on' "
        f"lines - every facts section names the bst it last ran against")
    assert len(set(hits)) == 1, f"the sections disagree: {hits}"


@pytest.mark.bst
@pytest.mark.skipif(not BST_AVAILABLE, reason=BST_SKIP_REASON)
def test_the_documented_version_is_the_one_the_binary_reports():
    documented = EXERCISED.search(_doc())
    assert documented, "no 'Last exercised on' line to check"
    # `UX-571`, corrected in round 83: the tier runs in two environments
    # with two binaries - CI's runner and the development container - so
    # the line names every version the facts were exercised on, and this
    # asks whether the binary running now is one of them. A version
    # outside the set is a tier that has never been run here.
    versions = [one.strip() for one in documented.group("version").split(",")]
    assert bst_version() in versions, (
        f"the document says it was last exercised on bst "
        f"{', '.join(versions)}; this binary reports {bst_version()}. "
        f"Re-run the bst tier here and add the version to the line.")


# --- fact 9: element_kind is read now ------------------------------------

def test_fact_9_no_longer_claims_element_kind_is_unread():
    assert "not read by any analysis consumer" not in _unquoted(_fact(9)), (
        "fact 9 asserts element_kind is read by no analysis consumer, "
        "outside of the quotation that supersedes it - but "
        + ", ".join(_fact_9_modules()) + " all read it")


def _fact_9_modules():
    return sorted(set(re.findall(r"`(bga/[A-Za-z0-9_/]+\.py)`", _fact(9))))


def test_fact_9_names_what_superseded_its_old_claim():
    assert "stopped being true" in _fact(9), (
        "fact 9 keeps its old claim as a quotation; it must also say what "
        "superseded it, the way UX-88 corrected fact 5")


def test_every_module_fact_9_names_really_reads_element_kind():
    modules = _fact_9_modules()
    assert len(modules) >= 6, modules
    for module in modules:
        path = REPO / module
        assert path.is_file(), f"fact 9 names {module}, which does not exist"
        assert ELEMENT_KIND_READ.search(path.read_text()), (
            f"fact 9 names {module} as reading `element_kind`; it does not")


# --- fact 11: the query-cache cost is measured now ------------------------

def test_fact_11_no_longer_claims_query_cache_is_dropped_entirely():
    assert "dropped by the ingestion pipeline entirely" not in _unquoted(_fact(11)), (
        "fact 11 asserts the Query cache activity is dropped entirely, "
        "outside of the quotation that supersedes it - but P4-14 landed "
        "`pipeline_overhead`")


def test_fact_11_names_what_superseded_its_old_claim():
    assert "stopped being true" in _fact(11), (
        "fact 11 keeps its old claim as a quotation; it must also say what "
        "superseded it, the way UX-88 corrected fact 5")


def test_fact_11_names_the_pipeline_overhead_that_replaced_it():
    block = _fact(11)
    assert "`pipeline_overhead`" in block, block
    assert "_compute_pipeline_overhead" in (REPO / "bga" / "analyzer.py").read_text()
    named = re.findall(r"`(tests/unit/[A-Za-z0-9_]+\.py)`", block)
    assert named, "fact 11 must name the guard that holds pipeline_overhead"
    for test_file in named:
        assert (REPO / test_file).is_file(), f"fact 11 names a missing {test_file}"
