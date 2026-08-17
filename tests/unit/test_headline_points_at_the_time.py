"""UX-65: the headline must name where the time actually is.

Asked whether the tool is what it claims to be, round 7's real capture
answered: the engine yes, the report no. On a 3587.6-second
`freedesktop-sdk` build `bga` led with

    Biggest Opportunity: 0.1% of wall-clock time is UNTRACKED HEAD (3.47s)

and ranked what to fix by blast radius, topped by two elements it
simultaneously labelled *"structural: may not reflect real compute
work"* — while its own critical-path block showed **four elements at 94%
of the build**, `cmake-stage1` alone 43.5%.

Neither ranking was mis-computed. Both were the wrong question for that
build: `Biggest Opportunity` is the largest *non-execution* category,
which degenerates when attribution is 99.9% execution-bound; blast radius
answers "who depends on me", which matters when the graph constrains, not
when the chain does.
"""
from bga.ingest.models import AnalysisResult
from bga.report.text import format_text


def _result(*, attribution, floors, path_detail, total_us, blast=None):
    return AnalysisResult(
        attribution=attribution,
        floors=floors,
        total_duration_us=total_us,
        confidence={"primary": 1.0},
        signals={
            "critical_path": [d["element_uid"] for d in path_detail],
            "critical_path_detail": path_detail,
            "top_blast_radius": list(blast or {}),
            "blast_radius": blast or {},
        },
    )


def _element(uid, dur_us, share, structural=False):
    return {
        "element_uid": uid, "duration_us": dur_us, "share_of_path": share,
        "is_structural_kind": structural,
        # Real `critical_path_detail` entries always carry these; the
        # renderer reads them for the chain listing further down.
        "element_kind": "import" if structural else "manual",
    }


# The real build's shape: execution-bound, chain-bound, concentrated.
CHAIN_BOUND = dict(
    attribution={"execution_on_chain_us": 3_583_900_000, "untracked_head_us": 3_470_000},
    floors={"t_infinity_observed": 3_583_900_000},
    total_us=3_587_600_000,
    path_detail=[
        _element("bootstrap/symlinks.bst", 0, 0.0, structural=True),
        _element("components/_private/cmake-stage1.bst", 1_558_750_000, 0.435),
        _element("components/openssl.bst", 679_900_000, 0.190),
        _element("components/python3.bst", 625_750_000, 0.175),
        _element("components/doxygen.bst", 503_550_000, 0.141),
        _element("components/libxml2.bst", 41_800_000, 0.012),
        # The rest of the real chain, so the 94.0% denominator is the
        # real 3583.90s path rather than a truncated one.
        _element("components/perl.bst", 0, 0.0),
        _element("components/_private/buildsystem-cmake.bst", 0, 0.0, structural=True),
        _element("components/expat.bst", 7_000_000, 0.002),
        _element("components/gperf.bst", 23_000_000, 0.006),
        _element("components/bison.bst", 144_150_000, 0.040),
    ],
    blast={"bootstrap/symlinks.bst": {"downstream_count": 124, "is_structural_kind": True}},
)


def _key_findings(result):
    return format_text(result).split("Certified Floors:")[0]


def test_a_sub_one_percent_category_is_not_headlined_as_an_opportunity():
    """3.47 seconds out of 3587.6 is rounding, not an opportunity."""
    text = _key_findings(_result(**CHAIN_BOUND))

    assert "UNTRACKED HEAD" not in text
    assert "execution-bound" in text


def test_the_headline_names_the_heaviest_elements_and_their_share():
    text = _key_findings(_result(**CHAIN_BOUND))

    assert "components/_private/cmake-stage1.bst" in text
    assert "94.0% of the" in text


def test_structural_elements_are_excluded_not_merely_tagged():
    """`UX-34` tagged them; here they must not be ranked at all, since a
    `stack` or `import` has no build commands to make faster."""
    text = _key_findings(_result(**CHAIN_BOUND))
    ranking = text.split("Most Worth Optimizing First")[1]

    assert "symlinks.bst" not in ranking


def test_a_chain_bound_build_ranks_by_critical_path_share():
    text = _key_findings(_result(**CHAIN_BOUND))

    assert "by share of the critical path" in text
    assert "chain-bound, not scheduler-bound" in text


# --- the other direction, which must not regress -----------------------


SCHEDULER_BOUND = dict(
    attribution={"execution_on_chain_us": 40_000_000, "resource_wait_us": 60_000_000},
    # T-infinity is a small share of wall clock: the graph has slack the
    # scheduler is not using, which is exactly when blast radius is right.
    floors={"t_infinity_observed": 20_000_000},
    total_us=100_000_000,
    path_detail=[_element("core.bst", 20_000_000, 1.0)],
    blast={"core.bst": {"downstream_count": 5, "is_structural_kind": False}},
)


def test_a_real_wait_category_is_still_the_headline():
    text = _key_findings(_result(**SCHEDULER_BOUND))

    assert "RESOURCE WAIT" in text
    assert "execution-bound" not in text


def test_a_scheduler_bound_build_still_ranks_by_blast_radius():
    text = _key_findings(_result(**SCHEDULER_BOUND))

    assert "by blast radius" in text
    assert "by share of the critical path" not in text
