"""UX-1087: the bounded-memory measurement varies identifiers.

UX-1069's guard held `ELEMENTS = 8` constant at N and 4N, so it never
saw `PseudonymMap._forward`, the originals set and the residue index
grow with *distinct* identifiers rather than records. Records at fixed
identifiers still grow the peak by under a quarter of the bytes gained;
distinct identifiers at fixed records grow the peak by at most a
measured per-identifier byte constant, with margin (Outcome table,
`/tmp/<track>/measure_axes.py`).
"""
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

import pytest
import test_the_anonymized_export_runs_in_bounded_memory as base

from bga import bundle, jsonstream

BOUND = 0.25
#: bytes/identifier at ELEMENTS 800->8000, N=1000 (Outcome table): 1311.6;
#: doubled for margin.
PER_IDENTIFIER_BOUND = 2600
MIN_GROWTH = 100_000


@pytest.fixture
def small_chunks(monkeypatch):
    monkeypatch.setattr(jsonstream, "CHUNK", 4096)
    monkeypatch.setattr(bundle, "RESIDUE_CHUNK", 4096)


def _run(elements, n, monkeypatch):
    monkeypatch.setattr(base, "ELEMENTS", elements)
    with tempfile.TemporaryDirectory() as td:
        tmp_path = pathlib.Path(td)
        base._peak(tmp_path / "warm", 10, False)  # first-call caches, as N pays none of them
        return base._peak(tmp_path / "run", n, False)


def test_records_vary_at_fixed_identifiers_stays_flat(monkeypatch, small_chunks):
    peak_n, bytes_n, outcome_n = _run(base.ELEMENTS, 1000, monkeypatch)
    peak_4n, bytes_4n, outcome_4n = _run(base.ELEMENTS, 4000, monkeypatch)
    assert (outcome_n, outcome_4n) == ("exported", "exported")
    grew, gained = peak_4n - peak_n, bytes_4n - bytes_n
    assert gained > 200_000, gained
    assert grew < BOUND * gained, (peak_n, peak_4n, gained)


def test_identifiers_vary_at_fixed_records_grows_at_most_linearly(monkeypatch, small_chunks):
    small_elements, large_elements, n = 8, 608, 100
    peak_small, _bytes_small, outcome_small = _run(small_elements, n, monkeypatch)
    peak_large, _bytes_large, outcome_large = _run(large_elements, n, monkeypatch)
    assert (outcome_small, outcome_large) == ("exported", "exported")
    grew = peak_large - peak_small
    assert grew > MIN_GROWTH, grew  # the records-only guard above does not see this
    assert grew <= PER_IDENTIFIER_BOUND * (large_elements - small_elements), grew
