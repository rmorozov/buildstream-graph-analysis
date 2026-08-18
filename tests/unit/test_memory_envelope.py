"""UX-104: the multiplication the report used to leave to the reader.

The standing memory line was *"its largest single process peaked at
1902 MB resident - multiply by however many elements build concurrently
before raising `builders`"*. Every input to that multiplication is
measured: per-element peak RSS (`UX-63`), the host's RAM (recorded at
capture time by this task), and the builders count (Plane 1). Leaving it
to the reader has a failure mode in each direction - raise `builders`
into swap, or leave headroom unused out of caution.
"""
from bga.correlate import compute_memory_envelope
from bga.findings import _memory_envelope_findings, _memory_refuses_more_builders
from bga.ingest.models import AnalysisResult


def _report(*peaks_mb):
    return {'peak_memory': {'per_element': {
        f"e{i}.bst": {'peak_rss_kb': int(peak * 1024), 'measured': 10, 'unmeasured': 0}
        for i, peak in enumerate(peaks_mb)
    }}}


def test_the_envelope_sums_the_n_largest_peaks():
    """Conservative by construction: as if the N heaviest elements built
    at once *and* peaked at the same instant. Neither is guaranteed, and
    for "is it safe to raise builders?" an upper bound is the useful
    direction to be wrong in."""
    envelope = compute_memory_envelope(_report(400, 300, 200, 100), 2, 8192)
    at_two = envelope['at_observed_builders']
    assert at_two['builders'] == 2
    assert at_two['envelope_mb'] == 700  # the two largest, not the two first
    assert at_two['fits'] is True


def test_the_first_builders_count_that_does_not_fit_is_named():
    """The number the reader wants: not "how much", but "how many
    before it stops fitting"."""
    envelope = compute_memory_envelope(_report(4000, 4000, 4000, 4000), 2, 9000)
    assert envelope['first_builders_that_does_not_fit'] == 3


def test_no_host_memory_means_no_envelope_rather_than_half_an_estimate():
    """The arithmetic needs both halves. Peaks without a denominator are
    not a conservative estimate, they are a guess."""
    assert compute_memory_envelope(_report(400, 300), 2, None) == {}


def test_no_measured_peaks_means_no_envelope():
    assert compute_memory_envelope({'peak_memory': {'per_element': {}}}, 2, 8192) == {}


def test_the_projection_stops_at_the_measured_population():
    """More builders than there are elements with a measured peak is a
    concurrency this build cannot reach out of this population, so the
    sum is over what exists rather than padded with a guess.

    It is also the *only* bound on how far the projection goes. An
    earlier version stopped two past the observed builders count, which
    is a number chosen from nothing, and it hid a ceiling three builders
    away - `first_builders_that_does_not_fit` came back None on a run
    that genuinely stops fitting at 5."""
    envelope = compute_memory_envelope(_report(400, 300), 4, 8192)
    assert [p['builders'] for p in envelope['projections']] == [1, 2]
    assert envelope['at_observed_builders'] is None


def test_no_reserve_is_invented_and_the_payload_says_so():
    """A margin for the OS and page cache would be a threshold picked
    from nothing. `fits` is strict, and the note is explicit that
    headroom below 100% is not the same as safe."""
    envelope = compute_memory_envelope(_report(4096, 4000), 2, 8192)
    assert envelope['at_observed_builders']['fits'] is True  # 8096 <= 8192
    assert 'not the same as safe' in envelope['note']


# --- what the advice does with it ---------------------------------------

def _result(envelope):
    result = AnalysisResult()
    result.memory_envelope = envelope
    return result


def test_the_sentence_is_the_one_the_readme_used_to_ask_for_in_prose():
    envelope = compute_memory_envelope(_report(2000, 1900, 1800, 1700), 4, 16000)
    line = _memory_envelope_findings(_result(envelope))[0]
    assert '4 builders of this shape peak at' in line
    assert 'GB of 15.6 GB' in line


def test_a_build_where_memory_does_not_bind_says_that_instead():
    """`examples/06` measured: 4 builders at ~0.6 GB of 15.7 GB. Telling
    a reader that is a different, equally useful answer from naming a
    ceiling."""
    envelope = compute_memory_envelope(_report(160, 155, 150, 145, 140, 135, 130), 4, 16000)
    line = _memory_envelope_findings(_result(envelope))[0]
    assert 'memory is not what binds first here' in line


def test_more_builders_is_refused_on_memory_grounds():
    """The failure this exists to prevent: capacity advice that clears
    the CPU check and blows the memory one is advice to build into swap,
    which no CPU-side signal predicts."""
    envelope = compute_memory_envelope(_report(3000, 3000, 3000, 3000), 2, 8000)
    refusal = _memory_refuses_more_builders(_result(envelope))
    assert refusal is not None
    assert 'do NOT raise --builders' in refusal
    assert 'would swap' in refusal


def test_a_ceiling_further_away_than_one_more_builder_is_not_a_refusal():
    """The refusal is about the *next* builder. A ceiling three builders
    away is a fact for the envelope line, not a reason to refuse a raise
    that would fit."""
    envelope = compute_memory_envelope(_report(1000, 1000, 1000, 1000, 1000), 2, 4500)
    assert envelope['first_builders_that_does_not_fit'] == 5
    assert _memory_refuses_more_builders(_result(envelope)) is None


def test_no_envelope_means_no_refusal_and_no_line():
    assert _memory_refuses_more_builders(_result({})) is None
    assert _memory_envelope_findings(_result({})) == []
