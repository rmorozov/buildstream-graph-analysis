"""UX-51: joining the two planes on element UID.

`docs/design/directions.md` named the seam between Plane 1 ("which
elements matter") and Plane 2 ("what happened inside them") as the
biggest remaining gap. It is closed as an explicit join rather than a
merge, and these tests pin the properties that make the join trustworthy
rather than merely present.

The payoff to protect is the sentence neither plane can produce alone:
*the element that dominates your critical path is not compute-bound, so
fix how it is built, not what it builds.*
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

from bga.correlate import correlate, format_correlation

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN_RUN = os.path.join(REPO, "tests", "fixtures", "golden", "mixed_task_kinds")


def _analysis(critical_path=(), opportunities=(), critical_path_us=20_000_000, blast=None):
    return {
        "signals": {
            "critical_path": list(critical_path),
            "blast_radius": blast or {},
        },
        "structural": {
            "sensitivity": {
                "top_opportunities": [list(o) for o in opportunities],
                "critical_path_us": critical_path_us,
            }
        },
    }


def _native(parallelism=(), cpu=None, unused=()):
    return {
        "by_element": {entry["element"]: 1 for entry in parallelism},
        "per_element_parallelism": list(parallelism),
        "cpu_time": {"per_element": cpu or {}},
        "declared_vs_used": {"unused_candidates": list(unused)},
    }


def _cpu(cores_busy, coverage=1.0):
    return {"cpu_per_wall_second": cores_busy, "coverage": coverage}


# --- the finding the join exists for -----------------------------------

def test_critical_path_element_that_is_waiting_is_told_to_fix_its_parallelism():
    """The real `core.bst` case: 25% of the critical path at 0.85 cores
    busy with `-j1`. Plane 1 knows the first half, Plane 2 the second,
    and only the join can say what to do."""
    result = correlate(
        _analysis(critical_path=["core.bst"], opportunities=[("core.bst", 0.25, 25.0)]),
        _native(
            parallelism=[{"element": "core.bst", "requested_jobs": 1,
                          "findings": ["pinned_to_one_job"]}],
            cpu={"core.bst": _cpu(0.85)},
        ),
    )

    steps = [s["text"] for s in result["actionable"][0]["recommendations"]]
    assert result["actionable"][0]["element"] == "core.bst"
    assert "waiting, not computing" in steps[0]
    assert "notparallel" in steps[0]


def test_critical_path_element_that_is_busy_is_told_the_opposite():
    """The negative result is the other half of the value: it stops a
    reader looking at the micro plane for an element that has nothing to
    give there."""
    result = correlate(
        _analysis(critical_path=["heavy.bst"], opportunities=[("heavy.bst", 0.4, 40.0)]),
        _native(
            parallelism=[{"element": "heavy.bst", "requested_jobs": 4, "findings": []}],
            cpu={"heavy.bst": _cpu(3.8)},
        ),
    )

    step = result["actionable"][0]["recommendations"][0]["text"]
    assert "already compute-bound" in step
    assert "less work" in step


def test_underachieving_element_is_distinguished_from_a_pinned_one():
    """Asked for -j4 and got one core: a different fix from `-j1`."""
    result = correlate(
        _analysis(critical_path=["slow.bst"], opportunities=[("slow.bst", 0.3, 30.0)]),
        _native(
            parallelism=[{"element": "slow.bst", "requested_jobs": 4, "findings": []}],
            cpu={"slow.bst": _cpu(0.9)},
        ),
    )

    step = result["actionable"][0]["recommendations"][0]["text"]
    assert "despite asking for -j4" in step
    assert "notparallel" not in step


def test_unused_dependencies_are_reported_as_a_macro_fix():
    result = correlate(
        _analysis(),
        _native(unused=[{"element": "lib.bst", "dependency": "codegen.bst"}]),
    )

    step = result["actionable"][0]["recommendations"][0]["text"]
    assert "1 declared build dependency" in step
    # UX-68: never a verdict - the producer cannot distinguish a
    # runtime-only dependency from an unused one.
    assert "free" not in step
    assert "evidence, not a verdict" in step
    assert "codegen.bst" in step


# --- the ways this could mislead ---------------------------------------

def test_element_on_the_path_but_unable_to_move_the_finish_makes_no_claim():
    """An element can sit on the critical path and still have zero
    measurable saving (UX-44). An earlier version rendered "holds 0% of
    the critical path and is genuinely compute-bound" for exactly that
    case - a confident statement about nothing."""
    result = correlate(
        _analysis(critical_path=["app.bst"], opportunities=[]),
        _native(
            parallelism=[{"element": "app.bst", "requested_jobs": 4, "findings": []}],
            cpu={"app.bst": _cpu(1.3)},
        ),
    )

    assert result["actionable"] == []


def test_untraced_but_impactful_elements_are_named_not_assumed_fine():
    """Plane 1 says this element matters; Plane 2 never saw it. Silence
    would read as "nothing to report inside it"."""
    result = correlate(
        _analysis(critical_path=["ghost.bst"], opportunities=[("ghost.bst", 0.5, 50.0)]),
        _native(),
    )

    assert result["coverage"]["plane1_only_with_impact"] == ["ghost.bst"]
    assert "ghost.bst" in format_correlation(result)


def test_partial_cpu_coverage_is_surfaced():
    """UX-45's coverage must survive the join - a recommendation built on
    81% of an element's processes should say so."""
    result = correlate(
        _analysis(critical_path=["core.bst"], opportunities=[("core.bst", 0.5, 50.0)]),
        _native(
            parallelism=[{"element": "core.bst", "requested_jobs": 1,
                          "findings": ["pinned_to_one_job"]}],
            cpu={"core.bst": _cpu(0.8, coverage=0.81)},
        ),
    )

    assert "81% of this element's processes were measured" in format_correlation(result)


def test_ranking_follows_plane1_impact():
    """Plane 2 explains the top of Plane 1's list; it must not reorder
    it, or the user's question changes under them."""
    result = correlate(
        _analysis(
            opportunities=[("small.bst", 0.1, 10.0), ("big.bst", 0.6, 60.0)],
            critical_path_us=10_000_000,
        ),
        _native(
            parallelism=[
                {"element": "big.bst", "requested_jobs": 1, "findings": ["pinned_to_one_job"]},
                {"element": "small.bst", "requested_jobs": 1, "findings": ["pinned_to_one_job"]},
            ],
            cpu={"big.bst": _cpu(0.5), "small.bst": _cpu(0.5)},
        ),
    )

    assert [e["element"] for e in result["actionable"]] == ["big.bst", "small.bst"]


def test_empty_inputs_are_safe():
    result = correlate(_analysis(), _native())

    assert result["actionable"] == []
    assert "No element has a finding in both planes" in format_correlation(result)


@pytest.mark.parametrize("count,expected", [(1, "1 declared build dependency"), (3, "3 declared build dependencies")])
def test_dependency_pluralisation(count, expected):
    unused = [{"element": "x.bst", "dependency": f"d{i}.bst"} for i in range(count)]

    result = correlate(_analysis(), _native(unused=unused))

    assert expected in result["actionable"][0]["recommendations"][0]["text"]


def test_join_reports_its_own_coverage():
    result = correlate(
        _analysis(critical_path=["a.bst", "b.bst"], opportunities=[("a.bst", 0.5, 50.0)]),
        _native(
            parallelism=[{"element": "a.bst", "requested_jobs": 4, "findings": []}],
            cpu={"a.bst": _cpu(2.0)},
        ),
    )

    coverage = result["coverage"]
    assert coverage["joined_elements"] == 1
    assert coverage["plane2_elements"] == 1
    assert coverage["plane1_elements"] >= 2


# --- UX-71: rank on what a fix is worth, not on a capped proxy ---------
#
# Round 9's real capture, reduced to the five elements that matter. Its
# `top_opportunities` score is `min(duration, next_binding_gap)/makespan`
# with `next_binding_gap` = 114.1s, so every one of the five scores an
# identical 0.0316 - while the simulated savings span 5x.

_TIED_SCORE = 114_100_000 / 3_610_500_000

REAL_ELEMENTS = [
    # (uid, duration_us, share_of_path, realizable_saving_us, cores_busy)
    ("components/_private/cmake-stage1.bst", 1_569_800_000, 0.435, 1_569_800_000, 3.41),
    ("components/openssl.bst", 672_100_000, 0.186, 522_550_000, 1.61),
    ("components/python3.bst", 639_750_000, 0.177, 114_100_000, 1.86),
    ("components/doxygen.bst", 513_550_000, 0.142, 513_550_000, 3.56),
    ("components/bison.bst", 144_150_000, 0.040, 144_150_000, 0.91),
]


def _real_analysis(with_savings=True):
    detail = []
    for uid, dur, share, saving, _cores in REAL_ELEMENTS:
        entry = {"element_uid": uid, "duration_us": dur, "share_of_path": share,
                 "is_structural_kind": False}
        if with_savings:
            entry["realizable_saving_us"] = saving
        detail.append(entry)
    return {
        "total_duration_us": 3_614_220_000,
        "signals": {
            "critical_path": [e[0] for e in REAL_ELEMENTS],
            "critical_path_detail": detail,
            "blast_radius": {},
        },
        "structural": {
            "sensitivity": {
                # The saturated proxy, exactly as the real capture carries it.
                "top_opportunities": [[e[0], _TIED_SCORE, _TIED_SCORE * 100]
                                      for e in REAL_ELEMENTS],
                "critical_path_us": 3_610_500_000,
            }
        },
    }


def _real_native():
    return _native(
        parallelism=[{"element": uid, "requested_jobs": 4, "findings": []}
                     for uid, *_ in REAL_ELEMENTS],
        cpu={uid: _cpu(cores) for uid, _d, _s, _sav, cores in REAL_ELEMENTS},
    )


def test_ranking_uses_the_realizable_saving_not_the_capped_proxy():
    """The defect `UX-71` was filed for: all five candidates scored an
    identical 0.0316, so `-potential_saving_us` was a constant and the
    order came from the alphabetical tiebreak - putting `bison.bst`
    (144.2s) second, above `openssl.bst` (672.1s)."""
    result = correlate(_real_analysis(), _real_native())

    ranked = [e["element"] for e in result["elements"] if e["potential_saving_us"]]
    assert ranked[:4] == [
        "components/_private/cmake-stage1.bst",
        "components/openssl.bst",
        "components/doxygen.bst",
        "components/bison.bst",
    ]
    assert result["ranking"]["metric"] == "realizable_saving_us"
    assert result["ranking"]["degenerate"] is False


def test_the_headline_verdict_fires_on_the_real_capture():
    """The sentence the join exists to produce, which the saturated gate
    made unreachable: `bison.bst` at 0.91 cores busy was measured every
    round and never mentioned."""
    result = correlate(_real_analysis(), _real_native())

    assert any("waiting, not computing" in step
               for step in _steps(result, "components/bison.bst"))
    assert any("already compute-bound" in step
               for step in _steps(result, "components/_private/cmake-stage1.bst"))


def test_a_cheap_win_below_the_gate_is_still_reported():
    """`bison.bst` is worth 4.0% of the build - below the 5% gate - and
    is reported anyway because Plane 2 says the fix is a job count.
    `python3.bst`, worth less and already compute-bound, is not: there is
    no cheap fix there to name."""
    result = correlate(_real_analysis(), _real_native())
    steps = {e["element"]: e["recommendations"] for e in result["actionable"]}

    assert "components/bison.bst" in steps
    assert "components/python3.bst" not in steps


def test_a_saturated_ranking_is_declared_rather_than_broken_by_name():
    """An artifact from a `bga` older than `UX-70` has no simulation to
    rank on. The join degrades to the proxy - and says that every element
    carries the same impact, instead of presenting alphabetical order as
    a ranking."""
    result = correlate(_real_analysis(with_savings=False), _real_native())

    assert result["ranking"]["metric"] == "sensitivity_score"
    assert result["ranking"]["degenerate"] is True
    assert result["ranking"]["tied_saving_us"] == 114_100_000
    text = format_correlation(result)
    assert "the order below is alphabetical, not an impact ranking" in text


def test_the_path_share_comes_from_the_same_place_analyze_prints():
    """`bga analyze` and `bga correlate` must not describe one element
    with two different numbers."""
    result = correlate(_real_analysis(), _real_native())
    by_uid = {e["element"]: e for e in result["elements"]}

    assert by_uid["components/openssl.bst"]["critical_path_share"] == 0.186
    assert by_uid["components/openssl.bst"]["potential_saving_us"] == 522_550_000


def test_analyze_and_correlate_name_the_same_element_first():
    """`UX-71`'s standing guarantee. The two commands read the same
    artifact and answer the same question; on the real capture they
    disagreed, because one had been re-based on the simulation and the
    other still ranked on the proxy. Cheaper to pin here than to
    re-notice in a later audit round."""
    import json as _json

    from bga.ingest.models import AnalysisResult
    from bga.report.json import format_json
    from bga.findings import heaviest_on_path

    analysis = _real_analysis()
    result = AnalysisResult(
        attribution={"execution_on_chain_us": 3_610_500_000},
        floors={"t_infinity_observed": 3_610_500_000},
        total_duration_us=analysis["total_duration_us"],
        confidence={"primary": 1.0},
        signals=analysis["signals"],
        structural=analysis["structural"],
    )

    analyze_first = heaviest_on_path(result)[0]["element_uid"]
    joined = correlate(_json.loads(format_json(result)), _real_native())
    correlate_first = joined["elements"][0]["element"]

    assert analyze_first == correlate_first == "components/_private/cmake-stage1.bst"


# --- UX-72: the join reads all of Plane 2, ranked by evidence ----------
#
# Round 9's own numbers for `cmake-stage1.bst`, which is 43.4% of the
# build and whose entire row used to be the hedged declared-vs-used
# sentence.

CMAKE = "components/_private/cmake-stage1.bst"


def _rich_native(**overrides):
    report = _real_native()
    report["binary_cost"] = {
        CMAKE: {
            "available": True,
            "measured_cpu_us": 5_351_136_759,
            "by_cpu": [
                {"binary": "cc1plus", "count": 885, "cpu_us": 4_352_550_957,
                 "wall_s": 5525.6, "cpu_share": 0.8134},
                {"binary": "as", "count": 1918, "cpu_us": 397_515_477,
                 "wall_s": 5929.8, "cpu_share": 0.0743},
            ],
            "by_count": [],
            "single_process_costs": [
                {"binary": "dwz", "cpu_us": 137_043_490, "wall_s": 138.55},
            ],
        },
    }
    report["peak_memory"] = {
        "available": True,
        "per_element": {CMAKE: {"peak_rss_kb": 1_947_536, "measured": 10057}},
    }
    report["declared_vs_used"] = {
        "unused_candidates": [
            {"element": CMAKE, "dependency": "public-stacks/runtime-minimal.bst"},
        ],
    }
    report.update(overrides)
    return report


def _steps(result, element):
    """UX-75: recommendations carry an id and a severity now, so the
    text a human reads and the class a machine acts on are the same
    record. These tests are about the prose."""
    entry = {e["element"]: e for e in result["actionable"]}[element]
    return [step["text"] for step in entry["recommendations"]]


def test_the_dominant_binary_reaches_the_join():
    """`UX-69` measured that 81.3% of this element's CPU is `cc1plus`
    three rounds ago. The command the workflow ends on never said so."""
    steps = _steps(correlate(_real_analysis(), _rich_native()), CMAKE)

    assert any("cc1plus" in step and "81%" in step for step in steps)


def test_a_single_process_serialization_point_reaches_the_join():
    steps = _steps(correlate(_real_analysis(), _rich_native()), CMAKE)

    assert any("dwz" in step and "SINGLE process" in step for step in steps)


def test_peak_memory_reaches_the_join():
    steps = _steps(correlate(_real_analysis(), _rich_native()), CMAKE)

    assert any("1902 MB" in step for step in steps)


def test_measured_findings_outrank_the_hedged_one():
    """`UX-72`: a measured 81%-of-CPU binary and an explicitly hedged
    dependency candidate must not print as two equal bullets."""
    steps = _steps(correlate(_real_analysis(), _rich_native()), CMAKE)
    hedged = next(i for i, s in enumerate(steps) if "evidence, not a verdict" in s)

    assert hedged == len(steps) - 1
    assert hedged > 0


def test_a_redundancy_worth_less_than_a_percent_of_the_element_is_not_a_step():
    """`cmake-stage1` paying 2.2s for a shared `rm -rf` against 1569.8s
    of realizable saving is true, and is noise in that row."""
    small = _rich_native(redundant_operations=[{
        "signature": "rm -rf -- /buildstream-build", "elements": [CMAKE, "components/x.bst"],
        "occurrence_count": 8, "total_duration_s": 8.0,
        "max_element_duration_s": 2.2, "worst_element": CMAKE,
    }])
    steps = _steps(correlate(_real_analysis(), small), CMAKE)
    assert not any("also run" in step for step in steps)

    big = _rich_native(redundant_operations=[{
        "signature": "/usr/bin/m4 -P", "elements": [CMAKE, "components/x.bst"],
        "occurrence_count": 30, "total_duration_s": 40.0,
        "max_element_duration_s": 20.4, "worst_element": CMAKE,
    }])
    steps = _steps(correlate(_real_analysis(), big), CMAKE)
    assert any("also run" in step and "20.4s" in step for step in steps)


def test_aggregating_dependencies_are_counted_and_stated():
    """`UX-68` set these aside three rounds ago and nothing has read them
    since - no renderer, no consumer."""
    report = _rich_native()
    report["declared_vs_used"] = {
        "unused_candidates": [],
        "aggregating_dependencies": [
            {"element": CMAKE, "dependency": "public-stacks/runtime-minimal.bst"},
            {"element": "components/openssl.bst", "dependency": "public-stacks/runtime-minimal.bst"},
        ],
    }
    result = correlate(_real_analysis(), report)

    assert result["coverage"]["aggregating_dependency_pairs"] == 2
    assert "set aside as aggregating" in format_correlation(result)


def test_correlate_recommendations_carry_ids_and_severities():
    """`UX-75`: the join's rows are conclusions too. A consumer acts on
    `id`, not on a substring of the prose, and the severity says out loud
    what `UX-68`'s own note says in words - the declared-vs-used row is
    evidence, not a verdict."""
    result = correlate(_real_analysis(), _rich_native())
    entry = {e["element"]: e for e in result["actionable"]}[CMAKE]
    by_id = {step["id"]: step for step in entry["recommendations"]}

    assert by_id["cpu-concentration"]["severity"] == "high"
    assert by_id["serialization-point"]["severity"] == "high"
    assert by_id["peak-memory"]["severity"] == "medium"
    assert by_id["declared-not-used"]["severity"] == "info"
    # And the order still puts the hedged one last.
    assert entry["recommendations"][-1]["id"] == "declared-not-used"


# --- UX-66 acceptance test 3, which was never met ----------------------


def test_a_name_that_is_not_a_declared_element_never_enters_the_join():
    """`UX-66` required that "a bucket name that is not a declared
    element uid never enters a join, even if it ends in `.bst`", because
    round 7 measured `flit_core` and `expat` arriving as bwrap `--dir`
    segments where neither is an element.

    Plane 2's own check is syntactic - a name ends in `.bst` - which is
    all it can do alone. Before this, a bucket called `flit_core.bst`
    passed that test, produced a "what to do next" row, and pushed the
    build's only real element into "not traced".
    """
    analysis = {
        "total_duration_us": 100_000_000,
        "signals": {
            "critical_path": ["real.bst"],
            "critical_path_detail": [{
                "element_uid": "real.bst", "duration_us": 50_000_000,
                "share_of_path": 1.0, "is_structural_kind": False,
                "realizable_saving_us": 50_000_000,
            }],
            "slack": {"real.bst": 0},
            "blast_radius": {},
        },
        "structural": {"sensitivity": {"top_opportunities": [],
                                       "critical_path_us": 50_000_000}},
    }
    native = _native(unused=[{"element": "flit_core.bst", "dependency": "d.bst"}])
    native["by_element"]["flit_core.bst"] = 5

    result = correlate(analysis, native)

    assert [e["element"] for e in result["actionable"]] == []
    assert result["coverage"]["undeclared_plane2_elements"] == ["flit_core.bst"]
    assert "are not declared elements" in format_correlation(result)


def test_an_off_path_element_is_still_declared():
    """The over-refusal this must not become: a real element that is off
    the critical path and has no blast radius still belongs to the graph.
    `slack` carries every element, which is why the check reads it."""
    analysis = {
        "total_duration_us": 100_000_000,
        "signals": {
            "critical_path": ["a.bst"],
            "critical_path_detail": [],
            "slack": {"a.bst": 0, "offpath.bst": 5_000_000},
            "blast_radius": {},
        },
        "structural": {"sensitivity": {"top_opportunities": [],
                                       "critical_path_us": 50_000_000}},
    }
    native = _native(unused=[{"element": "offpath.bst", "dependency": "d.bst"}])
    native["by_element"]["offpath.bst"] = 5

    result = correlate(analysis, native)

    assert [e["element"] for e in result["actionable"]] == ["offpath.bst"]
    assert result["coverage"]["undeclared_plane2_elements"] == []


def test_an_analysis_with_no_per_element_signals_degrades_rather_than_refusing():
    """No declared set to check against is not the same as "nothing is
    declared" - refusing every row there would be a worse failure than
    the one this check fixes."""
    result = correlate(
        _analysis(critical_path=[], opportunities=[]),
        _native(unused=[{"element": "x.bst", "dependency": "d.bst"}]),
    )

    assert [e["element"] for e in result["actionable"]] == ["x.bst"]



class TestTheReportArgumentIsOptionalWhenTheCaptureKeptThemTogether:
    """UX-134: `bga capture run --run-dir` and `bga snapshot` write the
    run directory and its Plane 2 report side by side, so restating the
    pairing is clerical - and getting it wrong (yesterday's report, this
    morning's run) is the mistake this whole direction exists to remove.

    Inferred from the filesystem, not from whether an alias was used, so
    an explicit path to a snapshot behaves the same as `@last`.
    """

    def _snapshot(self, tmp_path, with_plane2=True):
        snapshot = tmp_path / "20260101T000000Z"
        snapshot.mkdir()
        shutil.copytree(GOLDEN_RUN, snapshot / "run")
        if with_plane2:
            (snapshot / "plane2.json").write_text(json.dumps({
                "by_element": {},
                "per_element_parallelism": [],
                "cpu_time": {"per_element": {}},
                "declared_vs_used": {"unused_candidates": []},
            }))
        return snapshot

    def _correlate(self, *argv):
        return subprocess.run(
            [sys.executable, "-m", "bga.cli", "correlate", *argv],
            capture_output=True, text=True, cwd=REPO, timeout=300)

    def test_omitting_it_joins_the_report_that_came_from_the_same_build(
            self, tmp_path):
        snapshot = self._snapshot(tmp_path)

        inferred = self._correlate(str(snapshot / "run"))
        explicit = self._correlate(str(snapshot / "run"),
                                   str(snapshot / "plane2.json"))

        assert inferred.returncode == 0, inferred.stderr
        assert inferred.stdout == explicit.stdout, (
            "inferring the sibling produced a different report than naming it")
        assert str(snapshot / "plane2.json") in inferred.stderr, (
            "the inferred path is not stated, so the reader cannot tell which "
            "report was joined")

    def test_omitting_it_with_nothing_beside_the_run_says_what_to_pass(
            self, tmp_path):
        """Not a traceback and not a silent single-plane report: the
        argument is still required wherever there is nothing to infer."""
        snapshot = self._snapshot(tmp_path, with_plane2=False)

        result = self._correlate(str(snapshot / "run"))

        assert result.returncode == 2, result.stdout
        assert "no Plane 2 report given, and none beside" in result.stderr

    def test_a_run_directory_not_from_a_capture_is_not_guessed_about(self):
        result = self._correlate(GOLDEN_RUN)

        assert result.returncode == 2
        assert "none beside" in result.stderr
