"""JSON report formatting (Part 32.4/37)."""
import json as _json
from typing import Optional, Tuple

from .. import producer, provenance, schemas
from ..findings import (compute_findings, compute_headline,
                        compute_next_steps, finding_copy_text, reader_index)
from ..ingest.models import AnalysisResult
from ._shared import ATTRIBUTION_CATEGORY_HINTS_BY_KEY, GRAPH_SIGNAL_KEYS, resolve_attribution_hint


# `UX-344`: `structural.metrics` and `structural.summary` under their
# own names. At the top level `metrics` and `summary` would be two of
# the most generic keys in the document, and the page already draws a
# `summary` section - the run's own scalars - that a second one would
# have collided with.
_STRUCTURAL_RENAMES = {"metrics": "graph_metrics", "summary": "graph_summary"}


def _lift(data: dict, block: dict, renames: Optional[dict] = None) -> None:
    """`UX-344`: each named table of a namespace, as a key of its own.

    A collision is a programming error rather than a run-time
    possibility - two tables of one name in one document - so it is
    raised here rather than resolved by whichever block was lifted last.
    """
    for key, value in block.items():
        name = (renames or {}).get(key, key)
        if name in data:
            raise ValueError(
                f"lifting {key!r} would overwrite the document's {name!r}")
        data[name] = value


def _measure_shape(document: dict) -> Tuple[int, int, str, int]:
    """`(leaves, deepest_depth, deepest_path, deeper_than_three)`.

    A container step counts a level, which is how `UX-344` measured the
    depth it was filed against - so `findings[].evidence.rows[]` puts
    its leaves at six and the numbers here are comparable with the ones
    in that item.
    """
    leaves = deeper = 0
    deepest_depth, deepest_path = 0, ""

    def walk(value, path, depth):
        nonlocal leaves, deeper, deepest_depth, deepest_path
        if isinstance(value, dict):
            for key, sub in value.items():
                walk(sub, path + [str(key)], depth + 1)
        elif isinstance(value, (list, tuple)):
            for sub in value:
                walk(sub, path + ["[]"], depth + 1)
        else:
            leaves += 1
            if depth > 3:
                deeper += 1
            if depth > deepest_depth:
                deepest_depth, deepest_path = depth, ".".join(path)

    walk(document, [], 0)
    return leaves, deepest_depth, deepest_path, deeper


#: This block's own leaves (five, all at depth two) plus the `schema`
#: stamp that `UX-190` puts on the front afterwards. Counted rather
#: than ignored: the numbers describe the document a consumer receives.
_SHAPE_OWN_LEAVES = 6


def document_shape(document: dict, adding: int = _SHAPE_OWN_LEAVES) -> dict:
    """How deep this document is, as a block that counts itself.

    `UX-344` had to measure the depth with a script against two
    fixtures to find out that 57% and 67% of their leaves were deeper
    than three. The document says so now - and it says it about the
    finished document, `adding` the leaves that arrive after the walk:
    this block's own five, at depth two, and the `schema` stamp. A
    consumer that re-measures gets these numbers back.
    """
    leaves, depth, path, deeper = _measure_shape(document)
    leaves += adding
    return {
        "leaves": leaves,
        "deepest_depth": depth,
        "deepest_path": path,
        "deeper_than_three": deeper,
        "deeper_than_three_share": (deeper / leaves) if leaves else 0.0,
    }


def _binary_rows(binary_cost):
    """Plane 2's per-element binary costs, as one flat table.

    `UX-370`: the Plane 2 report nests these - element, then two
    rankings, then a row - and projecting that shape verbatim broke
    four of this contract's own rules at once. Measured on
    `macro_micro`:

        deeper than three levels   0.626 of leaves, against a 0.58 bound
        one population, twice      `configure_phase.per_element` and
                                   `binary_cost`, the same 9 elements
        table width                `configure_phase[]` at 9 columns,
                                   against `PRESET_COLUMNS_MAX` of 8

    Four rules saying one thing: this document is flat, publishes each
    population once, and draws tables a reader can read. So the two
    rankings become one row per **(element, binary)** pair - which is
    also the shape the item asked for, "a table with a share column" -
    and `configure_phase.per_element` is dropped rather than published
    as a second copy of the element population. The per-element split
    stays in `plane2.json`, where `bga correlate` reads it.

    `wall_s` becomes `wall_us` on the way: Plane 2 publishes seconds
    and this vocabulary carries one time member, in microseconds
    (`UX-341`). Converting at the boundary is `bga/units.py`'s own
    rule; the alternative is a number the page renders from a guess.
    """
    rows = []
    for element, cost in sorted((binary_cost or {}).items()):
        if not isinstance(cost, dict) or not cost.get('available'):
            continue
        calls = {entry.get('binary'): entry.get('count')
                 for entry in cost.get('by_count') or []}
        seen = set()
        for entry in cost.get('by_cpu') or []:
            binary = entry.get('binary')
            seen.add(binary)
            wall_s = entry.get('wall_s')
            rows.append({
                'element': element,
                'binary': binary,
                'calls': entry.get('count', calls.get(binary)),
                'cpu_us': entry.get('cpu_us'),
                'cpu_share': entry.get('cpu_share'),
                'wall_us': (round(wall_s * 1_000_000)
                            if isinstance(wall_s, (int, float)) else None),
            })
        # A binary ranked by count and not by CPU is a cheap one that
        # ran often - the process-storm shape, and the half of the
        # question a CPU ranking alone cannot answer.
        for binary, count in calls.items():
            if binary not in seen:
                rows.append({'element': element, 'binary': binary,
                             'calls': count, 'cpu_us': None,
                             'cpu_share': None, 'wall_us': None})
    return rows


def build_document(result: AnalysisResult, section: Optional[str] = None, by_kind: bool = False) -> dict:
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
        The `analyze/v1` document as a dict, stamped with its schema.
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
        # UX-207: what to fix first, and what it is worth. Decided in
        # `findings.py` beside the ratio it comes from, so the decision
        # panel reads a field instead of re-deriving a diagnosis the
        # pipeline already made. Passed the findings it references so
        # the ranking is read once.
        data['headline'] = compute_headline(result, findings)
        # `UX-372`: and who is served by what. Every finding already
        # declares its `reader`; this is the index over them, so a
        # consumer asking "what does this run say to the person who
        # owns the machines" has one lookup rather than a scan and a
        # severity ranking of its own. Only readers this run has
        # something for - a report with no capacity numbers offers no
        # capacity reader. After the headline because it defers to it.
        if findings:
            readers = reader_index(findings, data['headline'])
            if readers:
                data['readers'] = readers
        # UX-218: and what to run next, chosen by what this run
        # measured. Decided here for the same reason the diagnosis is:
        # a viewer that picked the next command from `chain_share`
        # would be a second decision-maker, and the terminal and CI
        # would give different advice from the page.
        data['next_steps'] = compute_next_steps(result, data['headline'])
        # UX-224: and the text each finding pastes as. Rendered here,
        # not in the page: the CI comment is Python and the viewer is
        # JavaScript, so the only honest way to have *one* renderer
        # across that boundary is to publish the string and have the
        # page copy it rather than word it.
        for finding in findings or []:
            finding['copy_text'] = finding_copy_text(
                finding, result, data['next_steps'])

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

    # UX-275: and what the capacity *should* be. Computed since UX-116,
    # rendered in full by the text report, and dropped here - so the
    # tool's answer to the question this backlog opened with (`UX-09`:
    # what should `--builders` and `--max-jobs` be, and which constraint
    # is the reason) was reachable only by a human reading a terminal,
    # and a CI job that wanted it had to parse prose.
    #
    # Absent rather than empty without `--plane2`, like `run_instance`:
    # the recommendation rests on measured cores-busy, and "not measured"
    # must not render as "no constraint".
    if section is None and getattr(result, 'capacity_recommendation', None):
        data['capacity_recommendation'] = result.capacity_recommendation

    # UX-202: Plane 2's own coverage of this build, when a Plane 2
    # report was in hand. Absent - not zeroed - without one, for the
    # reason `run_instance` is absent: "not looked at" and "looked at
    # and saw nothing" are different claims.
    if section is None and getattr(result, 'plane2_coverage', None):
        data['plane2_coverage'] = result.plane2_coverage

    # UX-329: and *why* it is absent when it is. `plane2_coverage`
    # missing has meant three different things - not captured, captured
    # with its raw log dropped, captured and declined - and a reader
    # could tell them apart only by looking in the store themselves. The
    # sentence is the same one the page and the export print, from
    # `bga.plane2`, so the three cannot describe one absence differently.
    if section is None and getattr(result, 'plane2_absence', None):
        data['plane2_absence'] = result.plane2_absence

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
            # `UX-344`: the element population first, because it comes
            # out of the block that is then lifted around it.
            elements = {key: signals_data.pop(key)
                        for key in schemas.ELEMENT_POPULATION
                        if key in signals_data}
            if elements:
                data['elements'] = elements
            _lift(data, signals_data)

    if section in (None, 'graph') and hasattr(result, 'structural') and result.structural:
        _lift(data, result.structural, _STRUCTURAL_RENAMES)

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

    # UX-215: the two-plane join, in the report rather than only in a
    # second command. Computed by the same `correlate()` the
    # `correlate/v1` document comes from - one join, so `bga analyze
    # --plane2` and `bga correlate` cannot describe the same element
    # differently - and fed the finished analysis dict, which is why
    # this runs here rather than where the Plane 2 report is read.
    #
    # Absent without `--plane2`, for the reason `plane2_coverage` is
    # absent: there is no *join* with one plane, and the Plane 1 half
    # is already published in `signals`. "Not looked at" and "looked at
    # and saw nothing" are different claims.
    native_report = getattr(result, 'plane2_report', None)
    if section is None and native_report:
        from bga.correlate import correlate as _correlate

        try:
            joined = _correlate(data, native_report)
        except Exception:                       # pragma: no cover
            # A join that cannot be computed must not cost the reader
            # the analysis - `UX-83`'s rule for the Plane 2 path, and
            # the reason `--plane2` is a warning rather than a failure
            # everywhere else it appears.
            joined = None
        if joined:
            data['element_join'] = joined.get('elements') or []
            data['element_join_coverage'] = joined.get('coverage') or {}
        # `UX-370`: what the build spent its time *running*, which
        # Plane 2 measures and nothing carried out of it. Round 58
        # asked what cmake configure costs and found the answer in
        # `plane2.json` beside the run and nowhere a reader goes: the
        # page had the binary *names* and none of the numbers.
        #
        # A projection, not a computation - each key is copied as the
        # Plane 2 report published it, which is why this sits beside
        # the join rather than in `correlate`. Absent without
        # `--plane2` for the same reason the join is.
        if native_report.get('by_binary'):
            data['by_binary'] = dict(native_report['by_binary'])
        rows = _binary_rows(native_report.get('binary_cost'))
        if rows:
            data['binary_cost'] = rows
        phase = native_report.get('configure_phase')
        if phase:
            data['configure_phase'] = {
                key: value for key, value in phase.items()
                if key != 'per_element'}

    # UX-229: and why every claim above is made. Last, and reading the
    # finished dict, because provenance is *references into this
    # document* - the paths are only checkable once the document they
    # point into exists. Same placement, and the same reason, as the
    # join above.
    #
    # `UX-344`: published as one list keyed by claim rather than written
    # into each claim. The claims carry the ids they already carried.
    if section is None:
        provenance.attach(data)

    # UX-249: which build wrote this. A published payload archived by a
    # CI job is re-read like any stored run, and until this landed
    # nothing in it said which `bga` produced it. The version is
    # provenance, never a compatibility signal - the `contracts` list
    # beside it is what a reader compares (Direction 10).
    producer.add(data)

    # `UX-344`: how deep this document turned out to be, measured on it.
    # After `producer`, so the block describes the document a consumer
    # actually receives - and before the stamp, which adds one more
    # leaf at depth one that `document_shape` counts for itself.
    if section is None:
        data['document_shape'] = document_shape(data)

    # UX-190: the version leads. A consumer reading the first line of a
    # streamed or truncated document sees what it is before it sees
    # anything it would have to interpret.
    return schemas.stamp(data, schemas.ANALYZE)


def format_json(result: AnalysisResult, section: Optional[str] = None,
                by_kind: bool = False) -> str:
    """The document, serialized.

    `UX-229` split the two: the text renderer's `--explain` needs the
    *object* so that the chain it prints is the one the JSON publishes
    rather than a second assembly of the same fields, and a renderer
    that had to parse its sibling's output to get there would be exactly
    the kind of re-derivation this codebase keeps deleting.
    """
    return _json.dumps(build_document(result, section=section, by_kind=by_kind),
                       indent=2, default=str)
