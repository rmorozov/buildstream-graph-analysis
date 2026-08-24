"""UX-260: which quantities carry a scale, and which deliberately do not.

`UX-259` gave blast radius a distribution because `753 downstream` is
p99.9 in a 1,202-element graph and unremarkable in one of forty
thousand. The brainstorm Direction 11 asked for was *where else*, and
the answer is not "everywhere":

```text
element duration       yes  spans orders of magnitude; "is 40s slow *here*?"
sandbox tax            yes  the question is literally "is this tax unusual"
process count          yes  heavy tails - one element with 40,000 *is* the finding
share of critical path  no  already a percentage of a known whole
confidence/coverage     no  run-level singletons with no population
wall-clock / horizon    no  one per run; the store aggregate holds their spread
```

The split lives in `bga/analyzer.py` as two named maps, and this file
holds it there. A `no` with no argument invites the next person to add
it; a `yes` that was never implemented is a decision nobody made.

Measured on a 44-element synthetic run whose durations span three
orders of magnitude:

```text
p10 2ms   p50 44ms   p80 1.01s   p90 2.47s   p95 3.85s   p99 6.02s
n 44      min 1ms    max 6.02s   is_flat false
```

and on the 4-element golden run: **no distribution at all**, which is
`UX-234`'s refusal rather than deciles over four numbers.
"""
import math
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"


@pytest.fixture(scope="module")
def big_run(tmp_path_factory):
    """A run with enough elements, and a real spread, to have a shape."""
    import json
    import shutil

    run = tmp_path_factory.mktemp("scale") / "run"
    shutil.copytree(GOLDEN, run)
    (run / "expected_output.json").unlink(missing_ok=True)
    graph = json.loads((run / "graph.json").read_text())
    trace = json.loads((run / "trace.json").read_text())
    for i in range(40):
        uid = f"mod{i:03d}.bst"
        graph["elements"].append(
            {"uid": uid, "cache_key": f"k-{i}", "requested_target": False})
        graph["dependencies"].append(
            {"predecessor": "base.bst", "successor": uid})
        trace["spans"].append(
            {"task_key": f"{uid}|BUILD|BUILD|0", "ts_us": 6000,
             "dur_us": int(1000 * (1.25 ** i)), "resources": ["PROCESS"],
             "primary_resource": "PROCESS"})
    (run / "graph.json").write_text(json.dumps(graph))
    (run / "trace.json").write_text(json.dumps(trace))
    return run


def _signals(run):
    from tools.bga_view import payloads

    return payloads(str(run)).get("report.json", {}).get("signals", {})


class TestTheSplitIsADecision:
    def test_every_distributed_quantity_says_why(self):
        from bga.analyzer import DISTRIBUTED_QUANTITIES

        for name, why in DISTRIBUTED_QUANTITIES.items():
            assert len(why) > 40, f"{name}: the reason is a label, not a reason"

    def test_every_refusal_says_why(self):
        """The half that rots. A quantity with no distribution and no
        recorded argument reads as an oversight, and the next round
        adds one."""
        from bga.analyzer import UNDISTRIBUTED_QUANTITIES

        for name, why in UNDISTRIBUTED_QUANTITIES.items():
            assert len(why) > 40, f"{name}: no argument against it"

    def test_the_two_sets_do_not_overlap(self):
        from bga.analyzer import (DISTRIBUTED_QUANTITIES,
                                  UNDISTRIBUTED_QUANTITIES)

        both = set(DISTRIBUTED_QUANTITIES) & set(UNDISTRIBUTED_QUANTITIES)
        assert both == set(), f"{both} is on both lists"

    def test_the_yes_list_is_the_one_that_shipped(self):
        """The list is a claim about the code; this is the check that
        it is not just prose. Each name maps to a published key."""
        from bga.analyzer import DISTRIBUTED_QUANTITIES

        assert set(DISTRIBUTED_QUANTITIES) == {
            "blast_radius", "element_duration", "sandbox_tax", "process_count"}


class TestDurationCarriesItsScale:
    def test_it_publishes_a_shape(self, big_run):
        shape = _signals(big_run).get("element_duration_distribution")
        assert shape, "a 44-element run published no duration distribution"
        assert shape["n"] == 44 and not shape["is_flat"], shape

    def test_the_deciles_agree_with_an_independent_computation(self, big_run):
        """Nearest-rank, computed here rather than trusted from there."""
        signals = _signals(big_run)
        shape = signals["element_duration_distribution"]
        values = sorted(int(v) for v in signals["element_durations"].values())
        for percent in (10, 20, 30, 40, 50, 60, 70, 80, 90):
            expected = values[math.ceil(percent / 100 * len(values)) - 1]
            assert shape["deciles"][f"p{percent}"] == expected, percent

    def test_a_small_run_refuses_rather_than_computing(self):
        """Deciles over four elements are four numbers wearing ten
        labels. Absent, not null - `UX-249`'s rule."""
        assert "element_duration_distribution" not in _signals(GOLDEN)


class TestTheCrossPlaneQuantities:
    def test_both_are_absent_when_their_plane_is(self):
        from bga.correlate import _scale_of

        assert _scale_of(None, {}) == {}

    def test_the_tax_shape_covers_every_payer_not_the_top_slice(self):
        """`top_payers` is every payer sorted, despite the name. A
        distribution over a truncated head would describe the head and
        be read as the population."""
        from bga.correlate import _scale_of

        payers = {"sandbox_tax": {
            "top_payers": [{"toll_us": i * 1000} for i in range(1, 21)]}}
        shape = _scale_of(payers, {})["sandbox_tax_distribution"]
        assert shape["n"] == 20, shape
        assert shape["min"] == 1000 and shape["max"] == 20000

    def test_the_process_shape_reads_plane_2(self):
        from bga.correlate import _scale_of

        native = {"per_element_parallelism":
                  [{"work_process_count": i} for i in range(1, 31)]}
        shape = _scale_of({}, native)["process_count_distribution"]
        assert shape["n"] == 30 and shape["deciles"]["p50"] == 15, shape

    def test_too_few_payers_refuses(self):
        from bga.correlate import _scale_of

        assert _scale_of(
            {"sandbox_tax": {"top_payers": [{"toll_us": 1}]}}, {}) == {}


class TestThereIsOneStatistic:
    def test_every_distribution_comes_from_one_function(self):
        """Two percentile implementations in one codebase is the drift
        this repository fixes more often than anything else."""
        source = (REPO / "bga/analyzer.py").read_text(encoding="utf-8")
        block = source.split("def distribution", 1)[1].split("\ndef ", 1)[0]
        assert "from .store_aggregate import percentile" in block

        correlate = (REPO / "bga/correlate.py").read_text(encoding="utf-8")
        assert "from .analyzer import distribution" in correlate, (
            "correlate computes its own distribution instead of reusing the "
            "one every other quantity uses (UX-260)")

    def test_the_refused_quantities_publish_no_shape(self, big_run):
        """The other direction: a `no` that quietly became a `yes`."""
        signals = _signals(big_run)
        for refused in ("critical_path_share", "confidence", "coverage",
                        "efficiency_score", "wall_clock"):
            assert f"{refused}_distribution" not in signals, (
                f"{refused} grew a distribution that UNDISTRIBUTED_QUANTITIES "
                f"argues against - change the argument or drop the field")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
