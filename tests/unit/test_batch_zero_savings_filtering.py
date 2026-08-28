"""Tests for UX-26: `compute_batch_opportunities` (UX-20) reports every
independent-element group it finds unconditionally, including ones with
zero real simulated combined savings - real repro from the doc: a real
`examples/05-cmake-cpp-toolchain` run reported
`lib-a.bst, lib-b.bst: ... (saves 0.00s combined, vs. lib-a.bst=0.00s,
lib-b.bst=0.00s fixed alone)`, pure noise since neither element was
ever a real bottleneck.

`compute_batch_opportunities` itself is untouched (out of scope, still
covered by `tests/unit/test_batch_opportunities.py`) - the fix lives in
the new `serialize_batch_opportunities` report-shape helper
(`bga/structural/batching.py`) and in `bga/report/text.py`'s rendering
of it.
"""
from bga.structural.batching import BatchGroup, BatchOpportunities, serialize_batch_opportunities


def _zero_group(elements):
    return BatchGroup(
        elements=list(elements),
        baseline_makespan_us=6_400_000,
        combined_makespan_us=6_400_000,
        combined_savings_us=0,
        individual_savings_us={e: 0 for e in elements},
    )


def _real_group(elements, baseline_us, combined_us):
    return BatchGroup(
        elements=list(elements),
        baseline_makespan_us=baseline_us,
        combined_makespan_us=combined_us,
        combined_savings_us=baseline_us - combined_us,
        individual_savings_us={e: 0 for e in elements},
    )


def test_zero_savings_group_is_moved_out_of_groups():
    batch_result = BatchOpportunities(
        groups=[_zero_group(["lib-a.bst", "lib-b.bst"])], serialized_pairs=[],
    )

    serialized = serialize_batch_opportunities(batch_result)

    assert serialized["groups"] == []
    assert serialized["omitted_zero_savings_groups"] == [{"elements": ["lib-a.bst", "lib-b.bst"]}]


def test_genuine_nonzero_savings_group_still_reported_in_groups():
    batch_result = BatchOpportunities(
        groups=[_real_group(["app.bst", "extra.bst"], 10_000_000, 6_000_000)], serialized_pairs=[],
    )

    serialized = serialize_batch_opportunities(batch_result)

    assert len(serialized["groups"]) == 1
    assert serialized["groups"][0]["elements"] == ["app.bst", "extra.bst"]
    assert serialized["groups"][0]["combined_savings_us"] == 4_000_000
    assert serialized["omitted_zero_savings_groups"] == []


def test_mixed_zero_and_nonzero_groups_are_partitioned_correctly():
    batch_result = BatchOpportunities(
        groups=[
            _real_group(["app.bst", "extra.bst"], 10_000_000, 6_000_000),
            _zero_group(["lib-a.bst", "lib-b.bst"]),
        ],
        serialized_pairs=[("core.bst", "lib-c.bst")],
    )

    serialized = serialize_batch_opportunities(batch_result)

    assert [g["elements"] for g in serialized["groups"]] == [["app.bst", "extra.bst"]]
    assert serialized["omitted_zero_savings_groups"] == [{"elements": ["lib-a.bst", "lib-b.bst"]}]
    # Untouched by this fix - not the target of this filtering.
    assert serialized["serialized_pairs"] == [("core.bst", "lib-c.bst")]


def test_no_groups_at_all_produces_empty_lists_not_missing_keys():
    serialized = serialize_batch_opportunities(BatchOpportunities(groups=[], serialized_pairs=[]))

    assert serialized["groups"] == []
    assert serialized["omitted_zero_savings_groups"] == []
    assert serialized["serialized_pairs"] == []


# --- text-report rendering --------------------------------------------

def _render_batch_section(batch_opportunities):
    """Exercises the same rendering path `format_text` uses for the
    batch_opportunities block, via a real (mostly-empty)
    `AnalysisResult` - every field has a real default, so only the
    fields this block actually reads need real content."""
    from bga.ingest.models import AnalysisResult
    from bga.report.text import format_text

    result = AnalysisResult(run_id="test-run", structural={
        "metrics": {"num_elements": 2, "num_edges": 1, "max_depth": 1},
        "sensitivity": {"top_opportunities": [], "total_improvable_time_us": 0, "best_case_speedup": 1.0},
        "batch_opportunities": batch_opportunities,
    })
    return format_text(result)


def test_text_report_omits_zero_savings_group_and_names_the_count():
    batch_opportunities = {
        "groups": [],
        "omitted_zero_savings_groups": [{"elements": ["lib-a.bst", "lib-b.bst"]}],
        "serialized_pairs": [],
    }

    output = _render_batch_section(batch_opportunities)

    assert "lib-a.bst" not in output
    assert "lib-b.bst" not in output
    assert "1 further group(s) had no measurable combined effect, omitted" in output


def test_text_report_still_shows_a_genuine_savings_group():
    batch_opportunities = {
        "groups": [{
            "elements": ["app.bst", "extra.bst"],
            "baseline_makespan_us": 10_000_000,
            "combined_makespan_us": 6_000_000,
            "combined_savings_us": 4_000_000,
            "individual_savings_us": {"app.bst": 0, "extra.bst": 0},
        }],
        "omitted_zero_savings_groups": [],
        "serialized_pairs": [],
    }

    output = _render_batch_section(batch_opportunities)

    assert "Independently workable together" in output
    assert "app.bst" in output and "extra.bst" in output
    assert "saves 4.00s combined" in output
    assert "further group(s)" not in output
