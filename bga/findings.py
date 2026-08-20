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
from typing import Dict, List, Optional

from .cache_effectiveness import (
    HEALTHY_HIT_RATIO, POOR_HIT_RATIO, TRANSFER_SHARE_NOTABLE,
)
from .ingest.models import AnalysisResult

# Severity is about what it means for the reader, not about size:
#   critical - the run itself is not what it appears to be
#   high     - a real opportunity or a real problem to act on
#   medium   - worth reading, secondary to the above
#   info     - scoping and context; changes how to read the rest
SEVERITY_CRITICAL = "critical"
SEVERITY_HIGH = "high"
SEVERITY_MEDIUM = "medium"
SEVERITY_INFO = "info"

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
    hit_ratio = cache.get('hit_ratio')
    if hit_ratio is None:
        return []

    built = cache.get('built_elements')
    cached = cache.get('cached_elements')
    closure = cache.get('target_closure') or {}
    findings: List[dict] = []

    detail: List[str] = []
    if closure.get('hit_ratio') is not None and closure.get('targets'):
        detail.append(
            f"    -> for {', '.join(closure['targets'])}'s own closure it is "
            f"{closure['hit_ratio'] * 100:.0f}% "
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
                'hit_ratio': hit_ratio, 'built_elements': built,
                'cached_elements': cached, 'run_mode': 'full',
            },
        )]

    if hit_ratio < POOR_HIT_RATIO:
        severity, verdict = SEVERITY_HIGH, (
            "barely incremental - most of the project rebuilt. Look for a "
            "volatile cache key near the root before reading any efficiency "
            "number below: they describe how well this build ran, not how "
            "much of it should have run at all"
        )
    elif hit_ratio < HEALTHY_HIT_RATIO:
        severity, verdict = SEVERITY_MEDIUM, (
            "under half the project was reused - worth checking what "
            "invalidated the rest"
        )
    else:
        severity, verdict = SEVERITY_INFO, "the cache did most of the work"

    findings.append(_finding(
        'cache-hit-ratio', severity,
        f"Cache hit ratio: {hit_ratio * 100:.0f}% "
        f"({cached} cached, {built} rebuilt) - {verdict}",
        detail=detail,
        evidence={
            'hit_ratio': hit_ratio, 'built_elements': built,
            'cached_elements': cached,
            'target_closure_hit_ratio': closure.get('hit_ratio'),
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
        findings.append(_finding(
            'build-failed', SEVERITY_CRITICAL,
            f"THIS BUILD FAILED: {build_failed.get('failed_count')} element(s) "
            f"ended in FAILURE ({shown}) - every figure below describes a build "
            f"that did not complete, and the elements that failed contributed "
            f"only the time they ran before failing",
            elements=list(failed),
            evidence={'failed_count': build_failed.get('failed_count')},
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
    density = (result.signals or {}).get('zero_slack_share')
    if density is not None and density >= 0.5:
        findings.append(_finding(
            'mesh-graph', SEVERITY_INFO,
            f"Note: {density:.0%} of elements have zero slack - this graph "
            "is a mesh of near-equal chains, so savings on one element are "
            "often capped by the next chain rather than by its own duration",
            evidence={'zero_slack_share': density},
        ))
        # Rendered inside the table it qualifies, where it has always been.
        findings[-1]['indent'] = '    '
    return findings


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
    host_gb = envelope['host_memory_mb'] / 1024
    line = (
        f"{at_observed['builders']} builders of this shape peak at "
        f"~{at_observed['envelope_mb'] / 1024:.1f} GB of {host_gb:.1f} GB "
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
                f"~{higher[-1]['envelope_mb'] / 1024:.1f} GB, so memory is not what "
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
        f"{ceiling} builders at ~{next(p['envelope_mb'] for p in envelope['projections'] if p['builders'] == ceiling) / 1024:.1f} GB "
        f"against {envelope['host_memory_mb'] / 1024:.1f} GB of RAM, so the extra "
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
            'measured_seconds': top.get('measured_seconds'),
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
            'envelope_mb': at_observed['envelope_mb'],
            'host_memory_mb': envelope['host_memory_mb'],
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
            'change': recommendation['change'],
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
            f"Biggest Opportunity: this build is execution-bound - "
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
        f"Biggest Opportunity: {pct:.1f}% of wall-clock time is "
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
    signals = result.signals or {}
    top_blast_radius = signals.get('top_blast_radius') or []
    if chain_bound or not top_blast_radius:
        return []
    # UX-65: blast radius answers "who depends on me", which is the right
    # question when the *graph* constrains the build, not when the chain
    # does.
    blast_radius = signals.get('blast_radius') or {}
    shown = top_blast_radius[:BLAST_RADIUS_SHOWN]
    detail = []
    for i, elem_uid in enumerate(shown, start=1):
        entry = blast_radius.get(elem_uid, {})
        count = entry.get('downstream_count', 0)
        detail.append(
            f"    {i}. {elem_uid} ({count} downstream elements)"
            f"{structural_kind_tag(entry)}"
        )
    return [_finding(
        'blast-radius-ranking', SEVERITY_MEDIUM,
        "Elements Most Worth Optimizing First (by blast radius):",
        detail=detail, elements=list(shown),
        evidence={'blast_radius': {u: blast_radius.get(u, {}) for u in shown}},
    )]


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
    floors = result.floors or {}
    total = result.total_duration_us
    t_infinity = floors.get('t_infinity_observed') or 0
    # `chain_bound` asks whether the chain or the scheduler is what binds;
    # `execution_bound` asks whether any wait category is large enough to
    # be worth naming. Different questions, and a real build is routinely
    # both.
    chain_bound = bool(total) and t_infinity / total >= CHAIN_BOUND_RATIO

    findings = _run_scope_findings(result)
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
    else:
        findings.extend(_ranking_findings(result, chain_bound))
    if concentration_emitted:
        findings.extend(_outlook_findings(result))
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
    return findings


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
