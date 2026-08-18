"""UX-89: seven near-identical blocks become one, and a 0.2s `ranlib`
stops being a finding.

On `examples/06`'s baseline capture, `correlate`'s "What to do next"
printed seven blocks - `lib-a.bst` through `lib-f.bst` and `app.bst` -
each carrying the same three lines and differing only in their numbers.
Forty-eight lines of report to convey two facts. At freedesktop-sdk
scale the same structure would bury the one distinctive row (`core.bst`)
under dozens of interchangeable ones.

Two changes, and they are independent:

1. Elements whose finding *sets* are identical share one block, with the
   per-element figures collapsed to ranges and still published
   per-element in `--format json`.
2. The single-process serialization rule gains the materiality bar every
   other Plane 2 rule already had. `ar` and `ranlib` are single
   processes by construction, so every element that links a static
   library earned a "SINGLE process holding 0.2s" line - which is how
   `ar` works, not a finding.

Measured on a real dual-plane capture of `examples/06` taken for this
task (bst 2.7.0, `--builders 4 --max-jobs 4`, cache cleared): 48 lines
before, 21 after, with `core.bst` still leading on its own.
"""
from bga.correlate import (
    _collapse_range, _grouped_blocks, _group_header, _name_elements,
    _SERIALIZATION_NOTABLE_S, ElementJoin, _recommend, format_correlation,
)


# --- the materiality bar ------------------------------------------------

def _joined(**kwargs) -> ElementJoin:
    base = dict(
        element="lib-a.bst", declared=True, on_critical_path=True,
        critical_path_share=0.09, potential_saving_us=3_000_000,
        saving_share=0.082, cores_busy=1.74, cpu_coverage=0.81,
    )
    base.update(kwargs)
    return ElementJoin(**base)


def _ids(joined) -> list:
    return [step['id'] for step in _recommend(joined)]


def test_a_tenth_of_a_second_of_ranlib_is_not_a_finding():
    """The real numbers from the capture: `ranlib`, one process, 0.2s,
    inside an element whose whole realizable saving is 3.0s."""
    assert 'serialization-point' not in _ids(
        _joined(serial_binary={"binary": "ranlib", "wall_s": 0.2})
    )


def test_a_real_serialization_point_still_reports():
    """The rule is not switched off - a single process holding a
    meaningful share of an element is exactly what it exists to name."""
    assert 'serialization-point' in _ids(
        _joined(potential_saving_us=60_000_000,
                serial_binary={"binary": "ld", "wall_s": 12.0})
    )


def test_the_bar_is_relative_as_well_as_absolute():
    """`UX-72`'s materiality bar is a share of the element's own worth,
    so on a large element the threshold rises rather than staying at the
    absolute backstop. 4s of `ld` inside an element worth 900s is 0.4% -
    below the 1% share - and is not the next thing to do."""
    assert 'serialization-point' not in _ids(
        _joined(potential_saving_us=900_000_000,
                serial_binary={"binary": "ld", "wall_s": 4.0})
    )
    assert 'serialization-point' in _ids(
        _joined(potential_saving_us=900_000_000,
                serial_binary={"binary": "ld", "wall_s": 20.0})
    )


def test_the_absolute_backstop_holds_when_saving_was_never_evaluated():
    """A finding worth under a second is not a next action however it is
    measured - including when there is no saving to take a share of."""
    assert _SERIALIZATION_NOTABLE_S == 1.0
    assert 'serialization-point' not in _ids(
        _joined(potential_saving_us=0, saving_share=None, cores_busy=0.5,
                serial_binary={"binary": "ranlib", "wall_s": 0.2})
    )


# --- range collapsing ---------------------------------------------------

def test_a_range_reads_as_one_number_when_the_group_agrees():
    """Two identical numbers are one number. Printing `1.7-1.7` implies
    a spread the group does not have."""
    assert _collapse_range([1.74, 1.74], lambda v: f"{v:.1f}") == "1.7"
    assert _collapse_range([1.82, 1.35], lambda v: f"{v:.1f}") == "1.4-1.8"


def test_the_unit_is_not_repeated_inside_a_range():
    assert _collapse_range([0.06, 0.09], lambda v: f"{v * 100:.0f}", "%") == "6-9%"


def test_an_empty_population_collapses_to_nothing_rather_than_zero():
    assert _collapse_range([None, None], lambda v: f"{v:.1f}") == ""


# --- naming a group -----------------------------------------------------

def test_a_run_of_sibling_names_contracts():
    assert _name_elements(
        ["lib-a.bst", "lib-b.bst", "lib-c.bst", "lib-d.bst", "lib-e.bst", "lib-f.bst"]
    ) == "lib-a.bst..lib-f.bst"


def test_unrelated_names_are_listed_in_full():
    """The contraction must not invent a family. `core`/`app`/`codegen`
    share nothing, so all three are named."""
    assert _name_elements(["app.bst", "codegen.bst", "core.bst"]) == (
        "app.bst, codegen.bst, core.bst"
    )


def test_a_run_and_an_outsider_keep_both_forms():
    assert _name_elements(
        ["app.bst", "lib-a.bst", "lib-b.bst", "lib-c.bst"]
    ) == "app.bst, lib-a.bst..lib-c.bst"


def test_two_elements_are_never_contracted():
    """`lib-a.bst..lib-b.bst` saves nothing and costs the reader an
    expansion."""
    assert _name_elements(["lib-a.bst", "lib-b.bst"]) == "lib-a.bst, lib-b.bst"


# --- grouping -----------------------------------------------------------

def _entry(name, ids, **facts):
    base = {
        "element": name,
        "recommendations": [{"id": i, "severity": "high", "text": f"{i} for {name}"}
                            for i in ids],
        "cpu_coverage": 0.81, "critical_path_share": 0.09,
        "potential_saving_us": 3_000_000,
    }
    base.update(facts)
    return base


def test_identical_finding_sets_form_one_group():
    groups = _grouped_blocks([
        _entry("lib-a.bst", ["already-compute-bound", "cpu-concentration"]),
        _entry("lib-b.bst", ["already-compute-bound", "cpu-concentration"]),
    ])
    assert len(groups) == 1
    assert groups[0][0] == ["lib-a.bst", "lib-b.bst"]


def test_a_different_finding_set_is_a_different_group():
    """`core.bst` carries `pinned-to-one-job` and the libs do not. That
    is the whole distinction the report exists to surface, so it must
    survive grouping."""
    groups = _grouped_blocks([
        _entry("core.bst", ["pinned-to-one-job", "cpu-concentration"]),
        _entry("lib-a.bst", ["already-compute-bound", "cpu-concentration"]),
        _entry("lib-b.bst", ["already-compute-bound", "cpu-concentration"]),
    ])
    assert [g[0] for g in groups] == [["core.bst"], ["lib-a.bst", "lib-b.bst"]]


def test_grouping_never_reorders_what_leads():
    """The list arrives ranked by Plane 1 impact and a group takes the
    position of its strongest member, so the first block is still the
    first element."""
    groups = _grouped_blocks([
        _entry("lib-a.bst", ["already-compute-bound"]),
        _entry("core.bst", ["pinned-to-one-job"]),
        _entry("lib-b.bst", ["already-compute-bound"]),
    ])
    assert groups[0][0] == ["lib-a.bst", "lib-b.bst"]
    assert groups[1][0] == ["core.bst"]


def test_a_single_element_group_renders_exactly_as_before():
    """Nothing changes for the case that was never repetitive - the
    header is the bare element name and the finding keeps its own
    words."""
    assert _group_header(["core.bst"], [_entry("core.bst", ["x"])]) == "core.bst:"


def test_a_group_header_carries_the_impact_the_findings_no_longer_do():
    header = _group_header(
        ["lib-a.bst", "lib-b.bst"],
        [_entry("lib-a.bst", ["x"], critical_path_share=0.09,
                potential_saving_us=3_000_000),
         _entry("lib-b.bst", ["x"], critical_path_share=0.06,
                potential_saving_us=2_000_000)],
    )
    assert header == (
        "lib-a.bst, lib-b.bst (2 elements, 6-9% of the critical path each, "
        "2.0-3.0s apiece, 5.0s together):"
    )


# --- end to end ---------------------------------------------------------

def _result(actionable):
    return {
        "elements": actionable, "actionable": actionable, "restructuring": [],
        "attribution_unreliable": False, "attribution_partial": False,
        "ranking": {"metric": "realizable_saving_us", "degenerate": False,
                    "tied_saving_us": None},
        "coverage": {"joined_elements": len(actionable), "plane1_elements": len(actionable),
                     "plane2_elements": len(actionable), "plane1_only_with_impact": [],
                     "undeclared_plane2_elements": [], "aggregating_dependency_pairs": 0},
        "note": "n/a",
    }


def test_the_grouped_block_states_the_range_not_one_members_number():
    entries = [
        _entry(name, ["already-compute-bound", "cpu-concentration"],
               cores_busy=cores,
               dominant_binary={"binary": "cc1plus", "cpu_share": share,
                                "count": 5, "cpu_us": 3_000_000})
        for name, cores, share in (
            ("lib-a.bst", 1.74, 0.76), ("lib-b.bst", 1.35, 0.72),
        )
    ]
    text = format_correlation(_result(entries))
    assert "already compute-bound at 1.4-1.7 cores busy" in text
    assert "`cc1plus` is 72-76% of each one's measured CPU" in text
    # And the per-element sentences it replaced are gone.
    assert "already-compute-bound for lib-a.bst" not in text


def test_a_finding_whose_figures_do_not_generalize_keeps_its_own_words():
    """`peak-memory` is an absolute RSS to multiply by concurrency and
    `redundant-operation` names other elements; averaging either would
    say something the measurement does not. The block gets longer rather
    than wronger."""
    entries = [
        _entry(name, ["peak-memory"], peak_rss_kb=2_000_000)
        for name in ("lib-a.bst", "lib-b.bst")
    ]
    text = format_correlation(_result(entries))
    assert "peak-memory for lib-a.bst" in text


def test_a_grouped_coverage_line_speaks_about_each_element():
    entries = [
        _entry(name, ["already-compute-bound"], cores_busy=1.7, cpu_coverage=0.81)
        for name in ("lib-a.bst", "lib-b.bst")
    ]
    text = format_correlation(_result(entries))
    assert "(81% of each element's processes were measured)" in text


def test_the_overflow_line_counts_elements_not_groups():
    """The cap is about how much a reader is asked to read, and a group
    of twelve is one block. The overflow must still say how many
    *elements* were withheld, or a reader cannot tell whether the list is
    complete."""
    entries = [
        _entry(f"solo-{i}.bst", [f"finding-{i}"]) for i in range(12)
    ]
    text = format_correlation(_result(entries))
    assert "(+4 more element(s) with findings, see --format json)" in text
