"""UX-258/UX-259: the blast ranking excludes structure and carries scale.

Reported from a real project — the ranking puts
`linux_base_image.bst`-shaped elements first — and reproduced on a
1,202-element synthetic run:

```text
next_steps[0]  "toolchain.bst is the first thing to fix"
toolchain.bst  downstream 1201  kind "import"  is_structural_kind TRUE
```

The advice was true and useless: a base image has a thousand dependents
**on purpose**. And the tool already knew — `is_structural_kind` is
published on the very entry the ranking put first, and
`_criticality_findings` in the same file has excluded structural kinds
since round 12 citing `UX-76`. The blast ranking simply never got the
rule.

The second half is scale. `753 downstream` is p99.9 in this run and
unremarkable in a graph of forty thousand, and it is the *number* that
travels into a ticket while the rank stays behind. Measured
distribution:

```text
p10 0   p50 30   p80 293   p90 465   p95 575   p99 682   max 1201
```

Positions 2-12 were 753..697 — an 8% spread across eleven elements,
presented as an ordered list of what to do first.
"""
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]


def _signals(blast, distribution=None, top=None):
    return {
        "blast_radius": blast,
        "top_blast_radius": top if top is not None else list(blast),
        "blast_radius_distribution": distribution,
    }


def _entry(count, kind="cmake", structural=False):
    return {"downstream_count": count, "element_kind": kind,
            "is_structural_kind": structural, "weighted_duration_us": count * 1000}


def _rank(signals):
    from bga import findings

    class R:
        pass

    result = R()
    result.signals = signals
    return findings._ranking_findings(result, chain_bound=False)


class TestStructureIsReportedNotRanked:
    def test_a_structural_root_does_not_lead_the_ranking(self):
        """The reported defect, in one assertion."""
        found = _rank(_signals({
            "toolchain.bst": _entry(1201, "import", structural=True),
            "components/a.bst": _entry(753),
            "components/b.bst": _entry(400),
        }))
        ranking = next(f for f in found if f["id"] == "blast-radius-ranking")
        assert "toolchain.bst" not in ranking["elements"], (
            "a structural element is still ranked as something to fix")
        assert ranking["elements"][0] == "components/a.bst"

    def test_it_is_still_reported_with_its_number(self):
        """`UX-203` was filed over unreachable views; answering this by
        hiding the element would trade one defect for an older one."""
        found = _rank(_signals({
            "toolchain.bst": _entry(1201, "import", structural=True),
            "components/a.bst": _entry(753),
        }))
        shape = next(f for f in found if f["id"] == "blast-radius-structural")
        assert "toolchain.bst" in shape["elements"]
        assert "1201" in shape["title"]
        assert "not a task" in shape["title"]
        # `UX-344`: the finding names the element and the title carries
        # the number; the per-element records are published once, in
        # `elements.blast_radius`, rather than sliced into the evidence
        # of the finding that names them.
        assert "blast_radius" not in (shape.get("evidence") or {})

    def test_a_graph_that_is_all_structural_still_says_something(self):
        """The degenerate case. An empty ranking and no statement would
        read as "nothing to report", which is a different claim."""
        found = _rank(_signals({
            "toolchain.bst": _entry(1201, "import", structural=True),
            "base.bst": _entry(900, "stack", structural=True),
        }))
        assert [f["id"] for f in found] == ["blast-radius-structural"]
        assert found[0]["elements"]

    def test_the_rule_is_the_one_criticality_already_applies(self):
        """`UX-76`'s rule, reaching the ranking that skipped it. If
        `_criticality_findings` ever stops excluding structural kinds,
        this file's premise is gone and it should fail loudly."""
        source = (REPO / "bga/findings.py").read_text(encoding="utf-8")
        criticality = source.split("def _criticality_findings", 1)[1]
        criticality = criticality.split("\ndef ", 1)[0]
        assert "is_structural_kind" in criticality, (
            "criticality no longer excludes structural kinds, so UX-258 is "
            "no longer applying an existing rule - re-argue it")


class TestTheNumberCarriesItsScale:
    DISTRIBUTION = {
        "n": 1202, "min": 0, "max": 1201, "is_flat": False,
        "deciles": {"p10": 0, "p20": 1, "p30": 4, "p40": 10, "p50": 30,
                    "p60": 66, "p70": 157, "p80": 293, "p90": 465},
        "p95": 575, "p99": 682,
    }

    def test_a_ranked_count_says_where_it_sits(self):
        found = _rank(_signals(
            {"components/a.bst": _entry(753), "components/b.bst": _entry(300)},
            self.DISTRIBUTION))
        text = "\n".join(found[0]["detail"])
        assert "753 downstream elements, at or above p99" in text, text

    def test_a_mid_pack_count_is_not_called_top(self):
        found = _rank(_signals(
            {"components/a.bst": _entry(60), "components/b.bst": _entry(20)},
            self.DISTRIBUTION))
        text = "\n".join(found[0]["detail"])
        assert "p50" in text and "p99" not in text, text

    def test_a_flat_graph_gets_no_percentile_theatre(self):
        """Ten identical buckets are not a shape, and saying "at or
        above p90" when every element is equal is noise."""
        flat = dict(self.DISTRIBUTION, is_flat=True)
        found = _rank(_signals(
            {"a.bst": _entry(5), "b.bst": _entry(5)}, flat))
        assert "at or above" not in "\n".join(found[0]["detail"])

    def test_ties_are_named_as_ties(self):
        found = _rank(_signals(
            {"a.bst": _entry(753), "b.bst": _entry(753), "c.bst": _entry(739)},
            self.DISTRIBUTION))
        text = "\n".join(found[0]["detail"])
        assert "not a difference worth acting on" in text, text

    def test_a_real_spread_is_not_called_a_tie(self):
        found = _rank(_signals(
            {"a.bst": _entry(900), "b.bst": _entry(300), "c.bst": _entry(50)},
            self.DISTRIBUTION))
        assert "not a difference" not in "\n".join(found[0]["detail"])

    def test_the_shape_is_one_line_not_a_chart(self):
        """`UX-196`: the numbers make themselves self-evident, and a
        decile histogram earns its place only if a sentence cannot."""
        found = _rank(_signals(
            {"a.bst": _entry(753), "b.bst": _entry(300)}, self.DISTRIBUTION))
        shape = [d for d in found[0]["detail"] if d.strip().startswith("Shape:")]
        assert len(shape) == 1, found[0]["detail"]
        assert "30 or fewer" in shape[0] and "465 or more" in shape[0]


class TestTheDistributionIsTheSameStatisticAsTheStore:
    def test_it_reuses_the_store_percentile(self):
        """Two percentile functions in one codebase is the drift this
        repository fixes more often than anything else."""
        source = (REPO / "bga/analyzer.py").read_text(encoding="utf-8")
        # `distribution`, not `blast_radius_distribution`: `UX-260`
        # generalised the statistic to four quantities and left the
        # blast-specific name as a wrapper. The property this guards -
        # one percentile function - is unchanged; where it lives moved.
        block = source.split("def distribution", 1)[1].split("\ndef ", 1)[0]
        assert "from .store_aggregate import percentile" in block, block[:400]
        wrapper = source.split("def blast_radius_distribution", 1)[1]
        assert "return distribution(" in wrapper.split("\ndef ", 1)[0], (
            "blast_radius_distribution grew its own arithmetic again")

    def test_a_run_too_small_refuses_rather_than_computing(self):
        """Deciles over four elements are four numbers wearing ten
        labels. `UX-234`'s `MIN_BASELINE_RUNS` is the precedent."""
        from bga.analyzer import blast_radius_distribution

        assert blast_radius_distribution([1, 2, 3]) is None
        assert blast_radius_distribution(list(range(10))) is not None

    def test_a_flat_population_says_it_is_flat(self):
        from bga.analyzer import blast_radius_distribution

        assert blast_radius_distribution([7] * 20)["is_flat"] is True
        assert blast_radius_distribution(list(range(20)))["is_flat"] is False

    def test_the_deciles_agree_with_an_independent_computation(self):
        """Nearest-rank, computed here rather than trusted from there."""
        import math

        from bga.analyzer import blast_radius_distribution

        values = list(range(1, 101))
        shape = blast_radius_distribution(values)
        for p in (10, 50, 90):
            expected = sorted(values)[math.ceil(p / 100 * len(values)) - 1]
            assert shape["deciles"][f"p{p}"] == expected, p


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
