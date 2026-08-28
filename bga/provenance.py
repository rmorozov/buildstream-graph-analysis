"""UX-229: why `bga` believes what it believes.

Round 24 found the *relationship* layer computed and unpublished, and
`correlate/v1` closed it. This is the same defect one level up, over the
conclusions rather than the facts: the headline says `scheduler_bound`,
and the fields that decided it, the threshold they were compared
against, and the query that would prove it deeper are all real and none
of them travel. A reader who asks *why do you say this* gets a document
to grep.

The chain this module publishes, per claim:

    claim -> evidence (field refs) -> rule -> trace query

**References, not copies.** Each evidence entry is a `path` into the
same `analyze/v1` document plus the `value` found there, so a consumer
can follow it rather than trust it, and a guard can assert that every
path resolves and every quoted value equals the field it cites. The
per-element rows a finding was drawn from already live in its
`evidence` object (`UX-217`) and are not re-published here; what was
missing was never the numbers, it was the *chain*.

**The threshold is read live.** `rule.threshold` is the constant
itself, not a literal copied beside it - change `CHAIN_BOUND_RATIO` and
the published record changes with it, which is the one property that
makes the record evidence rather than documentation.

**One table, four consumers.** The finding -> query mapping lived in
`bga/viewer/trace_context.js`, which made the page the only place that
knew which question deepens which finding; the text report and the CI
comment could not say it at all. It lives here now and the page reads
the published field, the same move `UX-207` made for the diagnosis.

Nothing here computes analysis. Every value is read back out of the
finished document, which is also why `attach` runs at the end of the
report build rather than beside `compute_findings`: the paths are only
meaningful once the document they point into exists.
"""
from typing import Any, List, Optional, Tuple

from . import findings as _findings
from . import schemas as _schemas
from .cache_effectiveness import (HEALTHY_HIT_RATIO, POOR_HIT_RATIO,
                                  TRANSFER_SHARE_NOTABLE)

# The module every threshold below is defined in, published so a record
# names where to go and change it rather than only what it is called.
# Which published document every `evidence[].path` below walks.
# `UX-341`: read from `schemas` rather than restated, so a
# version move cannot leave every provenance path resolving
# against a contract this release no longer builds.
ANALYZE_DOCUMENT = _schemas.ANALYZE

RULE_MODULE = "bga/findings.py"
CACHE_RULE_MODULE = "bga/cache_effectiveness.py"

_MISSING = object()


class _Bracket:
    """A `[...]` segment that is not a `key=value` selector.

    Kept as text rather than parsed to an int, because what it means
    depends on what it lands on: a list index, or a key of a map. Maps
    keyed by element uid are the reason - a uid contains dots, so it
    cannot be addressed through the dotted form at all.
    """

    __slots__ = ("text",)

    def __init__(self, text):
        self.text = text

    def __repr__(self):                             # pragma: no cover
        return f"[{self.text}]"


class _Unresolved:
    """What a dangling path resolves to. Distinct from `None`, which is
    a real published value on plenty of these fields."""

    def __repr__(self):                             # pragma: no cover
        return "<unresolved>"


UNRESOLVED = _Unresolved()


def resolve(document: dict, path: str):
    """Walk `path` through `document`; `UNRESOLVED` if it dangles.

    The grammar is the smallest one that addresses what claims are made
    of: dotted keys, `[i]` for a list index, and `[key=value]` for the
    one list entry whose `key` equals `value`. That last form exists
    because `violations` is a list whose *order* is not a contract -
    `violations[type=build_failed].failed_count` stays correct when a
    second violation is prepended, and `violations[0]` does not.
    """
    node: Any = document
    for segment in _segments(path):
        if isinstance(segment, tuple):
            key, wanted = segment
            if not isinstance(node, list):
                return UNRESOLVED
            node = next(
                (item for item in node
                 if isinstance(item, dict) and str(item.get(key)) == wanted),
                _MISSING,
            )
        elif isinstance(segment, _Bracket):
            # One bracket, two containers. A list takes it as an index;
            # a dict takes it as a key - which is how a map keyed by
            # element uid becomes addressable at all, since a uid
            # contains dots and cannot go through the dotted form.
            if isinstance(node, list):
                index = int(segment.text) if segment.text.lstrip("-").isdigit() \
                    else None
                node = (node[index] if index is not None and -len(node) <= index
                        < len(node) else _MISSING)
            elif isinstance(node, dict):
                node = node.get(segment.text, _MISSING)
            else:
                return UNRESOLVED
        else:
            if not isinstance(node, dict) or segment not in node:
                return UNRESOLVED
            node = node[segment]
        if node is _MISSING:
            return UNRESOLVED
    return node


def _segments(path: str):
    """Scan rather than `split(".")`.

    Element uids contain dots - `layer07/mod084.bst` - so a selector
    written as `[element_uid=core.bst]` splits into nonsense the moment
    the separator is taken literally. Found by `UX-227`, which emits
    exactly those paths from the page.
    """
    name, depth, buffer = "", 0, ""
    for char in path:
        if depth == 0 and char == ".":
            if name:
                yield name
            name = ""
        elif depth == 0 and char == "[":
            if name:
                yield name
            name, depth, buffer = "", 1, ""
        elif depth and char == "]":
            depth = 0
            if "=" in buffer:
                key, _, value = buffer.partition("=")
                yield (key, value)
            else:
                yield _Bracket(buffer)
        elif depth:
            buffer += char
        else:
            name += char
    if name:
        yield name


# Which library question deepens which claim.
#
# Moved out of `bga/viewer/trace_context.js` by this item. Keyed by the
# id `findings.py` assigns, so a renamed finding loses its query rather
# than silently pointing at the wrong one - and the coverage guard
# still asserts both directions, now across the language boundary.
TRACE_QUERIES = {
    # The diagnosis is a claim about the chain, so the query opens it.
    "diagnosis": "element-time",
    # Scheduling: the finding says time was spent waiting; the query
    # shows where the gaps are.
    "wait-category": "stalls",
    "capacity-recommendation": "stalls",
    # Execution: the finding names elements; the query opens them.
    "time-concentration": "element-time",
    # `UX-312`: `execution-bound` is a claim about how much of the
    # build was *running processes*, so the count is the drill-down and
    # `latent-heavies` keeps the command list - which is the question
    # about which commands, not how many.
    "execution-bound": "process-storm",
    "latent-heavies": "element-commands",
    # Dependencies: the finding is about shape, not speed.
    "criticality": "dependency-wait",
    "blast-radius-ranking": "dependency-wait",
    "blast-radius-structural": "dependency-wait",
    "shared-source-blast": "dependency-wait",
    # Resources: what the processes inside the sandbox cost.
    "memory-envelope": "peak-rss",
    "cache-transfer-cost": "sandbox-tax",
    # `UX-312`. The vocabulary `UX-308`..`UX-311` put on the trace made
    # seven more questions answerable, and a question no finding points
    # at is a question nobody arrives at - the page is where it lives,
    # a finding is how a reader gets there.
    #
    # `memory-envelope` moved above rather than gaining a second row:
    # it is a claim about *peak* memory, and `peak-rss` reads the same
    # per-process maximum the claim is computed from, where
    # `process-storm` answers a question about counts.
    "build-failed": "failed-processes",
    "failed-task-time": "failed-processes",
    "efficiency-score": "cpu-versus-wall",
    "certified-headroom": "concurrency-curve",
    "optimization-horizon": "time-by-kind",
    "run-mode-incremental": "which-run-is-this",
    "joint-saving": "waited-on-flow",
}


def _rule(name, threshold, comparison, observed_path, sentence,
          module=RULE_MODULE):
    rule = {"name": name, "threshold": threshold, "comparison": comparison,
            "observed_path": observed_path, "sentence": sentence,
            "module": module}
    # `UX-343`: a threshold is in the unit of the field it is compared
    # against, and `observed_path` names that field - so the unit is
    # resolvable rather than a property of the number. Omitted where
    # the rule compares against something no path names, which is a
    # smaller set than it looks: the thresholds without an observed
    # path are floors on a quantity the finding computes rather than
    # publishes.
    if observed_path:
        from . import schemas as _schemas

        quantity = _schemas.quantity_for_path(observed_path, ANALYZE_DOCUMENT)
        if quantity:
            rule["threshold_quantity"] = quantity
    return rule


def _unconditional(sentence):
    """A claim with no threshold. Published as `null` rather than as an
    invented number: "this fires whenever its evidence exists" is a
    different statement from "this fires above 0", and a consumer that
    cannot tell them apart is back to guessing."""
    return _rule(None, None, "present", None, sentence, module=RULE_MODULE)


def _diagnosis_rule(claim, document):
    ratio = resolve(document, "headline.chain_share")
    name = resolve(document, "headline.diagnosis")
    if ratio is UNRESOLVED or ratio is None:
        return _unconditional(
            "Neither branch could be taken: this run did not record both "
            "durations the ratio needs.")
    fired = ">=" if name == _findings.DIAGNOSIS_CHAIN_BOUND else "<"
    return _rule(
        "CHAIN_BOUND_RATIO", _findings.CHAIN_BOUND_RATIO, fired,
        "headline.chain_share",
        f"The critical path is {ratio:.1%} of wall-clock, which is {fired} "
        f"the {_findings.CHAIN_BOUND_RATIO:.0%} at which the chain rather "
        f"than the scheduler is called the constraint - so {name}.")


def _wait_category_rule(claim, document):
    share = ((claim.get("evidence") or {}).get("share"))
    return _rule(
        "OPPORTUNITY_FLOOR_PCT", _findings.OPPORTUNITY_FLOOR_PCT / 100, ">=",
        None,
        f"The largest non-execution category is {share:.1%} of wall-clock, "
        f"at or above the {_findings.OPPORTUNITY_FLOOR_PCT:.0f}% floor below "
        f"which the largest of the remainder is rounding rather than an "
        f"opportunity." if isinstance(share, (int, float)) else
        "The largest non-execution category cleared the opportunity floor.")


def _cache_hit_rule(claim, document):
    ratio = (claim.get("evidence") or {}).get("hit_share")
    if (claim.get("evidence") or {}).get("run_mode") == "full":
        return _rule(
            None, None, "present", "confidence.run_mode",
            "Caches were off for this run, so the hit ratio is the intent "
            "rather than a finding and no band is applied.")
    if not isinstance(ratio, (int, float)):        # pragma: no cover
        return _unconditional("The cache reported no hit ratio.")
    band = ("below POOR_HIT_RATIO" if ratio < POOR_HIT_RATIO
            else "below HEALTHY_HIT_RATIO" if ratio < HEALTHY_HIT_RATIO
            else "at or above HEALTHY_HIT_RATIO")
    return _rule(
        "POOR_HIT_RATIO/HEALTHY_HIT_RATIO", [POOR_HIT_RATIO, HEALTHY_HIT_RATIO],
        "banded", "cache.hit_share",
        f"A {ratio:.0%} hit ratio is {band} "
        f"({POOR_HIT_RATIO:.0%}/{HEALTHY_HIT_RATIO:.0%}), which is what sets "
        f"this finding's severity.",
        module=CACHE_RULE_MODULE)


def _confidence_rule(claim, document):
    primary = (claim.get("evidence") or {}).get("primary")
    if not isinstance(primary, (int, float)):      # pragma: no cover
        return _unconditional("This run published no confidence score.")
    return _rule(
        "_CONFIDENCE_HIGH/_CONFIDENCE_MEDIUM",
        [_findings._CONFIDENCE_MEDIUM, _findings._CONFIDENCE_HIGH], "banded",
        "confidence.primary",
        f"{primary:.2f} bands as "
        f"{_findings.confidence_band(primary)} against "
        f"{_findings._CONFIDENCE_MEDIUM:.2f}/{_findings._CONFIDENCE_HIGH:.2f}.")


def _efficiency_rule(claim, document):
    score = (claim.get("evidence") or {}).get("efficiency_score")
    if not isinstance(score, (int, float)):        # pragma: no cover
        return _unconditional("This run published no efficiency score.")
    return _rule(
        "_EFFICIENCY_HIGH/_EFFICIENCY_MEDIUM",
        [_findings._EFFICIENCY_MEDIUM, _findings._EFFICIENCY_HIGH], "banded",
        "floors.efficiency_score",
        f"{score:.2f} is "
        f"{'at or above' if score >= _findings._EFFICIENCY_HIGH else 'below'} "
        f"{_findings._EFFICIENCY_HIGH:.2f} and "
        f"{'at or above' if score >= _findings._EFFICIENCY_MEDIUM else 'below'} "
        f"{_findings._EFFICIENCY_MEDIUM:.2f}, which is what chooses the "
        f"sentence beside it; the caveat below "
        f"{_findings._CONFIDENCE_HIGH:.1f} confidence is a second rule, not "
        f"this one.")


def _mesh_rule(claim, document):
    density = (claim.get("evidence") or {}).get("zero_slack_share")
    return _rule(
        "MESH_ZERO_SLACK_SHARE", _findings.MESH_ZERO_SLACK_SHARE, ">=",
        "elements.zero_slack_share",
        f"{density:.0%} of elements have zero slack, at or above the "
        f"{_findings.MESH_ZERO_SLACK_SHARE:.0%} at which the graph is called "
        f"a mesh rather than a chain."
        if isinstance(density, (int, float)) else
        "The zero-slack share cleared the mesh threshold.")


# claim id -> (evidence paths, rule, unpublished inputs)
#
# `evidence` and `rule` may be callables taking `(claim, document)` when
# the fields a claim read depend on the claim - `wait-category` cites
# whichever attribution category won, and a static path would name the
# wrong one on every run but the one it was written against.
#
# `unpublished` names fields a claim was genuinely drawn from that the
# analyze document does not carry. It is deliberately not empty:
# `memory_envelope` is computed, is what its finding asserts, and
# reaches no consumer of this document. Naming it is the honest shape -
# a reference that resolved to nothing would read as a published field,
# and silence would read as no gap at all.
#
# `UX-275` emptied the other one: `capacity_recommendation` is published
# now, so its paths moved up into the evidence they always were.
_CLAIMS = {
    "diagnosis": (
        ("floors.t_infinity_observed", "total_duration_us",
         "headline.chain_share"),
        _diagnosis_rule, ()),
    "build-failed": (
        ("violations[type=build_failed].failed_count",
         "violations[type=build_failed].interrupted"),
        _unconditional(
            "Published whenever the run recorded a `build_failed` violation; "
            "there is no threshold - a build that did not finish is not a "
            "matter of degree."), ()),
    "failed-task-time": (
        ("confidence.failed_task_us", "confidence.failed_task_count"),
        _rule(None, 0, ">", "confidence.failed_task_us",
              "Published when any task attempt failed and still cost time.",
              ), ()),
    "run-mode-incremental": (
        ("confidence.run_mode",),
        _unconditional(
            "Published when the run recorded `run_mode: incremental`; the "
            "mode is a fact about the capture, not a measurement to band."),
        ()),
    "cache-hit-ratio": (
        ("cache.hit_share", "cache.built_elements",
         "cache.cached_elements", "confidence.run_mode"),
        _cache_hit_rule, ()),
    "cache-transfer-cost": (
        ("cache.transfer_share",),
        _rule("TRANSFER_SHARE_NOTABLE", TRANSFER_SHARE_NOTABLE, ">=",
              "cache.transfer_share",
              "Artifact transfer took at or above the share of wall-clock at "
              "which moving artifacts is worth saying out loud.",
              module=CACHE_RULE_MODULE), ()),
    "confidence": (
        ("confidence.primary", "confidence.coverage_score",
         "confidence.task_coverage"),
        _confidence_rule, ()),
    "time-concentration": (
        # `UX-345`: this named the same duration twice - once as
        # `signals.critical_path_length`, which held it under a `count`
        # declaration, and once truthfully.
        ("total_duration_us", "floors.t_infinity_observed"),
        _unconditional(
            "Published whenever the critical path has measured elements on "
            "it; which elements, and their share, are the finding's own "
            "`evidence.rows`."), ()),
    "mesh-graph": (
        ("elements.zero_slack_share",), _mesh_rule, ()),
    "shared-source-blast": (
        ("resource_blast.element_count",),
        _unconditional(
            "Published whenever the source inventory found a resource more "
            "than one element shares."), ()),
    "memory-envelope": (
        (),
        _unconditional(
            "Published whenever both halves were measured - the per-element "
            "peaks from Plane 2 and the host's RAM from the capture."),
        ("memory_envelope.at_observed_builders.envelope_mb",
         "memory_envelope.host_memory_mb",
         "memory_envelope.first_builders_that_does_not_fit")),
    "capacity-recommendation": (
        # UX-275: these resolve now. The block was computed, rendered by
        # the text report and dropped by the JSON renderer, so the four
        # fields this finding asserts were listed below as *unpublished*
        # - an honest label for a real gap, and the gap is closed. They
        # are evidence like any other citation, and the `unpublished`
        # tuple is empty rather than carrying paths that resolve.
        # `occupancy.builders` until UX-275, which never resolved: the
        # occupancy block publishes concurrency and idle time and has
        # never carried a builder count. The recommendation does, and
        # now that the recommendation is published the citation can
        # point at a field a reader can actually open.
        ("capacity_recommendation.builders",
         "capacity_recommendation.binding_constraint",
         "capacity_recommendation.recommended_builders",
         "capacity_recommendation.cores_busy"),
        _unconditional(
            "Published whenever the four constraints could be intersected; "
            "which one binds is the finding's own `evidence`."),
        ()),
    "execution-bound": (
        ("total_duration_us",),
        _rule("OPPORTUNITY_FLOOR_PCT", _findings.OPPORTUNITY_FLOOR_PCT / 100,
              "<", None,
              f"No wait category reaches "
              f"{_findings.OPPORTUNITY_FLOOR_PCT:.0f}% of wall-clock, so "
              f"there is no scheduling gap to close and the elements "
              f"themselves are the work."), ()),
    "wait-category": (
        lambda claim, document: (
            "attribution." + str((claim.get("evidence") or {}).get("category")),
            "total_duration_us"),
        _wait_category_rule, ()),
    "joint-saving": (
        ("joint_saving.joint_saving_us",
         "joint_saving.sum_of_individual_us",
         "joint_saving.savings_add", "total_duration_us"),
        _unconditional(
            "Published whenever the top elements have a joint projection; "
            "whether the savings add is the finding, not its gate."), ()),
    "optimization-horizon": (
        ("optimization_horizon[0].makespan_after_us",
         "optimization_horizon[0].cumulative_saving_us",
         "total_duration_us"),
        _unconditional(
            "Published when the horizon has more than one step - a "
            "single-step horizon is the first fix, which is already named."),
        ()),
    "latent-heavies": (
        ("latent_heavies[0].duration_us",),
        _unconditional(
            "Published whenever elements off the critical path are heavy "
            "enough to bound how far shortening the chain can go."), ()),
    "blast-radius-ranking": (
        ("headline.chain_share",),
        _rule("CHAIN_BOUND_RATIO", _findings.CHAIN_BOUND_RATIO, "<",
              "headline.chain_share",
              "Who-depends-on-me is ranked only on a build the chain does "
              "not already constrain; above the threshold the ranking that "
              "matters is how long each element takes."), ()),
    "blast-radius-structural": (
        ("elements.blast_radius",),
        _unconditional(
            "Published when the elements with the widest reach are "
            "structural kinds - a base image, a toolchain, a stack. Their "
            "dependents are the graph's shape rather than a task, which is "
            "why UX-258 reports them here instead of ranking them as work "
            "(the rule UX-76 already applied to criticality)."), ()),
    "criticality": (
        ("floors.t_infinity_observed",),
        _unconditional(
            "Published when at least one non-structural element has a "
            "non-certain probability of being on the path; a list where "
            "every entry is 1.0 ranks nothing."), ()),
    "certified-headroom": (
        ("floors.certified_headroom", "floors.t_infinity_observed",
         "floors.lb"),
        _rule(None, 0, ">", "floors.certified_headroom",
              "Published when the certified floor leaves any headroom at "
              "all; zero headroom is a fact the floors section states, not "
              "a finding."), ()),
    "efficiency-score": (
        ("floors.efficiency_score", "confidence.primary"),
        _efficiency_rule, ()),
}


def claim_ids() -> Tuple[str, ...]:
    """Every claim this module can explain - the guard's other direction
    against `findings.py`'s own ids."""
    return tuple(sorted(_CLAIMS))


def record(claim: dict, claim_id: str, kind: str, document: dict) -> dict:
    """The chain behind one claim: evidence refs, rule, trace query."""
    spec = _CLAIMS.get(claim_id)
    if spec is None:
        return {
            "claim": claim_id, "kind": kind, "document": ANALYZE_DOCUMENT,
            "evidence": [],
            "rule": _unconditional(
                "No rule is recorded for this claim - it is published "
                "without one rather than with an invented one."),
            "trace_query": TRACE_QUERIES.get(claim_id),
            "unpublished_inputs": [],
        }
    paths, rule, unpublished = spec
    if callable(paths):
        paths = paths(claim, document)
    if callable(rule):
        rule = rule(claim, document)
    from . import schemas as _schemas

    evidence = []
    for path in paths:
        value = resolve(document, path)
        row = {
            "path": path,
            "value": None if value is UNRESOLVED else value,
            "resolved": value is not UNRESOLVED,
        }
        # `UX-343`: the unit of `value`, resolved from the `path` beside
        # it. This is the one shape in the report that genuinely cannot
        # declare a unit on the key - `value` is whatever field the rule
        # read - so the row carries the answer instead. Omitted rather
        # than null when the path names something the schema does not
        # describe, which is `UX-249`'s rule about absence: "no unit"
        # and "a unit nobody declared" are different facts.
        quantity = _schemas.quantity_for_path(path, ANALYZE_DOCUMENT)
        if quantity:
            row["quantity"] = quantity
        evidence.append(row)
    return {
        "claim": claim_id,
        "kind": kind,
        # Which document the paths above are relative to. Load-bearing
        # the moment a record travels: `compare/v1` carries the
        # candidate run's diagnosis chain, and its paths resolve
        # against that run's `analyze/v1`, not against the comparison
        # it is quoted inside.
        "document": ANALYZE_DOCUMENT,
        "evidence": evidence,
        "rule": dict(rule),
        "trace_query": TRACE_QUERIES.get(claim_id),
        "unpublished_inputs": list(unpublished),
    }


def attach(document: dict) -> dict:
    """Publish one record per claim in `document`, in place.

    Runs last in the report build, for the reason in the module
    docstring: a reference into a document is only checkable once the
    document exists.

    `UX-344`: **one list, not one copy per claim.** The record used to
    be written into the headline, into every finding, and - as a `see`
    path pointing back at the finding's copy - into every top action,
    which put the document's deepest shape inside the record it
    explains and gave the top action a third spelling of a reference it
    already carried. `headline.top_actions[].finding_id` and
    `findings[].id` are the claim ids; this is what they resolve into.
    """
    records = [record(document["headline"], "diagnosis", "diagnosis", document)
               ] if isinstance(document.get("headline"), dict) else []
    records += [record(finding, finding.get("id"), "finding", document)
                for finding in document.get("findings") or []]
    document["provenance"] = records
    return document


def _finding_by_id(document: dict, finding_id: Optional[str]):
    return next((f for f in document.get("findings") or []
                 if f.get("id") == finding_id), None)


def unresolved_references(document: dict) -> List[str]:
    """Every published reference that does not resolve - the guard's
    whole job, and a function rather than a test helper because a
    consumer deserves the same check.

    `UX-344`: a claim that resolves into nothing counts too. The list is
    keyed by claim id, so a `finding_id` or a finding with no record is
    the dangling reference the `see` path used to be.
    """
    dangling: List[str] = []
    published = {entry.get("claim") for entry in document.get("provenance") or []}
    for _claim, entry in claims(document):
        for cited in entry.get("evidence") or []:
            if not cited.get("resolved"):
                dangling.append(f"{entry['claim']}: {cited['path']}")
    for action in (document.get("headline") or {}).get("top_actions") or []:
        if action.get("finding_id") and action["finding_id"] not in published:
            dangling.append(
                f"headline.top_actions: {action['finding_id']} explains nothing")
    for finding in document.get("findings") or []:
        if finding.get("id") and finding["id"] not in published:
            dangling.append(f"findings: {finding['id']} explains nothing")
    return dangling


def for_claim(document: dict, claim_id: Optional[str]) -> Optional[dict]:
    """The published record for one claim id, or `None`.

    The lookup every consumer of a `finding_id` needs since `UX-344`
    stopped writing a copy of the record beside each id.
    """
    if not claim_id:
        return None
    for entry in document.get("provenance") or []:
        if entry.get("claim") == claim_id:
            return entry
    return None


def claims(document: dict):
    """`(claim, provenance)` for every published record, paired with the
    thing it explains, in the order the document lists them."""
    by_id = {"diagnosis": document.get("headline") or {}}
    for finding in document.get("findings") or []:
        by_id[finding.get("id")] = finding
    for entry in document.get("provenance") or []:
        claim = by_id.get(entry.get("claim"))
        if claim is not None:
            yield claim, entry


def render(provenance: dict, indent: str = "    ") -> List[str]:
    """The chain as text lines. One renderer for the terminal, so
    `--explain` and the page cannot word the same chain differently."""
    if not provenance or not provenance.get("rule"):
        return []
    lines = [f"{indent}why: {provenance['rule']['sentence']}"]
    rule = provenance["rule"]
    if rule.get("name"):
        lines.append(
            f"{indent}rule: {rule['name']} = {rule['threshold']} "
            f"({rule['comparison']}, {rule['module']})")
    for entry in provenance.get("evidence") or []:
        mark = "" if entry.get("resolved") else "  [unresolved]"
        lines.append(f"{indent}  {entry['path']} = {entry['value']}{mark}")
    for path in provenance.get("unpublished_inputs") or []:
        lines.append(f"{indent}  {path} = (computed, not published)")
    if provenance.get("trace_query"):
        lines.append(f"{indent}deeper: trace query `{provenance['trace_query']}`")
    return lines
