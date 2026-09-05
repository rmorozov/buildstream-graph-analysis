"""UX-214: one verdict vocabulary, published as one.

Round 23's verification found the trend's colouring was a **second,
divergent verdict chain**. `_mark_verdicts` classified on the band's
edges alone and emitted `within_band` — a sixth value, outside
`schemas.VERDICT_KINDS` — with none of compare's significance or
disputed-region branches.

`UX-203`'s log (mine) claimed "the trend's colouring cannot disagree
with what `bga compare` would say about the same pair". Only
`compute_band` was shared. This file exists because that sentence was
an over-claim, and it now holds by construction.

The disagreement is not hypothetical, and the case that exposes it is
the exact one the band view exists to teach — `UX-170`'s disputed
region, silently re-litigated by a dot.
"""
import pytest

from bga import schemas
from bga.compare import classify_against_band, compute_band, widen_band

# Four identical runs and one outlier: MAD collapses to zero, so the
# band widens only to the fixed 5% floor, and the set's own high edge
# ends up *outside* the band it produced. That is the disputed region's
# precondition, and it takes a deliberately skewed set to reach.
DISPUTED_BASELINES = [100.0, 100.0, 100.0, 100.0, 200.0]


def _band(durations=DISPUTED_BASELINES):
    raw = compute_band(durations)
    return widen_band(raw, raw["median_us"])


class TestTheTwoChainsDisagreed:
    def test_the_case_that_exposes_it_is_real(self):
        """Measured, not argued: the band is [99, 101] with one set
        edge outside it, so a candidate of 150 is outside the band and
        inside the range the baselines themselves reached."""
        band = _band()
        assert band["low_us"] == pytest.approx(99.0)
        assert band["high_us"] == pytest.approx(101.0)
        assert band["edges_outside_band"] == 1
        assert band["observed_low_us"] <= 150.0 <= band["observed_high_us"]

    def test_the_old_store_rule_answered_differently(self):
        """The rule `_mark_verdicts` used to apply, kept here as the
        thing that must not come back: edges alone, no disputed region.
        On this pair it said `regressed`; compare says the set cannot
        support the claim."""
        band = _band()
        old_answer = ("regressed" if band["high_us"] < 150.0
                      else "improved" if band["low_us"] > 150.0 else "within_band")
        assert old_answer == "regressed"
        assert classify_against_band(150.0, band) == "within_observed_range"
        assert old_answer != classify_against_band(150.0, band)

    def test_the_store_now_gives_compares_answer(self):
        """End to end, through the function the listing actually calls."""
        from tools.bga_snapshot import _mark_verdicts

        rows = [{"total_duration_us": d}
                for d in DISPUTED_BASELINES + [150.0]]
        _mark_verdicts(rows)
        assert rows[-1]["verdict_kind"] == "within_observed_range"

    def test_compare_and_the_store_share_the_classifier(self):
        """Not "they agree today" - one function, asserted by reading
        the source. Two chains that happen to agree is the state this
        item found."""
        import inspect

        from bga import compare
        from tools import bga_snapshot

        assert "classify_against_band" in inspect.getsource(
            bga_snapshot._mark_verdicts)
        assert "classify_against_band(" in inspect.getsource(
            compare._compare_results if hasattr(compare, "_compare_results")
            else compare)


class TestTheVocabularyIsClosed:
    def test_the_store_emits_only_declared_kinds(self):
        from tools.bga_snapshot import _mark_verdicts

        rows = [{"total_duration_us": d}
                for d in (100, 100, 100, 100, 200, 150, 90, 101, 400)]
        _mark_verdicts(rows)
        for row in rows:
            assert row["verdict_kind"] is None \
                or row["verdict_kind"] in schemas.VERDICT_KINDS, row

    def test_within_band_is_gone(self):
        """It was a sixth value that existed only in the store."""
        from tools.bga_snapshot import _mark_verdicts

        rows = [{"total_duration_us": d} for d in range(100, 120)]
        _mark_verdicts(rows)
        assert "within_band" not in {r["verdict_kind"] for r in rows}
        assert "within_band" not in schemas.VERDICT_KINDS

    def test_compare_publishes_the_enum(self):
        """`UX-201` promised external consumers a closed set and
        delivered a Python constant plus a map in the viewer - both
        inside this repository. A consumer reading the schema saw
        `["string", "null"]` and no vocabulary at all."""
        declared = schemas.schema(schemas.COMPARE)["properties"]["verdict_kind"]
        assert "enum" in declared, declared
        assert set(schemas.VERDICT_KINDS) <= set(declared["enum"])
        assert None in declared["enum"], "a run with no verdict is legal"

    def test_the_store_rows_publish_the_same_enum(self):
        rows = schemas.schema(schemas.STORE)["properties"]["snapshots"]
        declared = rows["items"]["properties"]["verdict_kind"]
        assert set(declared["enum"]) == set(
            schemas.schema(schemas.COMPARE)["properties"]["verdict_kind"]["enum"])

    def test_the_enum_is_the_constant_not_a_second_list(self):
        source = open("bga/schemas.py", encoding="utf-8").read()
        assert source.count('"enum": list(VERDICT_KINDS) + [None]') == 2, (
            "the closed set is spelled out somewhere instead of built "
            "from VERDICT_KINDS")

    def test_a_real_store_listing_validates_against_its_own_schema(self, tmp_path):
        """The round-trip the Required Fix asks for, on rows the code
        actually produces."""
        jsonschema = pytest.importorskip("jsonschema")
        from tests.unit.test_the_views_nobody_could_reach import _store
        from tools.bga_snapshot import store_listing

        project, _ = _store(tmp_path, 6)
        listing = store_listing(str(project))
        jsonschema.validate(listing, schemas.schema(schemas.STORE))
        kinds = {r["verdict_kind"] for r in listing["snapshots"]}
        assert kinds <= set(schemas.VERDICT_KINDS) | {None}, kinds


class TestTheStyleSheetFollowedTheVocabulary:
    def test_no_rule_styles_a_kind_nothing_emits(self):
        """`style.css` styled `verdict-within_band` deliberately - the
        split was intentional and nowhere documented. With one
        vocabulary there is nothing to style."""
        import re

        css = open("bga/viewer/style.css", encoding="utf-8").read()
        styled = set(re.findall(r"\.verdict-([a-z_]+)", css))
        assert styled <= set(schemas.VERDICT_KINDS), (
            f"styles a verdict kind nothing publishes: "
            f"{styled - set(schemas.VERDICT_KINDS)}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
