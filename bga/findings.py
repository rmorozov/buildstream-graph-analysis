"""UX-75: the report's conclusions, as data.

Asked directly whether everything valuable reaches the JSON report, the
measured answer on round 9's real capture was **neither format is a
superset of the other**:

- `--format json` published every *number* - floors, attribution,
  occupancy, signals, confidence, violations - and **none of the
  conclusions**. Every sentence a human actually reads ("this build is
  execution-bound", "4 elements are 94.0% of the critical path", "work
  them in this order") was computed inside `bga/report/text.py` and
  thrown away. A machine consumer - the CI gate this project exists to
  serve - had to re-implement `_heaviest_on_path`'s structural exclusion
  and re-derive four thresholds from the source to reach the same
  conclusion a human reads for free.
- The text report, in the other direction, showed only part of the data.

Two implementations of one judgement is how they drift, and `UX-71`
documented that `bga analyze` and `bga correlate` had already drifted on
the single most important judgement the tool makes.

So the decision about *what is worth saying* happens once, here, as a
list of findings; `bga/report/text.py` decides only *how to say it*, and
`bga/report/json.py` publishes the same list. A finding that is not
produced here cannot appear in either format.

**Stable ids matter more than pretty titles.** `id` is what a CI gate
keys on and what a diff between two runs joins on, so it is part of the
contract and does not change with wording. `evidence` carries the raw
numbers behind the sentence, so a consumer never has to parse `title`.
"""

import collections
import os
import statistics
from typing import Optional

from . import shown as qty
from . import sweep_curve
from .cache_effectiveness import (
    HEALTHY_HIT_RATIO,
    POOR_HIT_RATIO,
    TRANSFER_SHARE_NOTABLE,
)
from .ingest.models import AnalysisResult
from .plural import plural
from .units import GIB, human_bytes

# Severity is about what it means for the reader, not about size:
#   critical - the run itself is not what it appears to be
#   high     - a real opportunity or a real problem to act on
#   medium   - worth reading, secondary to the above
#   info     - scoping and context; changes how to read the rest
SEVERITY_CRITICAL = "critical"
SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_INFO = "info"

# `UX-372`: **which reader a finding is for.**
#
# `docs/design/roles.md` has named eight roles since round 27, and no
# payload had ever said which one an answer serves - so the page opened
# with one question, "What should I do?", answered once for whoever was
# looking. Measured on `macro_micro`, all three top actions were the
# same kind of advice (shorten this element, then that one, then the
# third), which is the right answer for R1 and no answer at all for the
# CI owner whose lever is `capacity-recommendation`, nine findings down.
#
# Five of the eight, because those are the readers a *single build's*
# findings can serve: R5-R8's questions live across builds and this
# report has none of that. The ids are `roles.md`'s, so the backlog's
# `Serves:` lines and the payload speak one vocabulary rather than two.
READERS = (
    ("local-optimizer", "R1", "I can change these elements", "Which element should I shorten first?"),
    ("recipe-author", "R2", "I own one element's recipe", "Is my element a problem, and what does changing it cost?"),
    ("graph-owner", "R3", "I own the dependency graph", "What does the shape of this graph make impossible?"),
    ("ci-gatekeeper", "R4", "I decide whether this build passes", "Is this number trustworthy, and is it normal?"),
    ("capacity-operator", "R5", "I own the machines it runs on", "What should the fleet be configured as?"),
)

#: Every finding id this module can emit, and the reader it serves.
#:
#: A map rather than a `_finding()` argument on purpose: the assignment
#: is a claim about the whole set - "who is left with nothing to read" -
#: and nineteen call sites each naming their own reader is nineteen
#: places for the answer to that question to hide.
#: `test_the_page_has_a_reader.py` holds it exhaustive against the
#: source, so a new finding with no reader fails rather than defaulting.
FINDING_READERS = {
    # R1 - the shortest path from "my build is slow" to a fix.
    "build-failed": "local-optimizer",
    "failed-task-time": "local-optimizer",
    "time-concentration": "local-optimizer",
    "joint-saving": "local-optimizer",
    "blast-radius-ranking": "local-optimizer",
    "certified-headroom": "local-optimizer",
    "wait-category": "local-optimizer",
    "execution-bound": "local-optimizer",
    # R2 - the cost of *their* element, and what a change to it reaches.
    "latent-heavies": "recipe-author",
    "blast-radius-reach": "recipe-author",
    "blast-radius-structural": "recipe-author",
    # `UX-681`: the mirror. The ranking is R3's "which fan-in is
    # suspicious"; naming a stack as the graph's shape is R2's.
    "fan-in-structural": "recipe-author",
    "shared-source-blast": "recipe-author",
    "cache-transfer-cost": "recipe-author",
    # `UX-683`: the declared tier, same reader as the kind-based
    # exemption it widens - R2 owns the toolchain and wants out of the
    # noise these two name.
    "blast-radius-foundation": "recipe-author",
    "fan-in-foundation": "recipe-author",
    # R3 - the structural answers.
    "mesh-graph": "graph-owner",
    "chain-graph": "graph-owner",
    "graph-width": "graph-owner",
    "criticality": "graph-owner",
    "fan-in-ranking": "graph-owner",
    # `UX-683`: "declare or dismiss" is a graph-shape decision, R3's.
    "foundation-candidates": "graph-owner",
    # R4 - whether the number can be trusted and whether it is normal.
    "confidence": "ci-gatekeeper",
    "efficiency-score": "ci-gatekeeper",
    "cache-hit-ratio": "ci-gatekeeper",
    "run-mode-incremental": "ci-gatekeeper",
    # R5 - the fleet.
    "memory-envelope": "capacity-operator",
    "capacity-recommendation": "capacity-operator",
    # `UX-896`: how big the cache has to be is a fleet question, and it
    # is the one the field case asked - an agent holding most of a
    # project and evicting the rest rebuilds, which every other cache
    # finding reads as a key that moved.
    "cache-capacity": "capacity-operator",
    # `UX-907`: which artifacts are the expensive ones is the other half
    # of the same sizing question, and the one a developer shrinking an
    # element reads too.
    "artifact-weight": "capacity-operator",
    # `UX-860`: the envelope's own overcommit test, half of which is
    # swap - previously a word in the headline sentence and nowhere else.
    "swap-observed": "capacity-operator",
    # UX-1255: Plane 2's binary, job and configure findings - each a recipe's to change.
    "costliest-binary": "recipe-author",
    "jobs-waiting": "recipe-author",
    "configure-share": "recipe-author",
    # UX-680: R4, the task's own; R5's section needs Plane 2 and half (a) fires without it.
    "remote-execution-whatif": "ci-gatekeeper",
}

#: Rank order for choosing which of a reader's findings leads. Severity
#: first, then publication order, which is `compute_findings`' own
#: argued sequence - `UX-365` put the actions above the descriptions and
#: `UX-116` put capacity after the envelope it consumes, and neither
#: decision is re-litigated here.
_LEAD_ORDER = (SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM, SEVERITY_INFO)


def reader_index(findings, headline=None):
    """The published readers, in `READERS` order, for one findings list.

    One entry per reader that has something to say about *this* run, so
    a report with no capacity numbers offers no capacity reader - the
    dead-control rule (`UX-194`) applied to a selector. `leads_with` is
    the producer's decision about which of that reader's findings is
    their biggest lever, so the page routes by lookup rather than by
    re-ranking severities of its own (Direction 7).

    **The headline wins where it speaks.** `headline.top_actions`
    already carries this pipeline's decision about the single biggest
    lever, and the reader who owns the finding behind it must lead with
    that finding or the page contradicts itself. Measured before this
    rule existed, on `macro_micro`: severity-then-order gave R1
    `wait-category` - "5.9% of wall-clock is UNTRACKED HEAD", 2.72s -
    while `top_actions` and the decision chapter both named
    `time-concentration`, worth 23.1s. That is round 58's defect
    (`UX-365`) recreated one field over, and the fix is not a second
    ranking but deferring to the first.

    Severity, then published order, for every reader the headline does
    not speak for. Published order is `compute_findings`' own argued
    sequence and is not re-litigated here.
    """
    seen = {}
    for position, finding in enumerate(findings):
        reader = FINDING_READERS.get(finding.get("id"))
        if not reader:
            continue
        seen.setdefault(reader, []).append((position, finding))
    ranked = None
    for action in (headline or {}).get("top_actions") or []:
        ranked = action.get("finding_id")
        if ranked:
            break
    index = []
    for uid, role, label, question in READERS:
        rows = seen.get(uid)
        if not rows:
            continue
        published = [finding.get("id") for _at, finding in rows]
        if ranked in published:
            leads_with = ranked
        else:
            _at, lead = min(
                rows,
                key=lambda row: (
                    _LEAD_ORDER.index(row[1].get("severity"))
                    if row[1].get("severity") in _LEAD_ORDER
                    else len(_LEAD_ORDER),
                    row[0],
                ),
            )
            leads_with = lead.get("id")
        index.append(
            {
                "id": uid,
                "role": role,
                "label": label,
                "question": question,
                "leads_with": leads_with,
                "findings": published,
            }
        )
    return index


_CONFIDENCE_HIGH = 0.8
_CONFIDENCE_MEDIUM = 0.5

_EFFICIENCY_HIGH = 0.9
_EFFICIENCY_MEDIUM = 0.7

# UX-65: a "biggest opportunity" below this share of wall-clock is not an
# opportunity, it is rounding. On a real freedesktop-sdk build the largest
# non-execution category was UNTRACKED_HEAD at 0.1% - 3.47 seconds out of
# 3587.6 - and that was the report's headline while four elements sat at
# 94% of the critical path further down.
OPPORTUNITY_FLOOR_PCT = 1.0

# When the critical path is this share of total duration, the *chain* is
# the constraint, not the scheduler. Blast radius answers "who depends on
# me", which matters when the graph is the problem; here what matters is
# "how long do I take".
CHAIN_BOUND_RATIO = 0.9

# UX-1253: at or above this share of wall-clock the resource floor LB is the
# wall, so the run is bound by its capacity rather than by its schedule.
CAPACITY_BOUND_SHARE = 0.95

# UX-70: at or above this share of zero-slack elements the graph is a
# mesh of near-equal chains rather than one chain, and "optimize the top
# element" stops being meaningful advice on its own. Named by UX-229,
# which found it as a bare `>= 0.5` in the finding it gates: a rule
# whose threshold has no name cannot be published as one.
MESH_ZERO_SLACK_SHARE = 0.5

# UX-207: the diagnosis as an enum, a ratio and a sentence - the three
# things a consumer needs and none of which it should re-derive. The
# ratio decided this before; what changed is that it is now *published*
# rather than surviving only as a clause of one finding's title.
DIAGNOSIS_CHAIN_BOUND = 'chain_bound'
DIAGNOSIS_SCHEDULER_BOUND = 'scheduler_bound'
DIAGNOSIS_CAPACITY_BOUND = 'capacity_bound'
DIAGNOSIS_INCONCLUSIVE = 'inconclusive'
DIAGNOSES = (DIAGNOSIS_CHAIN_BOUND, DIAGNOSIS_SCHEDULER_BOUND, DIAGNOSIS_CAPACITY_BOUND, DIAGNOSIS_INCONCLUSIVE)

# One wording, read by the text report, the JSON and the page. The
# clause `_time_concentration_findings` used to spell out itself is now
# derived from the same enum, so the report and the headline cannot
# describe one build two ways.
#
# `UX-331`: each bound sentence names the line it fell on. Without it
# the scheduler-bound wording reads as a contradiction - the golden
# fixture says "scheduler-bound ... the critical path is 88% of
# wall-clock", and 88% *sounds* like the chain is the constraint. The
# unstated threshold is the whole of what flips it, and a reader who
# does not know `CHAIN_BOUND_RATIO` has no way to reach it from the
# sentence. `{bound}` is formatted from that constant rather than
# written out, so the number cannot drift from the rule that used it.
DIAGNOSIS_SENTENCES = {
    DIAGNOSIS_CHAIN_BOUND: "This build is chain-bound, not scheduler-bound: the critical path "
    "is {ratio} of the time tasks were running, at or above the "
    "{bound} chain-bound line, so the way to a shorter build is a "
    "shorter chain.",
    DIAGNOSIS_SCHEDULER_BOUND: "This build is scheduler-bound, not chain-bound: the critical path "
    "is {ratio} of the time tasks were running, below the {bound} "
    "chain-bound line, so the time is going somewhere other than the "
    "chain.",
    DIAGNOSIS_CAPACITY_BOUND: "This build is capacity-bound, not scheduler-bound: the resource floor "
    "is {ratio} of wall-clock, at or above the {bound} capacity-bound line, "
    "so its builder slots set the wall, not the chain or the scheduler. {step}.",
    DIAGNOSIS_INCONCLUSIVE: "Neither the chain nor the scheduler can be named the constraint: "
    "this run did not record the durations the comparison needs.",
}

# How many actions the decision names. Three, because the panel is a
# decision rather than a backlog - the rest of the ranking is a section
# away and says so.
TOP_ACTIONS_SHOWN = 3

TIME_CONCENTRATION_SHOWN_MAX = 4
FIX_ORDER_SHOWN_MAX = 3
HORIZON_STEPS_SHOWN = 3
LATENT_HEAVIES_SHOWN = 2
BLAST_RADIUS_SHOWN = 3
CRITICALITY_SHOWN = 3


def confidence_band(score: float) -> str:
    if score >= _CONFIDENCE_HIGH:
        return "high"
    if score >= _CONFIDENCE_MEDIUM:
        return "medium"
    return "low"


def efficiency_band(score: float) -> str:
    if score >= _EFFICIENCY_HIGH:
        return (
            "scheduling is near the certified floor for this graph — further "
            "gains need the graph or the work itself to change, not the "
            "scheduler (see Dispatch Occupancy and Critical Path)"
        )
    if score >= _EFFICIENCY_MEDIUM:
        return "worth checking certified headroom for real scheduling gains"
    return "significant scheduling headroom — see certified headroom below"


def structural_kind_tag(entry: dict) -> str:
    """P4-12 Direction 2 / P4-15 Direction 2 (linked): a short, only-
    shown-when-relevant caveat for report listings ranking elements by a
    real, directly-observed signal (blast radius, criticality, etc.) -
    flags when the listed element is a BuildStream plugin kind that
    typically does no real compute work of its own (junction/import/
    filter/compose/stack - see bga.ingest.models.STRUCTURAL_ELEMENT_KINDS),
    so a reader can judge whether its own recorded duration means what
    they'd assume. Never hidden, never used to reorder or exclude - the
    ranking itself is untouched, this is purely an annotation.
    """
    if not entry.get('is_structural_kind'):
        return ''
    kind = entry.get('element_kind', 'unknown')
    return f" [structural: {kind}, may not reflect real compute work]"


def heaviest_on_path(result) -> list[dict]:
    """Critical-path elements with real measured work, ranked by what
    optimizing them is actually worth (`UX-70`), falling back to raw
    duration where a realizable saving was not evaluated.

    Structural elements are excluded rather than ranked: a `stack` or
    `import` on the path is genuine graph structure with no build
    commands to speed up, and `UX-34` already established that ranking
    them as "worth optimizing" wastes the reader's first glance.
    """
    detail = (result.signals or {}).get('critical_path_detail') or []
    real = [d for d in detail if d.get('duration_us') and not d.get('is_structural_kind')]
    # UX-70: rank by realizable saving. Share of the path is what the
    # chain is made of; the saving is what changing it is worth, and on a
    # dense graph those differ by 5x. `None` means not evaluated, and
    # falls back to duration rather than sorting to the bottom.
    return sorted(
        real,
        key=lambda d: -(d['realizable_saving_us'] if d.get('realizable_saving_us') is not None else d['duration_us']),
    )


def path_elements_by_duration(result) -> list[dict]:
    """The same population `heaviest_on_path` ranks, ordered by measured
    duration (`UX-76`).

    Two orderings of one list, and they are not interchangeable: "where
    is the time" is a question about duration, "what should I fix" is a
    question about realizable saving, and on a mesh graph they disagree.
    `UX-70` re-sorted the shared helper by saving, and the concentration
    block silently inherited it - on a real capture it began reporting
    80.3% across four elements and omitting `python3.bst`, the third
    largest on the path, in favour of one 3.5x smaller. Answering a
    duration question with a saving ranking understated the
    concentration by 13.7 points.
    """
    detail = (result.signals or {}).get('critical_path_detail') or []
    real = [d for d in detail if d.get('duration_us') and not d.get('is_structural_kind')]
    return sorted(real, key=lambda d: -d['duration_us'])


def _downstream(blast_radius, uid):
    """`UX-1213`: `toolchain.bst (1,201 downstream)` - a count carries its comma."""
    return f"{uid} ({(blast_radius.get(uid) or {}).get('downstream_count') or 0:,} downstream)"


def _finding(
    id: str,
    severity: str,
    title: str,
    detail: Optional[list[str]] = None,
    elements: Optional[list[str]] = None,
    evidence: Optional[dict] = None,
    *,
    step: dict,
) -> dict:
    # `step` has no default: a finding without one is a TypeError, not a silent gap (UX-1256).
    return {
        'id': id,
        'severity': severity,
        'title': title,
        'detail': detail or [],
        'elements': elements or [],
        'evidence': evidence or {},
        'step': step,
    }


def _step(text: str, command: Optional[list[str]] = None) -> dict:
    """What to do about a finding, and the command line where one exists."""
    return {'text': text, 'command': ' '.join(command)} if command else {'text': text}


def _none(why: str) -> dict:
    """A finding with no step says why it has none."""
    return {'why_none': why}


def _run_command(result, *argv: str) -> Optional[list[str]]:
    """`bga <argv> <run>`, naming the run as `compute_next_steps` does; None without a run path."""
    run_dir = ((getattr(result, 'run_instance', None) or {}).get('run_dir') or '').strip()
    return ['bga', *argv, run_token(run_dir)] if run_dir else None


def _cache_findings(result: AnalysisResult) -> list[dict]:
    """UX-92 stage 1: the cache's own numbers, as findings.

    Deliberately not gated on the hit ratio being *bad*. Every other
    signal in this report describes the work the build did; on an
    incremental build the cache decides how much work that was, so "the
    cache worked" is load-bearing context for reading the rest, not a
    finding that only matters when something is wrong. What the ratio
    changes is the severity and the sentence, not whether it appears.
    """
    cache = (result.signals or {}).get('cache') or {}
    # `UX-896`: capacity is a fact about the machine, so it does not
    # wait on the Pipeline Summary that gives the ratio below its
    # population. A capture that recorded a quota and no summary still
    # answers the sizing question.
    capacity_findings = _cache_capacity_findings(cache.get('capacity') or {})
    # `UX-907`: and the per-element half, on the same terms - a capture
    # that walked the CAS answers "which artifacts are the expensive
    # ones" whether or not the summary says what the queues did.
    capacity_findings += _artifact_weight_findings(cache.get('artifact_weights') or {})
    hit_share = cache.get('hit_share')
    if hit_share is None:
        return capacity_findings

    built = cache.get('built_elements')
    cached = cache.get('cached_elements')
    closure = cache.get('target_closure') or {}
    findings: list[dict] = []

    detail: list[str] = []
    if closure.get('hit_share') is not None and closure.get('targets'):
        detail.append(
            f"    -> for {', '.join(closure['targets'])}'s own closure it is "
            f"{qty.share(closure['hit_share'])} "
            f"({closure['cached']} of {closure['elements']} elements cached)"
        )

    # UX-92/UX-86: a caches-off run has a 0% hit ratio *by construction*
    # and the banding below must not read that as an alarm. Caught by the
    # first cold capture this project ever took, hours after this finding
    # shipped: it reported freedesktop-sdk's nightly scenario as "barely
    # incremental - look for a volatile cache key near the root", which
    # is confidently wrong about a build that was told not to use the
    # cache. `run_mode` (UX-55) is the fact that settles it and it was
    # already in hand.
    if (result.confidence or {}).get('run_mode') == 'full':
        return [
            _finding(
                'cache-hit-ratio',
                SEVERITY_INFO,
                f"{qty.share(0)} cache hits — caches off: all {built} element{'' if built == 1 else 's'} "
                f"built from source, none reused",
                detail=[
                    "    This is the nightly scenario, so a 0% hit ratio is the intent rather than a finding",
                    *detail,
                ],
                evidence={
                    'hit_share': hit_share,
                    'built_elements': built,
                    'cached_elements': cached,
                    'run_mode': 'full',
                },
                step=_none("a caches-off run reuses nothing by design"),
            )
        ]

    if hit_share < POOR_HIT_RATIO:
        severity, verdict = (
            SEVERITY_HIGH,
            (
                "barely incremental — most of the project rebuilt. Look for a "
                "volatile cache key near the root before reading any efficiency "
                "number below: they describe how well this build ran, not how "
                "much of it should have run at all"
            ),
        )
    elif hit_share < HEALTHY_HIT_RATIO:
        severity, verdict = (
            SEVERITY_MEDIUM,
            ("under half the project was reused — worth checking what invalidated the rest"),
        )
    else:
        severity, verdict = SEVERITY_INFO, "the cache did most of the work"

    findings.append(
        _finding(
            'cache-hit-ratio',
            severity,
            f"{qty.share(hit_share)} cache hit ratio ({cached} cached, {built} rebuilt)",
            detail=[f"    {verdict[:1].upper()}{verdict[1:]}", *detail],
            evidence={
                'hit_share': hit_share,
                'built_elements': built,
                'cached_elements': cached,
                'target_closure_hit_share': closure.get('hit_share'),
            },
            step=(
                _none("the cache did most of the work")
                if severity == SEVERITY_INFO
                else _step(
                    "Find what moved the cache key near the root: most of this build should not have run."
                    if severity == SEVERITY_HIGH
                    else "Check what invalidated the elements that rebuilt."
                )
            ),
        )
    )

    share = cache.get('transfer_share')
    if share is not None and share >= TRANSFER_SHARE_NOTABLE:
        transfer = cache.get('transfer_us') or {}
        parts = ", ".join(f"{name.lower()} {qty.duration(us)}" for name, us in sorted(transfer.items()))
        # `UX-897`: the share alone cannot separate a slow link from a
        # slow remote from an object count that would be slow on any
        # link. The rate can, and it is absent rather than zero on a
        # capture with no counters - the clause simply does not appear.
        rate = cache.get('transfer_rate_bytes_per_s')
        moved = cache.get('transfer_bytes') or {}
        evidence = {'transfer_share': share, 'transfer_us': transfer}
        rate_clause = ""
        if rate:
            window_s = (cache.get('transfer_window_us') or 0) / 1e6
            rate_clause = (
                f", and the host moved {human_bytes(moved['total'])} over the "
                f"{qty.seconds(window_s)} it was transferring — {human_bytes(rate)}/s, "
                f"which is the whole host's traffic and so an upper bound on "
                f"this build's"
            )
            evidence.update(
                {
                    'transfer_bytes': moved['total'],
                    'transfer_rate_bytes_per_s': rate,
                    'transfer_window_us': cache.get('transfer_window_us'),
                }
            )
        findings.append(
            _finding(
                'cache-transfer-cost',
                SEVERITY_MEDIUM,
                f"{qty.share(share)} of wall-clock was artifact transfer ({parts})",
                detail=[f"    This build spent it moving artifacts rather than making them{rate_clause}"],
                evidence=evidence,
                step=_step(
                    "Check the link to the artifact cache and the objects each pull moves: this time went to transfer."
                ),
            )
        )
    findings.extend(capacity_findings)
    return findings


def _cache_capacity_findings(capacity: dict) -> list[dict]:
    """`UX-896`: the cache's ceiling against what it holds.

    Two claims, and both are about the machine rather than the project,
    which is why they carry `capacity-operator` and not the reader every
    other cache finding has. Neither fires on an absent number: a
    capture with no quota recorded says nothing here, because "this
    cache has no ceiling" and "nobody looked" are different facts and a
    sizing decision must not be made on the second.
    """
    findings = []
    over_volume = capacity.get('quota_over_volume_bytes')
    if over_volume:
        findings.append(
            _finding(
                'cache-capacity',
                SEVERITY_MEDIUM,
                f"{human_bytes(over_volume)} more cache quota ({capacity['quota_declared']}) than the volume can give",
                detail=[
                    "    The disk filling up will evict the cache before the quota does, so the quota "
                    "is not the ceiling it looks like"
                ],
                evidence={
                    'quota_bytes': capacity.get('quota_bytes'),
                    'volume_total_bytes': capacity.get('volume_total_bytes'),
                    'quota_over_volume_bytes': over_volume,
                },
                step=_step("Lower the cache quota to what the volume holds, or grow the volume."),
            )
        )
    if capacity.get('at_low_watermark'):
        headroom = capacity.get('headroom_bytes') or 0
        # Negative headroom is over the quota outright; at or above the
        # watermark and still under it is the case BuildStream is
        # already cleaning up in, which is the one the field case hit.
        state = f"{human_bytes(-headroom)} over it" if headroom < 0 else f"{human_bytes(headroom)} from it"
        findings.append(
            _finding(
                'cache-capacity',
                SEVERITY_HIGH,
                f"{qty.share(capacity['used_share'])} of the {capacity['quota_declared']} cache quota is used, "
                f"past the {qty.share(capacity['low_watermark_share'])} low watermark",
                detail=[
                    f"    {human_bytes(capacity['cache_used_bytes'])} held, {state}: BuildStream is evicting, "
                    f"and an element that rebuilt here may have had its artifact removed rather than its "
                    f"cache key moved"
                ],
                evidence={
                    'cache_used_bytes': capacity.get('cache_used_bytes'),
                    'quota_bytes': capacity.get('quota_bytes'),
                    'used_share': capacity.get('used_share'),
                    'headroom_bytes': capacity.get('headroom_bytes'),
                    'low_watermark_share': capacity.get('low_watermark_share'),
                },
                step=_step("Raise the cache quota or free the volume: BuildStream is evicting artifacts."),
            )
        )
    return findings


def _artifact_weight_findings(weights: dict) -> list[dict]:
    """`UX-907`: which elements' artifacts are the expensive ones.

    One claim, and the sentence has to carry what the number is as
    plainly as the number. Each figure is that artifact's whole weight -
    every distinct blob under its `files` tree - which is what it would
    need in an empty cache, not what it adds to this one. The two differ
    by the bytes its neighbours already hold, and that difference is
    stated rather than modelled away, because an operator sizing an
    agent and a developer shrinking one element read the same row for
    opposite purposes.
    """
    heaviest = weights.get('heaviest') or []
    if not heaviest:
        return []
    top = heaviest[0]
    walked = weights.get('elements_walked')
    shared = weights.get('shared_bytes')
    detail = [
        f"{row['element']}: {human_bytes(row['files_bytes'])}"
        + (f" (+{human_bytes(row['buildtree_bytes'])} buildtree)" if row.get('buildtree_bytes') else "")
        for row in heaviest
    ]
    if isinstance(shared, int) and shared > 0:
        detail.append(
            f"These are whole weights, so they overlap: the {walked} artifacts "
            f"walked sum to {human_bytes(weights['walked_bytes'])} but hold "
            f"{human_bytes(weights['run_unique_bytes'])} of distinct content, "
            f"{human_bytes(shared)} of it in more than one artifact"
        )
    return [
        _finding(
            'artifact-weight',
            SEVERITY_INFO,
            f"{human_bytes(top['files_bytes'])} is the heaviest artifact this run put in the cache",
            detail=[
                f"    {top['element']}, walked from the CAS: that artifact's own weight rather than a proxy for it",
                *detail,
            ],
            elements=[row['element'] for row in heaviest],
            evidence={
                'source': weights.get('source'),
                'elements_walked': walked,
                'elements_unweighed': weights.get('elements_unweighed'),
                'walked_bytes': weights.get('walked_bytes'),
                'run_unique_bytes': weights.get('run_unique_bytes'),
                'shared_bytes': shared,
                'heaviest': heaviest,
            },
            step=_none("a weight to size the cache by, not a defect"),
        )
    ]


def _run_scope_findings(result: AnalysisResult) -> list[dict]:
    """Everything true of the run rather than of an element.

    `UX-365` split what this returns into two lists without moving any
    finding between them. `_run_blocking_findings` is what invalidates
    the numbers below it - a failed build, the time its failures burned
    - and `UX-54` requires those first: a real capture in which all four
    attempted elements failed led with "Efficiency Score: 1.00" and
    never mentioned them.

    `_run_context_findings` is what *describes* the run - its mode, its
    cache, its confidence. Those opened the report until round 58
    measured what a reader meets first:

    ```text
    #0  info  cache-hit-ratio  "...so a 0% hit ratio is the intent
                                rather than a finding"
    #1  info  confidence       a score, not an action
    #2  high  wait-category    the first thing to do
    ```

    Two `info` entries, the first disclaiming itself, ahead of every
    action. They are still published and still in this module; they are
    now below the actions rather than above them.

    Kept as one entry point because `compute_findings` is the only
    caller that needs the halves apart.
    """
    return _run_blocking_findings(result) + _run_context_findings(result)


def _run_blocking_findings(result: AnalysisResult) -> list[dict]:
    """`UX-54`: what makes every number below describe a different build."""
    findings: list[dict] = []
    # UX-54: said first, before any efficiency number, because every
    # number below describes a build that did not finish. A real
    # freedesktop-sdk capture in which all four attempted elements failed
    # led with "Efficiency Score: 1.00" and never mentioned the failures.
    build_failed = next(
        (v for v in (result.violations or []) if v.get('type') == 'build_failed'),
        None,
    )
    if build_failed is not None:
        failed = build_failed.get('failed_elements') or []
        shown = ", ".join(failed[:3]) + (", ..." if len(failed) > 3 else "")
        # UX-185: this violation now carries three reasons, and only one
        # of them is a failure. Saying "THIS BUILD FAILED: 0 element(s)
        # ended in FAILURE ()" about a capture that met a laptop lid -
        # or, before this, about an interrupt - sends the reader hunting
        # for a compile error that does not exist. `UX-157` fixed that
        # wording in the report and this second site kept it.
        suspended = build_failed.get('suspended')
        if failed:
            headline = (
                f"THIS BUILD FAILED: {plural(build_failed.get('failed_count'), 'element')} "
                f"ended in FAILURE ({shown}) — every figure below describes a build "
                f"that did not complete, and the elements that failed contributed "
                f"only the time they ran before failing"
            )
        elif build_failed.get('interrupted'):
            headline = (
                "THIS BUILD DID NOT FINISH: it was interrupted before it "
                "completed — every figure below describes a partial build"
            )
        elif suspended:
            from .suspend import describe as _describe_suspension

            # No prefix: `describe` already opens with "This capture
            # spans a suspend", and the two together read as a stutter.
            headline = _describe_suspension(suspended)
        else:
            headline = "THIS BUILD DID NOT FINISH — every figure below describes a build that did not complete"
        findings.append(
            _finding(
                'build-failed',
                SEVERITY_CRITICAL,
                headline,
                elements=list(failed),
                evidence={
                    'failed_count': build_failed.get('failed_count'),
                    'interrupted': bool(build_failed.get('interrupted')),
                    'suspended': suspended,
                },
                step=_step("Capture a build that runs to completion: no figure here describes a finished build."),
            )
        )

    confidence = result.confidence or {}
    # UX-62: how much of the measured chain was work that was thrown
    # away. Attribution still counts it as EXECUTION_ON_CHAIN - moving it
    # would change `I4`'s identity - so this reports the waste instead of
    # silently reclassifying it.
    failed_us = confidence.get('failed_task_us') or 0
    if failed_us:
        failed_count = confidence.get('failed_task_count') or 0
        findings.append(
            _finding(
                'failed-task-time',
                SEVERITY_HIGH,
                f"{qty.duration(failed_us)} of the critical path went to "
                f"{plural(failed_count, 'failed task attempt')} that produced nothing",
                detail=[
                    "    Counted as execution, not as waste, because reclassifying it would move "
                    "the attribution identity (I4)"
                ],
                evidence={'failed_task_us': failed_us, 'failed_task_count': failed_count},
                step=_step("Find why the attempts failed: their time is on the chain and produced nothing."),
            )
        )

    return findings


def _run_context_findings(result: AnalysisResult) -> list[dict]:
    """What this run *was* - mode, cache, confidence. Description rather
    than action, which is why `UX-365` stopped it opening the list."""
    findings: list[dict] = []
    confidence = result.confidence or {}
    # UX-55: which of the two CI scenarios this run is, said before the
    # numbers, because it changes what they are *about*.
    if confidence.get('run_mode') == 'incremental':
        cached = confidence.get('critical_path_cached') or []
        findings.append(
            _finding(
                'run-mode-incremental',
                SEVERITY_INFO,
                f"{plural(len(cached), 'critical-path element')} skipped as already built — incremental run"
                if cached
                else "Incremental run: BuildStream skipped elements it had already built",
                detail=[
                    "    Coverage and the floors below describe the work this run actually did, not the whole project"
                ],
                elements=list(cached),
                evidence={'run_mode': 'incremental', 'critical_path_cached': len(cached)},
                step=_step("Compare it against another incremental run, not against a caches-off nightly."),
            )
        )

    # UX-92: what the cache did, said next to the run mode it explains.
    # An incremental run's whole point is the cache, and until now the
    # report said "incremental" without ever saying how well that went.
    findings.extend(_cache_findings(result))

    primary = confidence.get('primary')
    if primary is not None:
        band = confidence_band(primary)
        violations = result.violations or []
        suffix = f" — see {plural(len(violations), 'violation')} below" if violations else ""
        findings.append(
            _finding(
                'confidence',
                SEVERITY_INFO if band == 'high' else SEVERITY_MEDIUM,
                f"{qty.share(primary)} confidence ({band}){suffix}",
                evidence={'primary': primary, 'band': band, 'violation_count': len(violations)},
                step=(
                    _none("high confidence: nothing to correct")
                    if band == 'high'
                    else _step(
                        "Read the violations before trusting the figures."
                        if violations
                        else "Treat the figures as approximate."
                    )
                ),
            )
        )
    return findings


def _time_concentration_findings(
    result: AnalysisResult,
    execution_bound: bool,
    chain_bound: bool,
) -> list[dict]:
    """UX-65 named where the time is; UX-76 made it one table.

    The tool already computes every number here; it simply never put them
    where a reader looks first.
    """
    heavy = path_elements_by_duration(result)
    if not heavy:
        return []
    path_us = sum(d.get('duration_us', 0) for d in ((result.signals or {}).get('critical_path_detail') or []))
    if path_us <= 0:
        return []
    total = result.total_duration_us or 0
    top = heavy[:TIME_CONCENTRATION_SHOWN_MAX]
    share = sum(d['duration_us'] for d in top) / path_us
    verdict = " — chain-bound, not scheduler-bound" if chain_bound else ""
    detail: list[str] = []
    width = max(len(d['element_uid']) for d in top)
    rows = []
    for d in top:
        saving = d.get('realizable_saving_us')
        worth = ""
        if saving is not None and total:
            worth = f"  -> fixing it saves {qty.duration(saving)} ({qty.share(saving / total)} of the build)"
        detail.append(
            f"    {d['element_uid']:<{width}}  {qty.duration(d['duration_us']):>8} "
            f"({qty.share(d['duration_us'] / path_us):>6} of path){worth}"
        )
        rows.append(
            {
                'element_uid': d['element_uid'],
                'duration_us': d['duration_us'],
                'share_of_path': d['duration_us'] / path_us,
                'realizable_saving_us': saving,
            }
        )
    if execution_bound:
        detail.append(
            "    -> these elements must get faster, or come off the chain; the scheduler has no room left to give"
        )
    # UX-74 names the same elements in the same order *with* the makespan
    # each fix leaves behind, so this line would be a strictly weaker
    # duplicate whenever the horizon renders.
    fix_order = [
        d['element_uid'] for d in heaviest_on_path(result)[:FIX_ORDER_SHOWN_MAX] if d.get('realizable_saving_us')
    ]
    horizon_covers_it = len((result.signals or {}).get('optimization_horizon') or []) > 1
    if fix_order and not horizon_covers_it and fix_order != [d['element_uid'] for d in top[: len(fix_order)]]:
        detail.append(
            "    -> work them in this order (by what a fix is worth, which is "
            "not the order above): " + ", ".join(fix_order)
        )

    findings = [
        _finding(
            'time-concentration',
            SEVERITY_HIGH,
            f"{qty.share(share)} of the {qty.duration(path_us)} critical path is "
            f"{plural(len(top), 'element')}{verdict}",
            detail=detail,
            elements=[d['element_uid'] for d in top],
            evidence={'path_us': path_us, 'share_of_path': share, 'chain_bound': chain_bound, 'rows': rows},
            step=_step("Make these elements faster, or take them off the chain: the critical path is made of them."),
        )
    ]

    # UX-70: chain or mesh? This decides whether "optimize the top
    # element" is meaningful advice at all.
    #
    # `UX-475`: the share alone cannot tell them apart, and said so
    # about the least mesh-like graph there is. `linear_chain(n=5)` -
    # five elements, one path, four edges - reported
    # `zero_slack_share: 1.0` and was called "a mesh of near-equal
    # chains", because on a single-path graph **every** element has
    # zero slack by construction: with one path there is nowhere for
    # any of them to move. Fixing guide section 5, in a shipped
    # sentence, and not a cosmetic one - it told the reader their
    # saving would be "capped by the next chain" when the saving is
    # exactly the element's own duration.
    #
    # The discriminator is not a second proxy. An element with zero
    # slack lies on *some* longest path; if it is not on the critical
    # path this run reported, then a second path of the same length
    # exists - which is what "near-equal chains" means and what makes
    # the capping advice true. So: count the zero-slack elements that
    # are off the reported path.
    #
    #     linear_chain(5)     share 1.000   off-path 0   <- a chain
    #     macro_micro         share 0.909   off-path 0   <- a chain
    #     a_build_that_pulls  share 1.000   off-path 0   <- a chain
    #     diamond             share 1.000   off-path 1   <- two chains
    #     fan_in / fan_out    share 1.000   off-path 3   <- a mesh
    #     one_source_many     share 1.000   off-path 3   <- a mesh
    #
    # The density threshold stays in front of both: below it the graph
    # has slack everywhere and neither sentence is worth printing.
    density = (result.signals or {}).get('zero_slack_share')
    if density is not None and density >= MESH_ZERO_SLACK_SHARE:
        off_path = _zero_slack_off_path(result)
        if off_path:
            findings.append(
                _finding(
                    'mesh-graph',
                    SEVERITY_INFO,
                    f"{qty.share(density)} of elements have zero slack, {off_path} off the "
                    "critical path — a mesh of near-equal chains",
                    detail=["      A saving on one element is often capped by the next chain, not by its own duration"],
                    evidence={'zero_slack_share': density, 'zero_slack_off_path': off_path},
                    step=_none("how far a saving reaches, not a defect"),
                )
            )
        else:
            findings.append(
                _finding(
                    'chain-graph',
                    SEVERITY_INFO,
                    f"{qty.share(density)} of elements have zero slack, all on the critical "
                    "path — a saving is worth its own duration",
                    evidence={'zero_slack_share': density, 'zero_slack_off_path': 0},
                    step=_none("how far a saving reaches, not a defect"),
                )
            )
        # Rendered inside the table it qualifies, where it has always been.
        findings[-1]['indent'] = '    '
    return findings


def _zero_slack_off_path(result: AnalysisResult) -> int:
    """How many zero-slack elements are **not** on the reported path.

    Zero is the chain: every element with no room to move is on the one
    path, so there is no other chain to cap a saving. Any number above
    it is a second path of the same length - `UX-475`.

    Both inputs are already published: `elements.slack` and the
    critical path detail the table above is drawn from. Nothing new is
    computed and nothing new is stored.
    """
    signals = result.signals or {}
    slack = signals.get('slack') or {}
    on_path = {row.get('element_uid') for row in (signals.get('critical_path_detail') or [])}
    return sum(1 for uid, value in slack.items() if value == 0 and uid not in on_path)


def _graph_shape_findings(result: AnalysisResult) -> list[dict]:
    """`UX-478`: what the shape makes impossible, from the shape alone.

    The graph-owner's published question is *"What does the shape of
    this graph make impossible?"* and until this item every finding
    that reached that reader was a function of measured durations:
    `criticality` needs a contested path, and `mesh-graph`/`chain-graph`
    read the slack the durations produce. So on `UX-468`'s six-element
    serial chain - the one project whose entire defect *is* the graph -
    the reader index dropped R3 entirely:

    ```text
    ['local-optimizer', 'recipe-author', 'ci-gatekeeper', 'capacity-operator']
    ```

    and the same graph with the per-element seconds tripled brought it
    back. A reader whose presence turns on how long the build took is
    not a reader about shape.

    This one reads `elements.unweighted_depth` and nothing else. Group
    the elements by depth and you have the dependency levels; the widest
    is how many share one depth. It bounds nothing: an element waits on
    its own dependencies, not on its whole level above (UX-1265).

    It is silent on the one shape that imposes nothing - a single stage,
    where every element is independent and the widest stage is the whole
    graph. `UX-467`'s census file holds that negative case, and
    `test_no_shape_finding_speaks_about_every_shape` is what makes it
    load-bearing rather than decorative.
    """
    depth = (result.signals or {}).get('unweighted_depth') or {}
    if not depth:
        return []
    stages = max(depth.values()) + 1
    if stages <= 1:
        # Every element independent: the graph forbids nothing, and a
        # finding that fired here would be describing the absence of a
        # constraint as if it were one.
        return []
    widest = max(collections.Counter(depth.values()).values())
    return [
        _finding(
            'graph-width',
            SEVERITY_INFO,
            f"{stages:,} dependency levels; the widest holds {widest:,} of {len(depth):,} elements",
            evidence={'element_count': len(depth), 'dependency_stages': stages, 'widest_stage': widest},
            step=_none("a shape the dependency graph has; only its dependencies move it"),
        )
    ]


def _memory_envelope_findings(result: AnalysisResult) -> list[str]:
    """UX-104: the multiplication the report used to leave to the reader.

    One sentence, and it is the one the README used to perform in prose:
    *"4 builders of this shape peak at ~7.6 GB of 15.6 GB; 8 would not
    fit"*. Emitted only where both halves were measured - the peaks from
    Plane 2, the host's RAM from the capture. Returns the sentence, which
    `_memory_finding` wraps into the findings list.
    """
    envelope = getattr(result, 'memory_envelope', None) or {}
    at_observed = envelope.get('at_observed_builders')
    if not envelope or not at_observed:
        return []
    host_gb = envelope['host_memory_bytes'] / GIB
    line = (
        f"{at_observed['builders']} builders of this shape peak at "
        f"~{at_observed['envelope_bytes'] / GIB:.1f} GB of {host_gb:.1f} GB "
        f"({qty.share(at_observed['share_of_host'])})"
    )
    ceiling = envelope.get('first_builders_that_does_not_fit')
    if ceiling:
        line += f"; {ceiling} would not fit"
    else:
        higher = [p for p in envelope['projections'] if p['builders'] > at_observed['builders']]
        if higher:
            line += (
                f"; {higher[-1]['builders']} would still fit at "
                f"~{higher[-1]['envelope_bytes'] / GIB:.1f} GB, so memory is not what "
                f"binds first here"
            )
    return [line]


def _memory_refuses_more_builders(result: AnalysisResult) -> Optional[str]:
    """Whether raising `--builders` is refused on memory grounds.

    `UX-83` made "more builders" advice clear a CPU check. This is the
    other half: an answer that clears CPU and fails memory is advice to
    build into swap, which is the worst build slowdown there is and one
    no CPU-side signal predicts.
    """
    envelope = getattr(result, 'memory_envelope', None) or {}
    ceiling = envelope.get('first_builders_that_does_not_fit')
    at_observed = envelope.get('at_observed_builders')
    if not ceiling or not at_observed or ceiling != at_observed['builders'] + 1:
        return None
    return (
        f"do NOT raise --builders on this host — measured per-element peaks put "
        f"{ceiling} builders at ~{next(p['envelope_bytes'] for p in envelope['projections'] if p['builders'] == ceiling) / GIB:.1f} GB "
        f"against {envelope['host_memory_bytes'] / GIB:.1f} GB of RAM, so the extra "
        f"builder would swap. Swapping is the worst build slowdown there is and no "
        f"CPU-side signal predicts it"
    )


def _shared_source_findings(result: AnalysisResult) -> list[dict]:
    """UX-171: when one repository decides most of the build's rebuilds.

    Only the headline lands here. The table itself is a report section,
    because a monorepo can share a dozen resources and Key Findings is
    for the sentence a reader acts on.

    Silent when nothing is shared, which is the ordinary case for a
    project of per-element `local` sources - "no shared resource" is not
    a finding, it is the absence of one.
    """
    blast = getattr(result, 'resource_blast', None) or {}
    headline = blast.get('headline')
    if not headline:
        return []
    top = (blast.get('rows') or [{}])[0]
    reach, of = top.get('blast_count'), blast.get('element_count')
    return [
        _finding(
            'shared-source-blast',
            SEVERITY_MEDIUM,
            # The repository URL and the because-clause are the detail line (UX-1248).
            f"{reach:,} of {of:,} elements rebuild on any commit to one shared source"
            if reach is not None and of
            else "One shared source decides most of this build's rebuilds",
            detail=[f"    {headline}"],
            evidence={
                'resource': top.get('identity'),
                'kind': top.get('kind'),
                'keying': top.get('keying'),
                'direct_count': top.get('direct_count'),
                'blast_count': top.get('blast_count'),
                'element_count': blast.get('element_count'),
                'measured_us': top.get('measured_us'),
            },
            elements=top.get('direct_elements') or [],
            step=_step(
                "Narrow which elements take this source, or key it per element, so a change stops rebuilding the rest."
            ),
        )
        # The section leads with the same sentence; the card links there rather than drawing it twice.
        | {'section': 'resource_blast'}
    ]


def _memory_finding(result: AnalysisResult) -> list[dict]:
    """UX-104's envelope, as a finding with an id like everything else
    since `UX-75`.

    Severity is a fact about the run, not a taste: a build that would
    swap at one more builder is a different message from one where
    memory is nowhere near binding, and a reader scanning severities
    should be able to tell them apart without reading the sentence.
    """
    lines = _memory_envelope_findings(result)
    if not lines:
        return []
    envelope = result.memory_envelope
    at_observed = envelope['at_observed_builders']
    ceiling = envelope.get('first_builders_that_does_not_fit')
    severity = (
        SEVERITY_HIGH
        if not at_observed['fits']
        else SEVERITY_MEDIUM
        if ceiling == at_observed['builders'] + 1
        else SEVERITY_INFO
    )
    return [
        _finding(
            'memory-envelope',
            severity,
            (parts := lines[0].split('; ', 1))[0],
            detail=[f"    {parts[1]}"] if len(parts) > 1 else None,
            evidence={
                'builders': at_observed['builders'],
                'envelope_bytes': at_observed['envelope_bytes'],
                'host_memory_bytes': envelope['host_memory_bytes'],
                'share_of_host': at_observed['share_of_host'],
                'fits': at_observed['fits'],
                'first_builders_that_does_not_fit': ceiling,
                'elements_measured': envelope['elements_measured'],
            },
            step=(
                _none("memory does not bind at this setting")
                if severity == SEVERITY_INFO
                else _step(
                    f"Lower --builders below {at_observed['builders']}: the measured peaks do not fit in RAM."
                    if severity == SEVERITY_HIGH
                    else f"Keep --builders at {at_observed['builders']}: one more would swap."
                )
            ),
        )
    ]


def _max_jobs_advice_detail(advice: Optional[dict]) -> list[str]:
    """UX-739: the per-element price beside each `max_jobs_advice` row
    that actually changes something, plus the joint line once - the
    only rendering surface `capacity-recommendation` has, since neither
    `bga/cli.py`'s text format nor the viewer draws `max_jobs_advice`
    on their own (`grep -rn max_jobs_advice bga/viewer` finds nothing).
    """
    if not advice:
        return []
    lines = []
    for row in advice.get('elements') or []:
        priced = row.get('priced')
        if not priced or not row.get('max_jobs_change'):
            continue
        lines.append(
            f"    {row['element']}: max-jobs {row['current_max_jobs']} -> "
            f"{row['recommended_max_jobs']}: build "
            f"{qty.duration(priced['replayed_baseline_us'])} -> at least "
            f"{qty.duration(priced['projected_us'])} (floor, +"
            f"{qty.duration(priced['cost_us'])})"
        )
        if row.get('price_refusal'):
            lines.append(f"      Unpriced: {row['price_refusal']}")
    for row in advice.get('elements') or []:
        if row.get('price_refusal') and not row.get('priced'):
            lines.append(f"    {row['element']}: unpriced — {row['price_refusal']}")
    joint = advice.get('priced_jointly')
    if joint:
        lines.append(
            f"    Together ({', '.join(joint['elements'])}): build "
            f"{qty.duration(joint['replayed_baseline_us'])} -> at least "
            f"{qty.duration(joint['projected_us'])} (floor, +"
            f"{qty.duration(joint['cost_us'])})"
        )
    # UX-809: at least one priced row is what "the price" means here -
    # refusals alone (or none) carry no figure for these sentences to
    # qualify, so nothing new renders.
    if any(row.get('priced') for row in advice.get('elements') or []):
        for sentence in advice.get('pricing_assumptions') or []:
            lines.append(f"    {sentence}")
    return lines


def _capacity_recommendation_finding(result: AnalysisResult) -> list[dict]:
    """UX-116: the paragraph that intersects the four constraints.

    `UX-09` asked, in the first week of this backlog, whether `--builders`
    and `--max-jobs` compete for the same cores and what they should be
    set to. It was answered descriptively - yes, they compete, here is a
    six-configuration timing table - and then every round added one more
    input without ever assembling the answer: the sweep's knee, measured
    cores-busy per element, pinning detection, the memory envelope. Four
    blocks a reader had to reconcile, where one recommendation was
    wanted.

    The finding names the *binding* constraint, because that is the one
    that changes what to do. A knee at 5 on a host whose cores are
    already 85% drawn is not "raise builders to 5"; it is "CPU binds,
    and the free capacity you have is the element asking its build for
    `-j1`".
    """
    recommendation = getattr(result, 'capacity_recommendation', None) or {}
    if not recommendation:
        return []

    binding = recommendation['binding_constraint']
    recommended = recommendation['recommended_builders']
    builders = recommendation['builders']
    jobs = recommendation.get('native_max_jobs')
    # The question is the *joint* one, so an unrecorded `--max-jobs` is
    # named rather than dropped: "builders 4" reads as a complete setting
    # and "builders 4 x max-jobs unrecorded" does not, which is the
    # honest shape when UX-29 could not recover it from the log.
    setting = f"builders {builders} x max-jobs {jobs if jobs else 'unrecorded'}"
    # UX-861: a CPU-bound figure is clamped to the host's cores in
    # `compute_capacity_recommendation`, so the sentence says so rather
    # than leaving the clamp implicit in the number alone.
    binding_row = next(c for c in recommendation['constraints'] if c['name'] == binding)
    clamped_from = binding_row.get('clamped_from')
    clamp_note = f"; the CPU alone could feed {clamped_from}" if clamped_from else ""
    # UX-1246: a host-core cap is named as the cap, never as CPU binding.
    cap = f"the host's {plural(recommendation['host_cpu_count'], 'core')} cap it" if binding == 'host_cores' else ""
    if recommended > builders:
        # Deliberately weaker than "raise it to N". Measured on a
        # reconstructed macro-fixed `examples/06` where this block said
        # "room for 2 more": a real timing table at builders 2/4/6/8 came
        # back 21.6 / 24.2 / 23.5 / 23.3s - flat inside the run-to-run
        # spread, with no ordering. The knee is a *scheduling* answer and
        # `cores_busy` is an average over the whole run, so during the
        # parallel stretch each element draws more than the average and
        # the CPU ceiling is optimistic. The block's job is to name the
        # constraint and the hypothesis; the timing table is what settles
        # it, and saying otherwise would be UX-14's caveat with the
        # caveat removed.
        verdict = (
            f"{cap or f'{binding} binds first,'} at {recommended}{clamp_note} — nothing "
            f"measured here rules out {plural(recommended - builders, 'more builder')}, "
            f"which is a hypothesis to time rather than a "
            f"setting to apply"
        )
        short = "time it before keeping it"
        severity = SEVERITY_MEDIUM
    elif recommended < builders:
        verdict = (
            f"{cap or f'{binding} binds'} at {recommended}{clamp_note}, below the "
            f"{builders} configured — more builders contend rather than "
            f"overlap here"
        )
        short = f"below the {builders} configured"
        severity = SEVERITY_HIGH
    else:
        verdict = (
            f"{cap or f'{binding} binds'} at exactly {recommended}{clamp_note} — this "
            f"run is already at the setting its own measurements support"
        )
        short = "the setting this run supports"
        severity = SEVERITY_INFO

    # UX-1143: the section's own lead sentence first, so the text report and the page say one thing.
    detail = [f"    {recommendation['verdict']}"] if recommendation.get('verdict') else []
    # UX-1248: the title keeps the number and the cap; the setting and the verdict's reason read here.
    detail.append(
        f"    {setting} on {plural(recommendation['host_cpu_count'], 'core')}: {verdict.split(' — ', 1)[-1]}."
    )
    detail += [
        f"    {constraint['name']} allows {constraint['allows']}: {constraint['reason']}"
        for constraint in recommendation['constraints']
    ]
    pinned = recommendation.get('pinned_elements') or []
    if pinned:
        # Named whichever constraint binds, and the reason is the same in
        # both directions: an element pinned to `-j1` holds a builder slot
        # while drawing one core. Where CPU binds, the slot is the waste;
        # where the graph binds, the element is longer than it needs to be
        # and it is usually on the path. Either way it is capacity already
        # paid for and declined, and it beats raising anything.
        more = f" and {plural(len(pinned) - 3, 'more element')}" if len(pinned) > 3 else ""
        detail.append(
            "    Free capacity you already have: "
            + ", ".join(pinned[:3])
            + more
            + " asked its native build for -j1 — a builder slot drawing one core. "
            "Fix that before raising anything, then re-measure."
        )
    if recommended > builders:
        detail.append(
            "    Time it before keeping it: the knee is a scheduling answer and "
            "cores-busy is a whole-run average, so both overstate what a "
            "contended window can absorb."
        )
    detail.append(f"    {recommendation['caveat']}")
    # UX-678: the sweep's own memory check, from its replayed concurrent
    # set rather than the `memory` constraint's top-N sum above.
    sweep_binding = recommendation.get('sweep_binding')
    if sweep_binding:
        detail.append(
            f"    The sweep itself checked memory too: {sweep_binding['name']}-bound at {sweep_binding['builders']}."
        )
    detail.extend(_max_jobs_advice_detail(recommendation.get('max_jobs_advice')))

    return [
        _finding(
            'capacity-recommendation',
            severity,
            f"{plural(recommended, 'builder')}: {cap or f'{binding} binds'}{clamp_note} — {short}",
            detail=detail,
            elements=pinned,
            evidence={
                'builders': builders,
                'native_max_jobs': jobs,
                'host_cpu_count': recommendation['host_cpu_count'],
                'cores_busy': recommendation['cores_busy'],
                'binding_constraint': binding,
                'recommended_builders': recommended,
                'builders_change': recommendation['builders_change'],
                'constraints': recommendation['constraints'],
                # UX-678: additive - the sweep's own memory-feasible ceiling,
                # summed over its replay's real concurrent set at each swept
                # capacity rather than the envelope's top-N peaks, and which
                # of the two capacities is tighter. Absent unless the sweep
                # had both a measured peak RSS per element and host RAM.
                'sweep_memory_builders': recommendation.get('sweep_memory_builders'),
                'sweep_binding': recommendation.get('sweep_binding'),
            },
            step=(
                _step(f"Remove `notparallel` from {pinned[0]} or raise its job count before raising anything.")
                if pinned
                # UX-1244: a host-core cap's step is measuring past the cap, the decision panel's builders step.
                else _step(f"{_capacity_step(result)[1]}.", _run_command(result, 'sweep'))
                if binding == 'host_cores'
                else _step(
                    f"Time a build at --builders {recommended} against this one before keeping it.",
                    _run_command(result, 'sweep'),
                )
                if recommended > builders
                else _step(f"Lower --builders to {recommended}.")
                if recommended < builders
                else _none("this run is at the setting its measurements support")
            ),
        )
        # UX-1143: the page section drawing this evidence; the card links there rather than repeating it.
        | {'section': 'capacity_recommendation'}
    ]


def _swap_observed_finding(result: AnalysisResult) -> list[dict]:
    """`UX-860`: the CPU envelope's own `swapped_out` count, as a
    finding - `_headline` already names swap as one clause of an
    overcommit sentence ("load above N cores or pages written to
    swap"); this is the sentence that owns it when it happened.

    Present only where a window actually swapped, not wherever the
    table has a row - `overcommitted_intervals` also holds windows that
    qualified on load alone (`utilisation.envelope`'s own
    `test_load_above_the_cores_is_overcommit`), and reporting those as
    swap would be the word this item was filed to retire, restated.
    """
    rows = [
        row for row in (getattr(result, 'overcommitted_intervals', None) or []) if (row.get('swapped_out') or 0) > 0
    ]
    if not rows:
        return []
    total_pages = sum(row['swapped_out'] for row in rows)
    start = min(row['start_offset_us'] for row in rows)
    end = max(row['start_offset_us'] + row['duration_us'] for row in rows)
    elements = sorted({entry['element'] for row in rows for entry in row.get('building') or ()})
    return [
        _finding(
            'swap-observed',
            SEVERITY_HIGH,
            f"{plural(total_pages, 'page')} written to swap in {plural(len(rows), 'window')}, "
            f"{qty.duration(start)}-{qty.duration(end)} into the build",
            detail=[f"    While building {', '.join(elements)}"] if elements else None,
            elements=elements,
            evidence={
                'swapped_out_pages': total_pages,
                'swap_window_count': len(rows),
                'swap_start_offset_us': start,
                'swap_end_offset_us': end,
            },
            step=_step("Lower --builders or the per-element job count until the concurrent set fits in RAM."),
        )
    ]


# `UX-680`: the sentence that keeps the two remote-execution
# projections from being read as a total. Both remove time from the
# *same* critical-path seconds, by two different means - REAPI moves
# the sandbox that does the work, compiler offload moves the compile
# inside it - so buying both is not buying their sum.
REMOTE_EXECUTION_NOT_ADDITIVE_SENTENCE = (
    "Not additive: both remove the same critical-path seconds, so buying both is not buying their sum."
)


def _remote_execution_findings(result: AnalysisResult) -> list[dict]:
    """UX-680: what each remote-execution mechanism is worth, priced
    from numbers this run already measured, never summed.

    `bga.cli._attach_remote_execution_whatif` computes both halves onto
    `result.remote_execution_whatif` - `unbounded_builders` from `bga
    sweep`'s own unbounded-builder row (what BuildStream's REAPI buys:
    it moves whole sandboxes, so it removes the builder cap) and
    `compiler_offload` from Plane 2's compiler/linker CPU on the
    critical path (what a compiler-level service like recc/reclient
    buys: it moves compilations out of the sandbox, so it removes
    compile seconds from the agent). `compiler_offload` is absent, not
    zero, without a Plane 2 `binary_cost` for this run - then only the
    builder-cap half publishes.
    """
    whatif = getattr(result, 'remote_execution_whatif', None) or {}
    unbounded = whatif.get('unbounded_builders')
    offload = whatif.get('compiler_offload')
    if not unbounded and not offload:
        return []

    # UX-680/UX-351: seconds for a reader, from the published
    # microseconds - the report's own duration unit, never re-typed as
    # a `_s` field.
    def _s(us):
        return us / 1e6

    detail: list[str] = []
    if unbounded:
        before, after = _s(unbounded['wall_us_before']), _s(unbounded['wall_us_after'])
        detail.append(
            f"    Unbounded builders (REAPI moves whole sandboxes): "
            f"{qty.seconds(before)} -> {qty.seconds(after)} ({qty.seconds(before - after)}); "
            f"assumes {unbounded['assumption']}"
        )
    if offload:
        before, after = _s(offload['wall_us_before']), _s(offload['wall_us_after'])
        detail.append(
            f"    Compiler offload (recc/reclient move compiles out): "
            f"{qty.seconds(before)} -> {qty.seconds(after)} ({qty.seconds(before - after)}); "
            f"assumes {offload['assumption']}"
        )
    if unbounded and offload:
        detail.append(f"    {REMOTE_EXECUTION_NOT_ADDITIVE_SENTENCE}")
        title = (
            f"{qty.seconds(_s(unbounded['wall_us_after']))} with unbounded builders and "
            f"{qty.seconds(_s(offload['wall_us_after']))} with compiler offload — remote execution, not additive"
        )
    elif unbounded:
        title = (
            f"{qty.seconds(_s(unbounded['wall_us_after']))} with unbounded builders, from "
            f"{qty.seconds(_s(unbounded['wall_us_before']))} — remote execution, no per-binary cost"
        )
    elif offload:
        title = (
            f"{qty.seconds(_s(offload['wall_us_after']))} critical path with compiler offload, from "
            f"{qty.seconds(_s(offload['wall_us_before']))} — remote execution"
        )
    else:
        # Unreachable: the early return above already excludes
        # `not unbounded and not offload`. Kept so `title` is never
        # unbound rather than trusted to the branches above.
        title = "Remote execution: no projection could be priced"

    # UX-194: absent, not null - `compiler_offload` (or, in principle,
    # `unbounded_builders`) is left off `evidence` entirely rather than
    # published as `None` when that half was not priced, the same
    # "not looked for" spelling every other missing block in this report
    # uses.
    evidence = {
        'additive': False,
        'why_not_additive': REMOTE_EXECUTION_NOT_ADDITIVE_SENTENCE,
    }
    if unbounded:
        evidence = evidence | {'unbounded_builders': unbounded}
    if offload:
        evidence = evidence | {'compiler_offload': offload}

    # `info`: a projection, not a verdict on this run - it must not
    # outrank `confidence` for `ci-gatekeeper`'s `leads_with` slot
    # (`UX-365`'s rule, applied to the reader this shares rather than
    # to severity ordering generally).
    return [
        _finding(
            'remote-execution-whatif',
            SEVERITY_INFO,
            title,
            detail=detail,
            evidence=evidence,
            step=_none("a projection of two purchases, not a defect in this run"),
        )
    ]


def _plane2_capacity_hint(result: AnalysisResult, category: str) -> Optional[str]:
    """Replace the RESOURCE WAIT next step when Plane 2 contradicts it.

    Only for `resource_wait_us`, and only when a Plane 2 report was
    supplied: every other category, and every run without one, keeps
    today's text byte for byte.
    """
    if category != 'resource_wait_us':
        return None
    # UX-104: memory first, because it is the one that cannot be
    # recovered by working harder. An element pinned to `-j1` is free
    # capacity worth naming; a host that would swap at one more builder
    # makes "raise capacity" wrong whatever else is true.
    memory_refusal = _memory_refuses_more_builders(result)
    if memory_refusal:
        return memory_refusal
    plane2 = getattr(result, 'plane2_capacity', None) or {}
    pinned = plane2.get('pinned_elements') or []
    cores_busy, host = plane2.get('cores_busy'), plane2.get('host_cpu_count')
    measured = (
        f"Plane 2 measured {cores_busy:.2f} of {host} cores busy over this run"
        if cores_busy is not None and host
        else None
    )
    if pinned:
        # Named first: intra-element parallelism is free capacity that
        # `--builders` is not, and it costs nothing to reclaim.
        names = ", ".join(pinned[:3])
        lead = f"do NOT raise capacity — {measured}. " if plane2.get('saturated') and measured else ""
        return (
            f"{lead}{names} asked its native build for -j1 while the rest of this "
            f"build asked for more: remove `notparallel` or raise that element's "
            f"job count first. That is capacity you already have, and unlike "
            f"`--builders` it cannot contend with itself."
        )
    if plane2.get('saturated') and measured:
        return (
            f"do NOT raise capacity on this host — {measured}, so another builder "
            f"would contend for CPU rather than add throughput. The wait is real; "
            f"the remedy is less work or better intra-element parallelism, not more "
            f"concurrent elements."
        )
    return None


def _opportunity_findings(result: AnalysisResult, chain_bound: bool) -> list[dict]:
    attribution = result.attribution or {}
    total = result.total_duration_us
    non_execution = {k: v for k, v in attribution.items() if k != 'execution_on_chain_us'}
    if not non_execution or not total or total <= 0:
        return []
    top_category, top_duration_us = max(non_execution.items(), key=lambda kv: kv[1])
    pct = top_duration_us / total * 100 if top_duration_us > 0 else 0.0
    # UX-65: when nothing meaningful went anywhere other than useful
    # work, "the largest of the remaining 0.1%" is not the answer.
    if pct < OPPORTUNITY_FLOOR_PCT:
        concentration = _time_concentration_findings(
            result,
            execution_bound=True,
            chain_bound=chain_bound,
        )
        if not concentration:
            return []
        return [
            _finding(
                'execution-bound',
                SEVERITY_HIGH,
                f"{pct:.1f}% of wall-clock time is the biggest wait category, under "
                f"{OPPORTUNITY_FLOOR_PCT:.0f}% — this build is execution-bound",
                detail=["    No wait category is large enough to leave a scheduling gap to close"],
                evidence={'largest_wait_category': top_category, 'largest_wait_share': pct / 100},
                step=_step(
                    "Make the elements on the critical path faster, or take them off it: the scheduler has no room left."
                ),
            )
        ] + concentration
    if top_duration_us <= 0:
        return []
    label = top_category.replace('_us', '').replace('_', ' ').lower()
    # UX-04/UX-35: what the category means and what to do about it,
    # conditioned on this run's own capacity verdict. Imported here
    # rather than at module scope: `bga.report` imports this module, so a
    # top-level import back into it is a cycle.
    from .report._shared import resolve_attribution_hint, resource_wait_step

    hint = resolve_attribution_hint(
        top_category,
        getattr(result, 'capacity_verdict', None),
    )
    if top_category == 'resource_wait_us':
        # UX-1271: this run's saturated resource, and the sentence names the command the step hands over.
        hint = f"{_saturated_resource(result)} — {resource_wait_step(getattr(result, 'capacity_verdict', None))}"
    # UX-83: and conditioned on Plane 2, when Plane 2 is in hand. The
    # static RESOURCE WAIT hint says "try --capacity N with a higher N",
    # which on a measured-saturated host is the opposite of the fix - and
    # on one real dual-plane capture the tool said exactly that while its
    # own `correlate` output named a pinned element worth -32.4%.
    plane2_hint = _plane2_capacity_hint(result, top_category)
    if plane2_hint:
        hint = plane2_hint
    return [
        _finding(
            'wait-category',
            SEVERITY_HIGH,
            # `UX-365`: **which** biggest. This is the largest of the
            # non-execution wait categories - a real superlative over a real
            # population - and it used to read "Biggest Opportunity", which
            # is a claim about every finding in the report. On `macro_micro`
            # it named 2.72s while `joint-saving` three rows below was worth
            # 23.1s and claimed nothing. Naming the population is the whole
            # fix: the measurement was never wrong, the scope was.
            f"{pct:.1f}% of wall-clock time is {label} ({qty.duration(top_duration_us)}) — the biggest wait category",
            evidence={'category': top_category, 'category_us': top_duration_us, 'share': pct / 100},
            step=(
                _step(hint, _run_command(result, 'sweep') if top_category == 'resource_wait_us' else None)
                if hint
                else _none(f"no remedy is recorded for {label}")
            ),
        )
    ]


#: UX-1271: a resource is named saturated only this busy on average against its configured capacity.
SATURATED_SHARE = 0.9


def _saturated_resource(result: AnalysisResult) -> str:
    """Builder slots, when the run's configured builders were >= SATURATED_SHARE busy; else the neutral opening.

    Only builders have a configured capacity on the result; a peak is not a capacity.
    """
    from .report._shared import RESOURCE_WAIT_SATURATED

    builders = ((getattr(result, 'agent_sizing', None) or {}).get('builders') or {}).get('observed') or (
        getattr(result, 'capacity_recommendation', None) or {}
    ).get('builders')
    mean = (getattr(result, 'occupancy', None) or {}).get('resource_occupancy') or {}
    busy = next((v for k, v in mean.items() if str(k).rsplit('.', 1)[-1] == 'PROCESS'), None)
    if not builders or busy is None or busy / builders < SATURATED_SHARE:
        return RESOURCE_WAIT_SATURATED
    return f"builder slots were saturated ({busy:.2f} of {builders:g} busy on average)"


def _and(names: list[str]) -> str:
    return names[0] if len(names) == 1 else ", ".join(names[:-1]) + " and " + names[-1]


def _outlook_findings(result: AnalysisResult) -> list[dict]:
    """UX-74: what to do after the first fix, what the set is worth
    together, and what is waiting off the path."""
    signals = result.signals or {}
    total = result.total_duration_us or 0
    findings: list[dict] = []

    joint = signals.get('joint_saving')
    horizon = (signals.get('optimization_horizon') or [])[:HORIZON_STEPS_SHOWN]
    ordered = len(horizon) > 1
    if joint and joint.get('joint_saving_us') and total:
        marked: list[str] = []
        joint_us = joint['joint_saving_us']
        sum_us = joint.get('sum_of_individual_us') or 0
        kind = joint.get('relation') or ('add' if joint.get('savings_add') else 'overlap')
        if kind == 'add':
            relation = (
                "exactly the sum of their individual savings, so they are separate pieces of work that do not overlap"
            )
        elif kind == 'overlap':
            relation = (
                f"less than the {qty.duration(sum_us)} their individual savings add up "
                f"to — fixing one makes the others worth less"
            )
        else:
            elements = list(joint['elements'])
            marked = [uid for uid in joint.get('worth_more_after') or [] if uid in elements]
            later = marked or elements[1:]
            earlier = elements[: elements.index(later[0])] or elements[:1]
            relation = (
                # UX-1266: the order line names each element; a card names one once.
                f"more than the {qty.duration(sum_us)} alone: "
                + ("a later step pays off only once the earlier ones are done" if marked else "together they compound")
                if ordered
                else f"more than the {qty.duration(sum_us)} alone: {_and(later)} "
                f"{'pays' if len(later) == 1 else 'pay'} off after {_and(earlier)}"
            )
        order = " -> ".join(
            f"{step['element_uid']} ({qty.duration(step['makespan_after_us'])}"
            f"{(', pays off after the step before' if at == 1 else ', pays off after the steps before') if step['element_uid'] in marked else ''})"
            for at, step in enumerate(horizon)
        )
        findings.append(
            _finding(
                'joint-saving',
                SEVERITY_HIGH,
                f"{qty.duration(joint_us)} ({qty.share(joint_us / total)} of the build) is what the top "
                f"{len(joint['elements'])} are worth together",
                detail=[f"    That is {relation}"] + ([f"    In this order: {order}"] if ordered else []),
                elements=list(joint['elements']),
                evidence={
                    'joint_saving_us': joint_us,
                    'sum_of_individual_us': sum_us,
                    'savings_add': joint.get('savings_add'),
                    'relation': kind,
                },
                step=_step(
                    f"Start with {joint['elements'][0]}, then the rest.",
                    _run_command(result, 'blast', joint['elements'][0]),
                ),
            )
        )

    latent = signals.get('latent_heavies') or []
    if latent:
        shown = latent[:LATENT_HEAVIES_SHOWN]
        named = ", ".join(f"{e['element_uid']} ({qty.duration(e['duration_us'])})" for e in shown)
        more = f" (+{len(latent) - len(shown)} more)" if len(latent) > len(shown) else ""
        findings.append(
            _finding(
                'latent-heavies',
                SEVERITY_MEDIUM,
                f"{plural(len(latent), 'element')} off the critical path, worth nothing to fix today",
                detail=[f"    {named}{more} — they bound how far shortening the chain can go"],
                elements=[e['element_uid'] for e in shown],
                evidence={'latent_heavies': latent},
                step=_step("Shorten the chain first: these wait off it."),
            )
        )

    if findings:
        findings[-1]['detail'] = list(findings[-1]['detail']) + [
            "    (structural projections over this run's measured durations, where "
            "\"fixed\" means the element becomes instant — a re-capture is still "
            "the ground truth)"
        ]
    return findings


def _ranking_findings(result: AnalysisResult, chain_bound: bool) -> list[dict]:
    """Everything the run has to say about **reach** - who depends on me.

    Three claims, and `UX-479` is the round that separated them, because
    one `chain_bound` gate in front of all three meant a chain-bound
    build published none:

    - `blast-radius-ranking` - *which element to shorten first*. `UX-65`:
      that is the right question when the **graph** constrains the build
      and the wrong one when the chain does, so it stays gated.
    - `blast-radius-reach` - *what a change to this element rebuilds*.
      A different question from the one above, asked by a different
      reader, and true whichever way the build is bound. `UX-479` was
      filed because the recipe-author who owns the fat shared base was
      offered `latent-heavies` - "worth nothing to fix today" about
      three other elements - and nothing at all about their own.
    - `blast-radius-structural` - *these reach most of the graph by
      design*. A fact about the shape of the graph. Whether the chain or
      the scheduler binds this particular run has nothing to do with it,
      and gating it on that was never argued for anywhere.

    The old early return also carried `chain_bound` a second time, and
    `UX-474` found that inner half unreachable - `compute_findings`
    branched on the same value and only called this in the `else`. Both
    copies are gone; the one gate that remains is on the one claim
    `UX-65` argued for.
    """
    signals = result.signals or {}
    top_blast_radius = signals.get('top_blast_radius') or []
    if not top_blast_radius:
        return []
    blast_radius = signals.get('blast_radius') or {}
    distribution = signals.get('blast_radius_distribution')

    # UX-258: structural elements are reported, not ranked as actions.
    #
    # This is `UX-76`'s rule, which `_criticality_findings` below has
    # applied since round 12 - *"structural elements are excluded rather
    # than annotated here"* - reaching the one ranking that skipped it.
    # A base image, a toolchain, a `host_strip_tool` has a thousand
    # dependents **on purpose**; "changing it rebuilds everything" is a
    # fact about the graph, not a task. Measured on a 1,202-element run
    # before this: `next_steps[0]` said *"toolchain.bst is the first
    # thing to fix"* about an `import` whose own payload carried
    # `is_structural_kind: true`.
    #
    # Excluded from the *ranking*, never from the payload: `UX-203` was
    # filed because views were unreachable, and answering this by
    # hiding them would trade one defect for an older one.
    # UX-683: the *declared* tier is checked first and wins the report
    # even when the kind guess below would also have caught it - an
    # owner's declaration is a stronger claim than a plugin-kind guess,
    # and a toolchain the project declared foundation is reported as
    # exactly that rather than folded into the kind-based sentence.
    foundation = [u for u in top_blast_radius if (blast_radius.get(u) or {}).get('is_foundation')]
    structural = [
        u for u in top_blast_radius if (blast_radius.get(u) or {}).get('is_structural_kind') and u not in foundation
    ]
    actionable = [
        u
        for u in top_blast_radius
        if not (blast_radius.get(u) or {}).get('is_structural_kind')
        and not (blast_radius.get(u) or {}).get('is_foundation')
    ]

    # `UX-474`: rank only elements that reach something.
    #
    # On `shared_base_wide` - a shared base with six dependents, the
    # shape the blast findings exist for - the structural exclusion
    # above leaves six elements that reach nothing, and this finding
    # ranked three of them and called them the ones "Most Worth
    # Optimizing First (by blast radius)":
    #
    #     1. mod0.bst (0 downstream elements)
    #     2. mod1.bst (0 downstream elements)
    #     3. mod2.bst (0 downstream elements)
    #
    # An ordering over a constant is not a ranking, and the finding's
    # own hedge was switched off by the same fact: with every count
    # equal there is no `blast_radius_distribution`, so neither
    # `_blast_scale`'s tag nor `_density_sentence` appeared.
    #
    # Silence rather than a sentence saying there is nothing to rank -
    # `UX-194`'s dead-control rule, and `UX-365`'s "the list opens with
    # an action". `blast-radius-structural` still names the base on
    # that shape, which is the true thing to say about it.
    reaching = [u for u in actionable if ((blast_radius.get(u) or {}).get('downstream_count') or 0) > 0]

    findings = []
    shown = [] if chain_bound else reaching[:BLAST_RADIUS_SHOWN]
    if shown:
        detail = []
        for i, elem_uid in enumerate(shown, start=1):
            entry = blast_radius.get(elem_uid, {})
            count = entry.get('downstream_count', 0)
            detail.append(
                f"    {i}. {elem_uid} ({count:,} downstream elements"
                f"{_blast_scale(count, distribution)})"
                f"{structural_kind_tag(entry)}"
            )
        tie = _indistinguishable(shown, blast_radius, distribution)
        if tie:
            detail.append(f"    {tie}")
        if distribution:
            detail.append(f"    {_density_sentence(distribution)}")
        findings.append(
            _finding(
                'blast-radius-ranking',
                SEVERITY_MEDIUM,
                "Elements most worth optimizing first, by blast radius",
                detail=detail,
                elements=list(shown),
                # The distribution key is *absent* when there is none, not
                # `None`. A published null is a value a consumer has to
                # interpret; an absent key is the shape `UX-249` settled on
                # for "we do not have this".
                #
                # `UX-344`: the rows themselves are **not** repeated here.
                # `elements.blast_radius` publishes every element's record
                # once and `elements` above names which of them this finding
                # is about, so a slice keyed by element uid was one
                # population published twice - `UX-288`'s rule - and the
                # deepest shape in the document for the sake of it.
                evidence=({'blast_radius_distribution': distribution} if distribution else {}),
                step=_step(f"Shorten {shown[0]} first.", _run_command(result, 'blast', shown[0])),
            )
        )

    # `UX-479`: what a change to one of these rebuilds - the
    # recipe-author's own question, published on either arm because it
    # is not a ranking and does not compete with `time-concentration`
    # for the same screen. It reads the same `reaching` list as the
    # ranking above, so `shown` is a subset of it and `not shown` still
    # separates the two arms exactly.
    if reaching and not shown:
        named = ", ".join(_downstream(blast_radius, u) for u in reaching[:BLAST_RADIUS_SHOWN])
        findings.append(
            _finding(
                'blast-radius-reach',
                SEVERITY_MEDIUM,
                f"{(blast_radius.get(reaching[0]) or {}).get('downstream_count') or 0:,} downstream elements "
                f"rebuild on a change to the widest-reaching element",
                detail=[
                    f"    {named} — the cost of touching them is not their own duration but everything "
                    f"downstream that has to be built again"
                ],
                elements=list(reaching[:BLAST_RADIUS_SHOWN]),
                step=_step(
                    f"See what a change to {reaching[0]} rebuilds before touching it.",
                    _run_command(result, 'blast', reaching[0]),
                ),
            )
        )

    if structural:
        # Reported, with the number, as the graph's shape.
        named = ", ".join(_downstream(blast_radius, u) for u in structural[:BLAST_RADIUS_SHOWN])
        findings.append(
            _finding(
                'blast-radius-structural',
                SEVERITY_INFO,
                f"{plural(len(structural), 'structural element')} {'reaches' if len(structural) == 1 else 'reach'} "
                "most of the graph by design",
                detail=[
                    f"    {named} — "
                    f"{', '.join(sorted({(blast_radius.get(u) or {}).get('element_kind', 'unknown') for u in structural}))}"
                    f", whose dependents are the graph's shape, not a task"
                ],
                elements=list(structural[:BLAST_RADIUS_SHOWN]),
                step=_none("structural elements: their reach is the graph's shape"),
            )
        )

    if foundation:
        # UX-683: present, separated, never the top row - the owner
        # declared these, so "fix this first" would be arguing with
        # the declaration rather than the graph. Drawing this tier on
        # the page is a later track, not here (brief named UX-678/739;
        # neither file is this tier - see the implementer's report).
        named = ", ".join(_downstream(blast_radius, u) for u in foundation[:BLAST_RADIUS_SHOWN])
        findings.append(
            _finding(
                'blast-radius-foundation',
                SEVERITY_INFO,
                f"{plural(len(foundation), 'declared foundation element')} excluded from the ranking",
                detail=[f"    {named}"],
                elements=list(foundation[:BLAST_RADIUS_SHOWN]),
                step=_none("declared foundation, excluded by the project's own declaration"),
            )
        )

    findings.extend(_foundation_candidates(blast_radius, distribution, _graph_order(signals)))
    return findings


def _graph_order(signals: dict) -> dict:
    """Each uid's graph.json position: `compute_fan_in` publishes its rows in that order."""
    return {uid: index for index, uid in enumerate(signals.get('fan_in') or {})}


def _foundation_candidates(blast_radius: dict, distribution: Optional[dict], order: dict) -> list[dict]:
    """UX-683's discovery half: the owner declares, the tool proposes.

    Candidates are the top p5 fan-out among elements that are neither a
    `STRUCTURAL_ELEMENT_KINDS` kind nor already declared - the same
    population the kind exemption misses, named rather than silently
    exempted a second way. Needs a real distribution (`p95`); a run too
    small for one has nothing to compare a count against.
    """
    if not distribution or not distribution.get('p95'):
        return []
    threshold = distribution['p95']
    candidates = sorted(
        (
            uid
            for uid, row in blast_radius.items()
            if not row.get('is_structural_kind')
            and not row.get('is_foundation')
            and (row.get('downstream_count') or 0) >= threshold
        ),
        key=lambda uid: (-blast_radius[uid]['downstream_count'], order.get(uid, len(order)), uid),
    )
    if not candidates:
        return []
    named = ", ".join(_downstream(blast_radius, u) for u in candidates[:BLAST_RADIUS_SHOWN])
    return [
        _finding(
            'foundation-candidates',
            SEVERITY_INFO,
            f"{plural(len(candidates), 'element')} {'reaches' if len(candidates) == 1 else 'reach'} widely, "
            "not declared foundation — declare or dismiss",
            detail=[f"    {named}"],
            elements=list(candidates[:BLAST_RADIUS_SHOWN]),
            step=_step("Declare each as foundation, or dismiss it."),
        )
    ]


def _fan_in_findings(result: AnalysisResult) -> list[dict]:
    """`UX-681`: the blast ranking's mirror, on the same three rules.

    Two members, not four. `fan-in-reach` would be the ranking restated
    - "what this pulls in" *is* the count it is ranked on, where
    `blast-radius-reach` adds the cost argument a downstream count does
    not carry - and `fan-in-unread` would be `restructuring` restated,
    which already names the never-read edges and replays the saving
    (`UX-407`). The share those edges were read at is a column on the
    join row, where `ELEMENT_PLACEMENT_RULE` puts it.
    """
    signals = result.signals or {}
    ranked = signals.get('top_fan_in') or []
    fan_in = signals.get('fan_in') or {}
    if not fan_in:
        return []
    distribution = signals.get('fan_in_distribution')
    order = _graph_order(signals)

    findings = []
    shown = ranked[:BLAST_RADIUS_SHOWN]
    if shown:
        detail = []
        for index, uid in enumerate(shown, start=1):
            entry = fan_in.get(uid, {})
            count = entry.get('transitive_count', 0)
            detail.append(
                f"    {index}. {uid} ({count:,} upstream, "
                f"{entry.get('direct_count', 0):,} named directly"
                f"{_blast_scale(count, distribution)})"
                f"{structural_kind_tag(entry)}"
            )
        if distribution:
            detail.append(f"    {_density_sentence(distribution, 'pull in')}")
        findings.append(
            _finding(
                'fan-in-ranking',
                SEVERITY_INFO,
                "Elements that pull in the most, by upstream closure",
                detail=detail,
                elements=list(shown),
                evidence=({'fan_in_distribution': distribution} if distribution else {}),
                step=_none("a ranking of what each element pulls in, not a defect"),
            )
        )

    # UX-683: the declared tier is checked first and wins the report
    # even where the kind guess below would also have caught it - same
    # precedence as the blast ranking above.
    foundation = sorted(
        (uid for uid, row in fan_in.items() if row.get('is_foundation') and row.get('transitive_count')),
        key=lambda uid: (-fan_in[uid]['transitive_count'], order[uid]),
    )

    # `UX-76` again, and the one place this graph's widest fan-in
    # actually lands: a stack names everything on purpose.
    structural = sorted(
        (
            uid
            for uid, row in fan_in.items()
            if row.get('is_structural_kind') and row.get('transitive_count') and uid not in foundation
        ),
        key=lambda uid: (-fan_in[uid]['transitive_count'], order[uid]),
    )
    if structural:
        named = ", ".join(
            f"{uid} ({fan_in[uid]['transitive_count']:,} upstream)" for uid in structural[:BLAST_RADIUS_SHOWN]
        )
        findings.append(
            _finding(
                'fan-in-structural',
                SEVERITY_INFO,
                f"{plural(len(structural), 'structural element')} {'pulls' if len(structural) == 1 else 'pull'} "
                "in most of the graph by design",
                detail=[
                    f"    {named} — "
                    f"{', '.join(sorted({fan_in[uid].get('element_kind', 'unknown') for uid in structural}))}"
                    f", whose dependencies are the graph's shape, not a task"
                ],
                elements=list(structural[:BLAST_RADIUS_SHOWN]),
                step=_none("structural elements: their dependencies are the graph's shape"),
            )
        )

    # UX-683: present with its figures and excluded from the ranking
    # above the same way `top_fan_in` already excludes it
    # (`bga/graph/fan_in.py`) - this just says so.
    if foundation:
        named = ", ".join(
            f"{uid} ({fan_in[uid]['transitive_count']:,} upstream)" for uid in foundation[:BLAST_RADIUS_SHOWN]
        )
        findings.append(
            _finding(
                'fan-in-foundation',
                SEVERITY_INFO,
                f"{plural(len(foundation), 'declared foundation element')} excluded from the upstream ranking",
                detail=[f"    {named}"],
                elements=list(foundation[:BLAST_RADIUS_SHOWN]),
                step=_none("declared foundation, excluded by the project's own declaration"),
            )
        )
    return findings


def _blast_scale(count, distribution):
    """` , p90+` - where this count sits in its own run.

    `UX-259`: the count is what travels into a ticket and the rank is
    what stays behind, so the scale rides with the number.
    """
    if not distribution or distribution.get('is_flat'):
        return ""
    deciles = distribution.get('deciles') or {}
    for label in ('p99', 'p95'):
        if count >= (distribution.get(label) or 0):
            return f", at or above {label} of this run"
    for p in sorted((int(k[1:]) for k in deciles), reverse=True):
        if count >= deciles[f'p{p}']:
            return f", at or above p{p} of this run"
    return ", in the bottom decile of this run"


def _indistinguishable(shown, blast_radius, distribution):
    """Say when a rank is not a difference.

    Eleven entries inside an 8% spread, presented as an ordered list of
    what to do first, claims a precision the numbers do not have.
    """
    counts = [(blast_radius.get(u) or {}).get('downstream_count', 0) for u in shown]
    counts = [c for c in counts if c]
    if len(counts) < 2 or not distribution or distribution.get('is_flat'):
        return ""
    spread = (max(counts) - min(counts)) / max(counts)
    if spread > 0.1:
        return ""
    return (
        f"these {len(counts)} are within {qty.share(spread)} of each other "
        f"— the order between them is not a difference worth acting on"
    )


def _density_sentence(distribution, verb="reach"):
    """The graph's shape in one line, rather than a chart (`UX-196`).

    `UX-681`: the verb, because the same arithmetic reads in two
    directions - a blast radius is what an element *reaches* and a
    fan-in is what it *pulls in*, and one sentence for both would say
    the wrong one on half its uses.
    """
    deciles = distribution.get('deciles') or {}
    median, ninety = deciles.get('p50'), deciles.get('p90')
    if median is None or ninety is None:
        return ""
    return (
        f"Shape: half of this run's {distribution['n']:,} elements "
        f"{verb} {median:,} or fewer, the top tenth {verb} {ninety:,} or "
        f"more (max {distribution['max']:,})"
    )


def _criticality_findings(result: AnalysisResult) -> list[dict]:
    criticality = (result.signals or {}).get('criticality_probability') or {}
    if not criticality:
        return []
    # UX-76: structural elements are excluded rather than annotated here,
    # and a list where every entry scores 1.0 - the ordinary shape of a
    # deterministic replay - ranks nothing and is dropped.
    nonzero = sorted(
        (
            item
            for item in criticality.items()
            if item[1].get('probability', 0) > 0 and not item[1].get('is_structural_kind')
        ),
        key=lambda kv: kv[1].get('probability', 0),
        reverse=True,
    )[:CRITICALITY_SHOWN]
    if not nonzero or all(d.get('probability', 0) >= 1.0 for _u, d in nonzero):
        return []
    detail = [
        f"    {i}. {uid} ({qty.share(data.get('probability', 0))} probability of "
        f"being on critical path){structural_kind_tag(data)}"
        for i, (uid, data) in enumerate(nonzero, start=1)
    ]
    return [
        _finding(
            'criticality',
            SEVERITY_INFO,
            "Highest-criticality elements",
            detail=detail,
            elements=[uid for uid, _d in nonzero],
            evidence={'criticality_probability': dict(nonzero)},
            step=_none("a probability ranking, not a defect"),
        )
    ]


def _floor_findings(result: AnalysisResult) -> list[dict]:
    floors = result.floors or {}
    findings: list[dict] = []
    t_inf = floors.get('t_infinity_observed') or floors.get('t_infinity_observed_us', 0)
    lb_val = floors.get('lb') or floors.get('lb_us', 0)
    headroom = floors.get('certified_headroom') or floors.get('certified_headroom_us', 0)
    if headroom > 0:
        findings.append(
            _finding(
                'certified-headroom',
                SEVERITY_MEDIUM,
                f"{qty.duration(headroom)} of certified headroom at most "
                f"(T∞={qty.duration(t_inf)}, LB={qty.duration(lb_val)})",
                evidence={'certified_headroom_us': headroom, 't_infinity_us': t_inf, 'lb_us': lb_val},
                step=_step("Run the sweep to see which capacity reaches the floor.", _run_command(result, 'sweep')),
            )
        )
    # UX-02: never presented alone without the "not work-minimality"
    # caveat, and gated on confidence - low-confidence input gets an
    # explicit caveat rather than false precision.
    efficiency_score = floors.get('efficiency_score')
    if efficiency_score is not None:
        primary = (result.confidence or {}).get('primary')
        caveat = ""
        if primary is not None and primary < _CONFIDENCE_HIGH:
            caveat = " — low-confidence data, treat with caution"
        findings.append(
            _finding(
                'efficiency-score',
                SEVERITY_INFO,
                f"{qty.share(efficiency_score)} efficiency score — "
                + (
                    "scheduling is near the certified floor"
                    if efficiency_score >= _EFFICIENCY_HIGH
                    else "worth checking certified headroom"
                    if efficiency_score >= _EFFICIENCY_MEDIUM
                    else "significant scheduling headroom"
                )
                + caveat,
                evidence={'efficiency_score': efficiency_score, 'low_confidence': bool(caveat)},
                step=_step(
                    "Change the graph or the work itself, not the scheduler."
                    if efficiency_score >= _EFFICIENCY_HIGH
                    else "Read the certified headroom for the scheduling gain left."
                ),
            )
        )
    return findings


# UX-1255: the bounds Plane 2's findings clear. A binary below Plane 1's
# opportunity floor is noise; configure past a tenth of CPU is named.
PLANE2_BINARY_FLOOR_SHARE = OPPORTUNITY_FLOOR_PCT / 100
PLANE2_CONFIGURE_SHARE = 0.10


def _waiting_step(report: dict, elements) -> str:
    """UX-1275: the waiting elements' top 3 binaries by blocked time, where Plane 2 measured it."""
    blocked: dict[str, int] = {}
    for element in elements:
        cost = (report.get('binary_cost') or {}).get(element) or {}
        for entry in cost.get('binaries') or []:
            if entry.get('blocked_us'):
                blocked[entry['binary']] = blocked.get(entry['binary'], 0) + entry['blocked_us']
    top = sorted(blocked, key=lambda name: (-blocked[name], name))[:3]
    if not top:
        return "Find what these elements wait on before raising their job count."
    named = [f"{name} ({qty.duration(blocked[name])})" for name in top]
    listed = named[0] if len(named) == 1 else ", ".join(named[:-1]) + " and " + named[-1]
    # The figures are summed over the waiting elements, not by_binary's whole run; say so.
    return (
        f"Start with what {listed} wait on: across these {plural(len(elements), 'waiting element')}, "
        "the most time spent alive, off CPU and with no child running."
    )


def _plane2_findings(result: AnalysisResult) -> list[dict]:
    """UX-1255: the costliest binary, elements waiting on their jobs, and configure - only where Plane 2 ran."""
    report = getattr(result, 'plane2_report', None) or {}
    if not report:
        return []
    from .plane2 import binary_totals

    out = []
    rows = [row for row in binary_totals(report) if row.get('cpu_us') is not None]
    measured = sum(row['cpu_us'] for row in rows)
    if rows and measured and rows[0]['cpu_us'] / measured >= PLANE2_BINARY_FLOOR_SHARE:
        top = rows[0]
        reach = plural(top['elements'], 'element', shown=f"{top['elements']:,}")
        # UX-1269: a lever is a share of the run's capacity, not of the CPU Plane 2 measured.
        capacity = (getattr(result, 'utilisation', None) or {}).get('capacity_cpu_us')
        of_capacity = top['cpu_us'] / capacity if capacity else None
        step = _step(f"Start with {top['binary']}: no other binary spent as much CPU.")
        if of_capacity is not None and of_capacity < PLANE2_BINARY_FLOOR_SHARE:
            step = _none(
                f"{top['binary']} is {qty.share(of_capacity)} of the run's CPU capacity, under the "
                f"{OPPORTUNITY_FLOOR_PCT:.0f}% opportunity floor: context, not a lever."
            )
        out.append(
            _finding(
                'costliest-binary',
                SEVERITY_INFO,
                f"{qty.duration(top['cpu_us'])} of CPU in {top['binary']}, the costliest of "
                f"{len(rows):,} binaries, across {reach}",
                evidence={
                    'binary': top['binary'],
                    'cpu_us': top['cpu_us'],
                    'share': round(top['cpu_us'] / measured, 3),
                },
                step=step,
            )
            | {'section': 'by_binary'}
        )
    # Each element's own CPU over its own wall (the join's `cores_busy`), on correlate's compute-bound line.
    from .correlate import _COMPUTE_BOUND_CORES, _plane2_view

    waiting_by = {
        element: row
        for element, row in _plane2_view(report).items()
        if (row.get('requested_jobs') or 0) > 1
        and row.get('cores_busy') is not None
        and row['cores_busy'] < _COMPUTE_BOUND_CORES
    }
    waiting = list(waiting_by.values())
    if waiting:
        jobs = sorted(row['requested_jobs'] for row in waiting)
        asked = f"{jobs[0]}" if jobs[0] == jobs[-1] else f"{jobs[0]}-{jobs[-1]}"
        median = statistics.median(row['cores_busy'] for row in waiting)
        out.append(
            _finding(
                'jobs-waiting',
                SEVERITY_MEDIUM,
                f"{len(waiting):,} elements asked for {asked} jobs and ran at a median {median:.2f} cores busy: "
                "waiting, not computing",
                evidence={
                    'element_count': len(waiting),
                    'median_cores_busy': round(median, 2),
                    'requested_jobs': jobs[-1],
                },
                step=_step(_waiting_step(report, waiting_by)),
            )
            | {'section': 'element_join'}
        )
    phase = report.get('configure_phase') or {}
    if phase.get('available') and (phase.get('configure_share') or 0) >= PLANE2_CONFIGURE_SHARE:
        out.append(
            _finding(
                'configure-share',
                SEVERITY_MEDIUM,
                f"{qty.share(phase['configure_share'])} of CPU is configure: "
                f"{qty.duration(phase.get('configure_cpu_us'))} before any build step ran",
                evidence={
                    'configure_share': phase['configure_share'],
                    'configure_cpu_us': phase.get('configure_cpu_us'),
                },
                step=_step("Cache or skip configure in the elements that spend most on it."),
            )
            | {'section': 'configure_phase'}
        )
    return out


def _by_severity(findings: list[dict]) -> list[dict]:
    """`UX-1148`: severity, then the argued order below; an indented note stays under its table."""
    groups: list[list[dict]] = []
    for finding in findings:
        if finding.get('indent') and groups:
            groups[-1].append(finding)
        else:
            groups.append([finding])

    def rank(group):
        severity = group[0].get('severity')
        return _LEAD_ORDER.index(severity) if severity in _LEAD_ORDER else len(_LEAD_ORDER)

    return [finding for group in sorted(groups, key=rank) for finding in group]


def _said_once(findings: list[dict]) -> list[dict]:
    """`UX-1249`: a finding listing the elements a more severe one listed becomes a line of that one."""
    kept: list[dict] = []
    first: dict = {}
    served = collections.Counter(FINDING_READERS.get(f['id']) for f in findings)
    for finding in findings:
        key = frozenset(finding.get('elements') or ())
        # One shared element is two claims about it; a shared list is one claim said twice.
        earlier = first.get(key) if len(key) > 1 else None
        # A reader's only finding stays a finding: folding it would leave that reader no lead.
        sole = served[FINDING_READERS.get(finding['id'])] == 1
        if earlier is not None and not sole and _rank(earlier) < _rank(finding):
            earlier['detail'] = [*earlier['detail'], f"    {finding['title']}"]
            served[FINDING_READERS.get(finding['id'])] -= 1
            continue
        first.setdefault(key, finding)
        kept.append(finding)
    return kept


def _rank(finding: dict) -> int:
    severity = finding.get('severity')
    return _LEAD_ORDER.index(severity) if severity in _LEAD_ORDER else len(_LEAD_ORDER)


def compute_findings(result: AnalysisResult) -> list[dict]:
    """Every conclusion the report draws, in the order it draws them.

    Reads already-computed fields and performs no new analysis - the same
    contract `_format_key_findings` has always had. What changed is where
    the output goes: both renderers consume this, so they cannot disagree
    and a consumer never has to re-derive a threshold from the source.
    """
    # `chain_bound` asks whether the chain or the scheduler is what binds;
    # `execution_bound` asks whether any wait category is large enough to
    # be worth naming. Different questions, and a real build is routinely
    # both.
    #
    # UX-207: read from `diagnose()` rather than recomputed here, so the
    # findings, the headline block and the text report cannot answer the
    # same question differently.
    chain_bound = diagnose(result)['diagnosis'] == DIAGNOSIS_CHAIN_BOUND

    # `UX-365`: what invalidates the numbers, then what to do about
    # them, then what the run was. Before this the whole of
    # `_run_scope_findings` came first, so a successful build opened
    # with two `info` entries - a cache note that says it is "the intent
    # rather than a finding", and a confidence score - and the first
    # action was third.
    findings = _run_blocking_findings(result)
    opportunity = _opportunity_findings(result, chain_bound)
    findings.extend(opportunity)
    concentration_emitted = any(f['id'] == 'time-concentration' for f in opportunity)
    # UX-76: one table, not a second ranking of the same names.
    if chain_bound and heaviest_on_path(result) and not concentration_emitted:
        concentration = _time_concentration_findings(
            result,
            execution_bound=False,
            chain_bound=True,
        )
        findings.extend(concentration)
        concentration_emitted = bool(concentration)
    # `UX-479`: outside the branch. Reach is not the concentration
    # ranking's competitor - `_ranking_findings` gates the one claim
    # that competes and publishes the other two either way.
    findings.extend(_ranking_findings(result, chain_bound))
    # `UX-681`: beside its mirror, and after it - a reader asks what a
    # change costs before asking what the element is built on.
    findings.extend(_fan_in_findings(result))
    # `UX-478`: the one claim about the graph that reads no duration and
    # no capacity, so it is emitted here rather than inside the
    # concentration table - it has to survive a run that has no table.
    findings.extend(_graph_shape_findings(result))
    if concentration_emitted:
        findings.extend(_outlook_findings(result))
    # `UX-365`: the run's own description, after the actions it frames
    # and before the other descriptive findings it belongs with. Still
    # ahead of memory, capacity and the floors, so the reader meets
    # "what this run was" once, in one place.
    findings.extend(_run_context_findings(result))
    findings.extend(_memory_finding(result))
    # UX-116: after the memory envelope, because it consumes it - the
    # reader meets the inputs and then the sentence that intersects them.
    findings.extend(_capacity_recommendation_finding(result))
    # `UX-860`: beside the fleet's other R5 findings, after capacity -
    # the reader has met the configuration before meeting what it cost.
    findings.extend(_swap_observed_finding(result))
    # UX-1255: Plane 2's own measurements, beside the fleet findings that read it.
    findings.extend(_plane2_findings(result))
    # `UX-680`: beside the capacity/sweep findings it reads alongside -
    # `ci-gatekeeper`, not `capacity-operator`, because half (a) fires
    # without Plane 2 and R5's page section cannot.
    findings.extend(_remote_execution_findings(result))
    findings.extend(_criticality_findings(result))
    findings.extend(_floor_findings(result))
    # UX-171: last, because it is a fact about the project's shape
    # rather than about this run - the reader has met the run's own
    # numbers by the time they reach "and one repo rebuilds all of it".
    findings.extend(_shared_source_findings(result))
    findings = _said_once(_by_severity(findings))
    # `UX-372`: and who each is for. Stamped here rather than at the
    # nineteen construction sites, for the reason `FINDING_READERS`
    # gives - and after the whole list exists, so the map is applied to
    # exactly what gets published.
    for finding in findings:
        finding['reader'] = FINDING_READERS.get(finding['id'])
    return findings


def _diagnosis_denominator(result, total):
    """`(microseconds, which)` the critical path is a share **of**.

    `UX-477`. This was wall-clock, and wall-clock carries a constant the
    graph cannot explain: BuildStream's startup, cache query and initial
    staging, before the first task begins. The run's own `wait-category`
    finding names it and says it is *"not a scheduling issue"* — and the
    diagnosis then divided by it anyway.

    What that cost is a verdict that follows how **long** a build is
    rather than what shape it is. One graph, six elements in a strict
    line, with only the per-element seconds changed:

    ```text
      per link   critical path   old (wall)   new (horizon)   old verdict
        1.5s        8.95s          0.865         1.000        scheduler_bound
        4.5s       26.90s          0.950         1.000        chain_bound
    ```

    So the denominator is the **task horizon** — `wall_clock` minus the
    untracked head and tail, which is Part 12's own identity
    (`UNTRACKED_HEAD + task-horizon attribution + UNTRACKED_TAIL ==
    wall_clock`) read the other way round. It is the span the graph is
    actually responsible for, and it is what the scheduler could have
    compressed.

    The subtraction is skipped, and `wall_clock` used, only where the
    attribution is absent or the arithmetic would produce a
    non-positive span — a capture with no wall bounds already has
    `total_duration_us == horizon` (`analyzer.py`), so the two agree
    there and nothing is silently lost. Which one was used is published
    as `headline.chain_share_of`, because a share whose denominator a
    reader has to guess is `UX-345`'s defect.
    """
    attribution = getattr(result, 'attribution', None) or {}
    if 'untracked_head_us' not in attribution:
        # Not "the head was zero" - *we could not look*. A run whose
        # attribution never ran might have any head at all, and saying
        # `task_horizon` over a subtraction that did not happen is the
        # overclaim this field exists to prevent.
        return total, 'wall_clock'
    head = attribution.get('untracked_head_us') or 0
    tail = attribution.get('untracked_tail_us') or 0
    horizon = total - head - tail
    if horizon > 0:
        return horizon, 'task_horizon'
    # A corrupted capture can report a head longer than its own
    # wall-clock (`analyzer.py` reports that containment violation
    # separately). Dividing by a non-positive span is a crash or a
    # negative share; neither is an answer.
    return total, 'wall_clock'


def diagnose(result: AnalysisResult) -> dict:
    """Chain-bound, scheduler-bound, or neither - with the ratio and the
    sentence, so nobody downstream re-derives any of the three.

    `UX-207`. This decision has existed since `UX-65` (the ratio at
    `CHAIN_BOUND_RATIO`), but it lived inside `compute_findings` as a
    local `bool` and reached the outside world only as the clause
    " - this build is chain-bound, not scheduler-bound" glued onto one
    finding's title. A consumer wanting to *branch* on it - the viewer's
    decision panel, a CI gate, anything - had to string-match a
    sentence. Now it is a field.
    """
    floors = result.floors or {}
    total = result.total_duration_us or 0
    t_infinity = floors.get('t_infinity_observed') or 0
    if not total or not t_infinity:
        return {
            'diagnosis': DIAGNOSIS_INCONCLUSIVE,
            'chain_share': None,
            'chain_bound_share': CHAIN_BOUND_RATIO,
            'chain_share_of': None,
            'sentence': DIAGNOSIS_SENTENCES[DIAGNOSIS_INCONCLUSIVE],
        }
    against, source = _diagnosis_denominator(result, total)
    ratio = t_infinity / against
    name = DIAGNOSIS_CHAIN_BOUND if ratio >= CHAIN_BOUND_RATIO else DIAGNOSIS_SCHEDULER_BOUND
    if ratio < CHAIN_BOUND_RATIO and _capacity_is_the_wall(floors, total, t_infinity):
        name = DIAGNOSIS_CAPACITY_BOUND
    if name == DIAGNOSIS_CAPACITY_BOUND:
        sentence = DIAGNOSIS_SENTENCES[name].format(
            ratio=qty.share(floors['lb'] / total), bound=qty.share(CAPACITY_BOUND_SHARE), step=_capacity_step(result)[0]
        )
    else:
        sentence = DIAGNOSIS_SENTENCES[name].format(ratio=qty.share(ratio), bound=qty.share(CHAIN_BOUND_RATIO))
    return {
        'diagnosis': name,
        'chain_share': ratio,
        'chain_bound_share': CHAIN_BOUND_RATIO,
        'chain_share_of': source,
        'sentence': sentence,
    }


def _capacity_is_the_wall(floors: dict, total: int, t_infinity: int) -> bool:
    """LB within `CAPACITY_BOUND_SHARE` of the wall and longer than the chain (UX-1244)."""
    lb = floors.get('lb') or 0
    return lb / total >= CAPACITY_BOUND_SHARE and lb > t_infinity


def _capacity_step(result: AnalysisResult) -> tuple[str, str]:
    """`(sentence, action)` for the builders step: the recommendation's, else the RESOURCE WAIT hint."""
    recommendation = getattr(result, 'capacity_recommendation', None) or {}
    binding = recommendation.get('binding_constraint')
    row = next((c for c in recommendation.get('constraints') or [] if c.get('name') == binding), {})
    # UX-1274: the replayed wall at the knee, said once: on the step, not the sentence above it.
    replayed = sweep_curve.replayed_clause(recommendation)
    tail = f"; {replayed}" if replayed else ""
    if binding == 'host_cores':
        cores = recommendation.get('host_cpu_count')
        return (
            f"Builders are held at the host's {plural(cores, 'core')} by policy while the CPU could feed "
            f"{row.get('clamped_from')}: measure above that cap with bga sweep",
            f"Measure builders above the host's {cores}-core cap with bga sweep{tail}",
        )
    if binding and recommendation.get('recommended_builders') is not None:
        builders = recommendation['recommended_builders']
        return (
            f"{binding} binds at {plural(builders, 'builder')}: run with {builders} and measure it",
            f"Run with {plural(builders, 'builder')} and measure it{tail}",
        )
    from .report._shared import resolve_attribution_hint

    hint = _plane2_capacity_hint(result, 'resource_wait_us') or resolve_attribution_hint(
        'resource_wait_us', getattr(result, 'capacity_verdict', None)
    )
    hint = (hint or "time more builders with bga sweep").replace('`', '').rstrip('.')
    return f"The step this run supports is a builders step, measured: {hint}", hint


def _builders_actions(result: AnalysisResult, by_id: dict) -> list[dict]:
    """The decision's first action on a capacity-bound run: the builders step, and the finding reasoning it."""
    finding = next((fid for fid in ('capacity-recommendation', 'wait-category') if fid in by_id), None)
    # UX-1256: the capacity finding's own step where it has one; the derived step otherwise.
    said = ((by_id.get('capacity-recommendation') or {}).get('step') or {}).get('text')
    action = {'step': said.rstrip('.') if said else _capacity_step(result)[1]}
    # UX-1276: the replayed wall the step's clause gains, priced per day where a rate is declared.
    delta = sweep_curve.replayed_delta_us(getattr(result, 'capacity_recommendation', None) or {})
    if delta:
        action['replayed_delta_us'] = delta
    if finding:
        action['finding_id'] = finding
    return [action]


def _top_actions(result: AnalysisResult, findings: list[dict]) -> list[dict]:
    """Ordered references into the findings that already rank things.

    References, not copies: `finding_id` says where the reasoning is, so
    the panel can send a reader to it rather than restating it. The
    saving is carried where a projection exists and omitted where none
    does - `None` would read as "zero", which is a different claim.
    """
    by_id = findings_by_id(findings)
    actions: list[dict] = []
    # UX-1244: a capacity-bound run leads with its builders step, before any element.
    builders = _builders_actions(result, by_id) if diagnose(result)['diagnosis'] == DIAGNOSIS_CAPACITY_BOUND else []

    concentration = by_id.get('time-concentration')
    for row in ((concentration or {}).get('evidence') or {}).get('rows') or []:
        action = {'finding_id': 'time-concentration', 'element_uid': row['element_uid']}
        saving = row.get('realizable_saving_us')
        if saving is not None:
            action['saving_us'] = saving
        actions.append(action)

    # A scheduler-bound build has no chain to shorten, so the ranking
    # that matters is who-depends-on-me. Same shape, different source.
    ranking = by_id.get('blast-radius-ranking')
    if not actions and ranking:
        # `UX-344`: the run's own blast table, not the finding's slice
        # of it. The slice was a second copy of rows published in full
        # beside it, which is what `UX-288` settled; the finding names
        # the elements and the population says what they cost.
        blast = (result.signals or {}).get('blast_radius') or {}
        for uid in ranking.get('elements') or []:
            actions.append(
                {
                    'finding_id': 'blast-radius-ranking',
                    'element_uid': uid,
                    'downstream_count': (blast.get(uid) or {}).get('downstream_count', 0),
                }
            )
    return (builders + actions)[:TOP_ACTIONS_SHOWN]


def compute_headline(result: AnalysisResult, findings: Optional[list[dict]] = None) -> dict:
    """What to fix first, and what it is worth - as data.

    `UX-207`'s rule, and Direction 7's: **a viewer that derives the
    diagnosis is a second analyzer.** Everything the decision panel
    shows is decided here, where the text report, `--format json`, CI
    and every external consumer see the same answer.

    The opportunity split is published rather than left as a
    subtraction: `scheduling_gap_us` is wall-clock beyond the critical
    path, which is what a page would otherwise compute by taking
    `total_duration_us - floors.t_infinity_observed` and calling it its
    own.
    """
    if findings is None:
        findings = compute_findings(result)
    floors = result.floors or {}
    total = result.total_duration_us or 0
    t_infinity = floors.get('t_infinity_observed') or 0

    headline = dict(diagnose(result))
    headline['certified_headroom_us'] = floors.get('certified_headroom')
    headline['scheduling_gap_us'] = max(0, total - t_infinity) if total and t_infinity else None
    headline['top_actions'] = _top_actions(result, findings)
    # UX-261: what shape this graph has, before a list of elements.
    #
    # A graph where one element reaches everything is a different
    # problem from one where a hundred do, and the reader should know
    # which they have *before* being handed a ranking. One sentence
    # from the published distribution, never a chart - `UX-196`'s rule
    # holds, and a decile histogram earns its place only if a sentence
    # cannot carry the shape.
    shape = _graph_shape(result)
    if shape:
        headline['graph_shape'] = shape
    return headline


def _graph_shape(result) -> Optional[str]:
    """`UX-259`'s distribution, said in one line - or nothing."""
    signals = getattr(result, 'signals', None) or {}
    shape = signals.get('blast_radius_distribution')
    if not shape or shape.get('is_flat'):
        return None
    median = shape['deciles']['p50']
    top = shape['deciles']['p90']
    biggest = shape['max']

    def reach(count):
        return "nothing" if not count else f"{count:,} others"

    half = f"Half of this graph's {shape['n']:,} elements reach {reach(median)}" + ("" if not median else " or fewer")
    tenth = f"the top tenth reach {reach(top)}" + ("" if not top else " or more") + f", up to {biggest:,}"
    # Concentration is `max` against the top decile, not the top decile
    # against the median: in a star-shaped graph both of those are zero
    # and the first draft of this sentence called the most concentrated
    # shape there is "spread across many elements".
    concentrated = biggest >= 10 * max(1, top)
    return f"{half}; {tenth}. " + (
        "Reach is concentrated in a few elements — most of this graph cannot cause a wide rebuild."
        if concentrated
        else "Reach is spread across many elements — there is no single choke point to fix."
    )


# UX-218: the loop, not the report.
#
# `capture -> analyze -> read -> change -> capture again` is where the
# repetition lives, and after reading the decision panel the reader's
# next action comes from a small closed set - blast the top element,
# look inside it, measure again, compare. Every round they retype it,
# copying the run path and the element name by hand out of a page that
# holds both.
#
# The branch is the more important half. *Which* step is right depends
# on the diagnosis, and that mapping has lived in documentation prose.
# If the viewer encodes it the viewer becomes a second decision-maker -
# the thing `UX-207` exists to prevent - so it is decided here, and the
# terminal, CI and the page then give the same answer.
#
# No IO: every precondition below is a property of a published value.
# A step whose precondition is absent is *not published*, which is
# `UX-194`'s dead-button rule applied to advice rather than controls.


def _store_paths(run_dir: str):
    """`(project, in_store)` for a run directory, by shape alone.

    A snapshot lives at `<project>/.bga/runs/<stamp>/run`, so the
    project is four levels up. Read from the published path rather than
    from the filesystem: `compute_headline` is a pure function of the
    result and it stays one - and a path that does not have this shape
    simply yields no store-shaped steps.
    """
    parts = os.path.normpath(run_dir or '').split(os.sep)
    if len(parts) < 4 or parts[-1] != 'run' or parts[-3] != 'runs' or parts[-4] != '.bga':
        return None, False
    return os.sep.join(parts[:-4]) or '.', True


def run_token(run_dir: str) -> str:
    """`@<stamp>` for a store run, so a step runs from the project and on any machine; else the path."""
    from . import run_store

    if not _store_paths(run_dir)[1]:
        return run_dir
    token = '@' + os.path.normpath(run_dir).split(os.sep)[-2]
    return token if run_store.is_alias(token) else run_dir


def _store_run_modes(project: str) -> list[tuple]:
    """`(stamp, run_mode)` per run in the store, oldest first.

    `UX-577`: whether `bga compare @prev @last` is a command or a
    refusal is a fact about the store, not about this run, so it is
    read here rather than baked into the run document. One
    `run-context.json` per snapshot - the read `UX-296` chose for a
    band sample, no trace parse - and an unreadable store yields `[]`.
    """
    from . import run_store
    from .ingest.loader import load_run_context

    modes: list[tuple] = []
    try:
        snapshots = run_store.list_runs(project)
    except OSError:
        return []
    for snapshot in snapshots:
        path = os.path.join(snapshot, 'run', 'run-context.json')
        if not os.path.isfile(path):
            path = os.path.join(snapshot, 'run', 'run_context.json')
        try:
            context = load_run_context(path)
        except (OSError, ValueError, KeyError):
            continue
        modes.append((os.path.basename(snapshot), context.run_mode))
    return modes


def _pairable_baseline(project: str):
    """`(prev_mode, last_mode, stamp)` when `@prev @last` would be
    refused, else `None`.

    `stamp` is the newest run older than `@last` that shares its mode,
    or `None` when the store holds no such run. `unknown` on either
    side is not a mismatch, for `_check_run_modes`' reason: it must not
    be guessed into either bucket.
    """
    modes = _store_run_modes(project)
    if len(modes) < 2:
        return None
    (_, prev_mode), (_, last_mode) = modes[-2], modes[-1]
    if prev_mode in (None, 'unknown') or last_mode in (None, 'unknown'):
        return None
    if prev_mode == last_mode:
        return None
    for stamp, mode in reversed(modes[:-1]):
        if mode == last_mode:
            return prev_mode, last_mode, stamp
    return prev_mode, last_mode, None


def _longest_on_the_path(result) -> Optional[dict]:
    """The critical path's own biggest entry, or `None`.

    `UX-261`: read from `critical_path_detail`, which the analysis
    already publishes - this ranks nothing new, it just stops burying
    the answer that was already there.
    """
    detail = (getattr(result, 'signals', None) or {}).get('critical_path_detail') or []
    entries = [e for e in detail if e.get('element_uid') and e.get('duration_us')]
    if not entries:
        return None
    return max(entries, key=lambda e: e['duration_us'])


def compute_next_steps(result: AnalysisResult, headline: Optional[dict] = None) -> list[dict]:
    """The next commands, chosen by what this run measured.

    Each step carries the reason it was chosen (from published values),
    the command as an argv list with the run and element already
    substituted, and the signal it follows from - so a reader can check
    the advice against the number that produced it.
    """
    if headline is None:
        headline = compute_headline(result)
    # `getattr`, not attribute access: `AnalysisResult` grew
    # `run_instance` in UX-95 and a projection or a stub may not carry
    # it. Advice is the last thing that should be able to break a
    # report.
    instance = getattr(result, 'run_instance', None) or {}
    run_dir = (instance.get('run_dir') or '').strip()
    if not run_dir:
        # Without a run path nothing can be spelled exactly, and a step
        # spelled approximately is worse than no step.
        return []
    project, in_store = _store_paths(run_dir)
    run = run_token(run_dir)
    actions = headline.get('top_actions') or []
    top = actions[0] if actions else None
    steps: list[dict] = []

    # UX-261: what the build is *waiting for*, before what is big.
    #
    # The ranking `UX-258` fixed is still a ranking of reach; the
    # honest first answer is the longest element on the critical path,
    # because that is the one whose duration the wall-clock is made of.
    # It was already computed and already published, and it sat below a
    # list of blast counts.
    longest = _longest_on_the_path(result)
    if longest:
        share = longest.get('share_of_path')
        steps.append(
            {
                'id': 'shorten-what-the-build-waits-for',
                'reason': (
                    f"{longest['element_uid']} is the longest thing on the "
                    f"critical path"
                    # Same rule the two steps below use: a figure that
                    # rounds to "0.0s" argues against the sentence carrying
                    # it. The golden run's longest element is 6ms.
                    + (
                        f" at {qty.duration(longest['duration_us'])}"
                        if (longest.get('duration_us') or 0) >= 100_000
                        else ""
                    )
                    + (f", {qty.share(share)} of it" if share else "")
                    + " — the build cannot finish sooner than this chain."
                ),
                'argv': ['bga', 'blast', longest['element_uid'], run],
                'follows_from': 'critical_path_detail',
            }
        )

    if top and top.get('element_uid'):
        uid = top['element_uid']
        worth = top.get('saving_us')
        steps.append(
            {
                'id': 'blast-the-top-element',
                'reason': (
                    f"{uid} is the first thing to fix"
                    # Same rule as the gap below: a figure that rounds to
                    # "0.0s" argues against the sentence carrying it.
                    + (f", worth {qty.duration(worth)}" if worth and worth >= 100_000 else "")
                    + " — this is what changing it rebuilds."
                ),
                'argv': ['bga', 'blast', uid, run],
                'follows_from': top.get('finding_id') or 'headline.top_actions',
            }
        )
        # The two-plane join answers "compute-bound, or badly built",
        # and only where Plane 2 saw this run - `plane2_coverage` being
        # published is exactly that condition.
        if getattr(result, 'plane2_coverage', None):
            steps.append(
                {
                    'id': 'look-inside-the-element',
                    'reason': (
                        f"Plane 2 measured this run, so the join can say "
                        f"whether {uid} is compute-bound or under-parallelized."
                    ),
                    'argv': ['bga', 'correlate', run],
                    'follows_from': 'plane2_coverage',
                }
            )

    if headline.get('diagnosis') in (DIAGNOSIS_SCHEDULER_BOUND, DIAGNOSIS_CAPACITY_BOUND):
        gap = headline.get('scheduling_gap_us')
        steps.append(
            {
                'id': 'sweep-the-capacity',
                'reason': (
                    f"This build is {headline['diagnosis'].replace('_', '-')}"
                    # Only where the number would say something: a gap that
                    # rounds to "0.0s" reads as a contradiction of the
                    # sentence it is supposed to support.
                    + (
                        f": {qty.duration(gap)} of wall-clock is beyond the critical path"
                        if gap and gap >= 100_000
                        else ""
                    )
                    + " — the sweep says what more builders would buy."
                ),
                'argv': ['bga', 'sweep', run],
                'follows_from': 'headline.diagnosis',
            }
        )

    if in_store:
        # UX-326: `bga snapshot <project>` was printed here for six
        # rounds, and run verbatim it crashed - `snapshot`'s positional
        # is `argparse.REMAINDER`, the *build command*, so the project
        # path arrived as a command to execute and the wrapper refused
        # it. The project belongs in `--project`; the build goes after
        # the `--`. Both halves come from what this run recorded, which
        # is the only way "capture it the same way" can be true.
        #
        # No targets means the step is not offered at all, for the same
        # reason a missing run path returns no steps at the top of this
        # function: a command spelled approximately is worse than none.
        targets = [t for t in (instance.get('targets') or []) if t]
        if targets:
            steps.append(
                {
                    'id': 'measure-again',
                    'reason': f"Make the change, then capture it the same way — run it in {project}.",
                    'argv': ['bga', 'snapshot', '--', 'bst', 'build', *targets],
                    'follows_from': 'run_instance.targets',
                }
            )
        # UX-326, the same class as the step above and found by the
        # guard rather than by the walk: `bga compare` has no
        # `--project`. The printed line has read `--project <path>` since
        # `UX-218`, and every reader who pasted it got
        # `unrecognized arguments`. Aliases resolve against the working
        # directory, so the project belongs in the sentence, not in a
        # flag the parser does not have.
        #
        # UX-577: and it is only a command where the store's last two
        # runs share a run_mode - `UX-78` refuses a full baseline
        # against an incremental candidate with exit 6, so advising the
        # pair unconditionally advises a refusal.
        refused = _pairable_baseline(project)
        if refused is None:
            steps.append(
                {
                    'id': 'compare-with-the-run-before',
                    'reason': (f"Whether it helped, judged against this store's noise — run it in {project}."),
                    'argv': ['bga', 'compare', '@prev', '@last'],
                    'follows_from': 'run_instance.run_dir',
                }
            )
        else:
            prev_mode, last_mode, stamp = refused
            # No run of the candidate's own mode means no pair exists;
            # `measure-again` above is the step that makes one.
            if stamp:
                steps.append(
                    {
                        'id': 'compare-with-a-run-that-pairs',
                        'reason': (
                            f"@prev is a {prev_mode} run and @last a {last_mode} "
                            f"one, which compare refuses — {stamp} is the newest "
                            f"{last_mode} run and pairs with it. Run it in "
                            f"{project}."
                        ),
                        'argv': ['bga', 'compare', f'@{stamp}', '@last'],
                        'follows_from': 'confidence.run_mode',
                    }
                )
    return steps


def render_findings(findings: list[dict]) -> list[str]:
    """The text form: a title line per finding, plus its own detail lines.

    Detail lines carry their own indentation because they are tables and
    sub-rankings whose alignment is part of their meaning; titles are
    indented uniformly here.
    """
    lines: list[str] = []
    for finding in findings:
        indent = finding.get('indent', '  ')
        lines.append(f"{indent}{finding['title']}")
        step = finding.get('step') or {}
        if step.get('text'):
            lines.append(f"{indent}  -> {step['text']}")
            if step.get('command'):
                lines.append(f"{indent}     {step['command']}")
        lines.extend(finding.get('detail') or [])
    return lines


def findings_by_id(findings: list[dict]) -> dict[str, dict]:
    return {f['id']: f for f in findings}


# UX-224: a finding, as something you can paste.
#
# The report ends its life in a pull request, a chat message or a ticket,
# and getting it there was manual: select the finding, lose the evidence,
# retype the numbers, re-find the element name.
#
# Rendered **here**, in the pipeline, and published as
# `findings[].copy_text` - not built in the page. `UX-115`'s CI comment
# is Python and the viewer is JavaScript, so "one renderer" across that
# boundary is only honest one way: the text is a published value and the
# page copies it rather than wording it. The same reason `UX-218`'s
# commands are decided in the pipeline.
def _evidence_line(key: str, value):
    """One evidence pair, in the unit the schema declares for it.

    `None` for a value that has no useful plain-text form. Two things
    the first draft got wrong and the golden fixture showed immediately:
    a nested `blast_radius` dict rendered as 400 characters of Python
    `repr` into the middle of a paste, and `category` and `category_us`
    both had their label reduced to "category" - two different numbers
    under one name is worse than an ugly one.
    """
    from . import schemas

    if isinstance(value, (dict, list, tuple)):
        return None
    quantity = (schemas.EVIDENCE_QUANTITIES.get(key) or {}).get(schemas.QUANTITY)
    # The key verbatim. "category us" reads worse than `category_us`,
    # and a paste that names the published field is one a reader can
    # look up.
    label = key
    if quantity == "duration_us" and isinstance(value, (int, float)):
        return f"{label} {qty.duration(value)}"
    if quantity == "share" and isinstance(value, (int, float)):
        return f"{label} {qty.share(value)}"
    if quantity == "percent" and isinstance(value, (int, float)):
        return f"{label} {value:.1f}%"
    if quantity == "megabytes" and isinstance(value, (int, float)):
        return f"{label} {value:.0f} MB"
    if quantity == "seconds" and isinstance(value, (int, float)):
        return f"{label} {qty.seconds(value)}"
    return f"{label} {value}"


def finding_copy_text(finding: dict, result, next_steps=None) -> str:
    """The plain text one finding pastes as.

    Carries what a reader would otherwise retype: the title, the
    evidence in its declared units, the elements it names, the published
    next step, and - as importantly as the first line - the run identity.
    `UX-178` established that the identity must round-trip; a pasted
    finding without it is an assertion nobody can check.
    """
    lines = [f"BGA finding: {finding.get('title') or finding.get('id')}"]
    for line in finding.get('detail') or []:
        lines.append(f"  {line}")
    for key, value in (finding.get('evidence') or {}).items():
        line = _evidence_line(key, value)
        if line is not None:
            lines.append(f"  {line}")
    elements = finding.get('elements') or []
    if elements:
        lines.append(f"  Elements: {', '.join(elements)}")

    # UX-218's published step for this finding, where there is one. The
    # page does not choose it and neither does this - `follows_from`
    # already says which finding a step came out of.
    for step in next_steps or []:
        if step.get('follows_from') == finding.get('id'):
            lines.append(f"  Next: {' '.join(step.get('argv') or [])}")
            break

    run_id = getattr(result, 'run_id', None)
    if run_id:
        lines.append(f"  Run: {run_id}")
    instance = getattr(result, 'run_instance', None) or {}
    started = instance.get('started_at')
    if started:
        lines.append(f"  Captured: {started}")
    return "\n".join(lines)
