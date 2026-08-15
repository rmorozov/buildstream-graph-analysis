"""Tests for P2-08: structural measured/certified/advisory separation.

`bga/validation/provenance.py` adds a lightweight structural checkpoint
at the boundary where bga/analyzer.py::_compute_floors assembles the
final plain `floors` dict from its certified computations
(t_infinity_observed/lb/certified_headroom/t_c/model_slack) and
bga/floors/cold.py's advisory output (t_infinity_cold) - not a rewrite
of AnalysisResult's dict-based fields, just a type-checked assembly
step that makes an accidental swap loud (TypeError) instead of silent.
"""
import pytest

from bga.validation.provenance import Advisory, Certified, Measured, assemble_floors


def test_assemble_floors_produces_the_same_plain_dict_as_before():
    """The existing wire format - a plain dict of ints/None - is
    unchanged; only the assembly step is now type-checked."""
    floors = assemble_floors(
        certified={
            't_infinity_observed': Certified(100),
            'lb': Certified(100),
            'certified_headroom': Certified(0),
            't_c': Certified(100),
            'model_slack': Certified(0),
        },
        advisory={'t_infinity_cold': Advisory(150)},
    )
    assert floors == {
        't_infinity_observed': 100,
        'lb': 100,
        'certified_headroom': 0,
        't_c': 100,
        'model_slack': 0,
        't_infinity_cold': 150,
    }


def test_none_certified_value_is_allowed_for_not_yet_computed_floors():
    """t_c/model_slack are legitimately None before replay runs -
    None itself (not a raw int, not an Advisory) is accepted."""
    floors = assemble_floors(
        certified={'t_c': None, 'model_slack': None},
        advisory={},
    )
    assert floors == {'t_c': None, 'model_slack': None}


def test_advisory_value_rejected_where_certified_expected():
    """The real P2-08 acceptance scenario: a deliberate, test-only
    attempt to pass an Advisory (cold-prefixed) value into a slot that
    expects a Certified one must raise, not silently succeed."""
    with pytest.raises(TypeError, match="must be a Certified value"):
        assemble_floors(
            certified={'lb': Advisory(100)},
            advisory={},
        )


def test_certified_value_rejected_where_advisory_expected():
    """The reverse direction: a Certified value must not silently pass
    as an advisory (cold) one either."""
    with pytest.raises(TypeError, match="must be an Advisory value"):
        assemble_floors(
            certified={},
            advisory={'t_infinity_cold': Certified(100)},
        )


def test_raw_int_rejected_in_either_slot():
    """A bare, unwrapped int (the pre-P2-08 shape) is no longer accepted
    directly - forces the caller to be explicit about provenance."""
    with pytest.raises(TypeError):
        assemble_floors(certified={'lb': 100}, advisory={})
    with pytest.raises(TypeError):
        assemble_floors(certified={}, advisory={'t_infinity_cold': 100})


def test_certified_and_advisory_are_not_interchangeable_in_arithmetic():
    """Certified/Advisory/Measured deliberately implement no arithmetic
    or implicit int-conversion - mixing them in an expression raises
    TypeError immediately rather than silently coercing."""
    with pytest.raises(TypeError):
        Certified(100) + Advisory(50)
    with pytest.raises(TypeError):
        int(Certified(100))


def test_measured_is_a_distinct_type_from_certified_and_advisory():
    m = Measured(100)
    assert not isinstance(m, Certified)
    assert not isinstance(m, Advisory)
    with pytest.raises(TypeError):
        assemble_floors(certified={'lb': m}, advisory={})
