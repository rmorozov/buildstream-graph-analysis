"""UX-170: a duration the baseline set itself reached is not evidence.

The noise band exists because a fixed 1% rule called two captures of the
same commit a 5.8% improvement, and at n=3 it fixed exactly that. At n=5
on real GitHub runners it did not: five captures of one freedesktop-sdk
commit spanned 2712.39s .. 3614.22s, the band came to 2762.79s ..
4048.77s, and the *fastest* run fell below the band its own presence had
helped compute. `bga compare` then announced that same-commit pair as
`IMPROVED (-25.0%)`.
"""
import pytest

from bga.compare import _compare_results, compute_band

# The five real fdsdk captures, in microseconds. Same commit, same
# workflow, same `--builders 4 --max-jobs 4`.
FDSDK = [3614.22e6, 3434.43e6, 3405.78e6, 3261.22e6, 2712.39e6]


class TestTheBandReportsWhetherItDescribesItsOwnSet:
    def test_the_real_five_do_not_fit_their_own_band(self):
        band = compute_band(FDSDK)
        assert band["describes_its_own_set"] is False
        assert band["runs_outside_band"] == 1
        # The measured figures, to the hundredth of a second.
        assert band["low_us"] / 1e6 == pytest.approx(2762.79, abs=0.05)
        assert band["high_us"] / 1e6 == pytest.approx(4048.77, abs=0.05)
        assert band["observed_low_us"] / 1e6 == pytest.approx(2712.39, abs=0.05)

    def test_a_well_behaved_set_says_so(self):
        band = compute_band([26.30e6, 26.90e6, 27.17e6, 27.72e6, 27.00e6])
        assert band["describes_its_own_set"] is True
        assert band["runs_outside_band"] == 0

    def test_the_band_itself_is_unchanged(self):
        """The MAD is still the MAD - UX-59's robustness argument holds.

        This item does not widen the band; it reports a fact about it.
        Widening to cover the observed range was tried and rejected: it
        makes one contaminated baseline run swallow a real regression,
        which is precisely what the median and MAD were chosen to avoid.
        """
        band = compute_band(FDSDK)
        assert band["median_us"] / 1e6 == pytest.approx(3405.78, abs=0.05)
        assert band["scaled_mad_us"] / 1e6 == pytest.approx(214.33, abs=0.05)


class _Result:
    """The two fields the duration verdict reads."""

    def __init__(self, total_us):
        self.total_duration_us = total_us
        self.run_id = "same-identity"
        self.floors = {}
        self.attribution = {}
        self.confidence = {"primary": 1.0, "run_mode": "incremental"}
        self.violations = []
        self.graph = None
        self.signals = {}
        self.occupancy = {}
        self.element_kind_summary = None


def _verdict(baseline_us, candidate_us, baselines=FDSDK):
    comparison = _compare_results(
        _Result(baseline_us), _Result(candidate_us), [], [],
        baseline_band=compute_band(list(baselines)),
    )
    return comparison.verdict


class TestTheDisputedRegionIsRefused:
    def test_the_pair_that_read_improved_now_refuses(self):
        """The headline case, on the real numbers."""
        assert _verdict(3614.22e6, 2712.39e6) == \
            "within the baseline set's own observed range"

    def test_the_pairs_the_band_handled_keep_their_answer(self):
        """Deliberately narrower than "refuse whenever the set is noisy"."""
        assert _verdict(3614.22e6, 3405.78e6) == "no significant change"
        assert _verdict(3614.22e6, 3261.22e6) == "no significant change"

    def test_a_candidate_beyond_every_baseline_still_gets_a_verdict(self):
        """Outside the band *and* outside the range: a real answer."""
        assert _verdict(3405.78e6, 5000.00e6) == "regressed"
        assert _verdict(3405.78e6, 1000.00e6) == "improved"

    def test_a_well_behaved_set_never_reaches_the_refusal(self):
        clean = [26.30e6, 26.90e6, 27.17e6, 27.72e6, 27.00e6]
        assert _verdict(27.00e6, 31.00e6, baselines=clean) == "regressed"
        assert _verdict(27.00e6, 27.10e6, baselines=clean) == "no significant change"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
