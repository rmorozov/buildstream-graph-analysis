"""JSON report formatting (Part 32.4/37)."""
import json as _json
from typing import Optional

from .. import schemas
from ..findings import compute_findings
from ..ingest.models import AnalysisResult
from ._shared import ATTRIBUTION_CATEGORY_HINTS_BY_KEY, GRAPH_SIGNAL_KEYS, resolve_attribution_hint


def format_json(result: AnalysisResult, section: Optional[str] = None, by_kind: bool = False) -> str:
    """
    Format analysis results as JSON.

    Args:
        result: The AnalysisResult object from the analyzer
        section: Restrict output to one report section (see SECTIONS) -
            None (default) produces the full `analyze` report. The
            top-level key shape is unchanged either way (e.g. `floors`
            always lives under a `"floors"` key) - only which top-level
            keys are present differs, so existing `--format json`
            consumers of the full report see no shape change.
        by_kind: Include element_kind_summary (P4-12 Direction 3, `bga
            graph --by-kind`) - opt-in, same gating as the text report.

    Returns:
        JSON string suitable for machine processing
    """
    data = {
        'run_id': result.run_id,
        'total_duration_us': result.total_duration_us,
        # UX-190: which projection this is. `None` for the full report;
        # a section subcommand names its own restriction, so a consumer
        # can tell "this is `bga floors`" from "the field was removed".
        'section': section,
    }
    # UX-95: which capture this is, beside which captures it is
    # comparable with. Additive, and omitted entirely when the run
    # directory recorded nothing to say - an empty object would invite a
    # consumer to render a blank line where there is no fact.
    if getattr(result, 'run_instance', None):
        data['run_instance'] = result.run_instance

    # UX-75: the report's *conclusions*, not just its numbers. Every
    # other key here is raw measurement; a consumer that wanted to know
    # "is this build chain-bound", "which elements are worth fixing
    # first", "did the run finish" previously had to re-implement the
    # judgement - including four thresholds - out of
    # `bga/report/text.py`. This is the same list the text report
    # renders, so the two cannot disagree. Additive: no existing key
    # changes meaning or moves.
    if section is None:
        findings = compute_findings(result)
        if findings:
            data['findings'] = findings

    if section in (None, 'floors', 'replay'):
        data['floors'] = result.floors

    # UX-171: the resource blast table, same rows the text report
    # renders. Absent - not empty - when the run carries no source
    # inventory or nothing is shared, for the same reason `run_instance`
    # is: an empty list invites a consumer to render "no shared sources"
    # where the truth is "not looked for".
    if section in (None, 'graph') and getattr(result, 'resource_blast', None):
        blast = result.resource_blast
        if blast.get('rows'):
            data['resource_blast'] = blast

    # UX-35: the already-decided capacity verdict the hints above are
    # conditioned on - published so a consumer can see *why* a hint
    # said what it said, and so `checks_ran: false` is legible rather
    # than indistinguishable from a clean bill of health.
    if section is None and getattr(result, 'capacity_verdict', None):
        data['capacity_verdict'] = result.capacity_verdict

    # UX-202: Plane 2's own coverage of this build, when a Plane 2
    # report was in hand. Absent - not zeroed - without one, for the
    # reason `run_instance` is absent: "not looked at" and "looked at
    # and saw nothing" are different claims.
    if section is None and getattr(result, 'plane2_coverage', None):
        data['plane2_coverage'] = result.plane2_coverage

    if section is None and hasattr(result, 'attribution') and result.attribution:
        data['attribution'] = result.attribution
        # UX-04: additive sibling key, same category_us keys as
        # `attribution` itself - existing consumers of `attribution`'s
        # field names/values see no change.
        # UX-35: RESOURCE_WAIT's hint is conditioned on this run's own
        # capacity verdict - the static string tells a saturated host to
        # raise capacity, which is the opposite of the fix. Every other
        # category resolves to its unchanged static hint.
        capacity_verdict = getattr(result, 'capacity_verdict', None)
        data['attribution_hints'] = {
            key: resolve_attribution_hint(key, capacity_verdict)
            for key in result.attribution
            if key in ATTRIBUTION_CATEGORY_HINTS_BY_KEY
        }

    # occupancy field - check both occupancy (AnalysisResult field) and occupancy_stats (legacy name)
    if section is None:
        if hasattr(result, 'occupancy') and result.occupancy:
            data['occupancy'] = result.occupancy
        elif hasattr(result, 'occupancy_stats'):
            data['occupancy'] = result.occupancy_stats

    if section in (None, 'graph', 'diagnostics') and hasattr(result, 'signals') and result.signals:
        # Convert dataclasses to dicts for JSON serialization
        signals_data = {}
        for key, value in result.signals.items():
            if section == 'graph' and key not in GRAPH_SIGNAL_KEYS:
                continue
            if section == 'diagnostics' and key in GRAPH_SIGNAL_KEYS:
                continue
            if isinstance(value, list) and value:
                if hasattr(value[0], '__dict__'):
                    signals_data[key] = [v.__dict__ if hasattr(v, '__dict__') else v for v in value]
                else:
                    signals_data[key] = value
            elif hasattr(value, '__dict__'):
                signals_data[key] = value.__dict__
            else:
                signals_data[key] = value
        if signals_data:
            data['signals'] = signals_data

    if section in (None, 'graph') and hasattr(result, 'structural') and result.structural:
        data['structural'] = result.structural

    if section in (None, 'utilisation') and hasattr(result, 'utilisation') and result.utilisation:
        data['utilisation'] = result.utilisation

    if section is None and hasattr(result, 'confidence') and result.confidence:
        data['confidence'] = result.confidence

    if section is None and hasattr(result, 'violations'):
        # Always include, even when empty - an empty list means "checked,
        # none found", which is different from the key being absent.
        data['violations'] = result.violations

    if section is None and hasattr(result, 'model') and result.model:
        data['model'] = result.model

    if section is None and hasattr(result, 'pipeline_overhead') and result.pipeline_overhead:
        data['pipeline_overhead'] = result.pipeline_overhead

    # UX-110: the resolution of every duration in this report, from the
    # run's own two measurements of each task. Absent when the capture
    # carries only one - which is a different claim from "they agreed".
    if section is None and getattr(result, 'timestamp_agreement', None):
        data['timestamp_agreement'] = result.timestamp_agreement

    if section in (None, 'graph') and by_kind and hasattr(result, 'element_kind_summary') and result.element_kind_summary:
        data['element_kind_summary'] = result.element_kind_summary

    # UX-190: the version leads. A consumer reading the first line of a
    # streamed or truncated document sees what it is before it sees
    # anything it would have to interpret.
    return _json.dumps(schemas.stamp(data, schemas.ANALYZE), indent=2, default=str)
