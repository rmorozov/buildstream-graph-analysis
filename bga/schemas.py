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

ANALYZE = "analyze/v1"
COMPARE = "compare/v1"
BLAST = "blast/v1"

# The key that carries the version, and the first key of every payload -
# a consumer reading a truncated or streamed document sees it before it
# sees anything it would have to interpret.
VERSION_KEY = "schema"


def _document(name: str, title: str, required: Dict[str, str],
              description: str, optional: Dict[str, str] = None) -> dict:
    """A top-level object schema: `schema` plus the always-present keys.

    `required` maps a key to its JSON Schema type name, or to `""` for a
    key whose type genuinely varies (a metric that is a number when
    measured and `null` when not).
    """
    properties: Dict[str, dict] = {
        VERSION_KEY: {"const": name,
                      "description": "The shape of this document."},
    }
    for key, kind in {**required, **(optional or {})}.items():
        properties[key] = {} if not kind else {"type": [kind, "null"]}
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
}

# What a *full* `bga analyze --format json` of a normal run contains.
# Not part of the schema - a projection would fail it - but pinned here
# and asserted against the golden run, because this is the list a field
# rename silently shortens. `edges_outside_band` (renamed from
# `runs_outside_band` one round before this item was filed) is the case
# in point.
ANALYZE_FULL_KEYS = (
    "schema", "run_id", "total_duration_us", "section", "run_instance",
    "findings", "floors", "capacity_verdict", "attribution",
    "attribution_hints", "occupancy", "signals", "structural",
    "utilisation", "confidence", "violations",
)

_COMPARE_REQUIRED = {
    "baseline_run_id": "string",
    "candidate_run_id": "string",
    "baseline": "object",
    "candidate": "object",
    "deltas": "object",
    "verdict": "string",
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
    "measured_seconds": "",
    "measured_elements": "integer",
    "element_count": "integer",
    "has_inventory": "boolean",
    "element_exists": "boolean",
    "measured": "boolean",
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
        optional=_ANALYZE_OPTIONAL),
    COMPARE: lambda: _document(
        COMPARE, "bga compare --format json",
        _COMPARE_REQUIRED,
        "Two runs, their signed deltas and the verdict - which is "
        "`improved`, `regressed`, `no significant change`, `within the "
        "baseline set's own observed range` (UX-170), or a `not "
        "comparable (...)` refusal."),
    BLAST: lambda: _document(
        BLAST, "bga blast --format json",
        _BLAST_REQUIRED,
        "What a change to one resource rebuilds: the direct consumers, "
        "the closure, the split into kinds that build and kinds that "
        "assemble, and the measured cost unless --no-cost was passed."),
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
