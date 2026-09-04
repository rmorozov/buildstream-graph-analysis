"""UX-115: the artifact a reviewer actually reads.

`docs/design/directions.md` has carried a sketch of "what a good CI
comment should look like" since round 1. Every ingredient it names now
exists and is verified — the band verdict (`UX-59`/`UX-96`), both
whole-build gates (`UX-39`), the marginal gate and the new/changed
element diff (`UX-79`), cache churn (`UX-92`/`UX-93`), the run instance
(`UX-95`), never-read dependency edges from Plane 2 (`UX-46`). What did
not exist is the last inch: a CI owner got exit codes and a JSON blob,
and the sketch stayed a sketch.

The distinction this module is built on: **a gate that fails with a wall
of JSON gets its threshold loosened; a gate that fails by naming the
element gets the element fixed.**

Render-only, and strictly so. Every number here is read from a
`ComparisonResult` that was already computed, and every verdict is taken
from the same predicate `bga compare`'s exit code calls — never
recomputed from a threshold spelled out a second time. If this file and
the exit code ever disagree, that is a bug in this file.
"""
from typing import List, Optional

from ..compare import (
    DEFAULT_MAX_ADDITION_STRETCH, efficiency_below_floor,
    efficiency_regression_exceeds_threshold, regression_exceeds_threshold,
)

# The handle a CI job greps for to decide between editing its existing
# comment and posting a new one. Stable across versions by contract: a
# marker that moved would orphan every comment already posted, and the
# pipeline would start appending instead of updating.
MARKER = "<!-- bga-ci-comment -->"

# How many added elements the table lists before collapsing the rest into
# a count. A comment is read in a PR sidebar, and a 200-row table is a
# scroll, not a finding.
_MAX_ROWS = 8


def _s(value_us: Optional[float]) -> str:
    if value_us is None:
        return "n/a"
    return f"{value_us / 1e6:.1f}s"


def _signed_s(value_us: Optional[float]) -> str:
    if value_us is None:
        return "n/a"
    return f"{'+' if value_us >= 0 else '-'}{abs(value_us) / 1e6:.1f}s"


def _pct_points(delta: Optional[float]) -> str:
    if delta is None:
        return "n/a"
    return f"{'+' if delta >= 0 else '-'}{abs(delta) * 100:.1f}pp"


def _gate_rows(comparison, args) -> List[dict]:
    """One row per gate, in the order `_compare_exit_code` evaluates them.

    A gate the invocation did not ask for is reported as **not
    requested** rather than omitted, and a gate that could not run as
    **not applied**. Neither is a pass, and a comment that quietly showed
    only the gates that fired would read as a clean bill of health from a
    pipeline that checked nothing — the exact failure `UX-87` recorded
    against the efficiency gate itself.
    """
    rows: List[dict] = []

    marginal_on = getattr(args, 'fail_on_inefficient_additions', False)
    marginal = getattr(comparison, 'marginal_efficiency', None)
    limit = getattr(args, 'max_addition_stretch', None) or DEFAULT_MAX_ADDITION_STRETCH
    if not marginal_on:
        rows.append({'gate': 'Marginal efficiency', 'status': 'not requested',
                     'why': '`--fail-on-inefficient-additions` not passed'})
    elif marginal is None:
        rows.append({
            'gate': 'Marginal efficiency', 'status': 'not applied',
            'why': 'this change added no elements with measured work, so there is '
                   'nothing to judge — an empty check, not a pass',
        })
    elif marginal['stretch'] > limit:
        rows.append({
            'gate': 'Marginal efficiency', 'status': 'FAIL',
            'why': f"{_s(marginal['added_critical_path_us'])} of the "
                   f"{_s(marginal['added_work_us'])} this change added landed on the "
                   f"critical path (stretch {marginal['stretch']:.2f} > {limit:.2f})",
        })
    else:
        rows.append({
            'gate': 'Marginal efficiency', 'status': 'pass',
            'why': f"{_s(marginal['added_work_us'])} added, "
                   f"{_s(marginal['added_critical_path_us'])} of it on the critical "
                   f"path (stretch {marginal['stretch']:.2f} ≤ {limit:.2f})",
        })

    signal = getattr(comparison, 'efficiency_gate_signal', None) or {}
    drop_on = getattr(args, 'fail_on_efficiency_regression', False)
    floor_on = getattr(args, 'min_efficiency', None) is not None
    if not drop_on and not floor_on:
        rows.append({'gate': 'Whole-build efficiency', 'status': 'not requested',
                     'why': 'neither `--fail-on-efficiency-regression` nor '
                            '`--min-efficiency` passed'})
    elif signal.get('gates_not_applied'):
        runs = ' and '.join(signal.get('missing_occupancy_in') or [])
        rows.append({
            'gate': 'Whole-build efficiency', 'status': 'not applied',
            'why': f"the {runs} run has no `occupancy_share` signal, so there is "
                   f"nothing to gate on — an unevaluated check, not a pass",
        })
    else:
        floor = getattr(args, 'min_efficiency', None)
        below = floor_on and efficiency_below_floor(comparison, floor)
        dropped = drop_on and efficiency_regression_exceeds_threshold(comparison)
        occupancy = (comparison.candidate_metrics or {}).get('occupancy_share')
        delta = (comparison.deltas or {}).get('occupancy_share')
        if below:
            rows.append({'gate': 'Whole-build efficiency', 'status': 'FAIL',
                         'why': f"occupancy {occupancy:.0%} is below the "
                                f"{floor:.0%} floor"})
        elif dropped:
            rows.append({'gate': 'Whole-build efficiency', 'status': 'FAIL',
                         'why': f"occupancy fell {_pct_points(delta)} to "
                                f"{occupancy:.0%}"})
        else:
            rows.append({'gate': 'Whole-build efficiency', 'status': 'pass',
                         'why': f"occupancy {occupancy:.0%} ({_pct_points(delta)})"})

    regression_on = getattr(args, 'fail_on_regression', False)
    if not regression_on:
        rows.append({'gate': 'Wall-clock regression', 'status': 'not requested',
                     'why': '`--fail-on-regression` not passed'})
    else:
        threshold = getattr(args, 'regression_threshold', None)
        failed = regression_exceeds_threshold(comparison, threshold)
        baseline_total = (comparison.baseline_metrics or {}).get('total_duration_us')
        delta = (comparison.deltas or {}).get('total_duration_us')
        pct = (delta / baseline_total * 100) if (baseline_total and delta is not None) else None
        # The band itself is stated once, above the table. Repeating it
        # here would cost a row and say nothing new; what belongs in the
        # cell is which side of it this build landed on.
        rows.append({
            'gate': 'Wall-clock regression',
            'status': 'FAIL' if failed else 'pass',
            'why': (f"{_signed_s(delta)}" + (f" ({pct:+.1f}%)" if pct is not None else ""))
                   + (" — outside " if failed else " — within ") + _band_name(comparison),
        })
    return rows


def _band_name(comparison) -> str:
    band = comparison.baseline_band
    if not band or band.get('widened_to_fixed_pct'):
        return "the fixed 1% rule"
    return f"the band from {band['n']} baseline run(s)"


def _band_reason(comparison) -> str:
    band = comparison.baseline_band
    if not band:
        shortfall = getattr(comparison, 'baseline_band_shortfall', None)
        if shortfall:
            return (f"judged against the fixed 1% rule — "
                    f"{shortfall['supplied']} baseline run(s) supplied, "
                    f"{shortfall['required']} required for a measured band")
        return "judged against the fixed 1% rule (no baseline set supplied)"
    if band.get('widened_to_fixed_pct'):
        return (f"band from {band['n']} baseline run(s), widened to the fixed 1% "
                f"rule: {_s(band['low_us'])} .. {_s(band['high_us'])}")
    return (f"band from {band['n']} baseline run(s): {_s(band['low_us'])} .. "
            f"{_s(band['high_us'])} (median ±{band['k']:g}× scaled MAD)")


def _never_read_by_element(native_report: Optional[dict]) -> Optional[dict]:
    """`{element: [dependency, ...]}` from Plane 2's declared-vs-used.

    `None` — not the empty dict — when there is no Plane 2 data, because
    "nothing was staged and never read" and "nobody looked" are different
    claims and the table must render them differently.
    """
    if not native_report:
        return None
    declared = native_report.get('declared_vs_used') or {}
    if not declared.get('available'):
        return None
    by_element: dict = {}
    for entry in declared.get('unused_candidates') or []:
        by_element.setdefault(entry['element'], []).append(entry['dependency'])
    return by_element


def _element_table(comparison, never_read: Optional[dict]) -> List[str]:
    diff = comparison.element_diff or {}
    added = diff.get('new') or []
    moved = diff.get('moved_onto_critical_path') or []
    if not added and not moved:
        return ["**Elements** — this change added none and moved none onto the "
                "critical path."]

    lines = ["**Elements this change added or moved**", ""]
    header = "| Element | Duration | Critical path |"
    divider = "| --- | ---: | --- |"
    if never_read is not None:
        header += " Declared, never read |"
        divider += " --- |"
    lines += [header, divider]

    rows = (
        [(e['element_uid'], e['duration_us'],
          'yes — new on the path' if e['on_critical_path']
          else 'no — absorbed by existing parallelism', 'new')
         for e in added]
        + [(e['element_uid'], e['duration_us'], 'yes — moved onto the path', 'moved')
           for e in moved]
    )
    for uid, duration_us, path, _kind in rows[:_MAX_ROWS]:
        row = f"| `{uid}` | {_s(duration_us)} | {path} |"
        if never_read is not None:
            deps = never_read.get(uid) or []
            row += f" {', '.join(f'`{d}`' for d in deps) if deps else '—'} |"
        lines.append(row)
    if len(rows) > _MAX_ROWS:
        lines.append(f"| … {len(rows) - _MAX_ROWS} more | | |"
                     + (" |" if never_read is not None else ""))

    lines.append("")
    if never_read is None:
        lines.append("_No Plane 2 capture for the candidate run, so the "
                     "declared-but-never-read column is absent — not empty._")
    return lines


def _why_block(comparison) -> List[str]:
    """UX-229: the candidate run's diagnosis, with the chain behind it.

    The comment states verdicts; a reviewer's first question is *why do
    you say that*, and until this the answer lived in another command's
    output. Cited, not re-derived: every line here is a field of the
    published `candidate_diagnosis.provenance` record, which the
    terminal and the page render from too - so three surfaces cannot
    explain one claim three ways.

    Folded into a `<details>` because a comment is read in a sidebar
    and the reviewer who believes the verdict should not scroll past
    the reason they did not ask for.
    """
    diagnosis = getattr(comparison, 'candidate_diagnosis', None) or {}
    record = diagnosis.get('provenance') or {}
    rule = record.get('rule') or {}
    if not rule.get('sentence'):
        return []
    lines = ["<details><summary>Why the candidate looks like this</summary>", ""]
    lines.append(rule['sentence'])
    lines.append("")
    if rule.get("name"):
        lines.append(
            f"Rule `{rule['name']}` = `{rule['threshold']}` "
            f"({rule.get('module', '')}).")
        lines.append("")
    refs = [entry for entry in (record.get("evidence") or [])
            if entry.get("resolved")]
    if refs:
        lines += ["| Field | Value |", "| --- | --- |"]
        for entry in refs:
            lines.append(f"| `{entry['path']}` | {entry['value']} |")
        lines.append("")
        lines.append(
            f"<sub>Paths are into the candidate run's "
            f"`{record.get('document', 'analyze/v1')}`; "
            f"`bga analyze RUN --explain` prints the same chain.</sub>")
        lines.append("")
    lines += ["</details>", ""]
    return lines


def _verdict_why_block(comparison) -> List[str]:
    """UX-593: the chain behind the **verdict**, beside the one behind
    the candidate.

    `_why_block` above cites `candidate_diagnosis.provenance` - why the
    candidate run looks the way it does. The line a contributor argues
    with is the one at the top of this comment, and it published no
    grounds at all: the baseline it was measured against, the band or
    rule it crossed, and which elements crossed it were three greps
    away in a document nobody opens to defend a red gate.

    Cited, not re-derived, and folded for `_why_block`'s reason.

    **One line of references, where `_why_block` uses a table.** The
    comment's total length is capped at 60 lines because folded material
    a reviewer opens is still material they read, and a second table put
    the large-addition case at 65. A row per reference is unbounded -
    the band adds three and the culprits five - so the refs render as
    one bounded line and the block costs ten lines whatever it cites.
    """
    from ..compare import verdict_provenance

    record = verdict_provenance(comparison)
    if not record:
        return []
    rule = record.get('rule') or {}
    lines = [f"<details><summary>Why the verdict is "
             f"{(comparison.verdict_kind or '').upper()}</summary>", "",
             rule.get('sentence', ''), ""]
    if rule.get('name'):
        lines += [f"Rule `{rule['name']}` = `{rule['threshold']}` "
                  f"({rule.get('module', '')}). Paths are into this "
                  f"comparison's own `{record.get('document', 'compare/v2')}`:",
                  ""]
    refs = [entry for entry in (record.get('evidence') or [])
            if entry.get('resolved')]
    if refs:
        lines += [" · ".join(f"`{entry['path']}` = {entry['value']}"
                             for entry in refs), ""]
    lines += ["</details>", ""]
    return lines


def _cache_line(comparison) -> List[str]:
    churn = getattr(comparison, 'cache_churn', None) or {}
    if not churn.get('applicable'):
        # UX-93: not applicable is a reason, and the reason is the useful
        # half. Silence here would read as "the cache was fine".
        explanation = churn.get('explanation')
        if not explanation:
            return []
        return [f"**Cache** — churn not measured: {explanation}."]
    churned = churn.get('churned_count') or 0
    rebuilt = churn.get('rebuilt_in_both_count') or 0
    if churned:
        wasted = churn.get('wasted_rebuild_us')
        return [
            f"**Cache** — {churned} element(s) changed cache key between the two "
            f"runs" + (f", {_s(wasted)} of rebuild attributable to the change" if wasted else "")
            + f"; {rebuilt} rebuilt in both runs regardless.",
        ]
    return [
        f"**Cache** — no element changed its cache key; {rebuilt} rebuilt in both "
        f"runs, so the rebuild is the cache's retention, not this change.",
    ]


def _instance_stamp(comparison) -> str:
    """UX-95: which *runs* these numbers came from, not which identity.

    Two pushes produce two comments with identical identity hashes and
    different instants, and a reader who cannot tell them apart cannot
    tell a stale comment from a fresh one.
    """
    parts = []
    for label, key in (("baseline", 'baseline_run_instance'),
                       ("candidate", 'candidate_run_instance')):
        instance = getattr(comparison, key, None) or {}
        started = instance.get('started_at')
        parts.append(f"{label} {started}" if started else f"{label} (no start time)")
    return " · ".join(parts)


def render_ci_comment(comparison, args, native_report: Optional[dict] = None) -> str:
    """The markdown a CI job posts. Deterministic given its inputs."""
    baseline = comparison.baseline_metrics or {}
    candidate = comparison.candidate_metrics or {}
    deltas = comparison.deltas or {}
    baseline_total = baseline.get('total_duration_us')
    delta_total = deltas.get('total_duration_us')
    pct = (delta_total / baseline_total * 100) if (baseline_total and delta_total is not None) else None

    # The blank line after the marker is load-bearing, not cosmetic:
    # MD022 wants a heading surrounded by blank lines, and a CI owner who
    # pastes this comment into a document should not import a lint error.
    lines = [MARKER, "", "### Build efficiency", ""]

    headline = f"**{comparison.verdict.upper()}** — wall-clock {_s(baseline_total)} → {_s(candidate.get('total_duration_us'))}"
    if delta_total is not None:
        headline += f" ({_signed_s(delta_total)}"
        headline += f", {pct:+.1f}%)" if pct is not None else ")"
    lines += [headline, "", _band_reason(comparison), ""]

    if comparison.failed_runs:
        lines += [
            f"> **The {' and '.join(comparison.failed_runs)} run did not complete** — "
            "one or more elements ended in FAILURE, so no scheduling verdict below "
            "is meaningful for it.",
            "",
        ]
    if comparison.low_confidence:
        lines += [
            "> At least one run's confidence is below the 'high' band, so the gates "
            "fail open unless `--fail-on-low-confidence` was passed.",
            "",
        ]

    lines += ["| Gate | Result | Why |", "| --- | --- | --- |"]
    for row in _gate_rows(comparison, args):
        lines.append(f"| {row['gate']} | {row['status']} | {row['why']} |")
    lines.append("")

    lines += _element_table(comparison, _never_read_by_element(native_report))
    lines.append("")
    lines += _verdict_why_block(comparison)
    lines += _why_block(comparison)
    lines += _cache_line(comparison)
    lines += ["", f"<sub>{_instance_stamp(comparison)}</sub>"]

    # A trailing blank line is what a `gh pr comment --body-file` writes
    # anyway; collapsing the doubles keeps the rendering stable whether or
    # not an optional block was present.
    out: List[str] = []
    for line in lines:
        if line == "" and out and out[-1] == "":
            continue
        out.append(line)
    return "\n".join(out).rstrip() + "\n"
