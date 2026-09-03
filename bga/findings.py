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
from typing import Dict, List, Optional

from .cache_effectiveness import (
    HEALTHY_HIT_RATIO, POOR_HIT_RATIO, TRANSFER_SHARE_NOTABLE,
)
from .ingest.models import AnalysisResult
from .units import GIB

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
    ("local-optimizer", "R1",
     "I can change these elements",
     "Which element should I shorten first?"),
    ("recipe-author", "R2",
     "I own one element's recipe",
     "Is my element a problem, and what does changing it cost?"),
    ("graph-owner", "R3",
     "I own the dependency graph",
     "What does the shape of this graph make impossible?"),
    ("ci-gatekeeper", "R4",
     "I decide whether this build passes",
     "Is this number trustworthy, and is it normal?"),
    ("capacity-operator", "R5",
     "I own the machines it runs on",
     "What should the fleet be configured as?"),
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
    "optimization-horizon": "local-optimizer",
    "blast-radius-ranking": "local-optimizer",
    "certified-headroom": "local-optimizer",
    "wait-category": "local-optimizer",
    "execution-bound": "local-optimizer",
    # R2 - the cost of *their* element, and what a change to it reaches.
    "latent-heavies": "recipe-author",
    "blast-radius-reach": "recipe-author",
    "blast-radius-structural": "recipe-author",
    "shared-source-blast": "recipe-author",
    "cache-transfer-cost": "recipe-author",
    # R3 - the structural answers.
    "mesh-graph": "graph-owner",
    "chain-graph": "graph-owner",
    "graph-width": "graph-owner",
    "criticality": "graph-owner",
    # R4 - whether the number can be trusted and whether it is normal.
    "confidence": "ci-gatekeeper",
    "efficiency-score": "ci-gatekeeper",
    "cache-hit-ratio": "ci-gatekeeper",
    "run-mode-incremental": "ci-gatekeeper",
    # R5 - the fleet.
    "memory-envelope": "capacity-operator",
    "capacity-recommendation": "capacity-operator",
}

#: Rank order for choosing which of a reader's findings leads. Severity
#: first, then publication order, which is `compute_findings`' own
#: argued sequence - `UX-365` put the actions above the descriptions and
#: `UX-116` put capacity after the envelope it consumes, and neither
#: decision is re-litigated here.
_LEAD_ORDER = (SEVERITY_CRITICAL, SEVERITY_HIGH, SEVERITY_MEDIUM,
               SEVERITY_INFO)


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
    for action in ((headline or {}).get("top_actions") or []):
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
                key=lambda row: (_LEAD_ORDER.index(row[1].get("severity"))
                                 if row[1].get("severity") in _LEAD_ORDER
                                 else len(_LEAD_ORDER), row[0]))
            leads_with = lead.get("id")
        index.append({
            "id": uid,
            "role": role,
            "label": label,
            "question": question,
            "leads_with": leads_with,
            "findings": published,
        })
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
DIAGNOSIS_INCONCLUSIVE = 'inconclusive'
DIAGNOSES = (DIAGNOSIS_CHAIN_BOUND, DIAGNOSIS_SCHEDULER_BOUND,
             DIAGNOSIS_INCONCLUSIVE)

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
    DIAGNOSIS_CHAIN_BOUND:
        "This build is chain-bound, not scheduler-bound: the critical path "
        "is {ratio:.0%} of the time tasks were running, at or above the "
        "{bound:.0%} chain-bound line, so the way to a shorter build is a "
        "shorter chain.",
    DIAGNOSIS_SCHEDULER_BOUND:
        "This build is scheduler-bound, not chain-bound: the critical path "
        "is {ratio:.0%} of the time tasks were running, below the {bound:.0%} "
        "chain-bound line, so the time is going somewhere other than the "
        "chain.",
    DIAGNOSIS_INCONCLUSIVE:
        "Neither the chain nor the scheduler can be named the constraint: "
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
            "scheduling is near the certified floor for this graph - further "
            "gains need the graph or the work itself to change, not the "
            "scheduler (see Dispatch Occupancy and Critical Path)"
        )
    if score >= _EFFICIENCY_MEDIUM:
        return "worth checking Certified Headroom for real scheduling gains"
    return "significant scheduling headroom - see Certified Headroom below"


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


def heaviest_on_path(result) -> List[dict]:
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
        key=lambda d: -(d['realizable_saving_us']
                        if d.get('realizable_saving_us') is not None
                        else d['duration_us']),
    )


def path_elements_by_duration(result) -> List[dict]:
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


def _finding(
    id: str,
    severity: str,
    title: str,
    detail: Optional[List[str]] = None,
    elements: Optional[List[str]] = None,
    evidence: Optional[dict] = None,
) -> dict:
    return {
        'id': id,
        'severity': severity,
        'title': title,
        'detail': detail or [],
        'elements': elements or [],
        'evidence': evidence or {},
    }


def _cache_findings(result: AnalysisResult) -> List[dict]:
    """UX-92 stage 1: the cache's own numbers, as findings.

    Deliberately not gated on the hit ratio being *bad*. Every other
    signal in this report describes the work the build did; on an
    incremental build the cache decides how much work that was, so "the
    cache worked" is load-bearing context for reading the rest, not a
    finding that only matters when something is wrong. What the ratio
    changes is the severity and the sentence, not whether it appears.
    """
    cache = (result.signals or {}).get('cache') or {}
    hit_share = cache.get('hit_share')
    if hit_share is None:
        return []

    built = cache.get('built_elements')
    cached = cache.get('cached_elements')
    closure = cache.get('target_closure') or {}
    findings: List[dict] = []

    detail: List[str] = []
    if closure.get('hit_share') is not None and closure.get('targets'):
        detail.append(
            f"    -> for {', '.join(closure['targets'])}'s own closure it is "
            f"{closure['hit_share'] * 100:.0f}% "
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
        return [_finding(
            'cache-hit-ratio', SEVERITY_INFO,
            f"Caches off: all {built} element(s) built from source, none reused - "
            f"this is the nightly scenario, so a 0% hit ratio is the intent "
            f"rather than a finding",
            detail=detail,
            evidence={
                'hit_share': hit_share, 'built_elements': built,
                'cached_elements': cached, 'run_mode': 'full',
            },
        )]

    if hit_share < POOR_HIT_RATIO:
        severity, verdict = SEVERITY_HIGH, (
            "barely incremental - most of the project rebuilt. Look for a "
            "volatile cache key near the root before reading any efficiency "
            "number below: they describe how well this build ran, not how "
            "much of it should have run at all"
        )
    elif hit_share < HEALTHY_HIT_RATIO:
        severity, verdict = SEVERITY_MEDIUM, (
            "under half the project was reused - worth checking what "
            "invalidated the rest"
        )
    else:
        severity, verdict = SEVERITY_INFO, "the cache did most of the work"

    findings.append(_finding(
        'cache-hit-ratio', severity,
        f"Cache hit ratio: {hit_share * 100:.0f}% "
        f"({cached} cached, {built} rebuilt) - {verdict}",
        detail=detail,
        evidence={
            'hit_share': hit_share, 'built_elements': built,
            'cached_elements': cached,
            'target_closure_hit_share': closure.get('hit_share'),
        },
    ))

    share = cache.get('transfer_share')
    if share is not None and share >= TRANSFER_SHARE_NOTABLE:
        transfer = cache.get('transfer_us') or {}
        parts = ", ".join(
            f"{name.lower()} {us / 1e6:.1f}s" for name, us in sorted(transfer.items())
        )
        findings.append(_finding(
            'cache-transfer-cost', SEVERITY_MEDIUM,
            f"{share * 100:.0f}% of wall-clock was artifact transfer ({parts}) - "
            f"this build spent it moving artifacts rather than making them",
            evidence={'transfer_share': share, 'transfer_us': transfer},
        ))
    return findings


def _run_scope_findings(result: AnalysisResult) -> List[dict]:
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


def _run_blocking_findings(result: AnalysisResult) -> List[dict]:
    """`UX-54`: what makes every number below describe a different build."""
    findings: List[dict] = []
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
                f"THIS BUILD FAILED: {build_failed.get('failed_count')} element(s) "
                f"ended in FAILURE ({shown}) - every figure below describes a build "
                f"that did not complete, and the elements that failed contributed "
                f"only the time they ran before failing")
        elif build_failed.get('interrupted'):
            headline = (
                "THIS BUILD DID NOT FINISH: it was interrupted before it "
                "completed - every figure below describes a partial build")
        elif suspended:
            from .suspend import describe as _describe_suspension
            # No prefix: `describe` already opens with "This capture
            # spans a suspend", and the two together read as a stutter.
            headline = _describe_suspension(suspended)
        else:
            headline = (
                "THIS BUILD DID NOT FINISH - every figure below describes a "
                "build that did not complete")
        findings.append(_finding(
            'build-failed', SEVERITY_CRITICAL, headline,
            elements=list(failed),
            evidence={'failed_count': build_failed.get('failed_count'),
                      'interrupted': bool(build_failed.get('interrupted')),
                      'suspended': suspended},
        ))

    confidence = result.confidence or {}
    # UX-62: how much of the measured chain was work that was thrown
    # away. Attribution still counts it as EXECUTION_ON_CHAIN - moving it
    # would change `I4`'s identity - so this reports the waste instead of
    # silently reclassifying it.
    failed_us = confidence.get('failed_task_us') or 0
    if failed_us:
        failed_count = confidence.get('failed_task_count') or 0
        findings.append(_finding(
            'failed-task-time', SEVERITY_HIGH,
            f"{failed_count} failed task attempt(s) contributed "
            f"{failed_us / 1e6:.2f}s of EXECUTION_ON_CHAIN - real time the build "
            "spent producing nothing. Counted as execution, not as waste, because "
            "reclassifying it would move the attribution identity (I4)",
            evidence={'failed_task_us': failed_us, 'failed_task_count': failed_count},
        ))

    return findings


def _run_context_findings(result: AnalysisResult) -> List[dict]:
    """What this run *was* - mode, cache, confidence. Description rather
    than action, which is why `UX-365` stopped it opening the list."""
    findings: List[dict] = []
    confidence = result.confidence or {}
    # UX-55: which of the two CI scenarios this run is, said before the
    # numbers, because it changes what they are *about*.
    if confidence.get('run_mode') == 'incremental':
        cached = confidence.get('critical_path_cached') or []
        detail = f", {len(cached)} of them on the critical path" if cached else ""
        findings.append(_finding(
            'run-mode-incremental', SEVERITY_INFO,
            "Incremental run (caches on): BuildStream skipped elements it "
            f"had already built{detail}. Coverage and the floors below "
            "describe the work this run actually did, not the whole project - "
            "compare against another incremental run, not against a "
            "caches-off nightly",
            elements=list(cached),
            evidence={'run_mode': 'incremental', 'critical_path_cached': len(cached)},
        ))

    # UX-92: what the cache did, said next to the run mode it explains.
    # An incremental run's whole point is the cache, and until now the
    # report said "incremental" without ever saying how well that went.
    findings.extend(_cache_findings(result))

    primary = confidence.get('primary')
    if primary is not None:
        band = confidence_band(primary)
        violations = result.violations or []
        suffix = (
            f" - see {len(violations)} violation(s) below" if violations else ""
        )
        findings.append(_finding(
            'confidence', SEVERITY_INFO if band == 'high' else SEVERITY_MEDIUM,
            f"Confidence: {primary:.2f} ({band}){suffix}",
            evidence={'primary': primary, 'band': band,
                      'violation_count': len(violations)},
        ))
    return findings


def _time_concentration_findings(
    result: AnalysisResult, execution_bound: bool, chain_bound: bool,
) -> List[dict]:
    """UX-65 named where the time is; UX-76 made it one table.

    The tool already computes every number here; it simply never put them
    where a reader looks first.
    """
    heavy = path_elements_by_duration(result)
    if not heavy:
        return []
    path_us = sum(
        d.get('duration_us', 0)
        for d in ((result.signals or {}).get('critical_path_detail') or [])
    )
    if path_us <= 0:
        return []
    total = result.total_duration_us or 0
    top = heavy[:TIME_CONCENTRATION_SHOWN_MAX]
    share = sum(d['duration_us'] for d in top) / path_us
    verdict = " - this build is chain-bound, not scheduler-bound" if chain_bound else ""
    detail: List[str] = []
    width = max(len(d['element_uid']) for d in top)
    rows = []
    for d in top:
        saving = d.get('realizable_saving_us')
        worth = ""
        if saving is not None and total:
            worth = (
                f"  -> fixing it saves {saving / 1e6:.1f}s "
                f"({saving / total * 100:.1f}% of the build)"
            )
        detail.append(
            f"    {d['element_uid']:<{width}}  {d['duration_us'] / 1e6:8.1f}s "
            f"({d['duration_us'] / path_us * 100:4.1f}% of path){worth}"
        )
        rows.append({
            'element_uid': d['element_uid'],
            'duration_us': d['duration_us'],
            'share_of_path': d['duration_us'] / path_us,
            'realizable_saving_us': saving,
        })
    if execution_bound:
        detail.append(
            "    -> these elements must get faster, or come off the chain; "
            "the scheduler has no room left to give"
        )
    # UX-74 names the same elements in the same order *with* the makespan
    # each fix leaves behind, so this line would be a strictly weaker
    # duplicate whenever the horizon renders.
    fix_order = [
        d['element_uid'] for d in heaviest_on_path(result)[:FIX_ORDER_SHOWN_MAX]
        if d.get('realizable_saving_us')
    ]
    horizon_covers_it = len(
        (result.signals or {}).get('optimization_horizon') or []
    ) > 1
    if (
        fix_order
        and not horizon_covers_it
        and fix_order != [d['element_uid'] for d in top[:len(fix_order)]]
    ):
        detail.append(
            "    -> work them in this order (by what a fix is worth, which is "
            "not the order above): " + ", ".join(fix_order)
        )

    findings = [_finding(
        'time-concentration', SEVERITY_HIGH,
        f"Where the time is: {len(top)} element(s) are {share * 100:.1f}% of the "
        f"{path_us / 1e6:.1f}s critical path{verdict}",
        detail=detail,
        elements=[d['element_uid'] for d in top],
        evidence={'path_us': path_us, 'share_of_path': share,
                  'chain_bound': chain_bound, 'rows': rows},
    )]

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
            findings.append(_finding(
                'mesh-graph', SEVERITY_INFO,
                f"Note: {density:.0%} of elements have zero slack, "
                f"{off_path} of them off the critical path - this graph is "
                "a mesh of near-equal chains, so savings on one element are "
                "often capped by the next chain rather than by its own "
                "duration",
                evidence={'zero_slack_share': density,
                          'zero_slack_off_path': off_path},
            ))
        else:
            findings.append(_finding(
                'chain-graph', SEVERITY_INFO,
                f"Note: {density:.0%} of elements have zero slack, all on "
                "the critical path - no second chain of equal length, so a "
                "saving on any of them is worth its own duration",
                evidence={'zero_slack_share': density,
                          'zero_slack_off_path': 0},
            ))
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
    on_path = {row.get('element_uid')
               for row in (signals.get('critical_path_detail') or [])}
    return sum(1 for uid, value in slack.items()
               if value == 0 and uid not in on_path)



def _graph_shape_findings(result: AnalysisResult) -> List[dict]:
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
    the elements by depth and you have the dependency stages: nothing
    in a stage can start before the stage above it finishes, whatever
    the capacity, so the widest stage is a **ceiling on concurrency
    that no number of builders can lift**. That is the shape making
    something impossible, stated as the number it is.

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
    return [_finding(
        'graph-width', SEVERITY_INFO,
        f"The graph is {len(depth)} elements in {stages} dependency "
        f"stages, and its widest stage holds {widest} - so no more than "
        f"{widest} can ever be building at once, whatever the capacity",
        evidence={'element_count': len(depth),
                  'dependency_stages': stages,
                  'widest_stage': widest},
    )]


def _memory_envelope_findings(result: AnalysisResult) -> List[str]:
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
        f"({at_observed['share_of_host'] * 100:.0f}%)"
    )
    ceiling = envelope.get('first_builders_that_does_not_fit')
    if ceiling:
        line += f"; {ceiling} would not fit"
    else:
        higher = [
            p for p in envelope['projections']
            if p['builders'] > at_observed['builders']
        ]
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
        f"do NOT raise --builders on this host - measured per-element peaks put "
        f"{ceiling} builders at ~{next(p['envelope_bytes'] for p in envelope['projections'] if p['builders'] == ceiling) / GIB:.1f} GB "
        f"against {envelope['host_memory_bytes'] / GIB:.1f} GB of RAM, so the extra "
        f"builder would swap. Swapping is the worst build slowdown there is and no "
        f"CPU-side signal predicts it (UX-104)"
    )


def _shared_source_findings(result: AnalysisResult) -> List[dict]:
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
    return [_finding(
        'shared-source-blast', SEVERITY_MEDIUM, f"Shared source: {headline}",
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
    )]


def _memory_finding(result: AnalysisResult) -> List[dict]:
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
        SEVERITY_HIGH if not at_observed['fits']
        else SEVERITY_MEDIUM if ceiling == at_observed['builders'] + 1
        else SEVERITY_INFO
    )
    return [_finding(
        'memory-envelope', severity, f"Memory: {lines[0]}",
        evidence={
            'builders': at_observed['builders'],
            'envelope_bytes': at_observed['envelope_bytes'],
            'host_memory_bytes': envelope['host_memory_bytes'],
            'share_of_host': at_observed['share_of_host'],
            'fits': at_observed['fits'],
            'first_builders_that_does_not_fit': ceiling,
            'elements_measured': envelope['elements_measured'],
        },
    )]


def _capacity_recommendation_finding(result: AnalysisResult) -> List[dict]:
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
            f"{binding} binds first, at {recommended} - nothing measured here "
            f"rules out {recommended - builders} more builder(s), which is a "
            f"hypothesis to time rather than a setting to apply"
        )
        severity = SEVERITY_MEDIUM
    elif recommended < builders:
        verdict = (
            f"{binding} binds at {recommended}, below the {builders} configured - "
            f"more builders contend rather than overlap here"
        )
        severity = SEVERITY_HIGH
    else:
        verdict = (
            f"{binding} binds at exactly {recommended} - this run is already at "
            f"the setting its own measurements support"
        )
        severity = SEVERITY_INFO

    detail = [
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
        detail.append(
            "    Free capacity you already have: "
            + ", ".join(pinned[:3])
            + " asked its native build for -j1 - a builder slot drawing one core. "
              "Fix that before raising anything, then re-measure."
        )
    if recommended > builders:
        detail.append(
            "    Time it before keeping it: the knee is a scheduling answer and "
            "cores-busy is a whole-run average, so both overstate what a "
            "contended window can absorb."
        )
    detail.append(f"    {recommendation['caveat']}")

    return [_finding(
        'capacity-recommendation', severity,
        f"Capacity: {setting} on {recommendation['host_cpu_count']} core(s): {verdict}",
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
        },
    )]


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
        if cores_busy is not None and host else None
    )
    if pinned:
        # Named first: intra-element parallelism is free capacity that
        # `--builders` is not, and it costs nothing to reclaim.
        names = ", ".join(pinned[:3])
        lead = (
            f"do NOT raise capacity - {measured}. " if plane2.get('saturated') and measured
            else ""
        )
        return (
            f"{lead}{names} asked its native build for -j1 while the rest of this "
            f"build asked for more: remove `notparallel` / raise that element's job "
            f"count first. That is capacity you already have, and unlike --builders "
            f"it cannot contend with itself (UX-83)"
        )
    if plane2.get('saturated') and measured:
        return (
            f"do NOT raise capacity on this host - {measured}, so another builder "
            f"would contend for CPU rather than add throughput. The wait is real; "
            f"the remedy is less work or better intra-element parallelism, not more "
            f"concurrent elements (UX-83)"
        )
    return None


def _opportunity_findings(result: AnalysisResult, chain_bound: bool) -> List[dict]:
    attribution = result.attribution or {}
    total = result.total_duration_us
    non_execution = {
        k: v for k, v in attribution.items() if k != 'execution_on_chain_us'
    }
    if not non_execution or not total or total <= 0:
        return []
    top_category, top_duration_us = max(non_execution.items(), key=lambda kv: kv[1])
    pct = top_duration_us / total * 100 if top_duration_us > 0 else 0.0
    # UX-65: when nothing meaningful went anywhere other than useful
    # work, "the largest of the remaining 0.1%" is not the answer.
    if pct < OPPORTUNITY_FLOOR_PCT:
        concentration = _time_concentration_findings(
            result, execution_bound=True, chain_bound=chain_bound,
        )
        if not concentration:
            return []
        return [_finding(
            'execution-bound', SEVERITY_HIGH,
            f"Biggest wait category: this build is execution-bound - "
            f"no wait category exceeds {OPPORTUNITY_FLOOR_PCT:.0f}% of "
            f"wall-clock time, so there is no scheduling gap to close",
            evidence={'largest_wait_category': top_category,
                      'largest_wait_share': pct / 100},
        )] + concentration
    if top_duration_us <= 0:
        return []
    label = top_category.replace('_us', '').replace('_', ' ').upper()
    # UX-04/UX-35: what the category means and what to do about it,
    # conditioned on this run's own capacity verdict. Imported here
    # rather than at module scope: `bga.report` imports this module, so a
    # top-level import back into it is a cycle.
    from .report._shared import resolve_attribution_hint

    hint = resolve_attribution_hint(
        top_category, getattr(result, 'capacity_verdict', None),
    )
    # UX-83: and conditioned on Plane 2, when Plane 2 is in hand. The
    # static RESOURCE WAIT hint says "try --capacity N with a higher N",
    # which on a measured-saturated host is the opposite of the fix - and
    # on one real dual-plane capture the tool said exactly that while its
    # own `correlate` output named a pinned element worth -32.4%.
    plane2_hint = _plane2_capacity_hint(result, top_category)
    if plane2_hint:
        hint = plane2_hint
    return [_finding(
        'wait-category', SEVERITY_HIGH,
        # `UX-365`: **which** biggest. This is the largest of the
        # non-execution wait categories - a real superlative over a real
        # population - and it used to read "Biggest Opportunity", which
        # is a claim about every finding in the report. On `macro_micro`
        # it named 2.72s while `joint-saving` three rows below was worth
        # 23.1s and claimed nothing. Naming the population is the whole
        # fix: the measurement was never wrong, the scope was.
        f"Biggest wait category: {pct:.1f}% of wall-clock time is "
        f"{label} ({top_duration_us / 1e6:.2f}s)",
        detail=[f"    -> {hint}"] if hint else None,
        evidence={'category': top_category, 'category_us': top_duration_us,
                  'share': pct / 100, 'hint': hint},
    )]


def _outlook_findings(result: AnalysisResult) -> List[dict]:
    """UX-74: what to do after the first fix, what the set is worth
    together, and what is waiting off the path."""
    signals = result.signals or {}
    total = result.total_duration_us or 0
    findings: List[dict] = []

    joint = signals.get('joint_saving')
    if joint and joint.get('joint_saving_us') and total:
        joint_us = joint['joint_saving_us']
        sum_us = joint.get('sum_of_individual_us') or 0
        if joint.get('savings_add'):
            relation = (
                "exactly the sum of their individual savings, so they are three "
                "separate pieces of work that do not overlap"
            )
        else:
            relation = (
                f"less than the {sum_us / 1e6:.1f}s their individual savings add up "
                f"to - fixing one makes the others worth less"
            )
        findings.append(_finding(
            'joint-saving', SEVERITY_HIGH,
            f"Together, the top {len(joint['elements'])} are worth "
            f"{joint_us / 1e6:.1f}s ({joint_us / total * 100:.0f}% of the build) - "
            f"{relation}",
            elements=list(joint['elements']),
            evidence={'joint_saving_us': joint_us, 'sum_of_individual_us': sum_us,
                      'savings_add': joint.get('savings_add')},
        ))

    horizon = signals.get('optimization_horizon') or []
    if len(horizon) > 1:
        shown = horizon[:HORIZON_STEPS_SHOWN]
        steps = " -> ".join(
            f"{step['element_uid']} ({step['makespan_after_us'] / 1e6:.0f}s)"
            for step in shown
        )
        last = shown[-1]
        detail = []
        if total:
            detail.append(
                f"    - the last of those leaves "
                f"{last['cumulative_saving_us'] / total * 100:.0f}% of the build "
                f"removed, projected from this run without building again"
            )
        findings.append(_finding(
            'optimization-horizon', SEVERITY_HIGH,
            f"Work them in this order (by what a fix is worth, not by size), "
            f"with what the build drops to: {steps}",
            detail=detail,
            elements=[step['element_uid'] for step in shown],
            evidence={'steps': shown},
        ))

    latent = signals.get('latent_heavies') or []
    if latent:
        shown = latent[:LATENT_HEAVIES_SHOWN]
        named = ", ".join(
            f"{e['element_uid']} ({e['duration_us'] / 1e6:.0f}s)" for e in shown
        )
        more = f" (+{len(latent) - len(shown)} more)" if len(latent) > len(shown) else ""
        findings.append(_finding(
            'latent-heavies', SEVERITY_MEDIUM,
            f"Waiting off the critical path, worth nothing to fix today: "
            f"{named}{more} - they bound how far shortening the chain can go",
            elements=[e['element_uid'] for e in shown],
            evidence={'latent_heavies': latent},
        ))

    if findings:
        findings[-1]['detail'] = list(findings[-1]['detail']) + [
            "    (structural projections over this run's measured durations, where "
            "\"fixed\" means the element becomes instant - a re-capture is still "
            "the ground truth)"
        ]
    return findings


def _ranking_findings(result: AnalysisResult, chain_bound: bool) -> List[dict]:
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
    structural = [u for u in top_blast_radius
                  if (blast_radius.get(u) or {}).get('is_structural_kind')]
    actionable = [u for u in top_blast_radius
                  if not (blast_radius.get(u) or {}).get('is_structural_kind')]

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
    reaching = [u for u in actionable
                if ((blast_radius.get(u) or {}).get('downstream_count') or 0) > 0]

    findings = []
    shown = [] if chain_bound else reaching[:BLAST_RADIUS_SHOWN]
    if shown:
        detail = []
        for i, elem_uid in enumerate(shown, start=1):
            entry = blast_radius.get(elem_uid, {})
            count = entry.get('downstream_count', 0)
            detail.append(
                f"    {i}. {elem_uid} ({count} downstream elements"
                f"{_blast_scale(count, distribution)})"
                f"{structural_kind_tag(entry)}"
            )
        tie = _indistinguishable(shown, blast_radius, distribution)
        if tie:
            detail.append(f"    {tie}")
        if distribution:
            detail.append(f"    {_density_sentence(distribution)}")
        findings.append(_finding(
            'blast-radius-ranking', SEVERITY_MEDIUM,
            "Elements Most Worth Optimizing First (by blast radius):",
            detail=detail, elements=list(shown),
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
            evidence=({'blast_radius_distribution': distribution}
                      if distribution else {}),
        ))

    # `UX-479`: what a change to one of these rebuilds - the
    # recipe-author's own question, published on either arm because it
    # is not a ranking and does not compete with `time-concentration`
    # for the same screen. It reads the same `reaching` list as the
    # ranking above, so `shown` is a subset of it and `not shown` still
    # separates the two arms exactly.
    if reaching and not shown:
        named = ", ".join(
            f"{u} ({(blast_radius.get(u) or {}).get('downstream_count')} "
            f"downstream)"
            for u in reaching[:BLAST_RADIUS_SHOWN])
        findings.append(_finding(
            'blast-radius-reach', SEVERITY_MEDIUM,
            f"What a change to these rebuilds: {named} - the cost of "
            f"touching them is not their own duration but everything "
            f"downstream that has to be built again",
            elements=list(reaching[:BLAST_RADIUS_SHOWN]),
        ))

    if structural:
        # Reported, with the number, as the graph's shape.
        named = ", ".join(
            f"{u} ({(blast_radius.get(u) or {}).get('downstream_count', 0)} downstream)"
            for u in structural[:BLAST_RADIUS_SHOWN])
        findings.append(_finding(
            'blast-radius-structural', SEVERITY_INFO,
            f"Reaching most of the graph by design: {named} - structural "
            f"elements ({', '.join(sorted({(blast_radius.get(u) or {}).get('element_kind', 'unknown') for u in structural}))}) "
            f"whose dependents are the graph's shape, not a task",
            elements=list(structural[:BLAST_RADIUS_SHOWN]),
        ))
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
    return (f"these {len(counts)} are within {spread * 100:.0f}% of each other "
            f"- the order between them is not a difference worth acting on")


def _density_sentence(distribution):
    """The graph's shape in one line, rather than a chart (`UX-196`)."""
    deciles = distribution.get('deciles') or {}
    median, ninety = deciles.get('p50'), deciles.get('p90')
    if median is None or ninety is None:
        return ""
    return (f"Shape: half of this run's {distribution['n']} elements reach "
            f"{median} or fewer, the top tenth reach {ninety} or more "
            f"(max {distribution['max']})")


def _criticality_findings(result: AnalysisResult) -> List[dict]:
    criticality = (result.signals or {}).get('criticality_probability') or {}
    if not criticality:
        return []
    # UX-76: structural elements are excluded rather than annotated here,
    # and a list where every entry scores 1.0 - the ordinary shape of a
    # deterministic replay - ranks nothing and is dropped.
    nonzero = sorted(
        (
            item for item in criticality.items()
            if item[1].get('probability', 0) > 0
            and not item[1].get('is_structural_kind')
        ),
        key=lambda kv: kv[1].get('probability', 0), reverse=True,
    )[:CRITICALITY_SHOWN]
    if not nonzero or all(d.get('probability', 0) >= 1.0 for _u, d in nonzero):
        return []
    detail = [
        f"    {i}. {uid} ({data.get('probability', 0) * 100:.0f}% probability of "
        f"being on critical path){structural_kind_tag(data)}"
        for i, (uid, data) in enumerate(nonzero, start=1)
    ]
    return [_finding(
        'criticality', SEVERITY_INFO,
        "Highest Criticality Elements:",
        detail=detail, elements=[uid for uid, _d in nonzero],
        evidence={'criticality_probability': dict(nonzero)},
    )]


def _floor_findings(result: AnalysisResult) -> List[dict]:
    floors = result.floors or {}
    findings: List[dict] = []
    t_inf = floors.get('t_infinity_observed') or floors.get('t_infinity_observed_us', 0)
    lb_val = floors.get('lb') or floors.get('lb_us', 0)
    headroom = floors.get('certified_headroom') or floors.get('certified_headroom_us', 0)
    if headroom > 0:
        findings.append(_finding(
            'certified-headroom', SEVERITY_MEDIUM,
            f"Certified Headroom: up to {headroom / 1e6:.2f}s available "
            f"(T∞={t_inf / 1e6:.2f}s, LB={lb_val / 1e6:.2f}s)",
            evidence={'certified_headroom_us': headroom, 't_infinity_us': t_inf,
                      'lb_us': lb_val},
        ))
    # UX-02: never presented alone without the "not work-minimality"
    # caveat, and gated on confidence - low-confidence input gets an
    # explicit caveat rather than false precision.
    efficiency_score = floors.get('efficiency_score')
    if efficiency_score is not None:
        band = efficiency_band(efficiency_score)
        primary = (result.confidence or {}).get('primary')
        caveat = ""
        if primary is not None and primary < _CONFIDENCE_HIGH:
            caveat = " - low-confidence data, treat with caution"
        findings.append(_finding(
            'efficiency-score', SEVERITY_INFO,
            f"Efficiency Score: {efficiency_score:.2f} ({band}){caveat}",
            evidence={'efficiency_score': efficiency_score,
                      'low_confidence': bool(caveat)},
        ))
    return findings


def compute_findings(result: AnalysisResult) -> List[dict]:
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
    concentration_emitted = any(
        f['id'] == 'time-concentration' for f in opportunity
    )
    if chain_bound and heaviest_on_path(result):
        # UX-76: one table, not a second ranking of the same names.
        if not concentration_emitted:
            concentration = _time_concentration_findings(
                result, execution_bound=False, chain_bound=True,
            )
            findings.extend(concentration)
            concentration_emitted = bool(concentration)
    # `UX-479`: outside the branch. Reach is not the concentration
    # ranking's competitor - `_ranking_findings` gates the one claim
    # that competes and publishes the other two either way.
    findings.extend(_ranking_findings(result, chain_bound))
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
    findings.extend(_criticality_findings(result))
    findings.extend(_floor_findings(result))
    # UX-171: last, because it is a fact about the project's shape
    # rather than about this run - the reader has met the run's own
    # numbers by the time they reach "and one repo rebuilds all of it".
    findings.extend(_shared_source_findings(result))
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
        return {'diagnosis': DIAGNOSIS_INCONCLUSIVE, 'chain_share': None,
                'chain_bound_share': CHAIN_BOUND_RATIO,
                'chain_share_of': None,
                'sentence': DIAGNOSIS_SENTENCES[DIAGNOSIS_INCONCLUSIVE]}
    against, source = _diagnosis_denominator(result, total)
    ratio = t_infinity / against
    name = (DIAGNOSIS_CHAIN_BOUND if ratio >= CHAIN_BOUND_RATIO
            else DIAGNOSIS_SCHEDULER_BOUND)
    return {'diagnosis': name, 'chain_share': ratio,
            'chain_bound_share': CHAIN_BOUND_RATIO,
            'chain_share_of': source,
            'sentence': DIAGNOSIS_SENTENCES[name].format(
                ratio=ratio, bound=CHAIN_BOUND_RATIO)}


def _top_actions(result: AnalysisResult, findings: List[dict]) -> List[dict]:
    """Ordered references into the findings that already rank things.

    References, not copies: `finding_id` says where the reasoning is, so
    the panel can send a reader to it rather than restating it. The
    saving is carried where a projection exists and omitted where none
    does - `None` would read as "zero", which is a different claim.
    """
    by_id = findings_by_id(findings)
    actions: List[dict] = []

    concentration = by_id.get('time-concentration')
    for row in ((concentration or {}).get('evidence') or {}).get('rows') or []:
        action = {'finding_id': 'time-concentration',
                  'element_uid': row['element_uid']}
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
            actions.append({
                'finding_id': 'blast-radius-ranking', 'element_uid': uid,
                'downstream_count': (blast.get(uid) or {}).get(
                    'downstream_count', 0),
            })
    return actions[:TOP_ACTIONS_SHOWN]


def compute_headline(result: AnalysisResult,
                     findings: Optional[List[dict]] = None) -> dict:
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
    headline['scheduling_gap_us'] = (
        max(0, total - t_infinity) if total and t_infinity else None)
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
        return "nothing" if not count else f"{count} others"

    half = (f"Half of this graph's {shape['n']} elements reach "
            f"{reach(median)}" + ("" if not median else " or fewer"))
    tenth = (f"the top tenth reach {reach(top)}"
             + ("" if not top else " or more")
             + f", up to {biggest}")
    # Concentration is `max` against the top decile, not the top decile
    # against the median: in a star-shaped graph both of those are zero
    # and the first draft of this sentence called the most concentrated
    # shape there is "spread across many elements".
    concentrated = biggest >= 10 * max(1, top)
    return (
        f"{half}; {tenth}. "
        + ("Reach is concentrated in a few elements - most of this graph "
           "cannot cause a wide rebuild."
           if concentrated else
           "Reach is spread across many elements - there is no single "
           "choke point to fix."))


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
    if len(parts) < 5 or parts[-1] != 'run' or parts[-3] != 'runs' \
            or parts[-4] != '.bga':
        return None, False
    return os.sep.join(parts[:-4]) or '.', True


def _store_run_modes(project: str) -> List[tuple]:
    """`(stamp, run_mode)` per run in the store, oldest first.

    `UX-577`: whether `bga compare @prev @last` is a command or a
    refusal is a fact about the store, not about this run, so it is
    read here rather than baked into the run document. One
    `run-context.json` per snapshot - the read `UX-296` chose for a
    band sample, no trace parse - and an unreadable store yields `[]`.
    """
    from . import run_store
    from .ingest.loader import load_run_context

    modes: List[tuple] = []
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
    detail = (getattr(result, 'signals', None) or {}).get(
        'critical_path_detail') or []
    entries = [e for e in detail if e.get('element_uid')
               and e.get('duration_us')]
    if not entries:
        return None
    return max(entries, key=lambda e: e['duration_us'])


def compute_next_steps(result: AnalysisResult,
                       headline: Optional[dict] = None) -> List[dict]:
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
    actions = headline.get('top_actions') or []
    top = actions[0] if actions else None
    steps: List[dict] = []

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
        steps.append({
            'id': 'shorten-what-the-build-waits-for',
            'reason': (
                f"{longest['element_uid']} is the longest thing on the "
                f"critical path"
                # Same rule the two steps below use: a figure that
                # rounds to "0.0s" argues against the sentence carrying
                # it. The golden run's longest element is 6ms.
                + (f" at {longest['duration_us'] / 1e6:.1f}s"
                   if (longest.get('duration_us') or 0) >= 100_000 else "")
                + (f", {share * 100:.0f}% of it" if share else "")
                + " - the build cannot finish sooner than this chain."),
            'argv': ['bga', 'blast', longest['element_uid'], run_dir],
            'follows_from': 'critical_path_detail',
        })

    if top and top.get('element_uid'):
        uid = top['element_uid']
        worth = top.get('saving_us')
        steps.append({
            'id': 'blast-the-top-element',
            'reason': (
                f"{uid} is the first thing to fix"
                # Same rule as the gap below: a figure that rounds to
                # "0.0s" argues against the sentence carrying it.
                + (f", worth {worth / 1e6:.1f}s"
                   if worth and worth >= 100_000 else "")
                + " - this is what changing it rebuilds."),
            'argv': ['bga', 'blast', uid, run_dir],
            'follows_from': top.get('finding_id') or 'headline.top_actions',
        })
        # The two-plane join answers "compute-bound, or badly built",
        # and only where Plane 2 saw this run - `plane2_coverage` being
        # published is exactly that condition.
        if getattr(result, 'plane2_coverage', None):
            steps.append({
                'id': 'look-inside-the-element',
                'reason': (
                    f"Plane 2 measured this run, so the join can say "
                    f"whether {uid} is compute-bound or under-parallelized."),
                'argv': ['bga', 'correlate', run_dir],
                'follows_from': 'plane2_coverage',
            })

    if headline.get('diagnosis') == DIAGNOSIS_SCHEDULER_BOUND:
        gap = headline.get('scheduling_gap_us')
        steps.append({
            'id': 'sweep-the-capacity',
            'reason': (
                "This build is scheduler-bound"
                # Only where the number would say something: a gap that
                # rounds to "0.0s" reads as a contradiction of the
                # sentence it is supposed to support.
                + (f": {gap / 1e6:.1f}s of wall-clock is beyond the critical "
                   f"path" if gap and gap >= 100_000 else "")
                + " - the sweep says what more builders would buy."),
            'argv': ['bga', 'sweep', run_dir],
            'follows_from': 'headline.diagnosis',
        })

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
            steps.append({
                'id': 'measure-again',
                'reason': "Make the change, then capture it the same way.",
                'argv': ['bga', 'snapshot', '--project', project, '--',
                         'bst', 'build', *targets],
                'follows_from': 'run_instance.targets',
            })
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
            steps.append({
                'id': 'compare-with-the-run-before',
                'reason': ("Whether it helped, judged against this store's "
                           f"noise - run it in {project}."),
                'argv': ['bga', 'compare', '@prev', '@last'],
                'follows_from': 'run_instance.run_dir',
            })
        else:
            prev_mode, last_mode, stamp = refused
            # No run of the candidate's own mode means no pair exists;
            # `measure-again` above is the step that makes one.
            if stamp:
                steps.append({
                    'id': 'compare-with-a-run-that-pairs',
                    'reason': (
                        f"@prev is a {prev_mode} run and @last a {last_mode} "
                        f"one, which compare refuses - {stamp} is the newest "
                        f"{last_mode} run and pairs with it. Run it in "
                        f"{project}."),
                    'argv': ['bga', 'compare', f'@{stamp}', '@last'],
                    'follows_from': 'confidence.run_mode',
                })
    return steps


def render_findings(findings: List[dict]) -> List[str]:
    """The text form: a title line per finding, plus its own detail lines.

    Detail lines carry their own indentation because they are tables and
    sub-rankings whose alignment is part of their meaning; titles are
    indented uniformly here.
    """
    lines: List[str] = []
    for finding in findings:
        lines.append(f"{finding.get('indent', '  ')}{finding['title']}")
        lines.extend(finding.get('detail') or [])
    return lines


def findings_by_id(findings: List[dict]) -> Dict[str, dict]:
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
        return f"{label} {value / 1e6:.1f}s"
    if quantity == "share" and isinstance(value, (int, float)):
        return f"{label} {value * 100:.0f}%"
    if quantity == "percent" and isinstance(value, (int, float)):
        return f"{label} {value:.1f}%"
    if quantity == "megabytes" and isinstance(value, (int, float)):
        return f"{label} {value:.0f} MB"
    if quantity == "seconds" and isinstance(value, (int, float)):
        return f"{label} {value:.1f}s"
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
    for step in (next_steps or []):
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
