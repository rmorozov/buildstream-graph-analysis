"""UX-1139: the capacity finding names the costliest pinned elements first.

`summarize_plane2_capacity` sorted pinned elements by name, and the
finding's sentence names the first three - so a project with many pins
was told about whichever sort first, and never how many more there were.
"""

import pathlib
import sys
from types import SimpleNamespace

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga.correlate import summarize_plane2_capacity
from bga.findings import _capacity_recommendation_finding

SPANS = {"a.bst": 1.0, "b.bst": 50.0, "c.bst": 5.0, "d.bst": 300.0, "e.bst": 20.0}


def _report():
    return {
        "per_element_parallelism": [
            {"element": uid, "work_span_s": span, "findings": ["pinned_to_one_job"]} for uid, span in SPANS.items()
        ]
    }


def test_pinned_elements_are_ordered_by_work_span():
    pinned = summarize_plane2_capacity(_report(), 4)["pinned_elements"]
    assert pinned == ["d.bst", "b.bst", "e.bst", "c.bst", "a.bst"]


def test_the_sentence_names_three_and_counts_the_rest():
    pinned = summarize_plane2_capacity(_report(), 4)["pinned_elements"]
    result = SimpleNamespace(
        capacity_recommendation={
            "binding_constraint": "CPU",
            "recommended_builders": 4,
            "builders": 4,
            "native_max_jobs": 4,
            "host_cpu_count": 4,
            "cores_busy": 1.0,
            "builders_change": 0,
            "constraints": [{"name": "CPU", "allows": 4, "reason": "r"}],
            "pinned_elements": pinned,
            "caveat": "c",
        }
    )
    (finding,) = _capacity_recommendation_finding(result)
    line = next(d for d in finding["detail"] if "Free capacity" in d)
    assert "d.bst, b.bst, e.bst and 2 more elements asked" in line, line


def test_the_text_report_counts_the_rest_too():
    from bga.report.text import _plane2_knee_caveat

    plane2 = dict(summarize_plane2_capacity(_report(), 4), cores_busy=1.0)
    line = next(line for line in _plane2_knee_caveat(plane2, None) if "Free capacity" in line)
    assert "d.bst, b.bst, e.bst and 2 more elements asked" in line, line
