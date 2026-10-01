"""Whether the run's published verdicts agree with each other (`UX-1253`).

Five sections each publish a bound - the diagnosis, the binding floor, the
capacity recommendation's binding constraint, utilisation's oversubscription
flag and the capacity verdict - and each is computed alone. `read_verdicts`
collects them; `disagreements` checks them pairwise over `PAIRS` and returns
one `verdict_disagreement` record per pair that contradicts itself, naming
both sides. It names the disagreement; it does not pick a winner.
"""

from typing import Callable, NamedTuple, Optional

from . import shown as qty
from .findings import CAPACITY_BOUND_SHARE, DIAGNOSIS_CAPACITY_BOUND, DIAGNOSIS_INCONCLUSIVE

VIOLATION_TYPE = 'verdict_disagreement'


def read_verdicts(result, headline: Optional[dict]) -> dict:
    """The verdicts `PAIRS` compares, flat; `None` where a section did not publish one."""
    floors = getattr(result, 'floors', None) or {}
    recommendation = getattr(result, 'capacity_recommendation', None) or {}
    utilisation = getattr(result, 'utilisation', None) or {}
    verdict = getattr(result, 'capacity_verdict', None) or {}
    wall = getattr(result, 'total_duration_us', None) or 0
    lb = floors.get('lb')
    return {
        'diagnosis': (headline or {}).get('diagnosis'),
        'lb_us': lb,
        't_infinity_us': floors.get('t_infinity_observed'),
        'lb_share_of_wall': lb / wall if lb is not None and wall else None,
        'lb_cpu_binds': floors.get('lb_cpu_binds'),
        'binding_constraint': recommendation.get('binding_constraint'),
        'builders_change': recommendation.get('builders_change'),
        'potential_oversubscription': utilisation.get('potential_oversubscription'),
        'capacity_checks_ran': verdict.get('checks_ran'),
        'capacity_oversubscribed': verdict.get('oversubscribed'),
    }


class Pair(NamedTuple):
    pair: str
    left: str
    right: str
    disagree: Callable[[dict], bool]
    reads: Callable[[dict], tuple]


def _lb_is_the_wall(v: dict) -> bool:
    share, lb, t_inf = v['lb_share_of_wall'], v['lb_us'], v['t_infinity_us']
    return share is not None and share >= CAPACITY_BOUND_SHARE and lb is not None and lb > (t_inf or 0)


PAIRS = (
    Pair(
        'diagnosis_vs_floors',
        'headline.diagnosis',
        'floors.lb',
        lambda v: v['diagnosis'] not in (None, DIAGNOSIS_CAPACITY_BOUND, DIAGNOSIS_INCONCLUSIVE) and _lb_is_the_wall(v),
        lambda v: (
            v['diagnosis'],
            f"LB {qty.share(v['lb_share_of_wall'])} of wall, at or above {qty.share(CAPACITY_BOUND_SHARE)}",
        ),
    ),
    Pair(
        'oversubscription_vs_capacity_verdict',
        'utilisation.potential_oversubscription',
        'capacity_verdict.oversubscribed',
        lambda v: (
            v['potential_oversubscription'] is True
            and v['capacity_checks_ran'] is True
            and v['capacity_oversubscribed'] is False
        ),
        lambda v: ('oversubscribed', 'not oversubscribed, checks ran'),
    ),
    Pair(
        'binding_constraint_vs_cpu_floor',
        'capacity_recommendation.binding_constraint',
        'floors.lb_cpu_binds',
        lambda v: v['binding_constraint'] == 'CPU' and v['lb_cpu_binds'] is False,
        lambda v: ('CPU binds', 'the CPU floor does not bind'),
    ),
    Pair(
        'capacity_bound_vs_recommendation',
        'headline.diagnosis',
        'capacity_recommendation.builders_change',
        lambda v: (
            v['diagnosis'] == DIAGNOSIS_CAPACITY_BOUND
            and v['builders_change'] == 0
            and v['binding_constraint'] not in (None, 'host_cores')
        ),
        lambda v: (DIAGNOSIS_CAPACITY_BOUND, f"keep builders, {v['binding_constraint']} binds and is not a cap"),
    ),
)


def disagreements(verdicts: dict) -> list[dict]:
    """One `verdict_disagreement` record per pair in `PAIRS` whose two sides contradict."""
    out = []
    for row in PAIRS:
        if not row.disagree(verdicts):
            continue
        left_reads, right_reads = row.reads(verdicts)
        out.append(
            {
                'type': VIOLATION_TYPE,
                'pair': row.pair,
                'left': {'verdict': row.left, 'reads': left_reads},
                'right': {'verdict': row.right, 'reads': right_reads},
                'detail': f"{row.left} reads {left_reads}; {row.right} reads {right_reads}",
            }
        )
    return out


def verdict_violations(result, headline: Optional[dict]) -> list[dict]:
    return disagreements(read_verdicts(result, headline))
