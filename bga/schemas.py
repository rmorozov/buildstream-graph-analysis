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
    "saving_share": {QUANTITY: "share"},
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
EVIDENCE_QUANTITIES = {
    key: {QUANTITY: "duration_us"} for key in (
        "category_us", "certified_headroom_us", "failed_task_us",
        "joint_saving_us", "lb_us", "path_us", "sum_of_individual_us",
        "t_infinity_us", "transfer_us")
}
EVIDENCE_QUANTITIES.update({
    key: {QUANTITY: "share"} for key in (
        "criticality_probability", "efficiency_score", "hit_ratio",
        "largest_wait_share", "primary", "share", "share_of_host",
        "share_of_path", "target_closure_hit_ratio", "transfer_share",
        "zero_slack_share")
})
EVIDENCE_QUANTITIES.update({
    key: {QUANTITY: "count"} for key in (
        "blast_count", "builders", "built_elements", "cached_elements",
        "critical_path_cached", "direct_count", "element_count",
        "elements_measured", "failed_count", "failed_task_count",
        "first_builders_that_does_not_fit", "host_cpu_count",
        "native_max_jobs", "recommended_builders", "violation_count")
})
EVIDENCE_QUANTITIES.update({
    "envelope_mb": {QUANTITY: "megabytes"},
    "host_memory_mb": {QUANTITY: "megabytes"},
    "cores_busy": {QUANTITY: "ratio"},
    "measured_seconds": {QUANTITY: "seconds"},
})


_ANALYZE_HINTS = {
    "timestamp_agreement": {QUESTION: 'Do the two planes agree about the clock?', RAIL: 'prove'},
    "run_instance": {QUESTION: 'Which capture is this?', RAIL: 'raw'},
    "resource_blast": {QUESTION: 'What does one shared resource rebuild?', RAIL: 'investigate'},
    "capacity_verdict": {QUESTION: 'Was the capacity right for this build?', RAIL: 'prove'},
    "violations": {QUESTION: 'What did not add up?', RAIL: 'prove'},
    "structural": {QUESTION: 'What shape is this dependency graph?', RAIL: 'investigate'},
    "occupancy": {QUESTION: 'Were the builders busy?', RAIL: 'prove'},
    "signals": {
        QUESTION: 'Which elements are on the chain that binds?',
        RAIL: 'act',
        # UX-208: the three element tables a reader lands on from the
        # decision panel. They carry element uids, so they say so - and
        # every row earns the same Inspect with no per-table code.
        "properties": {
            "critical_path_detail": {
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
    "floors": {QUESTION: 'How much faster could this build possibly be?', RAIL: 'prove'},
    "total_duration_us": {QUANTITY: "duration_us"},
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
            "fraction_of_horizon": {QUANTITY: "share"},
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
            "coverage_score": {QUANTITY: "share"},
            "task_coverage": {QUANTITY: "share"},
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
        "properties": {
            "joined_elements": {QUANTITY: "count"},
            "plane1_elements": {QUANTITY: "count"},
            "plane2_elements": {QUANTITY: "count"},
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
            "certified_headroom_us": {QUANTITY: "duration_us"},
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
                        "saving_us": {QUANTITY: "duration_us"},
                        "downstream_count": {QUANTITY: "count"},
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
            "cpu_disagreement_count": {QUANTITY: "count"},
            "exec_chains_collapsed": {QUANTITY: "count"},
        },
    },
    "utilisation": {
        QUESTION: 'What did the machine cost to run this?',
        RAIL: 'investigate',
        "properties": {
            # The two the external review caught rendering wrongly, and
            # the reason this item exists: `_mb` name-sniffed to bytes
            # ("512 B" for 512 MB) and `_pct` to a 0..1 share
            # ("4200.0%" for 42%).
            "peak_rss_mb": {QUANTITY: "megabytes"},
            "cpu_pct": {QUANTITY: "percent"},
            "cpu_seconds": {QUANTITY: "seconds"},
        },
    },
}

_COMPARE_HINTS = {
    # Every delta in this object is a *change*, and for every metric bga
    # compares, smaller is the improvement - duration, contention,
    # serialization. A viewer colours the sign from this without knowing
    # which metric it has.
    "deltas": {
        DIRECTION: "lower_is_better",
        # UX-201: and each member says what it *is*. Before this, a
        # hinted section still formatted its own members by name.
        "properties": {
            "total_duration_us": {QUANTITY: "duration_us"},
            "contention_us": {QUANTITY: "duration_us"},
            "serialization_us": {QUANTITY: "duration_us"},
            "efficiency_pct": {QUANTITY: "percent"},
            "inefficiency_ratio": {QUANTITY: "ratio"},
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
    "direct_count": {QUANTITY: "count"},
    "blast_count": {QUANTITY: "count"},
    "building_count": {QUANTITY: "count"},
    "assembling_count": {QUANTITY: "count"},
    "element_count": {QUANTITY: "count"},
    "measured_elements": {QUANTITY: "count"},
    "measured_seconds": {QUANTITY: "seconds"},
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
                "depth": {QUANTITY: "count"},
                "measured_seconds": {QUANTITY: "seconds"},
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
    "total_bytes": {QUANTITY: "bytes"},
    "count": {QUANTITY: "count"},
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
                          "total_duration_us": {QUANTITY: "duration_us"},
                          "cache_hit_rate": {QUANTITY: "share"},
                          "bytes": {QUANTITY: "bytes"},
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
        "properties": {
            "joined_elements": {QUANTITY: "count"},
            "plane1_elements": {QUANTITY: "count"},
            "plane2_elements": {QUANTITY: "count"},
        },
    },
    "ranking": {
        RAIL: "prove",
        "properties": {
            "tied_saving_us": {QUANTITY: "duration_us"},
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
            "host_memory_mb": {QUANTITY: "megabytes"},
            "builders": {QUANTITY: "count"},
            "elements_measured": {QUANTITY: "count"},
            "largest_element_peak_mb": {QUANTITY: "megabytes"},
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
        "comparable (...)` refusal.", hints=_COMPARE_HINTS),
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
