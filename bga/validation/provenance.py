"""
Structural measured/certified/advisory separation (P2-08).

The specification's own governing principle: "Measure what happened.
Certify what cannot be improved. Label what is estimated. Never mix the
three." This has always been enforced correctly - by naming convention
(cold_-prefixed dict keys) and caller discipline (bga/floors/cold.py's
own docstring states plainly that its output is "fully independent of
LB/certified_headroom/primary confidence/measured attribution" and is
merged in only under cold-prefixed keys). But nothing at the type level
stopped a future edit from accidentally substituting an advisory value
where a certified one belongs, or vice versa - `AnalysisResult.floors`
is a single flat dict, so `floors['lb']` and `floors['t_infinity_cold']`
are structurally indistinguishable ints once assembled.

This module adds a lightweight structural checkpoint at exactly the
boundary where that risk is real: bga/analyzer.py::_compute_floors's
final assembly of the plain `floors` dict from its certified
computations (t_infinity_observed/lb/certified_headroom/t_c/model_slack)
and bga/floors/cold.py's advisory output (t_infinity_cold). It does not
rewrite AnalysisResult's dict-based fields into a typed object graph
(out of scope - see docs/backlog/tasks/P2-08) - the wire format (JSON/text
report output) is unchanged; these wrapper types exist only inside the
assembly step, unwrapped immediately into the same plain ints/None the
rest of the codebase has always used.

Certified/Advisory/Measured deliberately implement no arithmetic or
implicit int-conversion dunders - passing one where the wrong wrapper
(or a raw int) is expected is a TypeError at the call site, not a
silent substitution. Unwrap explicitly (.value) only where a plain
value is genuinely needed.
"""
from dataclasses import dataclass
from typing import Optional, Union


@dataclass(frozen=True)
class Certified:
    """A value proven un-improvable given the input trace (Parts 14-16)
    - e.g. LB, T-infinity,observed, certified_headroom, T_C, model_slack
    (int microseconds), or a derived ratio of certified quantities, e.g.
    efficiency_score = lb / total_duration_us (UX-02, a float 0.0-1.0) -
    still "proven, not guessed" even though it's not itself a duration."""
    value: Union[int, float]


@dataclass(frozen=True)
class Advisory:
    """A value derived from historical/estimated data (Part 15 cold
    floor) - may be unresolved (value=None). Never a substitute for a
    Certified value."""
    value: Optional[int]


@dataclass(frozen=True)
class Measured:
    """A value computed directly from this run's own observed trace
    data (Parts 11-13 attribution/occupancy)."""
    value: int


def assemble_floors(
    certified: dict[str, Optional[Certified]],
    advisory: dict[str, Advisory],
) -> dict:
    """
    Merge certified and advisory values into the plain `floors` dict -
    the existing wire format (JSON/text report output), unchanged.

    The parameter types are the guard: every value in `certified` must
    be a `Certified` instance (or None, for a floor that legitimately
    has no value yet, e.g. t_c/model_slack before replay runs), and
    every value in `advisory` must be an `Advisory` instance. Passing a
    raw int, or the wrong wrapper type, for either raises TypeError
    immediately - accidental conflation is loud, not silent.
    """
    result: dict = {}
    for key, wrapped in certified.items():
        if wrapped is not None and not isinstance(wrapped, Certified):
            raise TypeError(
                f"floors[{key!r}] must be a Certified value, got {type(wrapped).__name__} "
                "- certified floors (LB, T-infinity,observed, certified_headroom, T_C, "
                "model_slack) must never be silently substituted with an advisory (cold) value."
            )
        result[key] = wrapped.value if wrapped is not None else None
    for key, wrapped in advisory.items():
        if not isinstance(wrapped, Advisory):
            raise TypeError(
                f"floors[{key!r}] must be an Advisory value, got {type(wrapped).__name__} "
                "- advisory (cold) floors must never be silently substituted with a "
                "certified value."
            )
        result[key] = wrapped.value
    return result
