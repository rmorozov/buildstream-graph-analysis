"""UX-261: the first screen leads with what the build waits for.

`UX-258` fixed the ranking's *content*. This is what the first screen
should lead with once it is fixed, and the answer is not "the same
list, filtered".

Before, on the 1,202-element run, the reader met a list of eleven
near-identical blast counts. What they need, in order:

1. **What the build is waiting for** — the longest element on the
   critical path. Already computed, already published, and sitting
   below a ranking of reach.
2. **What shape this graph has** — the density, in a sentence rather
   than a chart (`UX-196`).
3. **What is unusual for its kind** — which `UX-258` and `UX-259`
   already supply to the ranking itself.

Measured after, on a 44-element synthetic run:

```text
next_steps[0]  shorten-what-the-build-waits-for
               "mod039.bst is the longest thing on the critical path at
                6.0s, 100% of it - the build cannot finish sooner than
                this chain."
next_steps[1]  blast-the-top-element
```
"""
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
GOLDEN = REPO / "tests/fixtures/golden/mixed_task_kinds"


def _shape(distribution):
    from bga.findings import _graph_shape

    class Result:
        signals = {"blast_radius_distribution": distribution}

    return _graph_shape(Result())


class TestTheCriticalPathComesFirst:
    def test_the_first_step_is_the_chain_not_the_ranking(self):
        from bga.findings import compute_next_steps

        class Result:
            run_instance = {"run_dir": "/runs/one"}
            signals = {"critical_path_detail": [
                {"element_uid": "slow.bst", "duration_us": 60_000_000,
                 "share_of_path": 0.6},
                {"element_uid": "quick.bst", "duration_us": 1_000_000,
                 "share_of_path": 0.01}]}

        steps = compute_next_steps(
            Result(), headline={"top_actions": [
                {"element_uid": "wide.bst", "saving_us": 1_000_000}]})
        assert steps[0]["id"] == "shorten-what-the-build-waits-for", steps
        assert "slow.bst" in steps[0]["reason"]
        assert "60.0s" in steps[0]["reason"]
        assert steps[1]["id"] == "blast-the-top-element", steps

    def test_it_names_the_longest_not_the_first_on_the_path(self):
        """The path is in order; the answer is the biggest entry in it,
        which is rarely the first."""
        from bga.findings import _longest_on_the_path

        class Result:
            signals = {"critical_path_detail": [
                {"element_uid": "a.bst", "duration_us": 10},
                {"element_uid": "b.bst", "duration_us": 900},
                {"element_uid": "c.bst", "duration_us": 20}]}

        assert _longest_on_the_path(Result())["element_uid"] == "b.bst"

    def test_a_run_with_no_path_says_nothing_rather_than_guessing(self):
        from bga.findings import _longest_on_the_path

        class Result:
            signals = {}

        assert _longest_on_the_path(Result()) is None

    def test_it_follows_from_the_published_field(self):
        """`UX-229`'s rule: advice names the signal it came from."""
        from bga.findings import compute_next_steps

        class Result:
            run_instance = {"run_dir": "/runs/one"}
            signals = {"critical_path_detail": [
                {"element_uid": "slow.bst", "duration_us": 60_000_000}]}

        steps = compute_next_steps(Result(), headline={})
        assert steps[0]["follows_from"] == "critical_path_detail"


class TestTheShapeIsOneLine:
    def test_a_spread_graph_says_so(self):
        line = _shape({"n": 1202, "max": 1201, "is_flat": False,
                       "deciles": {"p50": 30, "p90": 465}})
        assert "1202 elements reach 30 others or fewer" in line, line
        assert "spread across many elements" in line, line

    def test_a_star_graph_says_the_opposite(self):
        """The case the first draft got backwards: in a star both the
        median and the top decile are zero, and comparing them called
        the most concentrated shape there is "spread"."""
        line = _shape({"n": 44, "max": 42, "is_flat": False,
                       "deciles": {"p50": 0, "p90": 0}})
        assert "reach nothing" in line, line
        assert "concentrated in a few elements" in line, line

    def test_a_flat_graph_gets_no_sentence(self):
        assert _shape({"n": 20, "max": 5, "is_flat": True,
                       "deciles": {"p50": 5, "p90": 5}}) is None

    def test_a_run_with_no_distribution_gets_no_sentence(self):
        from bga.findings import _graph_shape

        class Result:
            signals = {}

        assert _graph_shape(Result()) is None

    def test_it_is_a_sentence_and_not_a_chart(self):
        """`UX-196`: a decile histogram earns its place only if a
        sentence cannot carry the shape. This is the check that nobody
        quietly grew one."""
        line = _shape({"n": 1202, "max": 1201, "is_flat": False,
                       "deciles": {"p50": 30, "p90": 465}})
        assert line.count(".") <= 3 and "\n" not in line, line


class TestTheHeadlineCarriesIt:
    def test_the_shape_reaches_the_headline(self):
        from tools.bga_view import payloads

        headline = payloads(str(GOLDEN)).get("report.json", {}).get(
            "headline", {})
        # The 4-element golden run publishes no distribution, so no
        # sentence - absence rather than an invented one.
        assert "graph_shape" not in headline


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
