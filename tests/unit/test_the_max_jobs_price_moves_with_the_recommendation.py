"""UX-739: `compute_max_jobs_advice`'s rows, priced by replay.

Synthetic tasks, built with the same `NormalizedTask`/`TaskKey` helpers
`test_the_max_jobs_advisor_does_not_overcommit.py` uses - no fixture,
because the claim is about the pricing arithmetic, not a real capture
(the real capture is `UX-739`'s own Outcome).
"""
from bga.correlate import (
    _PRICE_DISPATCH_ASSUMPTION,
    _PRICE_FLOOR_ASSUMPTION,
    compute_capacity_recommendation,
    price_max_jobs_advice,
)
from bga.findings import _capacity_recommendation_finding
from bga.ingest.models import NormalizedTask, RunContext, TaskKey, TaskKind

US = 1_000_000


def _task(element, start_s, finish_s):
    return NormalizedTask(
        task_key=TaskKey(element_uid=element, task_kind=TaskKind.BUILD,
                          phase="build"),
        ready_us=0, start_us=int(start_s * US), finish_us=int(finish_s * US),
        dependencies=[], resources=[], primary_resource=None,
    )


def _row(element, current, recommended, refusal=None):
    return {"element": element, "current_max_jobs": current,
            "recommended_max_jobs": recommended,
            "max_jobs_change": (recommended - current
                                 if recommended is not None else None),
            "refusal": refusal}


def _advice(*rows):
    return {"min_samples_in_span": 2, "host_cores": 4, "elements": list(rows)}


class TestTheMutationTheAcceptanceTestNames:
    """(1): change the recommendation 2 -> 1 and `projected_us` moves."""

    def test_a_tighter_recommendation_moves_the_projected_makespan(self):
        tasks = [_task("a.bst", 0, 2)]
        run_context = RunContext(resource_capacities={"PROCESS": 4})
        binary_cost = {"a.bst": {"available": True, "measured_cpu_us": 12 * US}}

        priced_at_2 = price_max_jobs_advice(
            _advice(_row("a.bst", 4, 2)), tasks, run_context, binary_cost)
        priced_at_1 = price_max_jobs_advice(
            _advice(_row("a.bst", 4, 1)), tasks, run_context, binary_cost)

        row_2 = priced_at_2["elements"][0]["priced"]
        row_1 = priced_at_1["elements"][0]["priced"]
        # measured_cpu_us/2 = 6s, /1 = 12s - both floors, both above the
        # 2s observed duration, and the tighter one is the bigger floor.
        assert row_2["duration_floor_us"] == 6 * US
        assert row_1["duration_floor_us"] == 12 * US
        assert row_1["projected_us"] > row_2["projected_us"], (
            "recommending 1 rather than 2 must cost at least as much, and "
            "here strictly more - a price that does not track its own "
            "recommendation is not reading it")


class TestARaiseIsARefusal:
    """(2): a RAISED recommendation has no evidence of how the element
    scales up, and is refused rather than priced."""

    def test_a_raise_is_unpriced_and_named(self):
        tasks = [_task("a.bst", 0, 2)]
        run_context = RunContext(resource_capacities={"PROCESS": 4})
        advice = _advice(_row("a.bst", 1, 4))
        priced = price_max_jobs_advice(advice, tasks, run_context, {})
        row = priced["elements"][0]
        assert "priced" not in row
        assert row["price_refusal"] and "1 job" in row["price_refusal"]

    def test_an_unchanged_recommendation_costs_nothing(self):
        tasks = [_task("a.bst", 0, 2)]
        run_context = RunContext(resource_capacities={"PROCESS": 4})
        advice = _advice(_row("a.bst", 2, 2))
        priced = price_max_jobs_advice(advice, tasks, run_context, {})
        row = priced["elements"][0]
        assert row["priced"]["cost_us"] == 0
        assert "price_refusal" not in row


class TestTheFloorReadsPlaneTwo:
    """(3): `measured_cpu_us / recommended` below the observed duration
    - the floor is the observed duration itself, and it costs nothing."""

    def test_plenty_of_slots_for_the_measured_cpu_costs_nothing(self):
        tasks = [_task("a.bst", 0, 10)]
        run_context = RunContext(resource_capacities={"PROCESS": 4})
        # measured_cpu_us/recommended = 8s/2 = 4s, under the 10s observed.
        binary_cost = {"a.bst": {"available": True, "measured_cpu_us": 8 * US}}
        advice = _advice(_row("a.bst", 4, 2))
        priced = price_max_jobs_advice(advice, tasks, run_context, binary_cost)
        row = priced["elements"][0]["priced"]
        assert row["duration_floor_us"] == row["duration_before_us"] == 10 * US
        assert row["cost_us"] == 0

    def test_no_binary_cost_is_a_named_refusal(self):
        tasks = [_task("a.bst", 0, 10)]
        run_context = RunContext(resource_capacities={"PROCESS": 4})
        advice = _advice(_row("a.bst", 4, 2))
        priced = price_max_jobs_advice(advice, tasks, run_context, {})
        row = priced["elements"][0]
        assert "priced" not in row
        assert row["price_refusal"] and "binary_cost" in row["price_refusal"]

    def test_an_element_with_no_build_task_is_a_named_refusal(self):
        # The verifier's mutation (round 112): dropping the `task is None`
        # clause raised AttributeError here instead of refusing by name.
        tasks = [_task("a.bst", 0, 2)]
        run_context = RunContext(resource_capacities={"PROCESS": 4})
        binary_cost = {"b.bst": {"available": True, "measured_cpu_us": 8 * US}}

        priced = price_max_jobs_advice(
            _advice(_row("b.bst", 4, 1)), tasks, run_context, binary_cost)

        row = priced["elements"][0]
        assert "priced" not in row
        assert "no BUILD task for b.bst" in row["price_refusal"]

    def test_a_refusal_already_on_the_row_stays_unpriced_with_no_extra_text(self):
        tasks = [_task("a.bst", 0, 10)]
        run_context = RunContext(resource_capacities={"PROCESS": 4})
        binary_cost = {"a.bst": {"available": True, "measured_cpu_us": 8 * US}}
        advice = _advice(_row("a.bst", 4, 2, refusal="only 1 sample"))
        priced = price_max_jobs_advice(advice, tasks, run_context, binary_cost)
        row = priced["elements"][0]
        assert "priced" not in row
        assert "price_refusal" not in row


class TestJointIsARecomputeNotASum:
    """(4): two elements on different chains, sharing a capacity of 2
    against a third, unpriced element that only becomes the constraint
    once *both* are stretched - the shape where a sum cannot be right."""

    def _tasks(self):
        return [_task("a.bst", 0, 2), _task("b.bst", 0, 2), _task("c.bst", 0, 3)]

    def test_the_joint_cost_is_not_the_sum_of_the_individual_costs(self):
        run_context = RunContext(resource_capacities={"PROCESS": 2})
        binary_cost = {
            "a.bst": {"available": True, "measured_cpu_us": 6 * US},
            "b.bst": {"available": True, "measured_cpu_us": 6 * US},
        }
        tasks = self._tasks()

        priced_a = price_max_jobs_advice(
            _advice(_row("a.bst", 4, 1), _row("b.bst", 2, 2)),
            tasks, run_context, binary_cost)
        priced_b = price_max_jobs_advice(
            _advice(_row("a.bst", 2, 2), _row("b.bst", 4, 1)),
            tasks, run_context, binary_cost)
        priced_both = price_max_jobs_advice(
            _advice(_row("a.bst", 4, 1), _row("b.bst", 4, 1)),
            tasks, run_context, binary_cost)

        cost_a_alone = next(r for r in priced_a["elements"]
                             if r["element"] == "a.bst")["priced"]["cost_us"]
        cost_b_alone = next(r for r in priced_b["elements"]
                             if r["element"] == "b.bst")["priced"]["cost_us"]
        joint_cost = priced_both["priced_jointly"]["cost_us"]

        assert joint_cost != cost_a_alone + cost_b_alone, (
            f"joint {joint_cost} equalled the sum {cost_a_alone} + "
            f"{cost_b_alone} - on this shape (a third element only "
            f"delayed once both chains stretch) it cannot, so this "
            f"guard read a sum instead of the recompute")


def _recommendation(max_jobs_advice):
    """A minimal `compute_capacity_recommendation` result, carrying
    whatever `max_jobs_advice` shape a test wants to render."""
    envelope = {
        'host_memory_bytes': 16000, 'elements_measured': 11,
        'largest_element_peak_bytes': 1000,
        'projections': [
            {'builders': n, 'envelope_bytes': 1000 * n,
             'share_of_host': 1000 * n / 16000, 'fits': n <= 11}
            for n in range(1, 12)],
    }
    recommendation = compute_capacity_recommendation(
        {'cores_busy': 2.0, 'host_cpu_count': 4, 'saturated': False,
         'pinned_elements': []},
        envelope, knee=5, builders=4, native_max_jobs=4)
    recommendation['max_jobs_advice'] = max_jobs_advice
    return recommendation


def _detail(max_jobs_advice):
    result = type('_R', (), {
        'capacity_recommendation': _recommendation(max_jobs_advice)})()
    return "\n".join(_capacity_recommendation_finding(result)[0]['detail'])


class TestThePriceSTwoAssumptionsRenderWithAPricedRow:
    """UX-809: `pricing_assumptions` is on the payload and in the guide
    already - these cover whether it also reaches the text a reader
    sees, and only when there is a figure for it to qualify."""

    def test_a_priced_row_carries_both_sentences_verbatim(self):
        tasks = [_task("a.bst", 0, 2)]
        run_context = RunContext(resource_capacities={"PROCESS": 4})
        binary_cost = {"a.bst": {"available": True, "measured_cpu_us": 12 * US}}
        advice = price_max_jobs_advice(
            _advice(_row("a.bst", 4, 2)), tasks, run_context, binary_cost)

        detail = _detail(advice)

        assert _PRICE_DISPATCH_ASSUMPTION in detail
        assert _PRICE_FLOOR_ASSUMPTION in detail

    def test_refusals_only_carry_neither_sentence(self):
        tasks = [_task("a.bst", 0, 2)]
        run_context = RunContext(resource_capacities={"PROCESS": 4})
        advice = price_max_jobs_advice(
            _advice(_row("a.bst", 1, 4)), tasks, run_context, {})
        assert "priced" not in advice["elements"][0]  # a raise, refused

        detail = _detail(advice)

        assert _PRICE_DISPATCH_ASSUMPTION not in detail
        assert _PRICE_FLOOR_ASSUMPTION not in detail

    def test_no_advice_carries_neither_sentence(self):
        detail = _detail(None)

        assert _PRICE_DISPATCH_ASSUMPTION not in detail
        assert _PRICE_FLOOR_ASSUMPTION not in detail
