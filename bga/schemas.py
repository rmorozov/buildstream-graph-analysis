"""UX-190: the JSON outputs say what shape they are.

Field feedback: *"our analyze schema and other schemas evolved
considerably — maybe it's good idea to update them and have a command
line switch [to] output schemas [the] tool support[s] and produce[s] —
this can be later used to visualize json report."*

Round 20 ground-truthed the asymmetry. The **input** formats are
specified (`run-context/v9`, `graph/v9`, `trace/v9` in the spec's Part
32; `sources/v1` self-declares and is checked on load), and the
**output** JSON of `analyze`, `compare` and `blast` carried no version
field, had no schema anywhere in the repo, and was guarded only by
prose-consistency tests. The drift is not hypothetical: the round-19
range renamed a published compare field (`runs_outside_band` →
`edges_outside_band`) with nothing to signal it to a consumer.

**The rule** (also in the fixing guide): a field *rename or removal*
bumps the version; an *addition* does not. That is the usual contract,
and it is what lets a consumer pin `analyze/v1` and keep working while
the tool grows.

**What these schemas claim, and what they do not.** They pin the top
level: the keys that are always present, their types, and the `schema`
key itself. They deliberately do not describe every nested object -
`findings` alone has a dozen shapes across the analysis, and a schema
that tried to enumerate them would be a second implementation of the
renderer, drifting from the first. `additionalProperties` is true
everywhere, because additions are not breaking changes.

The renderers are built against this module, and a round-trip guard
validates the golden run's real output against the schema this module
produces - so a field removed from the payload without a matching
schema edit fails a test rather than a consumer.
"""
from typing import Dict, List

# UX-207: the diagnosis vocabulary is decided in `findings.py`,
# beside the ratio that decides it. Imported rather than restated,
# so the published enum and the value the pipeline emits are the
# same tuple - `UX-201`'s rule about closed sets, applied to the
# set this round adds. No cycle: `findings` reaches only
# `ingest.models` and `cache_effectiveness`, neither of which
# imports this module.
from .findings import DIAGNOSES

ANALYZE = "analyze/v1"
COMPARE = "compare/v1"
BLAST = "blast/v1"
STORE = "store/v1"
# UX-215: the two-plane join, which `bga correlate --format json` has
# emitted since UX-51 as an unversioned blob. Everything in it was
# already computed and already correct; what it lacked was a contract,
# so `bga view` could not serve it, CI could not gate on it and no
# consumer could validate it.
CORRELATE = "correlate/v1"

# The key that carries the version, and the first key of every payload -
# a consumer reading a truncated or streamed document sees it before it
# sees anything it would have to interpret.
VERSION_KEY = "schema"

# ---------------------------------------------------------------------
# View-hints v1 (`UX-193`)
#
# A schema says a field is a number. It does not say whether 4_200_000
# is microseconds, bytes, a share or a count - so every consumer that
# wants to *show* the number has to hard-code that, and the moment a
# field is added the consumer is wrong until someone edits it.
#
# These annotations put the answer in the schema, where the field is
# defined. `bga view` reads them and renders generically; so can any
# external tool, which is the point Direction 7 makes about not
# blessing a frontend stack - a TypeScript charting library that reads
# JSON Schema gets everything `bga view` gets.
#
# JSON Schema ignores unknown keywords, so annotated documents validate
# exactly as before. `UX-190`'s rules apply unchanged: adding a hint is
# an addition, changing what one *means* is a version bump.
QUANTITY = "bga:quantity"        # how to format the number
# UX-209: the question a section answers, so the heading, the TOC and
# the text renderer name it the same way. Silent -> the viewer falls
# back to `title(key)`.
QUESTION = "bga:question"
# UX-209: which part of the argument a section belongs to, so the TOC
# groups by meaning rather than by payload key order.
RAIL = "bga:rail"
RAILS = ("decide", "act", "prove", "investigate", "raw")
# UX-208: a column can say it holds element uids, which is what earns a
# row its generic Inspect - declared once, no per-table code.
ROLE = "bga:role"
ROLES = ("element",)
# UX-212: the verdict's *shape*. The trend encoded `verdict_kind` as
# fill colour alone, so grayscale, a monochrome print or a colour-blind
# reader lost the direction entirely. Declared here rather than in the
# viewer for the reason `UX-201` gives and `UX-214` proved the cost of:
# a second list of verdict kinds living in JavaScript is a vocabulary
# waiting to diverge from this one.
MARKERS = "bga:markers"
MARKER_SHAPES = ("circle", "circle-open", "triangle-up", "triangle-down",
                 "diamond", "square")
# `within_observed_range` reuses the circle, opened: it is the "the set
# cannot support the claim" answer - an undecided no-change rather than
# a fourth direction - and the shape should say so.
VERDICT_MARKERS = {
    "improved": "triangle-down",
    "regressed": "triangle-up",
    "no_significant_change": "circle",
    "within_observed_range": "circle-open",
    "not_comparable": "diamond",
}
SEVERITY = "bga:severity"          # this array carries findings
COLUMNS = "bga:columns"            # column order for an array of objects
DIRECTION = "bga:direction"        # what the sign of a delta means

# The closed set of quantities. Closed deliberately: an open vocabulary
# is one a renderer cannot be complete against, and a renderer that
# silently falls back to "print the raw number" is what this replaces.
QUANTITIES = (
    "duration_us",   # microseconds; render as a human duration
    "bytes",
    "megabytes",     # UX-201: `peak_rss_mb` is not a byte count
    "kilobytes",     # UX-215: nor is `peak_rss_kb`, and calling it
                     # `bytes` would be wrong by 1024x - which is the
                     # exact class of error UX-201 exists to stop
    "share",         # 0..1; render as a percentage
    "percent",       # UX-201: already 0..100; do not multiply again
    "count",
    "seconds",
    "ratio",         # unbounded; render as a multiplier
)

# UX-201: the verdict as a value, beside the sentence. `compare/v1`
# typed `verdict` as a plain string, so the viewer styled its banner by
# string-matching the prose ("regress"/"improve"/"not comparable") -
# which makes a reworded sentence a silent rendering change.
VERDICT_KINDS = (
    "improved",
    "regressed",
    "no_significant_change",
    "within_observed_range",
    "not_comparable",
)

# What "better" means for a signed delta, so a viewer can colour it
# without knowing which metric it is looking at.
DIRECTIONS = ("lower_is_better", "higher_is_better", "neutral")


def _check_hint(document: str, key: str, hint: dict) -> None:
    """Reject a hint a renderer could not act on.

    Caught here rather than in the viewer because a mistyped quantity is
    invisible at the point of use: the renderer falls through to its
    default and prints a raw number that looks plausible.
    """
    # UX-209: the rail a section belongs to, closed so the TOC can be
    # complete against it - an unknown rail would silently drop a
    # section out of every group.
    rail = hint.get(RAIL)
    if rail is not None and rail not in RAILS:
        raise ValueError(
            f"{document}.{key}: {RAIL}={rail!r} is not one of "
            f"{', '.join(RAILS)}")
    question = hint.get(QUESTION)
    if question is not None and not str(question).strip().endswith("?"):
        raise ValueError(
            f"{document}.{key}: {QUESTION}={question!r} is not a question")
    # UX-212: a marker map must cover the vocabulary it claims to draw
    # and must draw each kind differently - a map that assigns two
    # verdicts the same shape is a colour-only encoding again, wearing
    # a declaration.
    markers = hint.get(MARKERS)
    if markers is not None:
        if not isinstance(markers, dict):
            raise ValueError(f"{document}.{key}: {MARKERS} must be a mapping")
        unknown = set(markers) - set(VERDICT_KINDS)
        if unknown:
            raise ValueError(
                f"{document}.{key}: {MARKERS} names {sorted(unknown)}, which "
                f"is not a verdict kind")
        missing = set(VERDICT_KINDS) - set(markers)
        if missing:
            raise ValueError(
                f"{document}.{key}: {MARKERS} has no shape for "
                f"{sorted(missing)}")
        bad = [shape for shape in markers.values()
               if shape not in MARKER_SHAPES]
        if bad:
            raise ValueError(
                f"{document}.{key}: {MARKERS} shape(s) {sorted(bad)} not one "
                f"of {', '.join(MARKER_SHAPES)}")
        if len(set(markers.values())) != len(markers):
            raise ValueError(
                f"{document}.{key}: {MARKERS} gives two verdict kinds the "
                f"same shape, which is a colour-only encoding again")
    quantity = hint.get(QUANTITY)
    if quantity is not None and quantity not in QUANTITIES:
        raise ValueError(
            f"{document}.{key}: {QUANTITY}={quantity!r} is not one of "
            f"{', '.join(QUANTITIES)}")
    direction = hint.get(DIRECTION)
    if direction is not None and direction not in DIRECTIONS:
        raise ValueError(
            f"{document}.{key}: {DIRECTION}={direction!r} is not one of "
            f"{', '.join(DIRECTIONS)}")
    columns = hint.get(COLUMNS)
    if columns is not None:
        # UX-201: v2 entries are objects - {key, title, quantity,
        # sortable} - so `renderTable` stops sampling row values to
        # decide numeric-ness and the sorter stops guessing. Plain
        # strings still parse, because a column that needs nothing said
        # about it should not have to say it.
        if not isinstance(columns, (list, tuple)):
            raise ValueError(f"{document}.{key}: {COLUMNS} must be a list")
        for column in columns:
            if isinstance(column, str):
                continue
            if not isinstance(column, dict) or "key" not in column:
                raise ValueError(
                    f"{document}.{key}: every {COLUMNS} entry is a name or "
                    f"an object with a `key`")
            if column.get("quantity") is not None \
                    and column["quantity"] not in QUANTITIES:
                raise ValueError(
                    f"{document}.{key}.{column['key']}: quantity "
                    f"{column['quantity']!r} is not one of "
                    f"{', '.join(QUANTITIES)}")
            # UX-208: a column may say what its values *are*, which is
            # what earns the rows a generic Inspect. Closed, for the
            # same reason quantities are: a role a renderer cannot act
            # on is a promise nothing keeps.
            if column.get("role") is not None and column["role"] not in ROLES:
                raise ValueError(
                    f"{document}.{key}.{column['key']}: role "
                    f"{column['role']!r} is not one of {', '.join(ROLES)}")

    # UX-201: hints resolve *recursively*. The renderer walks the schema
    # node alongside the value, so a nested property carries its own
    # semantics instead of falling to name-sniffing - which is how
    # `peak_rss_mb: 512` rendered as "512 B" and a 0-100 `cpu_pct`
    # rendered as "4200.0%". Both measured before this existed.
    for nested_key, nested in (hint.get("properties") or {}).items():
        _check_hint(document, f"{key}.{nested_key}", nested)
    items = hint.get("items")
    if isinstance(items, dict):
        _check_hint(document, f"{key}[]", items)
        for nested_key, nested in (items.get("properties") or {}).items():
            _check_hint(document, f"{key}[].{nested_key}", nested)


def _document(name: str, title: str, required: Dict[str, str],
              description: str, optional: Dict[str, str] = None,
              hints: Dict[str, dict] = None) -> dict:
    """A top-level object schema: `schema` plus the always-present keys.

    `required` maps a key to its JSON Schema type name, or to `""` for a
    key whose type genuinely varies (a metric that is a number when
    measured and `null` when not).

    `hints` maps a key to its view-hints (`UX-193`), merged into that
    key's subschema. They are annotations: JSON Schema ignores keywords
    it does not know, so a hinted document validates exactly as an
    unhinted one did.
    """
    properties: Dict[str, dict] = {
        VERSION_KEY: {"const": name,
                      "description": "The shape of this document."},
    }
    for key, kind in {**required, **(optional or {})}.items():
        properties[key] = {} if not kind else {"type": [kind, "null"]}
    for key, hint in (hints or {}).items():
        # A hint for a key the document does not declare is a typo, and
        # a silent one - the renderer would simply never see it.
        if key not in properties:
            raise KeyError(f"{name}: view-hint for unknown key {key!r}")
        _check_hint(name, key, hint)
        properties[key].update(hint)
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": title,
        "description": description,
        "type": "object",
        "properties": properties,
        "required": [VERSION_KEY] + list(required),
        # Additions are not breaking changes, and a schema that forbade
        # them would turn every new signal into a version bump.
        "additionalProperties": True,
    }


# `analyze` is the one output with a variable key set: the section
# subcommands (`bga floors`, `bga graph`, ...) emit a *projection* of the
# same document, and `findings` is omitted rather than empty when there
# is nothing to conclude. So the schema requires only what every analyze
# document carries and types the rest as optional.
_ANALYZE_REQUIRED = {
    "run_id": "string",
    "total_duration_us": "",
    # Which projection this is: `null` for the full report, otherwise the
    # section name. Added by UX-190 precisely so a consumer can tell a
    # missing key ("this is `bga floors`") from a missing key ("the field
    # was removed").
    "section": "string",
}

_ANALYZE_OPTIONAL = {
    "findings": "array",
    "floors": "object",
    "attribution": "object",
    "attribution_hints": "object",
    "occupancy": "object",
    "signals": "object",
    "structural": "object",
    "utilisation": "object",
    "confidence": "object",
    "violations": "array",
    "capacity_verdict": "object",
    "run_instance": "object",
    "resource_blast": "object",
    # UX-193 found these two by serving a *real* capture: both are
    # present on every run with Plane 1 wrapper data, and absent from
    # `tests/fixtures/golden/`, so UX-190's round-trip guard - which
    # runs against the golden fixture - had never seen them. Declared
    # here as an addition (UX-190's rule: additions do not bump the
    # version), and the guard now also validates a real capture.
    "pipeline_overhead": "object",
    "timestamp_agreement": "object",
    # UX-202: present only when a Plane 2 report was in hand.
    "plane2_coverage": "object",
    # UX-215: the two-plane join, present when `--plane2` was given.
    # Same rows as `correlate/v1`'s `elements`, from the same function.
    "element_join": "array",
    "element_join_coverage": "object",
    # UX-207: what to fix first, and what it is worth.
    "headline": "object",
    "next_steps": "array",
}

# What a *full* `bga analyze --format json` of a normal run contains.
# Not part of the schema - a projection would fail it - but pinned here
# and asserted against the golden run, because this is the list a field
# rename silently shortens. `edges_outside_band` (renamed from
# `runs_outside_band` one round before this item was filed) is the case
# in point.
ANALYZE_FULL_KEYS = (
    "schema", "run_id", "total_duration_us", "section", "run_instance",
    # UX-207: the decision the run supports. In this list because it is
    # present on every full report - a run with nothing to diagnose
    # still publishes `inconclusive` rather than dropping the key, so a
    # consumer never has to tell "no diagnosis" from "no field".
    "headline",
    # UX-218: what to run next. Present on every full report - a run
    # with nothing to suggest publishes an empty list rather than
    # dropping the key, so "no next step" and "no field" stay
    # distinguishable.
    "next_steps",
    "findings", "floors", "capacity_verdict", "attribution",
    "attribution_hints", "occupancy", "signals", "structural",
    "utilisation", "confidence", "violations",
)

# UX-215: the keys a full report carries only when `--plane2` was
# given. Kept out of `ANALYZE_FULL_KEYS` because that list is what the
# pin asserts is *always* there, and a run with one plane is still a
# full report.
ANALYZE_PLANE2_KEYS = (
    "plane2_coverage", "element_join", "element_join_coverage",
)

_COMPARE_REQUIRED = {
    "baseline_run_id": "string",
    "candidate_run_id": "string",
    "baseline": "object",
    "candidate": "object",
    "deltas": "object",
    "verdict": "string",
    # UX-201: the enum beside the sentence.
    "verdict_kind": "string",
    "low_confidence": "boolean",
    "mismatches": "array",
    "failed_runs": "array",
    "attribution_deltas": "object",
    # UX-221: emitted on every comparison, so *required* rather than
    # optional. UX-190's own guard is what said so: a key the payload
    # always carries but the schema only permits is one a consumer could
    # lose without any test noticing.
    "element_deltas": "object",
}

# UX-221: `element_diff` has been emitted since UX-79 and declared by
# nothing, so `UX-190`'s contract never covered it and `bga view` had no
# reason to render it. Conditional - it is absent on a refusal - so it
# is declared without being required, which is the distinction
# `test_compares_schema_requires_every_key_it_emits` exists to force.
_COMPARE_OPTIONAL = {
    "element_diff": "object",
}

_BLAST_REQUIRED = {
    "target": "string",
    "resolved_as": "string",
    "also_matched": "array",
    "keying": "string",
    "kind": "string",
    "direct_elements": "array",
    "direct_count": "integer",
    "blast_elements": "array",
    "blast_count": "integer",
    "building_count": "integer",
    "assembling_count": "integer",
    "by_element_kind": "object",
    # UX-206: additive - the closure keyed by depth, kind and cost.
    "blast_tree": "array",
    "measured_seconds": "",
    "measured_elements": "integer",
    "element_count": "integer",
    "has_inventory": "boolean",
    "element_exists": "boolean",
    "measured": "boolean",
}


# The hints themselves. Kept beside the key lists they annotate, so a
# field and its rendering are edited in one place - `UX-190`'s finding
# was that a payload and a description in two places drift.
# UX-201: severities, as an enum rather than "whatever the renderer
# hard-coded". `renderFindings` matched five field names against a
# `findings` the schema declared as a bare array.
SEVERITIES = ("critical", "high", "warning", "medium", "low", "info")

# The element row's columns, declared once and reused for `actionable`,
# which carries the same shape. `role: "element"` is what earns every
# row `UX-208`'s Inspect with no per-table code.
_JOIN_COLUMNS = [
    {"key": "element", "title": "Element", "role": "element",
     "sortable": True},
    {"key": "critical_path_share", "title": "Share of path",
     "quantity": "share", "sortable": True},
    {"key": "potential_saving_us", "title": "Worth fixing",
     "quantity": "duration_us", "sortable": True},
    {"key": "blast_radius", "title": "Blast radius",
     "quantity": "count", "sortable": True},
    {"key": "cores_busy", "title": "Cores busy",
     "quantity": "ratio", "sortable": True},
    {"key": "requested_jobs", "title": "Jobs asked for",
     "quantity": "count", "sortable": True},
    {"key": "peak_rss_kb", "title": "Peak RSS",
     "quantity": "kilobytes", "sortable": True},
]

_JOIN_ITEM_PROPERTIES = {
    "element": {"type": "string"},
    "declared": {
        "type": "boolean",
        "description": "Whether Plane 1's declared graph knows this "
                       "element. False means Plane 2 produced a name "
                       "that looks like an element and is not one "
                       "(UX-66), and nothing may be recommended for "
                       "it."},
    "on_critical_path": {"type": "boolean"},
    "critical_path_share": {
        QUANTITY: "share",
        "description": "This element's share of the critical path - "
                       "what the chain is made of, which is a "
                       "different fact from what changing it is "
                       "worth."},
    "potential_saving_us": {
        QUANTITY: "duration_us",
        "description": "What removing this element's work entirely "
                       "would take off the makespan. Not off the path: "
                       "the difference is whatever enters the path "
                       "behind it."},
    "saving_share": {QUANTITY: "share",
                     "description": "What fixing this element would take "
                                    "off the run, as a share of its "
                                    "wall-clock."},
    "blast_radius": {
        QUANTITY: "count",
        "description": "How many elements a change here rebuilds."},
    "cores_busy": {
        QUANTITY: "ratio",
        "description": "CPU-seconds per wall-second inside the "
                       "sandbox: 1.0 is one core saturated, 4.0 is "
                       "four. Measured by Plane 2, absent without it."},
    "cpu_coverage": {
        QUANTITY: "share",
        "description": "How much of this element's wall-clock Plane 2 "
                       "actually observed. A low coverage makes "
                       "`cores_busy` a sample rather than a "
                       "measurement."},
    "requested_jobs": {
        QUANTITY: "count",
        "description": "The parallelism the element's own build "
                       "commands asked for, read from the observed "
                       "argv - not what BuildStream granted."},
    "peak_rss_kb": {
        QUANTITY: "kilobytes",
        "description": "The largest single process's resident memory, "
                       "which is what a builder count has to be "
                       "multiplied against."},
    "native_findings": {"type": ["array", "null"]},
    "unused_dependencies": {"type": ["array", "null"]},
    "recommendations": {"type": ["array", "null"]},
}

# UX-217: every unit a finding's `evidence` can be in, declared rather
# than sniffed from the key's name. Each was checked against a rendered
# value rather than inferred from its suffix - `primary` is 0.875 and a
# share, `cores_busy` is 1.60 and a ratio, `envelope_mb` is 613.7 and
# megabytes - because a guessed unit is exactly the error UX-201
# exists to stop, and `_us` is the only suffix in this vocabulary that
# is safe to read mechanically.
# UX-217 declared what each evidence key *is*; UX-220 makes each say so
# in words too. Quantity and sentence are declared together here so a key
# cannot acquire one without the other - the completeness guard reads
# this table, and a new key with no sentence fails it.
_EVIDENCE_FIELDS = {
    # Durations.
    "category_us": ("duration_us",
        "Wall-clock in the attribution category this finding is about."),
    "certified_headroom_us": ("duration_us",
        "What better scheduling alone could recover, from the certified "
        "floor. Zero means the scheduler is not the constraint."),
    "failed_task_us": ("duration_us",
        "Wall-clock spent in tasks that then failed - work the run paid "
        "for and did not keep."),
    "joint_saving_us": ("duration_us",
        "What fixing the named elements together is worth. Less than "
        "their sum, because their savings overlap on the path."),
    "lb_us": ("duration_us",
        "The resource lower bound: no schedule of this recorded work on "
        "these capacities finishes sooner."),
    "path_us": ("duration_us",
        "The critical path's duration - the chain, not the wall-clock."),
    "sum_of_individual_us": ("duration_us",
        "The savings added one at a time, which double-counts the "
        "overlap. Published beside `joint_saving_us` to show the gap."),
    "t_infinity_us": ("duration_us",
        "The critical path with builders unlimited - the floor the "
        "graph's shape imposes by itself."),
    "transfer_us": ("duration_us",
        "Wall-clock spent moving artifacts rather than building them."),
    # Shares and ratios.
    "criticality_probability": ("share",
        "How often this element came out on the critical path across the "
        "schedules considered - not a certainty that it is on it."),
    "efficiency_score": ("share",
        "Makespan against the certified floor. Measured against a bound "
        "this run proved, never against an ideal build."),
    "hit_ratio": ("share",
        "Cache hits as a share of lookups."),
    "largest_wait_share": ("share",
        "The biggest single wait category, as a share of wall-clock."),
    "primary": ("share",
        "How much of this run's own record supports the conclusion."),
    "share": ("share",
        "This finding's quantity as a share of the run's wall-clock."),
    "share_of_host": ("share",
        "As a share of what the host offers - not of what the build "
        "asked for."),
    "share_of_path": ("share",
        "As a share of the critical path - not of wall-clock."),
    "target_closure_hit_ratio": ("share",
        "Cache hits within the target's own dependency closure, which is "
        "the part a change to the target can affect."),
    "transfer_share": ("share",
        "Artifact transfer as a share of wall-clock."),
    "zero_slack_share": ("share",
        "Elements with no slack, as a share of all of them - how much of "
        "the graph sits on a critical path."),
    # Counts.
    "blast_count": ("count",
        "Elements a change here rebuilds, transitively."),
    "builders": ("count",
        "Builder slots this run recorded. BuildStream's scheduler slots, "
        "not host cores."),
    "built_elements": ("count",
        "Elements that actually built, rather than coming from cache."),
    "cached_elements": ("count",
        "Elements served from cache, whose recorded time is a restore "
        "and not work."),
    "critical_path_cached": ("count",
        "Critical-path elements that came from cache - each one makes "
        "the path's duration a restore time, not a build time."),
    "direct_count": ("count",
        "Immediate consumers only, not the transitive closure."),
    "element_count": ("count",
        "Elements this finding is about."),
    "elements_measured": ("count",
        "Elements the process capture measured, which can be fewer than "
        "the run built."),
    "failed_count": ("count",
        "Elements that failed. The time they spent was paid and not "
        "kept, so it counts against the run without building anything."),
    "failed_task_count": ("count",
        "Tasks that failed. Higher than the element count when a task "
        "was retried."),
    "first_builders_that_does_not_fit": ("count",
        "The smallest builder count whose measured peaks would exceed "
        "the host's memory. A bound from what was measured, not advice."),
    "host_cpu_count": ("count",
        "Cores the host reported. Not what the build was allowed to use."),
    "native_max_jobs": ("count",
        "The build system's own parallelism inside one element "
        "(--max-jobs) - a separate axis from builder count."),
    "recommended_builders": ("count",
        "The builder count this run's evidence supports, bounded by "
        "memory wherever memory was measured."),
    "violation_count": ("count",
        "Ordering violations in the recorded log. Each one weakens every "
        "timing conclusion drawn from it."),
    # Everything else.
    "envelope_mb": ("megabytes",
        "Peak resident memory the run would need at the recommended "
        "builder count."),
    "host_memory_mb": ("megabytes",
        "Memory the host reported."),
    "cores_busy": ("ratio",
        "CPU-seconds per wall-second inside the element - how much "
        "parallelism its own build actually achieved."),
    "measured_seconds": ("seconds",
        "Wall-clock actually measured, as opposed to estimated."),
}

EVIDENCE_QUANTITIES = {
    key: {QUANTITY: quantity, "description": sentence}
    for key, (quantity, sentence) in _EVIDENCE_FIELDS.items()
}

_ANALYZE_HINTS = {
    "timestamp_agreement": {QUESTION: 'Do the two planes agree about the clock?', RAIL: 'prove'},
    "run_instance": {QUESTION: 'Which capture is this?', RAIL: 'raw'},
    "resource_blast": {QUESTION: 'What does one shared resource rebuild?', RAIL: 'investigate'},
    "capacity_verdict": {
        QUESTION: 'Was the capacity right for this build?',
        RAIL: 'prove',
        "description": "Whether this run's capacities suited its work - "
                       "and whether the checks could run at all. A check "
                       "that did not run is inert, not passing.",
        "properties": {
            "oversubscribed": {
                "description": "Whether the run asked for more parallelism "
                               "than the host could serve. False also when "
                               "the checks did not run - read `checks_ran` "
                               "before reading this."},
            "undersubscribed": {
                "description": "Whether the host could have served more "
                               "parallelism than the run asked for. Carries "
                               "the same caveat as `oversubscribed`."},
            "checks_ran": {
                "description": "Whether the inputs these checks need were "
                               "present. When false the two verdicts above "
                               "are silent, not negative."},
            "skipped_inputs": {
                "description": "The missing inputs, named - so a reader can "
                               "supply them rather than guess why the check "
                               "said nothing."},
        },
    },
    "violations": {QUESTION: 'What did not add up?', RAIL: 'prove'},
    "structural": {QUESTION: 'What shape is this dependency graph?', RAIL: 'investigate'},
    "occupancy": {
        QUESTION: 'Were the builders busy?',
        RAIL: 'prove',
        "description": "How busy the builder slots were across the run's "
                       "horizon. Slot-time, not CPU time: a build of H "
                       "seconds on N builders has N*H of it to spend.",
        "properties": {
            "average_concurrency": {
                QUANTITY: "ratio",
                "description": "Tasks running at once, averaged over the "
                               "horizon. An average, so it hides a run "
                               "that alternated saturation and idleness."},
            "peak_concurrency": {
                QUANTITY: "count",
                "description": "The most tasks that ran at once - a high "
                               "-water mark, reached perhaps only once."},
            "horizon_start_us": {
                QUANTITY: "duration_us",
                "description": "Where this accounting starts, offset from "
                               "the run's own zero."},
            "horizon_end_us": {
                QUANTITY: "duration_us",
                "description": "Where it ends. Beyond it nothing was "
                               "scheduled, so nothing is counted."},
            "horizon_us": {
                QUANTITY: "duration_us",
                "description": "The span the ratios below divide by - the "
                               "scheduled window, which can be shorter "
                               "than the run's wall-clock."},
            "idle_us": {
                QUANTITY: "duration_us",
                "description": "Slot-time with nothing running at all. "
                               "More builders cannot recover this; only a "
                               "different graph shape can."},
            "resource_occupancy": {
                "description": "Occupancy per resource kind, so a "
                               "saturated fetcher is not averaged away by "
                               "idle builders."},
            "peak_resource_occupancy": {
                "description": "The most in flight at once, per resource "
                               "kind."},
        },
    },
    "signals": {
        QUESTION: 'Which elements are on the chain that binds?',
        RAIL: 'act',
        "description": "The graph's own account of where the time is: "
                       "which elements lie on the chain, what slack the "
                       "rest have, and what fixing each in turn is worth.",
        # UX-208: the three element tables a reader lands on from the
        # decision panel. They carry element uids, so they say so - and
        # every row earns the same Inspect with no per-table code.
        "properties": {
            "critical_path_detail": {
                "description": "The chain itself, element by element. "
                               "The longest path through the graph as "
                               "this run recorded it - a cached element "
                               "on it contributes its restore, not its "
                               "build.",
                COLUMNS: [
                    {"key": "element_uid", "title": "Element",
                     "role": "element", "sortable": True},
                    {"key": "element_kind", "title": "Kind", "sortable": True},
                    {"key": "duration_us", "title": "Duration",
                     "quantity": "duration_us", "sortable": True},
                    {"key": "share_of_path", "title": "Share of path",
                     "quantity": "share", "sortable": True},
                    {"key": "realizable_saving_us", "title": "Realizable",
                     "quantity": "duration_us", "sortable": True,
                     "description": "What removing this element entirely "
                                    "would take off the makespan, not off "
                                    "the path."},
                ],
            },
            "optimization_horizon": {
                "description": "What fixing the top elements in turn is "
                               "worth, in order. The savings stop adding "
                               "up because each fix lets other elements "
                               "onto the path - which is why this is a "
                               "sequence and not a sum.",
                COLUMNS: [
                    {"key": "element_uid", "title": "Element",
                     "role": "element", "sortable": True},
                    {"key": "saving_us", "title": "Saving",
                     "quantity": "duration_us", "sortable": True},
                    {"key": "makespan_after_us", "title": "Makespan after",
                     "quantity": "duration_us", "sortable": True},
                    {"key": "cumulative_saving_us", "title": "Cumulative",
                     "quantity": "duration_us", "sortable": True},
                ],
            },
            "latent_heavies": {
                "description": "Heavy elements not on the path today. "
                               "They cost nothing now and become the "
                               "constraint once what is above them is "
                               "fixed.",
                COLUMNS: [
                    {"key": "element_uid", "title": "Element",
                     "role": "element", "sortable": True},
                    {"key": "duration_us", "title": "Duration",
                     "quantity": "duration_us", "sortable": True},
                ],
            },
        },
    },
    "attribution": {QUESTION: 'Where did the wall-clock go?', RAIL: 'act'},
    # UX-220: a floor is the number in this report most easily read as a
    # prediction, and it is not one. Every member says what it is, what it
    # is not, and what it rests on - and the text report reads these same
    # sentences back out of the schema rather than keeping its own.
    "floors": {
        QUESTION: 'How much faster could this build possibly be?',
        RAIL: 'prove',
        "description": "Lower bounds this run certifies: what no schedule "
                       "of the same recorded work could have beaten. "
                       "Floors, not forecasts - beating one needs the "
                       "graph or the work to change, not the scheduler.",
        "properties": {
            "t_infinity_observed": {
                QUANTITY: "duration_us",
                "description": "The critical path's duration - the floor "
                               "the graph's shape imposes on its own, with "
                               "builders unlimited. Observed, from this "
                               "run's own recorded durations."},
            "lb": {
                QUANTITY: "duration_us",
                "description": "The resource lower bound: no schedule of "
                               "this run's recorded work on the capacities "
                               "it recorded finishes sooner. A floor this "
                               "run proves, not an estimate of a rerun."},
            "certified_headroom": {
                QUANTITY: "duration_us",
                "description": "Makespan minus the lower bound - what "
                               "scheduling alone could still recover. Zero "
                               "means the scheduler is not the constraint."},
            "t_c": {
                QUANTITY: "duration_us",
                "description": "The makespan a replay of this run's "
                               "recorded work produces. A check on the "
                               "model behind the floors, not a prediction."},
            "model_slack": {
                QUANTITY: "duration_us",
                "description": "How far the replay sits above the lower "
                               "bound - the model's own slack. Published "
                               "so it cannot be mistaken for headroom."},
            "efficiency_score": {
                QUANTITY: "ratio",
                "description": "Makespan against the certified floor. A "
                               "ratio against a bound this run proved, "
                               "never against an ideal build."},
            "occupancy_ratio": {
                QUANTITY: "share",
                "description": "Slot-time used as a share of slot-time "
                               "available. Unlike the efficiency score it "
                               "falls when independent work is serialized."},
            "t_infinity_cold": {
                QUANTITY: "duration_us",
                "description": "The critical path with cached elements "
                               "costed at what building them would take. "
                               "Advisory: it rests on other runs' "
                               "durations, so it certifies nothing here."},
            "cold_partial": {
                "description": "Whether some elements had no duration to "
                               "draw on, making the cold path a partial "
                               "figure rather than a complete one."},
            "cold_confidence": {
                "description": "How far the cold path can be trusted - it "
                               "is only as good as the history it drew "
                               "its durations from."},
            "cold_duration_sources": {
                "description": "Where each cold duration came from, by "
                               "tier, so the figure can be judged rather "
                               "than taken."},
            "cold_critical_path_duration_sources": {
                "description": "The same provenance, narrowed to the "
                               "elements actually on the cold path."},
            "capacity_model_note": {
                "description": "What these floors certify against, in "
                               "words - and, as importantly, what they do "
                               "not."},
        },
    },
    "total_duration_us": {
        QUANTITY: "duration_us",
        "description": "The run's wall-clock, end to end. The denominator "
                       "of every share in this document.",
    },
    "pipeline_overhead": {
        QUESTION: 'What did BuildStream spend outside the elements?',
        RAIL: 'investigate',
        COLUMNS: [
            {"key": "phase", "title": "Phase", "sortable": True},
            {"key": "elapsed_us", "title": "Elapsed",
             "quantity": "duration_us", "sortable": True},
        ],
        "properties": {
            "total_us": {QUANTITY: "duration_us",
                         "description": "Time BuildStream spent outside any "
                                        "element - loading, resolving, cache "
                                        "queries."},
            "fraction_of_horizon": {
                QUANTITY: "share",
                "description": "That time as a share of the run. Overhead "
                               "no element can be blamed for, and no "
                               "builder count reduces."},
        },
    },
    "findings": {
        QUESTION: 'What did this run conclude?',
        RAIL: 'decide',
        SEVERITY: "severity",
        COLUMNS: ["severity", "title", "detail", "elements"],
        # The item shape, so the semantic renderer reads a declared
        # contract instead of five hardcoded names.
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "severity": {"type": "string", "enum": list(SEVERITIES)},
                "title": {"type": "string"},
                "detail": {"type": ["array", "string", "null"]},
                "elements": {"type": ["array", "null"]},
                # UX-217: the numbers a finding was drawn from, and
                # what unit each is in. `renderFindings` read the
                # conclusion and dropped these on the floor - in a tool
                # whose whole proposition is that its conclusions are
                # measured rather than guessed.
                "evidence": {"type": ["object", "null"],
                             "properties": EVIDENCE_QUANTITIES},
                "copy_text": {
                    "description": "This finding as plain text: its "
                                   "title, its evidence in declared "
                                   "units, the elements it names, the "
                                   "published next step, and the run "
                                   "identity. Rendered in the pipeline "
                                   "so the page copies it rather than "
                                   "wording it - a pasted finding and "
                                   "the CI comment cannot then say the "
                                   "same thing differently."},
            },
            "required": ["id", "severity", "title"],
        },
    },
    "confidence": {
        QUESTION: 'How much of this can be believed?',
        RAIL: 'prove',
        "properties": {
            "primary": {QUANTITY: "share",
                        "description": "How much of this run's own record "
                                       "supports the conclusions above - "
                                       "coverage, provenance and model fit "
                                       "combined."},
            "band": {"description": "The score as a word, from the same "
                                    "thresholds the report's headline uses."},
            "coverage_score": {
                QUANTITY: "share",
                "description": "How much of the run the record accounts "
                               "for. A high score on a thin record still "
                               "means the record was thin."},
            "task_coverage": {
                QUANTITY: "share",
                "description": "The share of tasks carrying the timings "
                               "this analysis needs. Tasks without them "
                               "are excluded, never assumed."},
        },
    },
    # UX-215: the join, rendered by the same machinery as any other
    # table - which is the whole reason it is declared rather than
    # special-cased. `role: "element"` earns every row UX-208's Inspect.
    "element_join": {
        QUESTION: 'What does each element look like from both planes?',
        RAIL: "investigate",
        COLUMNS: _JOIN_COLUMNS,
        "description": "Plane 1's place in the graph beside Plane 2's "
                       "measurement inside the sandbox, per element. "
                       "Present only when `--plane2` supplied a report: "
                       "there is no join with one plane.",
        "items": {"type": "object", "properties": _JOIN_ITEM_PROPERTIES,
                  "required": ["element", "declared"]},
    },
    "element_join_coverage": {
        QUESTION: 'How much of the build did the two planes agree on?',
        RAIL: "prove",
        "description": "How far the join reaches. The two planes see "
                       "different things, and an element only one of them "
                       "saw carries only that plane's fields.",
        "properties": {
            "joined_elements": {
                QUANTITY: "count",
                "description": "Elements both planes saw - the only ones "
                               "carrying a full row."},
            "plane1_elements": {
                QUANTITY: "count",
                "description": "Elements the scheduling record knows. "
                               "Everything the build ran, whether or not "
                               "anything looked inside it."},
            "plane2_elements": {
                QUANTITY: "count",
                "description": "Elements the process capture saw inside. "
                               "Fewer whenever a capture was partial."},
        },
    },
    "next_steps": {
        QUESTION: 'What should I run next?',
        RAIL: "decide",
        "description": "The next commands, chosen by what this run "
                       "measured. Decided in the pipeline rather than "
                       "by a consumer, so the terminal, CI and the "
                       "page cannot advise differently - and a step "
                       "whose precondition this run does not meet is "
                       "absent rather than offered and broken.",
        COLUMNS: [
            {"key": "reason", "title": "Why", "sortable": False},
            {"key": "argv", "title": "Run", "sortable": False},
            {"key": "follows_from", "title": "From", "sortable": False},
        ],
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "reason": {"type": "string",
                           "description": "Why this step, in terms of "
                                          "the values that chose it."},
                "argv": {"type": "array",
                         "description": "The command, with the run and "
                                        "the element already "
                                        "substituted. Executable as "
                                        "spelled."},
                "follows_from": {"type": "string",
                                 "description": "The finding or the "
                                                "published field this "
                                                "step was chosen by, so "
                                                "the advice can be "
                                                "checked against the "
                                                "number behind it."},
            },
            "required": ["id", "reason", "argv"],
        },
    },
    "headline": {
        QUESTION: 'What should I fix first, and what is it worth?',
        RAIL: 'decide',
        "description": "The decision this run supports: which constraint "
                       "binds, what the opportunity is worth, and which "
                       "elements to look at first. Decided in the "
                       "pipeline so no consumer re-derives it.",
        "properties": {
            "diagnosis": {"enum": list(DIAGNOSES),
                          "description": "Whether the chain or the "
                                         "scheduler is the constraint, or "
                                         "neither where the run did not "
                                         "record enough to say."},
            "chain_ratio": {QUANTITY: "share",
                            "description": "The critical path as a share "
                                           "of wall-clock - the number the "
                                           "diagnosis is decided by."},
            "chain_bound_ratio": {QUANTITY: "share",
                                  "description": "The threshold "
                                                 "`chain_ratio` is compared "
                                                 "against."},
            "certified_headroom_us": {
                QUANTITY: "duration_us",
                "description": "What scheduling alone could still recover, "
                               "repeated here from `floors` so the "
                               "decision needs no second lookup."},
            "scheduling_gap_us": {
                QUANTITY: "duration_us",
                "description": "Wall-clock beyond the critical path. "
                               "Published rather than left as a "
                               "subtraction for a consumer to perform."},
            "top_actions": {
                COLUMNS: [
                    {"key": "element_uid", "title": "Element", "role": "element",
                     "sortable": True},
                    {"key": "saving_us", "title": "Worth",
                     "quantity": "duration_us", "sortable": True},
                    {"key": "finding_id", "title": "Reasoning in",
                     "sortable": False},
                ],
                "items": {
                    "properties": {
                        "saving_us": {
                            QUANTITY: "duration_us",
                            "description": "What fixing this element is "
                                           "worth on its own, before any "
                                           "other fix moves the path."},
                        "downstream_count": {
                            QUANTITY: "count",
                            "description": "Elements a change here "
                                           "rebuilds - the cost of "
                                           "touching it, beside the gain."},
                    },
                },
            },
        },
    },
    "plane2_coverage": {
        QUESTION: 'How much did Plane 2 see?',
        RAIL: 'prove',
        "properties": {
            "processes": {QUANTITY: "count",
                          "description": "Processes Plane 2 saw across both "
                                         "record streams - the hook and the "
                                         "spine, counted once each."},
            "opens_coverage": {QUANTITY: "share",
                               "description": "The share of those processes "
                                              "whose opened paths were "
                                              "recorded; only the hook can "
                                              "see them."},
            "cpu_disagreement_count": {
                QUANTITY: "count",
                "description": "Processes the hook and the spine costed "
                               "differently. Each one is a place the two "
                               "record streams disagree, not an error."},
            "exec_chains_collapsed": {
                QUANTITY: "count",
                "description": "Exec chains billed to one process rather "
                               "than counted repeatedly - a shell that "
                               "execs a compiler is one process, not two."},
        },
    },
    "utilisation": {
        QUESTION: 'What did the machine cost to run this?',
        RAIL: 'investigate',
        "description": "Where the run's slot-time went, reconciled against "
                       "the capacity it had. Slot-time again, not CPU "
                       "time - `bga` does not measure host cores.",
        "properties": {
            # UX-220: these are the keys `_compute_utilization` actually
            # emits. Until this item they were `peak_rss_mb`, `cpu_pct`
            # and `cpu_seconds` - three names no code path has ever put
            # in this object, so UX-201's hints described a shape that
            # did not exist and every real member of it went unhinted.
            # The lesson those three carried is kept where it is live:
            # `element_join[].peak_rss_kb` is the published peak-memory
            # field, and `megabytes` remains a declared quantity.
            "cpu_accounting_available": {
                "description": "Whether the run recorded enough to account "
                               "for its slot-time at all. When false every "
                               "figure below is absent, not zero."},
            "effective_cpus": {
                QUANTITY: "count",
                "description": "The capacity this accounting divides by. "
                               "Builder slots as recorded, not host cores."},
            "effective_cpus_source": {
                "description": "How that capacity was established - "
                               "measured, declared, or assumed. An assumed "
                               "capacity makes every share below assumed."},
            "wall_clock_us": {
                QUANTITY: "duration_us",
                "description": "The span this accounting covers."},
            "capacity_cpu_us": {
                QUANTITY: "duration_us",
                "description": "Slot-time available across that span - "
                               "wall-clock times the capacity. The "
                               "denominator of the percentages below."},
            "buckets": {
                "description": "Slot-time split by what it was doing: "
                               "useful work, idleness with nothing ready, "
                               "idleness with too little parallelism, and "
                               "work thrown away by retry or rebuild."},
            "total_accounted_us": {
                QUANTITY: "duration_us",
                "description": "The buckets summed. Compared against "
                               "capacity to check the accounting closes."},
            "unaccounted_us": {
                QUANTITY: "duration_us",
                "description": "Slot-time no bucket claimed. Non-zero here "
                               "is a gap in the record, and it weakens "
                               "every share this object publishes."},
            "reconciliation_error_pct": {
                QUANTITY: "percent",
                "description": "That gap as a percentage. The honesty "
                               "check on this whole object: near zero "
                               "means the buckets really do cover it."},
            "potential_oversubscription": {
                "description": "Whether the evidence hints the run asked "
                               "for more than it could get. A hint from "
                               "this accounting, not the capacity verdict."},
            "oversubscription_evidence": {
                "description": "What that hint rests on, including the "
                               "case where there was not enough to say."},
            "max_observed_concurrency": {
                QUANTITY: "count",
                "description": "The most tasks seen running together in "
                               "this accounting's own view of the run."},
            "useful_pct": {
                QUANTITY: "percent",
                "description": "Slot-time that did work kept, as a share "
                               "of capacity. Not a share of wall-clock."},
            "idle_pct": {
                QUANTITY: "percent",
                "description": "Slot-time with nothing to run. Bounded "
                               "below by the graph's shape, so it is never "
                               "entirely recoverable."},
            "wasted_pct": {
                QUANTITY: "percent",
                "description": "Slot-time spent on work that was then "
                               "thrown away - retries and rebuilds. This "
                               "is the recoverable share."},
        },
    },
}

_COMPARE_HINTS = {
    # UX-221: which elements the run's verdict is actually about.
    "element_deltas": {
        QUESTION: 'Which elements caused this?',
        RAIL: 'act',
        "description": "Every element in either run, with its duration on "
                       "each side and the signed change. Ranked by what "
                       "moved most. These deltas are **not banded** - "
                       "judging one element against a set of runs is a "
                       "question this does not answer, so a row states "
                       "its change and the run's verdict and no more.",
        "properties": {
            "ranked_by": {
                "description": "What the ordering means, so a consumer "
                               "does not re-sort by something else and "
                               "call it the same ranking."},
            "banded": {
                "description": "Always false, and published rather than "
                               "left implicit: no per-element noise band "
                               "exists, so no row's verdict rests on one."},
            "counts": {
                "description": "How many elements grew, shrank, stayed "
                               "put, appeared and disappeared - the shape "
                               "of the change before any single row."},
            "rows": {
                COLUMNS: [
                    {"key": "element_uid", "title": "Element",
                     "role": "element", "sortable": True},
                    {"key": "baseline_us", "title": "Before",
                     "quantity": "duration_us", "sortable": True},
                    {"key": "candidate_us", "title": "After",
                     "quantity": "duration_us", "sortable": True},
                    {"key": "delta_us", "title": "Change",
                     "quantity": "duration_us", "sortable": True,
                     "description": "Candidate minus baseline. Absent, "
                                    "not zero, where an element is in "
                                    "only one of the runs."},
                    {"key": "presence", "title": "Presence",
                     "sortable": True},
                    {"key": "verdict_kind", "title": "Verdict",
                     "sortable": True},
                ],
                DIRECTION: "lower_is_better",
                "items": {
                    "properties": {
                        "baseline_us": {
                            QUANTITY: "duration_us",
                            "description": "What this element cost in the "
                                           "baseline run. Absent if it did "
                                           "not exist there."},
                        "candidate_us": {
                            QUANTITY: "duration_us",
                            "description": "What it cost in the candidate "
                                           "run. Absent if it is gone."},
                        "delta_us": {
                            QUANTITY: "duration_us",
                            "description": "Candidate minus baseline, so "
                                           "negative is faster. Absent "
                                           "rather than zero when there is "
                                           "nothing to subtract."},
                        "presence": {
                            "enum": ["both", "appeared", "disappeared"],
                            "description": "Whether both runs had this "
                                           "element. An element in one run "
                                           "only has no delta at all - "
                                           "reading it as a change from "
                                           "zero would make a removed "
                                           "element the run's biggest "
                                           "improvement."},
                        "verdict_kind": {
                            "enum": list(VERDICT_KINDS),
                            MARKERS: VERDICT_MARKERS,
                            "description": "The same closed vocabulary the "
                                           "run verdict uses. "
                                           "`not_comparable` where there "
                                           "is no delta; the run's own "
                                           "kind where the run came out "
                                           "inside its observed range, so "
                                           "noise is never coloured as a "
                                           "regression."},
                    },
                },
            },
        },
    },
    "element_diff": {
        QUESTION: 'What did this change add or remove?',
        RAIL: 'investigate',
        "description": "The elements this change introduced, removed, or "
                       "moved onto the critical path (UX-79). Complements "
                       "`element_deltas`, which covers the elements both "
                       "runs share.",
    },
    # Every delta in this object is a *change*, and for every metric bga
    # compares, smaller is the improvement - duration, contention,
    # serialization. A viewer colours the sign from this without knowing
    # which metric it has.
    "deltas": {
        DIRECTION: "lower_is_better",
        # UX-201: and each member says what it *is*. Before this, a
        # hinted section still formatted its own members by name.
        "properties": {
            "total_duration_us": {
                QUANTITY: "duration_us",
                "description": "Change in wall-clock, candidate minus "
                               "baseline. Negative is faster."},
            "contention_us": {
                QUANTITY: "duration_us",
                "description": "Change in time lost waiting for a busy "
                               "resource."},
            "serialization_us": {
                QUANTITY: "duration_us",
                "description": "Change in time independent work spent "
                               "running one after another."},
            "efficiency_pct": {
                QUANTITY: "percent",
                "description": "Change in makespan against the certified "
                               "floor. Each run is measured against its "
                               "own floor, so this compares two ratios "
                               "and not two durations."},
            "inefficiency_ratio": {
                QUANTITY: "ratio",
                "description": "Change in the gate's ratio - the figure "
                               "`--fail-on` thresholds are read against."},
        },
    },
    "attribution_deltas": {DIRECTION: "lower_is_better"},
    "mismatches": {
        COLUMNS: [
            {"key": "field", "title": "Field", "sortable": True},
            {"key": "baseline", "title": "Baseline", "sortable": False},
            {"key": "candidate", "title": "Candidate", "sortable": False},
        ],
    },
    "verdict_kind": {
        # UX-214: the closed set, published. `UX-201` promised external
        # consumers an enum and delivered a Python constant plus a map
        # in the viewer - the two places inside this repository. A
        # consumer reading the schema saw `["string", "null"]` and no
        # vocabulary at all.
        "enum": list(VERDICT_KINDS) + [None],
        "description": "The verdict as a value rather than a sentence, so a "
                       "consumer styles from it and a reworded sentence is "
                       "not a rendering change.",
    },
}

_BLAST_HINTS = {
    "direct_count": {QUANTITY: "count",
                     "description": "Elements that depend on this one "
                                    "directly. The first hop only."},
    "blast_count": {QUANTITY: "count",
                    "description": "Everything a change here rebuilds, "
                                   "transitively - the number that makes "
                                   "a small element expensive to touch."},
    "building_count": {QUANTITY: "count",
                       "description": "Of those, the ones that do real "
                                      "build work."},
    "assembling_count": {QUANTITY: "count",
                         "description": "Of those, the ones that only "
                                        "gather what is below them - they "
                                        "rebuild, but cost little."},
    "element_count": {QUANTITY: "count",
                      "description": "Elements in the project, as the "
                                     "denominator for the reach above."},
    "measured_elements": {QUANTITY: "count",
                          "description": "How many of the affected "
                                         "elements have a recorded "
                                         "duration. The rest are counted, "
                                         "never estimated."},
    "measured_seconds": {QUANTITY: "seconds",
                         "description": "Recorded rebuild time below this "
                                        "element. A sum over the measured "
                                        "elements only, so it is a lower "
                                        "bound on the real cost."},
    # UX-206: the closure as a hierarchy rather than a flat list. The
    # depth is what an indented tree needs, and deriving it in the
    # viewer would be a graph walk in JavaScript - a second analysis.
    "blast_tree": {
        COLUMNS: [
            {"key": "element_uid", "title": "Element", "role": "element", "sortable": True},
            {"key": "depth", "title": "Depth", "quantity": "count",
             "sortable": True,
             "description": "Hops from the direct consumers. Breadth-first, "
                            "so an element reachable by two paths is listed "
                            "at the shorter one."},
            {"key": "element_kind", "title": "Kind", "sortable": True},
            {"key": "measured_seconds", "title": "Measured",
             "quantity": "seconds", "sortable": True},
        ],
        "items": {
            "properties": {
                "depth": {QUANTITY: "count",
                          "description": "Hops from the direct consumers, "
                                         "breadth-first."},
                "measured_seconds": {QUANTITY: "seconds",
                                     "description": "This element's own "
                                                    "recorded duration, "
                                                    "not its subtree's."},
            },
        },
    },
}

_STORE_REQUIRED = {
    "project": "string",
    "snapshots": "array",
    "count": "integer",
    "total_bytes": "integer",
}

_STORE_HINTS = {
    "total_bytes": {QUANTITY: "bytes",
                    "description": "What the stored snapshots occupy on "
                                   "disk, together."},
    "count": {QUANTITY: "count",
              "description": "Snapshots held. The length of every trend "
                             "drawn from this store."},
    # UX-203: duration leads, because "is this project drifting" is a
    # question about time. Size is still here - it is what the store
    # warning is about - but it stopped being the answer.
    "snapshots": {COLUMNS: ["stamp", "total_duration_us", "verdict_kind",
                            "cache_hit_rate", "bytes", "alias",
                            "incomplete_reason"],
                  "items": {
                      "properties": {
                          # UX-214: the same closed set as `compare/v1`.
                          # These rows used to carry `within_band`, a
                          # sixth value that existed only here.
                          "verdict_kind": {
                              "enum": list(VERDICT_KINDS) + [None],
                              # UX-212: the shape the trend draws for
                              # each kind. One source, validated to
                              # cover the vocabulary and to give no two
                              # kinds the same shape.
                              MARKERS: VERDICT_MARKERS,
                          },
                          "total_duration_us": {
                              QUANTITY: "duration_us",
                              "description": "That run's wall-clock. "
                                             "Comparable across snapshots "
                                             "only as far as the runs "
                                             "themselves are comparable."},
                          "cache_hit_rate": {
                              QUANTITY: "share",
                              "description": "Cache hits as a share of "
                                             "lookups in that run - the "
                                             "usual reason two runs of the "
                                             "same project differ."},
                          "bytes": {
                              QUANTITY: "bytes",
                              "description": "What that snapshot occupies "
                                             "on disk."},
                          # UX-226: a *history*, not an archive. Bounded
                          # at capture time to the elements that were
                          # worth looking at in that run - the critical
                          # path and the top actions - so the store does
                          # not become a second copy of every report.
                          "elements": {
                              "description": "What this run cost the "
                                             "elements worth watching: "
                                             "the critical path and the "
                                             "top actions, bounded. "
                                             "`null` - not an empty list "
                                             "- for a snapshot captured "
                                             "before this existed, so a "
                                             "reader is told there is no "
                                             "history rather than shown "
                                             "a flat line at zero.",
                              COLUMNS: [
                                  {"key": "element_uid", "title": "Element",
                                   "role": "element", "sortable": True},
                                  {"key": "duration_us", "title": "Duration",
                                   "quantity": "duration_us", "sortable": True},
                                  {"key": "share_of_path",
                                   "title": "Share of path",
                                   "quantity": "share", "sortable": True},
                              ],
                              "items": {
                                  "properties": {
                                      "duration_us": {
                                          QUANTITY: "duration_us",
                                          "description": "What this "
                                                         "element cost in "
                                                         "that run."},
                                      "share_of_path": {
                                          QUANTITY: "share",
                                          "description": "Its share of "
                                                         "that run's "
                                                         "critical path. "
                                                         "Absent for an "
                                                         "element that "
                                                         "was not on it - "
                                                         "zero would read "
                                                         "as on the path "
                                                         "and costing "
                                                         "nothing."},
                                      "on_critical_path": {
                                          "description": "Whether it was "
                                                         "on the chain in "
                                                         "that run. An "
                                                         "element can "
                                                         "leave the path "
                                                         "between runs, "
                                                         "and that is "
                                                         "usually the "
                                                         "answer a reader "
                                                         "is looking "
                                                         "for."},
                                  },
                              },
                          },
                      },
                  }},
}

# UX-215: `correlate/v1`. Every key below is one `bga correlate
# --format json` has emitted since `UX-51`; nothing here is new
# analysis, renamed or reshaped. The document is the join, and the join
# is the only place in this tool where "this element is on the path, is
# worth 12.05s, and was pinned to one job on four cores" is a single
# row.
_CORRELATE_REQUIRED = {
    "run_id": "string",
    "run_instance": "object",
    # One row per element seen by either plane - `ElementJoin`, as
    # `bga/correlate.py` already builds it.
    "elements": "array",
    # The subset the join is willing to recommend on, ranked. Separate
    # from `elements` because `UX-66`'s rule is that an element Plane 2
    # named and Plane 1 never declared may appear, and may never carry
    # a recommendation.
    "actionable": "array",
    "ranking": "object",
    "coverage": "object",
    "note": "string",
}

_CORRELATE_OPTIONAL = {
    "restructuring": "array",
    "granularity": "array",
    "memory_envelope": "object",
    "attribution_unreliable": "",
    "attribution_partial": "",
}

_CORRELATE_HINTS = {
    "elements": {
        QUESTION: 'What does each element look like from both planes?',
        RAIL: "investigate",
        COLUMNS: _JOIN_COLUMNS,
        "items": {"type": "object", "properties": _JOIN_ITEM_PROPERTIES,
                  "required": ["element", "declared"]},
    },
    "actionable": {
        QUESTION: 'Which elements is the join willing to act on?',
        RAIL: "act",
        COLUMNS: _JOIN_COLUMNS,
        "items": {"type": "object", "properties": _JOIN_ITEM_PROPERTIES,
                  "required": ["element", "declared"]},
        "description": "Ranked by what a fix is worth. An element Plane "
                       "2 named that Plane 1 never declared is in "
                       "`elements` and never here.",
    },
    "coverage": {
        QUESTION: 'How much of the build did the two planes agree on?',
        RAIL: "prove",
        "description": "How far the join reaches. The two planes see "
                       "different things, and an element only one of them "
                       "saw carries only that plane's fields.",
        "properties": {
            "joined_elements": {
                QUANTITY: "count",
                "description": "Elements both planes saw - the only ones "
                               "carrying a full row."},
            "plane1_elements": {
                QUANTITY: "count",
                "description": "Elements the scheduling record knows. "
                               "Everything the build ran, whether or not "
                               "anything looked inside it."},
            "plane2_elements": {
                QUANTITY: "count",
                "description": "Elements the process capture saw inside. "
                               "Fewer whenever a capture was partial."},
        },
    },
    "ranking": {
        RAIL: "prove",
        "properties": {
            "tied_saving_us": {
                QUANTITY: "duration_us",
                "description": "The saving every tied element shares. When "
                               "the ranking degenerates this is the one "
                               "number it has left."},
        },
        "description": "The metric the ranking used, and whether it "
                       "degenerated into a tie - a ranking everything "
                       "ties in is not a ranking, and says so rather "
                       "than presenting an arbitrary order.",
    },
    "restructuring": {
        QUESTION: 'Which dependency edges are never read?',
        RAIL: "act",
    },
    "granularity": {
        QUESTION: 'Which elements pay more sandbox tax than they build?',
        RAIL: "act",
    },
    "memory_envelope": {
        QUESTION: 'How much memory would more builders need?',
        RAIL: "prove",
        "properties": {
            "host_memory_mb": {
                QUANTITY: "megabytes",
                "description": "Memory the host reported. The ceiling the "
                               "envelope below is judged against."},
            "builders": {
                QUANTITY: "count",
                "description": "The builder count this envelope is "
                               "computed for."},
            "elements_measured": {
                QUANTITY: "count",
                "description": "Elements whose peak memory was actually "
                               "measured. The envelope is a bound over "
                               "these, and says nothing about the rest."},
            "largest_element_peak_mb": {
                QUANTITY: "megabytes",
                "description": "The heaviest single element measured. One "
                               "builder must fit this no matter how few "
                               "builders run."},
        },
    },
    "run_instance": {QUESTION: 'Which capture is this?', RAIL: "raw"},
}


_SCHEMAS = {
    ANALYZE: lambda: _document(
        ANALYZE, "bga analyze --format json",
        _ANALYZE_REQUIRED,
        "One run's analysis: where the time went, the certified floors, "
        "the efficiency signals and the confidence in all of it. A "
        "section subcommand (`bga floors`, `bga graph`, ...) emits the "
        "same document restricted to its own keys, with `section` "
        "naming the restriction.",
        optional=_ANALYZE_OPTIONAL, hints=_ANALYZE_HINTS),
    COMPARE: lambda: _document(
        COMPARE, "bga compare --format json",
        _COMPARE_REQUIRED,
        "Two runs, their signed deltas and the verdict - which is "
        "`improved`, `regressed`, `no significant change`, `within the "
        "baseline set's own observed range` (UX-170), or a `not "
        "comparable (...)` refusal.",
        optional=_COMPARE_OPTIONAL, hints=_COMPARE_HINTS),
    BLAST: lambda: _document(
        BLAST, "bga blast --format json",
        _BLAST_REQUIRED,
        "What a change to one resource rebuilds: the direct consumers, "
        "the closure, the split into kinds that build and kinds that "
        "assemble, and the measured cost unless --no-cost was passed.",
        hints=_BLAST_HINTS),
    CORRELATE: lambda: _document(
        CORRELATE, "bga correlate --format json",
        _CORRELATE_REQUIRED,
        "The two planes joined on element UID: for each element, what "
        "Plane 1 knows about its place in the graph (path share, what "
        "a fix is worth, blast radius) beside what Plane 2 measured "
        "inside its sandbox (cores busy, jobs asked for, peak RSS, the "
        "binary that dominated). Neither plane can say alone whether "
        "the elements that dominate the critical path are "
        "compute-bound or merely badly built.",
        optional=_CORRELATE_OPTIONAL, hints=_CORRELATE_HINTS),
    STORE: lambda: _document(
        STORE, "bga snapshot --list --format json",
        _STORE_REQUIRED,
        "What the run store holds: every snapshot with its stamp, size, "
        "the alias `@last`/`@prev` resolution would give it, and why it "
        "is not a measurement if it is not one. Incomplete captures are "
        "listed rather than hidden - they occupy the disk.",
        hints=_STORE_HINTS),
}


def names() -> List[str]:
    """Every schema this tool produces, newest contract first."""
    return sorted(_SCHEMAS)


def schema(name: str) -> dict:
    """The JSON Schema for one output, by its `schema` value."""
    try:
        return _SCHEMAS[name]()
    except KeyError:
        raise KeyError(
            f"unknown schema {name!r} - this tool produces "
            f"{', '.join(names())}") from None


def stamp(payload: dict, name: str) -> dict:
    """`payload` with its `schema` key first.

    Rebuilt rather than mutated so the version leads: `dict` preserves
    insertion order, `json.dumps` follows it, and a human reading the
    first line of a report should see what they are reading.
    """
    stamped = {VERSION_KEY: name}
    stamped.update(payload)
    return stamped


def description(document: str, path: str) -> str:
    """The published sentence for a dotted `path` inside `document`.

    `UX-220`: the schema is the one place a published number's meaning
    is written down, and this is how everything else reads it. The text
    report and `--help` call this rather than keeping their own wording,
    so a reworded description cannot leave two explanations of the same
    number in the tool.

    `path` walks `properties`; a `[]` segment steps into an array's
    `items` (`"snapshots[].bytes"`). A path that does not resolve, or
    resolves to a node with no description, raises `KeyError` - a
    caller asking for a sentence that does not exist is a typo, and a
    silent one would print nothing at all.
    """
    node = schema(document)
    walked = []
    for part in path.split("."):
        if part.endswith("[]"):
            part, into_items = part[:-2], True
        else:
            into_items = False
        node = (node.get("properties") or {}).get(part)
        walked.append(part)
        if node is None:
            raise KeyError(
                f"{document}: no such path {'.'.join(walked)!r} "
                f"(asked for {path!r})")
        if into_items:
            node = node.get("items") or {}
            walked[-1] += "[]"
    sentence = node.get("description")
    if not sentence:
        raise KeyError(f"{document}: {path!r} carries no description")
    return sentence
