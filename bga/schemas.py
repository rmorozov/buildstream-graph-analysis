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

# UX-288: v2. Three fields were **removed** - `signals.critical_path`,
# `signals.leaf_analysis.leaves` and `structural.deferrability`'s two
# uid lists - each of which republished element membership already
# published beside it. The versioning rule below is explicit that a
# removal moves the version, and this is the case it was written for.
ANALYZE = "analyze/v2"
COMPARE = "compare/v1"
BLAST = "blast/v1"
STORE = "store/v1"
# UX-234: the store as a distribution rather than as a list. Beside
# `store/v1` rather than inside it: a listing is one row per snapshot
# and this is one row per *host class*, and a consumer wanting the
# trend should not have to skip an aggregate to reach it.
STORE_AGGREGATE = "store-aggregate/v1"
# UX-230: the projected build for a chosen subset of fixes. Its own
# document because it answers a *question a reader asked*, not a
# property of the run - two selections over one run are two answers.
WHATIF = "whatif/v1"

# `UX-339`: the capacity sweep. `UX-328` found it as the one printed
# document with no id at all - and `bga sweep --schema` answering
# `analyze/v2` for a document with **none** of that contract's four
# required keys, which is a confidently wrong answer rather than a
# missing one.
SWEEP = "sweep/v1"
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

# UX-303 (styleguide §2): a value that *is* a shape renders as its
# shape first and its numbers second.
#
# Two hints, and each names the reading its control needs so that no
# renderer has to guess:
#
# `bga:series` — an **ordered numeric array**. The order is the axis;
# the hint's value says what one step along it is (`"snapshot"`,
# `"level"`, `"run"`), because the sentence beside the drawing has to
# name the unit and a viewer must not invent one. Fewer than
# `SERIES_MIN_POINTS` values is a sentence rather than a drawing: two
# points joined by a line is a claim about a trend that two points
# cannot make (`UX-226`'s rule, now global).
#
# `bga:distribution` — an **object publishing percentiles over a
# population**. Its value names the key holding the sample count, and
# the renderer reads `min`, the median (`median` or `deciles.p50`),
# `p95` and `max`. Two shapes in this repository publish that:
# `store-aggregate/v1`'s `{samples, min, median, p95, max, mad}` and
# `analyze/v2`'s `{n, min, max, deciles, p95, p99, is_flat}`. Declaring
# where the count lives is what lets one control draw both, and `n` is
# always printed - a strip without its population is a picture of an
# opinion.
SERIES = "bga:series"
DISTRIBUTION = "bga:distribution"
# Below this a series is a sentence. Stated here because the page and
# the guards must agree on it, and `UX-273`'s rule is that a threshold
# lives in one place.
SERIES_MIN_POINTS = 3

# UX-289: a named view over a table - which rows, which columns, in
# what order, how many.
#
# The page had bounds (`UX-262`'s `Top N`) and filters (`UX-205`) and
# **zero named presets**: measured on the 1,202-element run, no element
# on the page carried a preset role. The controls existed; nothing named
# what a reader would use them for, so "the critical path" was a table
# the payload published separately rather than a view of the one table
# every element is already in.
#
# Declared here rather than in the viewer for `UX-201`'s reason: a
# second list of views living in JavaScript is a vocabulary waiting to
# diverge from the payload it draws.
#
# A preset is `{name, question?, from?|where?, columns, sort?, bound?}`:
#
#   from    a dotted path to a published *selection* - an ordered list
#           of records naming an element each, or a map keyed by
#           element. The rows are that selection, in the order it is
#           published, which is how "the critical path" keeps its order
#           without the page knowing what a critical path is.
#   where   `{column, equals}` - a predicate over a column of the table
#           itself, for a membership the records already carry.
#   columns which columns this view shows, in order. This is the half
#           that makes the table readable: one table serving every
#           question carried 13 columns on the 1,202-element run, and a
#           reader asking one question wants four.
#   sort    `{column, direction}`; `bound` an opening row cap.
#
# `from` and `where` are alternatives, never both: two ways of saying
# which rows would be two answers to one question, which is the defect
# `UX-288` had just finished removing from the payload.
PRESETS = "bga:presets"
PRESET_DIRECTIONS = ("asc", "desc")
# The acceptance bound `UX-289` was filed with: a table that needs more
# than this to answer one question is not a view of the data, it is the
# data. Measured before: the element table carried 13 columns because
# one table had to serve every question.
PRESET_COLUMNS_MAX = 8

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
    # UX-289: a preset a renderer could not act on is worse than none -
    # it names a view in the rail and then draws the unfiltered wall.
    presets = hint.get(PRESETS)
    if presets is not None:
        if not isinstance(presets, (list, tuple)) or not presets:
            raise ValueError(
                f"{document}.{key}: {PRESETS} must be a non-empty list")
        names = []
        for preset in presets:
            if not isinstance(preset, dict):
                raise ValueError(f"{document}.{key}: {PRESETS} entry is not a "
                                 f"mapping: {preset!r}")
            name = preset.get("name")
            if not name or not isinstance(name, str):
                raise ValueError(
                    f"{document}.{key}: {PRESETS} entry has no name")
            names.append(name)
            if "from" in preset and "where" in preset:
                raise ValueError(
                    f"{document}.{key}: preset {name!r} says both `from` and "
                    f"`where` - two ways of choosing rows are two answers")
            where = preset.get("where")
            if where is not None and (not isinstance(where, dict)
                                      or "column" not in where
                                      or "equals" not in where):
                raise ValueError(
                    f"{document}.{key}: preset {name!r} `where` must be "
                    f"{{column, equals}}")
            columns = preset.get("columns")
            if not columns or not isinstance(columns, (list, tuple)):
                raise ValueError(
                    f"{document}.{key}: preset {name!r} names no columns")
            if len(columns) > PRESET_COLUMNS_MAX:
                raise ValueError(
                    f"{document}.{key}: preset {name!r} shows {len(columns)} "
                    f"columns; the point of a preset is that it shows fewer "
                    f"than {PRESET_COLUMNS_MAX}")
            sort = preset.get("sort")
            if sort is not None:
                if not isinstance(sort, dict) or "column" not in sort:
                    raise ValueError(
                        f"{document}.{key}: preset {name!r} `sort` must name "
                        f"a column")
                if sort.get("direction", "desc") not in PRESET_DIRECTIONS:
                    raise ValueError(
                        f"{document}.{key}: preset {name!r} sorts "
                        f"{sort.get('direction')!r}, not one of "
                        f"{', '.join(PRESET_DIRECTIONS)}")
            question = preset.get("question")
            if question is not None and not str(question).strip().endswith("?"):
                raise ValueError(
                    f"{document}.{key}: preset {name!r} question "
                    f"{question!r} is not a question")
            # `UX-338`: the columns without which this view has no
            # answer. A preset whose *subject* the run does not carry
            # is not offered - "there are no choke points" and "this
            # run has no Plane 2" are different claims, and the second
            # one is not a view with two columns in it.
            #
            # Declared rather than inferred: "which of my columns make
            # me this view" is a question only the preset's author can
            # answer. Inferring it from what a run happens to carry was
            # tried and is wrong - `Plane 2 (sandbox)` also names
            # `element_durations`, which every run has, so any
            # "some column is present" rule keeps offering it.
            requires = preset.get("requires")
            if requires is not None:
                if (not isinstance(requires, (list, tuple)) or not requires
                        or not all(isinstance(name_, str)
                                   for name_ in requires)):
                    raise ValueError(
                        f"{document}.{key}: preset {name!r} `requires` must "
                        f"be a non-empty list of column names")
                missing = [name_ for name_ in requires
                           if name_ not in columns]
                if missing:
                    raise ValueError(
                        f"{document}.{key}: preset {name!r} requires "
                        f"{missing} which it does not show - a view cannot "
                        f"depend on a column it does not draw")
        if len(set(names)) != len(names):
            raise ValueError(
                f"{document}.{key}: two presets share a name: {names}")
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


def _distribution(quantity: str, noun: str, description: str) -> dict:
    """`UX-343`: a distribution declares the unit of its own leaves.

    `{n, min, max, deciles{p10..p90}, p95, p99, is_flat}` is one shape
    published twice, and declaring `bga:quantity` on the *object* left
    every percentile inside it undeclared - measured through the page's
    own `quantityFor`, `min`, `max`, `p95`, `p99` and all nine deciles
    reached the reader as bare numbers. The count is a count; everything
    else is the quantity the population is of.
    """
    # `UX-220`: a declared quantity carries a sentence. Generated rather
    # than written out twenty-six times, because "the 30th percentile of
    # this population" is the same sentence with a number in it, and
    # twenty-six copies of it by hand is how one of them ends up saying
    # the 40th.
    def extreme(what):
        return {QUANTITY: quantity, "description": f"The {what} {noun}."}

    def rank(step):
        return {QUANTITY: quantity,
                "description": f"The {step}th percentile {noun}."}

    return {
        DISTRIBUTION: "n", QUANTITY: quantity, "description": description,
        "properties": {
            "n": {
                QUANTITY: "count",
                "description": "How many values the percentiles are over. A "
                               "strip without its population is a picture of "
                               "an opinion."},
            "min": extreme("smallest"), "max": extreme("largest"),
            "p95": rank(95), "p99": rank(99),
            "deciles": {
                "description": "The nine deciles, nearest-rank.",
                "properties": {f"p{step}": rank(step)
                               for step in range(10, 100, 10)}},
        },
    }


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
    # UX-275: and what the capacity *should* be, which is the question
    # `UX-09` opened this backlog with. Present only when `--plane2` was
    # given, because the recommendation rests on measured cores-busy and
    # a host core count; an addition, so no version bump (`UX-190`).
    #
    # Here rather than beside `memory_envelope` in `correlate/v1`: that
    # document is the per-element join, one row per element, and a
    # run-level recommendation is not a row of it. This one intersects
    # the Plane 1 sweep with Plane 2's draw, and `capacity_verdict` -
    # "was the capacity right?" - is already here for it to sit beside.
    "capacity_recommendation": "object",
    "run_instance": "object",
    # UX-249: which build of `bga` wrote this document, and the contract
    # set it had. An *addition*, so no version bump - UX-190's rule.
    # Optional rather than required because a section report is not a
    # full document and does not carry it, and because declaring it
    # required would make every pre-UX-249 archived payload fail
    # validation, which is the opposite of what recording provenance is
    # for.
    "producer": "object",
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
    # UX-329: present only when Plane 2 is *absent*, saying which of the
    # three absences it is. Additive, so `analyze/v2` does not bump.
    "plane2_absence": "string",
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
# UX-229: the chain behind one claim. Declared once and referenced from
# the three places a claim is published - the diagnosis, each finding
# and each top action - because a consumer that learns to read one has
# learned to read all three, and a second shape would be a second
# contract to keep in step.
_PROVENANCE = {
    "description": "Why this claim is made: the published fields it was "
                   "read from, the rule that fired, and the trace query "
                   "that deepens it. References into this same document "
                   "rather than copies, so a reader can follow them.",
    "properties": {
        "claim": {"description": "Which claim this explains - a finding "
                                 "id, or `diagnosis` for the headline."},
        "kind": {"description": "Where the claim is published: "
                                "`diagnosis`, `finding` or `top_action`."},
        "document": {"description": "The schema of the document every "
                                    "path below walks. Load-bearing the "
                                    "moment a record travels: "
                                    "`compare/v1` carries the candidate "
                                    "run's chain, whose paths resolve "
                                    "against that run's `analyze/v1`."},
        "evidence": {
            "description": "Each field this claim was read from, as a "
                           "path into this document and the value found "
                           "there. A quotation, not a second publication: "
                           "where this names a quantity the finding's own "
                           "`evidence` also carries, the finding's is the "
                           "one to believe, and a guard holds the two "
                           "equal (UX-291).",
            "items": {
                "type": "object",
                "properties": {
                    "path": {"description": "A path into this document: "
                                            "dotted keys, `[i]` for a list "
                                            "index, `[key=value]` for the "
                                            "one list entry matching it."},
                    "value": {"description": "What that path held when the "
                                             "report was written."},
                    "resolved": {"description": "False where the path did "
                                                "not resolve - published "
                                                "rather than dropped, so a "
                                                "broken reference is "
                                                "visible instead of "
                                                "absent."},
                },
                "required": ["path", "resolved"],
            },
        },
        "rule": {
            "description": "What decided this claim.",
            "properties": {
                "name": {"description": "The constant that decided it, or "
                                        "null where the claim has no "
                                        "threshold - which is a different "
                                        "statement from a threshold of "
                                        "zero."},
                "threshold": {"description": "That constant's value, read "
                                             "live: change the constant and "
                                             "this changes with it."},
                "comparison": {"description": "How the observed value was "
                                              "compared: `>=`, `<`, `>`, "
                                              "`banded`, or `present` for a "
                                              "claim with no threshold."},
                "observed_path": {"description": "Where the compared value "
                                                 "is published, when it is."},
                "sentence": {"description": "The comparison in words - one "
                                            "wording, so the terminal, the "
                                            "page and the CI comment cannot "
                                            "explain one claim three ways."},
                "module": {"description": "The file the threshold is "
                                          "defined in."},
            },
            "required": ["comparison", "sentence"],
        },
        "see": {"description": "On a top action: the path to the "
                               "finding's record, which holds the chain. "
                               "The action *is* a reference to that "
                               "finding, so its provenance is one too."},
        "trace_query": {"description": "The `questions.js` query id that "
                                       "deepens this claim in the timeline, "
                                       "or null where none does."},
        "unpublished_inputs": {
            "description": "Fields this claim was genuinely drawn from "
                           "that this document does not carry. Named "
                           "rather than omitted: silence would read as "
                           "no gap."},
    },
    "required": ["claim", "kind", "document"],
}


_SWEEP_REQUIRED = {
    "resource": "string",
    "sweeps": "array",
    "knee_points": "object",
    "monotonicity_violations": "array",
    "capacity_model_caveat": "string",
    "calibration_capacities": "array",
}

_SWEEP_HINTS = {
    "resource": {"description": "The resource whose capacity was swept - "
                                "`PROCESS`, `DOWNLOAD` or `UPLOAD`. One "
                                "sweep answers about one of them."},
    "sweeps": {
        # `prove`: the sweep is the evidence behind a capacity
        # recommendation, not the recommendation itself.
        RAIL: "prove",
        QUESTION: "What does more capacity buy?",
        COLUMNS: [
            {"key": "capacity", "title": "Capacity"},
            {"key": "makespan_us", "title": "Makespan",
             "quantity": "duration_us"},
            {"key": "normalized_improvement", "title": "Improvement",
             "quantity": "ratio"},
        ],
        "description": "One row per capacity tried: the full capacity "
                       "vector at that point, the makespan the replay "
                       "produced, and what that capacity bought over the "
                       "one before it. `normalized_improvement` is a "
                       "*step* gain, not a total - reading it as a total "
                       "is the mistake the column exists to prevent."},
    "knee_points": {
        "description": "Per resource, the capacity past which more buys "
                       "little. Absent for a resource with no knee, "
                       "which is a different answer from a knee at the "
                       "minimum."},
    "monotonicity_violations": {
        "description": "Capacities where the makespan got *worse* as "
                       "capacity rose. The replay model says that cannot "
                       "happen, so each one is a hole in the model rather "
                       "than a finding about the build - published so a "
                       "reader can see the model failing rather than "
                       "trust a number it produced."},
    "capacity_model_caveat": {
        "description": "What this projection does not model, published "
                       "with every answer so a figure that travels keeps "
                       "its assumption attached: the replay replays each "
                       "task's already-observed duration and does not "
                       "model CPU contention rising with concurrency."},
    "calibration_capacities": {
        "description": "The capacities that had real measurements behind "
                       "them, when a contention calibration was supplied. "
                       "Empty means every point is a projection - the "
                       "difference between a curve with data in it and "
                       "one without."},
}


_WHATIF_REQUIRED = {
    "run_id": "string",
    "selected": "array",
    "total_duration_us": "integer",
    "convention": "string",
    "refusals": "array",
    "projected": "object",
}

_WHATIF_HINTS = {
    "run_id": {"description": "The run this projection is over."},
    "selected": {"description": "The elements the caller chose, in the "
                                "order they were given."},
    "total_duration_us": {
        QUANTITY: "duration_us",
        "description": "This run's wall-clock, for scale. The projection "
                       "below is over the critical path, which is a "
                       "different quantity."},
    "convention": {"description": "What \"fixed\" means, published with "
                                  "every answer so a figure that travels "
                                  "keeps its assumption attached."},
    "refusals": {
        "description": "Why no projection is published, when none is: an "
                       "empty selection, an element the graph does not "
                       "know, or one with no measured duration. Each "
                       "names the check and the elements it fired on.",
        "items": {"properties": {
            "check": {"description": "The name a caller matches on, "
                                     "rather than the prose."},
            "elements": {"description": "Which elements failed it."},
            "sentence": {"description": "The refusal in words."},
        }},
    },
    "projected": {
        QUESTION: 'What would the build drop to?',
        "description": "The projection, computed by the same "
                       "`compute_joint_saving` the report's own horizon "
                       "uses. `null` when anything was refused.",
        "properties": {
            "baseline_makespan_us": {
                QUANTITY: "duration_us",
                "description": "The critical path as this run measured it."},
            "joint_saving_us": {
                QUANTITY: "duration_us",
                "description": "What the whole selection is worth "
                               "together - a longest-path recompute with "
                               "every chosen element zeroed, not a sum."},
            "makespan_after_us": {
                QUANTITY: "duration_us",
                "description": "What the chain drops to. Published rather "
                               "than left as a subtraction, for the "
                               "reason `headline.scheduling_gap_us` is."},
            "sum_of_individual_us": {
                QUANTITY: "duration_us",
                "description": "What each element is worth *alone*, added "
                               "up - published as the wrong answer, "
                               "deliberately. On a shared chain it "
                               "differs from the joint saving, and that "
                               "difference is why a page must never add."},
        },
    },
}


ANALYZE_FULL_KEYS = (
    "schema", "run_id", "total_duration_us", "section", "run_instance",
    # UX-249: which build wrote this. On every full report, beside
    # `run_instance` and for the same reason - both answer "which run,
    # measured by what" rather than anything about the analysis. An
    # addition, so no version bump.
    "producer",
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
    # UX-329: the other side of the same conditional. `plane2_absence`
    # is present exactly when the three above are not, so it belongs in
    # the same list for the same reason: a full report is full with
    # either, and the pin must not demand both.
    "plane2_absence",
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
    # UX-229: the candidate run's headline claim with its chain. Always
    # emitted from a real comparison - both runs are analyzed - so it is
    # required rather than permitted, by the same rule `element_deltas`
    # landed under one round earlier.
    "candidate_diagnosis": "object",
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
    # `UX-343`: the three nested records a Plane 2 join carries per
    # element, and the count beside them. Thirty-one leaves reaching the
    # reader with no unit, in the block that exists to say what the
    # sandbox did with the cores it was given.
    "redundancy_count": {
        QUANTITY: "count",
        "description": "How many times this element repeated work it had "
                       "already done."},
    "dominant_binary": {
        "description": "The one binary that took most of this element's "
                       "measured CPU.",
        "properties": {
            "count": {
                QUANTITY: "count",
                "description": "Processes this binary accounted for."},
            "cpu_us": {
                QUANTITY: "duration_us",
                "description": "CPU time those processes used between them."},
            "cpu_share": {
                QUANTITY: "share",
                "description": "That CPU over the element's own. High means "
                               "one binary is the element."},
            "wall_s": {
                QUANTITY: "seconds",
                "description": "Wall-clock those processes spanned."},
        }},
    "serial_binary": {
        "description": "The binary whose work ran one process at a time.",
        "properties": {
            "cpu_us": {
                QUANTITY: "duration_us",
                "description": "CPU time this binary used while running one "
                               "process at a time."},
            "wall_s": {
                QUANTITY: "seconds",
                "description": "Wall-clock it spanned doing so - close to "
                               "`cpu_us` is the tell."},
        }},
    "worst_redundancy": {
        "description": "The repeated work this element paid for most.",
        "properties": {
            "occurrence_count": {
                QUANTITY: "count",
                "description": "How many times the repeated work ran."},
            "total_duration_s": {
                QUANTITY: "seconds",
                "description": "Wall-clock the repeated work cost across all "
                               "its occurrences."},
            "max_element_duration_s": {
                QUANTITY: "seconds",
                "description": "The longest single occurrence of the repeated "
                               "work."},
        }},
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
    "saving_share": {
        QUANTITY: "share",
        "description": "What fixing this element would take off the run, as a "
                       "share of its wall-clock."},
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
        "Memory the host reported, which the memory ceiling is computed against."),
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

# `UX-343`: the *structured* members of a finding's evidence. The scalars
# above have been declared since `UX-217`; the tables and maps a finding
# carries beside them had nothing, so a finding that showed its rows
# printed durations and shares as bare numbers while the same columns
# rendered correctly one section away.
#
# These mirror the shapes they are drawn from rather than restating
# them: what a finding shows is a slice of a published population, and
# a slice that disagreed with its source about a unit would be worse
# than a slice with no unit at all.
EVIDENCE_QUANTITIES.update({
    "change": {
        QUANTITY: "share",
        "description": "The signed change this finding is about, as a share of "
                       "the baseline."},
    "blast_radius": {
        "additionalProperties": {"properties": {
            "downstream_count": {
                QUANTITY: "count",
                "description": "Elements this one's change rebuilds."},
            "weighted_duration_us": {
                QUANTITY: "duration_us",
                "description": "What that rebuild costs, summed over the elements it touches."},
            "risk_score": {
                QUANTITY: "ratio",
                "description": "Downstream work weighted by duration - a "
                               "ranking within this run, not a measurement."},
        }},
        "description": "What each named element's change rebuilds."},
    "constraints": {"items": {"properties": {
        "allows": {
            QUANTITY: "count",
            "description": "How many builders this particular ceiling permits."},
    }}},
    "rows": {"items": {"properties": {
        "duration_us": {
            QUANTITY: "duration_us",
            "description": "How long this row's element took in this run."},
        "realizable_saving_us": {
            QUANTITY: "duration_us",
            "description": "What removing it would take off the makespan."},
        "share_of_path": {
            QUANTITY: "share",
            "description": "How much of the chain this row's element accounts for."},
    }}},
    "steps": {"items": {"properties": {
        "saving_us": {
            QUANTITY: "duration_us",
            "description": "What taking this step alone is worth, before the ones after it."},
        "makespan_after_us": {
            QUANTITY: "duration_us",
            "description": "Where the finish lands once this step is taken."},
        "cumulative_saving_us": {
            QUANTITY: "duration_us",
            "description": "Everything saved up to and including it."},
    }}},
    "latent_heavies": {"items": {"properties": {
        "duration_us": {
            QUANTITY: "duration_us",
            "description": "This element's duration, off the chain today."},
    }}},
})

_ANALYZE_HINTS = {
    "timestamp_agreement": {
        QUESTION: 'Do the two planes agree about the clock?', RAIL: 'prove',
        # `UX-343`: this block is entirely seconds and counts, and said
        # so nowhere - nine leaves, no unit. The `_s` suffix is what
        # `UX-341` will take to microseconds; declaring it is what makes
        # that a rename rather than a guess.
        "properties": {
            "resolution_s": {
                QUANTITY: "seconds",
                "description": "The finest interval the two planes' clocks can "
                               "tell apart."},
            "shortest_task_s": {
                QUANTITY: "seconds",
                "description": "The shortest task measured - the case the "
                               "resolution above matters most for."},
            "worst_excess_s": {
                QUANTITY: "seconds",
                "description": "The largest amount by which one plane's "
                               "duration exceeded the other's."},
            "worst_shortfall_s": {
                QUANTITY: "seconds",
                "description": "The largest amount by which one plane's "
                               "duration fell short of the other's."},
            "material_share": {
                QUANTITY: "share",
                "description": "The share of tasks where the disagreement is "
                               "large enough to change a reading."},
            "tasks_compared": {
                QUANTITY: "count",
                "description": "Tasks both planes recorded, so their clocks can be compared."},
            "tasks_measured": {
                QUANTITY: "count",
                "description": "Tasks with a duration in both planes."},
            "tasks_shorter_than_bst": {
                QUANTITY: "count",
                "description": "Tasks the sandbox measured as shorter than "
                               "BuildStream did."},
            "tasks_where_material": {
                QUANTITY: "count",
                "description": "Tasks where the disagreement is large enough "
                               "to matter."},
        }},
    "run_instance": {
        QUESTION: 'Which capture is this?', RAIL: 'raw',
        "properties": {
            "started_at_us": {
                QUANTITY: "duration_us",
                "description": "When the capture began, as microseconds "
                               "since the epoch. A point in time rather "
                               "than a span - the unit is the same and "
                               "the reading is not."},
            "host_manifest": {"properties": {
                "cpu_count": {
                    QUANTITY: "count",
                    "description": "Cores the host reported, which the CPU ceiling is computed against."},
                "memory_mb": {
                    QUANTITY: "megabytes",
                    "description": "Memory the host reported, which the memory ceiling is computed against."},
            }},
        }},
    "producer": {QUESTION: 'Which build of bga measured this?', RAIL: 'raw'},
    "resource_blast": {QUESTION: 'What does one shared resource rebuild?', RAIL: 'investigate'},
    "capacity_recommendation": {
        QUESTION: 'What should the capacity be, and what decides it?',
        RAIL: 'act',
        "description": "The four constraints on `--builders` intersected: "
                       "what the graph can use, what the host's cores can "
                       "feed, what its memory can hold, and what was "
                       "actually set. The smallest is the one that binds, "
                       "and it is the only one worth acting on.",
        "properties": {
            "builders": {
                QUANTITY: "count",
                "description": "The builder count this run was given - what "
                               "everything below is measured at."},
            "native_max_jobs": {
                QUANTITY: "count",
                "description": "The `-j` each element's own build used, "
                               "recovered from the log (`UX-29`). Null when "
                               "the log did not record it, which is a "
                               "different claim from 1."},
            "host_cpu_count": {
                QUANTITY: "count",
                "description": "Cores the host reported. The ceiling the "
                               "CPU constraint is computed against, and "
                               "the reason a recommendation is about this "
                               "machine rather than about the graph "
                               "alone."},
            "cores_busy": {
                QUANTITY: "count",
                "description": "Cores drawn on average across the whole "
                               "run, from Plane 2. An average, not a peak: "
                               "during the parallel stretch each element "
                               "draws more, so the CPU ceiling below is "
                               "optimistic."},
            "constraints": {
                "description": "One record per ceiling that could be "
                               "measured. A constraint with no measurement "
                               "behind it is absent rather than infinite.",
                COLUMNS: [
                    {"key": "name", "title": "Constraint", "sortable": True,
                     "description": "`graph`, `CPU` or `memory` - which of "
                                    "the four inputs this ceiling comes "
                                    "from."},
                    {"key": "allows", "title": "Builders it allows",
                     "quantity": "count", "sortable": True},
                    {"key": "reason", "title": "Why",
                     "description": "The measurement this ceiling was read "
                                    "off, in the units it was measured in."},
                ]},
            "binding_constraint": {
                "description": "The name of the smallest constraint. This "
                               "is the one that changes what to do: a knee "
                               "at 5 on a host already 85% drawn is not "
                               "'raise builders to 5'."},
            "recommended_builders": {
                QUANTITY: "count",
                "description": "What the binding constraint allows. A "
                               "hypothesis to time, not a setting to "
                               "apply - see `caveat`."},
            "change": {
                QUANTITY: "count",
                "description": "`recommended_builders` minus `builders`, "
                               "signed - negative means the run asked for "
                               "more than something can serve."},
            "pinned_elements": {
                "description": "Elements whose own build pinned itself to "
                               "one core, from Plane 2. Free capacity these "
                               "leave is capacity no builder count can "
                               "use."},
            "caveat": {
                "description": "What this recommendation is not. Read it "
                               "before acting: the sweep replays observed "
                               "durations and does not model contention "
                               "(`UX-14`), and one capture went in. A "
                               "consumer that drops this sentence is left "
                               "with a number that looks like a setting."},
        },
    },
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
    "structural": {
        QUESTION: 'What shape is this dependency graph?',
        RAIL: 'investigate',
        "properties": {
            # `UX-343`: `metrics`, `summary` and `deferrability` said
            # nothing about a single one of their members - twenty-six
            # leaves reaching the reader as bare numbers, in the block
            # whose whole job is to describe the graph's shape.
            "metrics": {
                "description": "The graph's shape as numbers, "
                               "independent of how long anything took.",
                "properties": {
                    "num_elements": {
                        QUANTITY: "count",
                        "description": "How many elements this run's graph holds."},
                    "num_edges": {
                        QUANTITY: "count",
                        "description": "How many dependency edges this run's graph holds."},
                    "max_depth": {
                        QUANTITY: "count",
                        "description": "The longest chain of dependencies, "
                                       "counted in edges."},
                    "avg_fanin": {
                        QUANTITY: "ratio",
                        "description": "Direct dependents per element, "
                                       "averaged."},
                    "avg_fanout": {
                        QUANTITY: "ratio",
                        "description": "Direct dependencies per element, "
                                       "averaged."},
                    "max_parallelism": {
                        QUANTITY: "count",
                        "description": "The most elements that could run at "
                                       "once given the graph alone."},
                    "avg_parallelism": {
                        QUANTITY: "ratio",
                        "description": "Elements that could run at once, "
                                       "averaged over the graph's levels."},
                    "critical_path_length": {
                        QUANTITY: "count",
                        "description": "Elements on the chain, not its "
                                       "duration."},
                    "critical_path_ratio": {
                        QUANTITY: "share",
                        "description": "The chain's length over the graph's "
                                       "depth - how much of the shape the "
                                       "chain accounts for."},
                    "serialization_ratio": {
                        QUANTITY: "share",
                        "description": "How much of the graph has to run one "
                                       "thing after another."},
                    "cyclomatic_complexity": {
                        QUANTITY: "count",
                        "description": "Edges minus elements plus one - how "
                                       "tangled the graph is."},
                }},
            "summary": {
                "description": "The headline shape numbers, for a reader "
                               "who wants one line rather than the block.",
                "properties": {
                    "total_elements": {
                        QUANTITY: "count",
                        "description": "How many elements this run's graph holds."},
                    "critical_path_length": {
                        QUANTITY: "count",
                        "description": "Elements on the chain, not its "
                                       "duration."},
                    "max_parallelism": {
                        QUANTITY: "count",
                        "description": "The most elements that could run at "
                                       "once given the graph alone."},
                    "bottleneck_count": {
                        QUANTITY: "count",
                        "description": "Elements everything funnels through."},
                    "deferrable_leaves": {
                        QUANTITY: "count",
                        "description": "Leaf elements nothing downstream is waiting on."},
                    "best_case_speedup": {
                        QUANTITY: "ratio",
                        "description": "How much faster an unlimited-"
                                       "capacity replay of this graph "
                                       "would be. A multiplier, and a "
                                       "ceiling rather than a plan."},
                }},
            "deferrability": {
                "properties": {
                    "total_deferrable_work_us": {
                        QUANTITY: "duration_us",
                        "description": "Work that could be moved out of this "
                                       "build without anything waiting for it."},
                }},
            # UX-303: the graph's width, level by level - an ordered
            # numeric array whose order *is* the axis, which is what
            # `bga:series` says. Drawn as a sparkline with the sentence
            # beside it naming the unit this hint declares; below three
            # levels it is a sentence and no drawing, because two
            # points joined by a line claim a trend two points cannot
            # make.
            "parallelism": {
                "properties": {
                    # `UX-343`: the four scalars beside the series, and
                    # the series' own values.
                    "levels": {
                        QUANTITY: "count",
                        "description": "One entry per level of the graph, "
                                       "in order.",
                        "items": {
                            QUANTITY: "count",
                            "description": "How many elements sit at this level of the graph."}},
                    "min_width": {
                        QUANTITY: "count",
                        "description": "The narrowest level of the graph - "
                                       "where it is closest to serial."},
                    "max_width": {
                        QUANTITY: "count",
                        "description": "The widest level of the graph - its most parallel point."},
                    "mean_width": {
                        QUANTITY: "ratio",
                        "description": "Elements per level of the graph, averaged over the levels."},
                    "width_uniformity": {
                        QUANTITY: "share",
                        "description": "How evenly the width is spread. Low "
                                       "means the graph pinches somewhere."},
                    "width_at_level": {
                        # `UX-343`: the series declared its axis and not
                        # the values on it.
                        "items": {
                            QUANTITY: "count",
                            "description": "The graph's width at this "
                                           "level."},
                        SERIES: "level",
                        "description": "How many elements sit at each "
                                       "depth of the graph, from the "
                                       "roots down. The shape of this "
                                       "series is the shape of what can "
                                       "run at once.",
                    },
                },
            },
            "bottleneck": {
                "description": "Where work funnels through one element, "
                               "and how much waits behind it.",
                "properties": {
                    "serial_chain_length": {
                        QUANTITY: "count",
                        "description": "The longest run of elements that must "
                                       "go one after another."},
                    # UX-283: the choke points are an element table like
                    # any other, so they earn the Inspect route and the
                    # sort every other element table has. Before this
                    # the whole `structural` section carried **zero**
                    # links out of it, measured on the 1,202-element run.
                    "choke_points": {
                        "description": "Elements every other element is "
                                       "either upstream or downstream of - "
                                       "the graph's waists, ranked by how "
                                       "much waits on them.",
                        COLUMNS: [
                            {"key": "element_uid", "title": "Element",
                             "role": "element", "sortable": True},
                            {"key": "downstream_count",
                             "title": "Waiting on it",
                             "quantity": "count", "sortable": True,
                             "description": "How many elements are "
                                            "downstream of this one, and "
                                            "so cannot start until it "
                                            "finishes."},
                        ]},
                    # UX-290: a tuple is described by naming its members
                    # in order. `bga:columns` already says what an array
                    # of *objects* holds; for an array of pairs, entry
                    # `i` describes position `i`. Before this the page
                    # drew them as `#1` and `#2`, which is honest about
                    # being a position and says nothing about the
                    # measure.
                    "high_fanin_elements": {
                        "description": "Elements many others depend on "
                                       "directly, with how many.",
                        COLUMNS: [
                            {"key": "element_uid", "title": "Element",
                             "role": "element", "sortable": True},
                            {"key": "fan_in", "title": "Direct dependents",
                             "quantity": "count", "sortable": True,
                             "description": "Elements naming this one as "
                                            "a dependency - an in-degree, "
                                            "not a transitive count."},
                        ]},
                    "high_fanout_elements": {
                        "description": "Elements that depend on many "
                                       "others directly, with how many.",
                        COLUMNS: [
                            {"key": "element_uid", "title": "Element",
                             "role": "element", "sortable": True},
                            {"key": "fan_out", "title": "Direct dependencies",
                             "quantity": "count", "sortable": True,
                             "description": "Dependencies this element "
                                            "names - an out-degree, not a "
                                            "transitive count."},
                        ]},
                }},
            "sensitivity": {
                "properties": {
                    # `UX-343`: the three scalars beside the list.
                    "critical_path_us": {
                        QUANTITY: "duration_us",
                        "description": "The chain's duration, which the "
                                       "savings below are measured against."},
                    "total_improvable_time_us": {
                        QUANTITY: "duration_us",
                        "description": "How much of the chain sits in elements "
                                       "that could move."},
                    "best_case_speedup": {
                        QUANTITY: "ratio",
                        "description": "How much faster an unlimited-capacity "
                                       "replay would be. A ceiling, not a "
                                       "plan."},
                    "top_opportunities": {
                        "description": "Elements whose duration the "
                                       "makespan is most sensitive to.",
                        COLUMNS: [
                            {"key": "element_uid", "title": "Element",
                             "role": "element", "sortable": True},
                            {"key": "sensitivity", "title": "Sensitivity",
                             "quantity": "share", "sortable": True,
                             "description": "How much of the makespan "
                                            "moves per unit this element "
                                            "moves."},
                            {"key": "saving_us", "title": "Worth fixing",
                             "quantity": "duration_us", "sortable": True,
                             "description": "What the makespan would drop "
                                            "by, in seconds, if this "
                                            "element cost nothing."},
                        ]},
                }},
            "serialization_point_risks": {
                "items": {"properties": {
                    # `UX-343`: the record's own scalars, beside the
                    # nested element table that was already declared.
                    "builders": {
                        QUANTITY: "count",
                        "description": "The builder count this risk was "
                                       "measured at."},
                    "governing_cores": {
                        QUANTITY: "count",
                        "description": "Cores the pinned elements were "
                                       "competing for."},
                    "typical_max_jobs": {
                        QUANTITY: "count",
                        "description": "The `-j` the pinned elements' own "
                                       "builds used."},
                    "downstream_count": {
                        QUANTITY: "count",
                        "description": "Elements downstream of this one."},
                    "pinned_elements": {
                        "description": "The elements pinned at this "
                                       "serialization point, and what each "
                                       "one was pinned to.",
                        COLUMNS: [
                            {"key": "element_uid", "title": "Element",
                             "role": "element", "sortable": True},
                            {"key": "max_jobs", "title": "Native jobs",
                             "quantity": "count", "sortable": True,
                             "description": "The parallelism this "
                                            "element's own build system "
                                            "was allowed."},
                            {"key": "duration_us", "title": "Duration",
                             "quantity": "duration_us", "sortable": True},
                        ]},
                }}},
            "batch_opportunities": {
                "properties": {
                    "serialized_pairs": {
                        "description": "Pairs that ran one after the other "
                                       "with nothing forcing the order.",
                        COLUMNS: [
                            {"key": "first", "title": "Ran first",
                             "role": "element", "sortable": True},
                            {"key": "then", "title": "Ran after it",
                             "role": "element", "sortable": True},
                        ]},
                }},
        }},
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
                # `UX-343`: keyed by resource kind, which is data.
                QUANTITY: "ratio",
                "additionalProperties": {
                    QUANTITY: "ratio",
                    "description": "How occupied this resource kind was, "
                                   "averaged over the run."},
                "description": "Occupancy per resource kind, so a "
                               "saturated fetcher is not averaged away by "
                               "idle builders."},
            "peak_resource_occupancy": {
                QUANTITY: "count",
                "additionalProperties": {
                    QUANTITY: "count",
                    "description": "The most of this resource kind in "
                                   "flight at once."},
                "description": "The most in flight at once, per resource "
                               "kind."},
        },
    },
    "signals": {
        QUESTION: 'Which elements are on the chain that binds?',
        RAIL: 'act',
        # UX-289: the views over the one element table.
        #
        # `UX-268` joined the six element-keyed signals into one row per
        # element, and that table then had to serve every question at
        # once - 13 columns on the 1,202-element run. These name the
        # questions a reader actually arrives with, and each shows the
        # four to six columns that answer one.
        #
        # Every population here is a **filter over a published field**,
        # which is what `UX-288` made possible: `from` reads a selection
        # the payload already publishes once (and takes its order from
        # it), `where` tests a column the element records already carry.
        # Nothing here computes a membership the payload does not have -
        # Direction 7's boundary, and the reason `UX-288` came first.
        PRESETS: [
            {"name": "All elements",
             "question": "Which element should I look at?",
             "columns": ["element", "element_durations", "downstream_count",
                         "is_leaf", "observed_critical", "element_kind"],
             "sort": {"column": "element_durations", "direction": "desc"},
             "bound": 25},
            {"name": "Critical path",
             "question": "Which elements are on the chain that binds?",
             # In the order the chain runs, which is the order the
             # selection is published in - the page does not need to know
             # what a critical path is to draw it in the right order.
             "from": "signals.critical_path_detail",
             "columns": ["element", "element_durations", "slack",
                         "element_kind", "probability"]},
            {"name": "Leaves",
             "question": "What could be deferred?",
             "where": {"column": "is_leaf", "equals": True},
             "columns": ["element", "element_durations", "downstream_count",
                         "element_kind", "is_structural_kind"],
             "sort": {"column": "element_durations", "direction": "desc"}},
            {"name": "Choke points",
             "question": "What does everything wait on?",
             "from": "structural.bottleneck.choke_points",
             "columns": ["element", "element_durations", "downstream_count",
                         "weighted_duration_us", "element_kind"]},
            {"name": "Latent heavies",
             "question": "What is big and off the chain?",
             "where": {"column": "observed_critical", "equals": False},
             "columns": ["element", "element_durations", "slack",
                         "downstream_count", "risk_score"],
             "sort": {"column": "element_durations", "direction": "desc"},
             "bound": 25},
            # UX-338: the two-plane join, as a *view* of this table
            # rather than a second table of the same eleven elements.
            # `UX-215` published `element_join` and the page drew it on
            # its own, so every reader of a two-plane snapshot has seen
            # the whole population twice since then - which `UX-289` had
            # already ruled out. The columns are the join's: what the
            # sandbox actually did with the cores it was given.
            #
            # A run with no Plane 2 report carries none of these
            # columns, and `presetTable` drops a preset whose columns
            # are all absent - so this appears exactly when there is
            # something behind it, which is `UX-194`'s dead-control
            # rule at the level of a view.
            {"name": "Plane 2 (sandbox)",
             "question": "Compute-bound, or badly built?",
             "columns": ["element", "element_durations", "cores_busy",
                         "requested_jobs", "peak_rss_kb"],
             # Without these the view is `element_durations` under a
             # heading that promises the sandbox, so it is not offered
             # at all on a run that captured no Plane 2.
             "requires": ["cores_busy", "requested_jobs", "peak_rss_kb"],
             "sort": {"column": "element_durations", "direction": "desc"},
             "bound": 25},
        ],
        "description": "The graph's own account of where the time is: "
                       "which elements lie on the chain, what slack the "
                       "rest have, and what fixing each in turn is worth.",
        # UX-208: the three element tables a reader lands on from the
        # decision panel. They carry element uids, so they say so - and
        # every row earns the same Inspect with no per-table code.
        "properties": {
            # UX-303: the two populations `UX-260` publishes a shape
            # for. Both are `{n, min, max, deciles, p95, p99, is_flat}`,
            # so the hint names `n` as the count and one control draws
            # them and the store aggregate's `samples` shape alike.
            "element_duration_distribution": _distribution(
                "duration_us", "element duration in this run",
                "How this run's element durations are spread. The answer "
                "to \"is 40s slow *here*?\", which has none without the "
                "population. Nearest-rank percentiles, `null` below the "
                "sample floor."),
            "blast_radius_distribution": _distribution(
                "count", "blast radius in this graph",
                "How many elements sit downstream of each, spread across "
                "this graph. \"753 downstream\" is p99.9 in a "
                "1,202-element run and unremarkable in 40,000."),
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
            # `UX-343`: the element-keyed maps. A map whose keys are
            # *data* - an element uid - cannot name them in
            # `properties`, so the value's schema is declared once under
            # `additionalProperties` and every key resolves to it.
            # Measured through the page's own resolution, these were 56
            # leaves reaching the reader with no unit at all.
            "element_durations": {
                QUANTITY: "duration_us",
                "additionalProperties": {
                    QUANTITY: "duration_us",
                    "description": "How long this element took in this run, restore or build."},
                "description": "Each element's own duration, keyed by "
                               "uid. A cached element contributes its "
                               "restore, not its build."},
            "slack": {
                QUANTITY: "duration_us",
                "additionalProperties": {
                    QUANTITY: "duration_us",
                    "description": "How long this element could have been "
                                   "delayed without moving the makespan."},
                "description": "How long each element could have been "
                               "delayed without moving the makespan. "
                               "Zero is on the chain."},
            "downstream_count": {
                QUANTITY: "count",
                "additionalProperties": {
                    QUANTITY: "count",
                    "description": "Elements downstream of this one."},
                "description": "How many elements sit downstream of "
                               "each - what a change to it rebuilds."},
            "unweighted_depth": {
                QUANTITY: "count",
                "additionalProperties": {
                    QUANTITY: "count",
                    "description": "Edges from this element to the root."},
                "description": "Edges from each element to the root, "
                               "ignoring duration. The graph's shape "
                               "rather than this run's timings."},
            "wall_clock_share": {
                QUANTITY: "share",
                "additionalProperties": {
                    QUANTITY: "share",
                    "description": "This task's duration over the "
                                   "makespan."},
                "description": "Each task's duration over the makespan. "
                               "Keyed by the task's own identity, not by "
                               "element, because one element can run "
                               "more than one task."},
            "criticality_probability": {
                "additionalProperties": {
                    "properties": {
                        "probability": {
                            QUANTITY: "share",
                            "description": "How often this element lands "
                                           "on the critical path under "
                                           "the run's own perturbation - "
                                           "1.0 is always."},
                        "slack_us": {
                            QUANTITY: "duration_us",
                            "description": "How long this element could "
                                           "have been delayed - zero is "
                                           "on the chain."},
                    }},
                "description": "How reliably each element binds, rather "
                               "than whether it happened to today."},
            "blast_radius": {
                "additionalProperties": {
                    "properties": {
                        "downstream_count": {
                            QUANTITY: "count",
                            "description": "Elements this one's change "
                                           "rebuilds."},
                        "weighted_duration_us": {
                            QUANTITY: "duration_us",
                            "description": "What that rebuild costs, "
                                           "summed over the elements it "
                                           "touches."},
                        "risk_score": {
                            QUANTITY: "ratio",
                            "description": "Downstream work weighted by "
                                           "duration. A ranking, not a "
                                           "measurement - comparable "
                                           "within a run, not across."},
                    }},
                "description": "What one element's change rebuilds, and "
                               "what that costs."},
            "critical_path_length": {
                QUANTITY: "count",
                "description": "How many elements the chain runs "
                               "through. A count of elements, not a "
                               "duration - `floors.t_infinity_observed` "
                               "is the time."},
            "zero_slack_share": {
                QUANTITY: "share",
                "description": "The share of elements with no slack at "
                               "all. High means the chain is wide, not "
                               "long."},
            "cache": {
                "description": "What this run had to build and what it "
                               "restored.",
                "properties": {
                    "built_elements": {
                        QUANTITY: "count",
                        "description": "Elements this run had to build."},
                    "cached_elements": {
                        QUANTITY: "count",
                        "description": "Elements this run restored instead of "
                                       "building."},
                    "hit_ratio": {
                        QUANTITY: "share",
                        "description": "Elements restored over elements "
                                       "considered."},
                    "fetch": {
                        "description": "What this run pulled from a remote cache rather than rebuilding.",
                        "properties": {
                            "fetched": {
                                QUANTITY: "count",
                                "description": "Artifacts pulled from a "
                                               "remote."},
                            "already_present": {
                                QUANTITY: "count",
                                "description": "Artifacts already local, "
                                               "so nothing was pulled."},
                            "hit_ratio": {
                                QUANTITY: "share",
                                "description": "Artifacts already local "
                                               "over artifacts "
                                               "considered."}}},
                    "target_closure": {
                        "description": "The same question restricted to "
                                       "what the target actually needs.",
                        "properties": {
                            "elements": {
                                QUANTITY: "count",
                                "description": "Elements in the target's "
                                               "closure."},
                            "built": {
                                QUANTITY: "count",
                                "description": "Of the closure's elements, the ones that had to be built."},
                            "cached": {
                                QUANTITY: "count",
                                "description": "Of those, the ones "
                                               "restored."},
                            "hit_ratio": {
                                QUANTITY: "share",
                                "description": "Restored over considered, "
                                               "inside the closure."}}},
                }},
            "ready_queue": {
                "description": "How much work was ready to run and had "
                               "nowhere to run it.",
                "properties": {
                    "average_depth": {
                        QUANTITY: "ratio",
                        "description": "How many elements were ready and "
                                       "waiting, averaged over the build."},
                    "peak_depth": {
                        QUANTITY: "count",
                        "description": "The most elements ready and waiting at "
                                       "once."},
                    "nonzero_fraction": {
                        QUANTITY: "share",
                        "description": "The share of the build spent with "
                                       "anything waiting. High means "
                                       "capacity bound, not graph "
                                       "bound."}}},
            "fetch_build_overlap": {
                "properties": {
                    "overlap_us": {
                        QUANTITY: "duration_us",
                        "description": "Wall-clock where fetching and building "
                                       "ran at the same time."},
                    "fetch_prefix_us": {
                        QUANTITY: "duration_us",
                        "description": "Wall-clock at the start spent fetching "
                                       "with nothing building."},
                    "build_suffix_us": {
                        QUANTITY: "duration_us",
                        "description": "Wall-clock at the end spent building "
                                       "with nothing left to fetch."},
                    "fraction": {
                        QUANTITY: "share",
                        "description": "The overlap over the span the two "
                                       "phases covered together."}}},
            "joint_saving": {
                "properties": {
                    "joint_saving_us": {
                        QUANTITY: "duration_us",
                        "description": "What fixing the candidates together is "
                                       "worth, simulated - not the sum of what "
                                       "each is worth alone."},
                    "sum_of_individual_us": {
                        QUANTITY: "duration_us",
                        "description": "Those same savings added up, "
                                       "published so the difference from "
                                       "the joint figure is visible "
                                       "rather than implied."}}},
            "leaf_analysis": {
                "properties": {
                    "deferrable_count": {
                        QUANTITY: "count",
                        "description": "Leaf elements nothing else waits "
                                       "on, which could be built later or "
                                       "not at all."}}},
        },
    },
    "attribution": {
        QUESTION: 'Where did the wall-clock go?', RAIL: 'act',
        # `UX-343`: eight durations that rendered correctly only because
        # `guessQuantity` recognised `_us`. A guess that happens to be
        # right is still the gap UX-201 wrote the rule for.
        "properties": {
            "execution_on_chain_us": {
                QUANTITY: "duration_us",
                "description": "Time the chain's own elements spent executing "
                               "- the part of the makespan that is work rather "
                               "than waiting."},
            "dependency_wait_us": {
                QUANTITY: "duration_us",
                "description": "Time a chain element spent ready but waiting "
                               "on something it depends on."},
            "scheduler_wait_us": {
                QUANTITY: "duration_us",
                "description": "Time work was ready and the scheduler had not "
                               "started it."},
            "resource_wait_us": {
                QUANTITY: "duration_us",
                "description": "Time work was ready and the capacity to run it "
                               "was not free."},
            "retry_wait_us": {
                QUANTITY: "duration_us",
                "description": "Time spent on attempts that were thrown away "
                               "and run again."},
            "idle_us": {
                QUANTITY: "duration_us",
                "description": "Time with nothing running at all."},
            "untracked_head_us": {
                QUANTITY: "duration_us",
                "description": "Wall-clock before the first tracked task "
                               "started - BuildStream's own startup, outside "
                               "per-task tracking."},
            "untracked_tail_us": {
                QUANTITY: "duration_us",
                "description": "Wall-clock after the last tracked task "
                               "finished, outside per-task tracking."},
        }},
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
            "total_us": {
                QUANTITY: "duration_us",
                "description": "Time BuildStream spent outside any element - "
                               "loading, resolving, cache queries."},
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
                # UX-291: **this is the carrier a consumer should
                # believe.** A number here may also appear in
                # `provenance.evidence[].value` (a quotation of the
                # document at a path) and inside `copy_text` (a
                # rendering for a human). The three are written in one
                # pass from these values and a guard holds them equal;
                # where a consumer must pick one, it is this.
                #
                # Not a projection over `provenance.evidence`, which was
                # the other candidate: measured on the `macro_micro`
                # run, 14 of the finding evidence entries have a
                # citation and the rest are derived ratios with no
                # published path, so a projection would have to drop
                # numbers or invent paths for them.
                "evidence": {"type": ["object", "null"],
                             "properties": EVIDENCE_QUANTITIES},
                "provenance": _PROVENANCE,
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
            # `UX-343`: the scores are shares of a population, and
            # `ordering_violations` is a count of events. Both reached
            # the reader as bare numbers.
            "attribution_score": {
                QUANTITY: "share",
                "description": "How much of the makespan the attribution split "
                               "accounts for. Below one, the split is "
                               "describing part of the run."},
            "model_score": {
                QUANTITY: "share",
                "description": "How closely the replay model reproduced the "
                               "run it is modelling."},
            "provenance_score": {
                QUANTITY: "share",
                "description": "How much of what this report claims resolves "
                               "back to a published field."},
            "duration_coverage": {
                QUANTITY: "share",
                "description": "The share of elements whose duration was "
                               "actually recorded."},
            "critical_path_coverage": {
                QUANTITY: "share",
                "description": "The share of the chain whose elements carry a "
                               "measured duration."},
            "dominator_coverage": {
                QUANTITY: "share",
                "description": "The share of the graph the dominator analysis "
                               "could reach."},
            "blame_chain_coverage": {
                QUANTITY: "share",
                "description": "The share of waiting time that resolves to a "
                               "named cause."},
            "ordering_violations": {
                QUANTITY: "count",
                "description": "Task pairs whose recorded order "
                               "contradicts the graph. Nonzero means the "
                               "clock, not the graph, is the thing to "
                               "distrust."},
            "task_count": {
                QUANTITY: "count",
                "description": "How many tasks this run recorded at all."},
            "failed_task_count": {
                QUANTITY: "count",
                "description": "Tasks that failed. A failed run is not a slow "
                               "run, and the two must not be read together."},
            "failed_task_us": {
                QUANTITY: "duration_us",
                "description": "Wall-clock spent on tasks that failed."},
            "explained_untracked_us": {
                QUANTITY: "duration_us",
                "description": "How much of the untracked time this report can "
                               "account for."},
            "primary": {
                QUANTITY: "share",
                "description": "How much of this run's own record supports the "
                               "conclusions above - coverage, provenance and "
                               "model fit combined."},
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
            "aggregating_dependency_pairs": {
                QUANTITY: "count",
                "description": "Dependency pairs where one element's "
                               "measurement includes another's."},
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
            "chain_ratio": {
                QUANTITY: "share",
                "description": "The critical path as a share of wall-clock - "
                               "the number the diagnosis is decided by."},
            "chain_bound_ratio": {
                QUANTITY: "share",
                "description": "The threshold `chain_ratio` is compared "
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
            "provenance": _PROVENANCE,
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
                        "provenance": _PROVENANCE,
                    },
                },
            },
        },
    },
    "plane2_absence": {
        QUESTION: 'Why is Plane 2 not in this report?',
        RAIL: 'prove',
        "description": "One of three sentences (bga/plane2.py): the plane "
                       "was never captured, or it was captured and its raw "
                       "log was not kept, or this analysis was told to "
                       "ignore it. Absent when Plane 2 is here.",
    },
    "plane2_coverage": {
        QUESTION: 'How much did Plane 2 see?',
        RAIL: 'prove',
        "properties": {
            # `UX-343`: process counts, every one of them.
            "cpu_reconciled_processes": {
                QUANTITY: "count",
                "description": "Processes whose CPU both planes agree on."},
            "cpu_from_spine_only": {
                QUANTITY: "count",
                "description": "Processes whose CPU only the ptrace spine saw."},
            "opens_covered_processes": {
                QUANTITY: "count",
                "description": "Processes the open-file hook covered."},
            "fork_only_exits": {
                QUANTITY: "count",
                "description": "Exits seen for a process that only ever forked "
                               "- no exec, so no command to name."},
            "unmatched_ends": {
                QUANTITY: "count",
                "description": "Process ends with no matching start. Non-zero "
                               "here weakens every per-process figure."},
            "by_coverage": {
                QUANTITY: "count",
                "additionalProperties": {
                    QUANTITY: "count",
                    "description": "Processes in this coverage class."},
                "description": "How many processes each coverage class "
                               "accounts for, keyed by the class."},
            "processes": {
                QUANTITY: "count",
                "description": "Processes Plane 2 saw across both record "
                               "streams - the hook and the spine, counted once "
                               "each."},
            "opens_coverage": {
                QUANTITY: "share",
                "description": "The share of those processes whose opened "
                               "paths were recorded; only the hook can see "
                               "them."},
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
            # UX-297: which shape of Plane 2 report served these
            # numbers. Not a qualifier on them - both shapes publish
            # the same aggregates - but the answer to "why is this
            # capture's report a gigabyte".
            "source": {
                "description": "Which Plane 2 report shape this run's "
                               "numbers came from. `plane2/v2` carries "
                               "per-element aggregates only; the "
                               "unstamped `plane2/v1` a capture before "
                               "`UX-297` wrote also embeds every "
                               "per-process record, which no published "
                               "number reads.",
                "properties": {
                    "schema": {"description": "The report's contract id."},
                    "records_embedded": {
                        "description": "Whether the file still carries the "
                                       "per-process record list."},
                    "records": {
                        QUANTITY: "count",
                        "description": "How many records it carries; zero for "
                                       "`plane2/v2`."},
                    "note": {"description": "What that means for this run, "
                                            "in a sentence."},
                },
            },
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
                # `UX-343`: the six the shares below are computed from.
                # The object said what it was; its members said nothing,
                # so they printed as raw microsecond integers beside the
                # percentages derived from them.
                QUANTITY: "duration_us",
                "description": "Slot-time split by what it was doing: "
                               "useful work, idleness with nothing ready, "
                               "idleness with too little parallelism, and "
                               "work thrown away by retry or rebuild.",
                "properties": {
                    "useful": {
                        QUANTITY: "duration_us",
                        "description": "Slot-time spent on work that "
                                       "ended up in the result."},
                    "idle_no_tasks": {
                        QUANTITY: "duration_us",
                        "description": "Slot-time with nothing ready to "
                                       "run. The graph's shape, not the "
                                       "capacity."},
                    "idle_underparallel": {
                        QUANTITY: "duration_us",
                        "description": "Slot-time with work ready and too "
                                       "few slots to take it. The "
                                       "capacity, not the graph."},
                    "wasted_rebuild": {
                        QUANTITY: "duration_us",
                        "description": "Slot-time rebuilding what a cache "
                                       "could have supplied."},
                    "wasted_retry": {
                        QUANTITY: "duration_us",
                        "description": "Slot-time on attempts that were "
                                       "thrown away and run again."},
                    "untracked": {
                        QUANTITY: "duration_us",
                        "description": "Slot-time no bucket claimed. A "
                                       "gap in the record rather than a "
                                       "kind of work."},
                }},
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
    "direct_count": {
        QUANTITY: "count",
        "description": "Elements that depend on this one directly. The first "
                       "hop only."},
    "blast_count": {
        QUANTITY: "count",
        "description": "Everything a change here rebuilds, transitively - the "
                       "number that makes a small element expensive to touch."},
    "building_count": {
        QUANTITY: "count",
        "description": "Of those, the ones that do real build work."},
    "assembling_count": {
        QUANTITY: "count",
        "description": "Of those, the ones that only gather what is below them "
                       "- they rebuild, but cost little."},
    "element_count": {
        QUANTITY: "count",
        "description": "Elements in the project, as the denominator for the "
                       "reach above."},
    "measured_elements": {
        QUANTITY: "count",
        "description": "How many of the affected elements have a recorded "
                       "duration. The rest are counted, never estimated."},
    "measured_seconds": {
        QUANTITY: "seconds",
        "description": "Recorded rebuild time below this element. A sum over "
                       "the measured elements only, so it is a lower bound on "
                       "the real cost."},
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
                "depth": {
                    QUANTITY: "count",
                    "description": "Hops from the direct consumers, "
                                   "breadth-first."},
                "measured_seconds": {
                    QUANTITY: "seconds",
                    "description": "This element's own recorded duration, not "
                                   "its subtree's."},
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

_STORE_AGGREGATE_REQUIRED = {
    "project": "string",
    "snapshots": "integer",
    "measured": "integer",
    "excluded": "object",
    "contract_composition": "object",
    "host_classes": "array",
    "store_bytes": "object",
    # `""` rather than `"object"`: both are genuinely absent as `null`
    # - no blend was asked for, nothing was refused - and `_document`
    # already makes every declared type nullable, so spelling it here
    # would nest the union.
    "blended": "object",
    "refusal": "object",
}

# UX-234: one distribution's shape. Declared once and referenced from
# every figure, because a reader who has learned `duration_us` has
# learned `cache_hit_rate` too.
_DISTRIBUTION = {
    # UX-303: and this *is* a distribution, so it draws as one. The
    # hint names where the sample count lives, which is what lets the
    # density strip read this shape and `analyze/v2`'s (which counts in
    # `n`) with one control.
    DISTRIBUTION: "samples",
    "description": "A distribution over finished runs: `samples` (the "
                   "count it was computed from), `min`, `median`, "
                   "`p95`, `max` and `mad` (median absolute deviation, "
                   "unscaled - the robust spread `compute_band` is "
                   "built on, without its 1.4826 scaling or its k). "
                   "Percentiles are nearest-rank - the value at index "
                   "ceil(p*n)-1 of the sorted samples - so every figure "
                   "is one a build actually took rather than a point "
                   "between two of them. `null` below the sample floor; "
                   "incomplete captures are excluded and counted in "
                   "`excluded`. The description lives here rather than "
                   "on each leaf because this object appears eight "
                   "times, and eight copies of one paragraph is weight "
                   "the export pays for nothing.",
}

_STORE_AGGREGATE_HINTS = {
    "project": {"description": "The project whose store this describes."},
    "snapshots": {
        QUANTITY: "count",
        "description": "Snapshots on disk, finished or not."},
    "measured": {
        QUANTITY: "count",
        "description": "Of those, the ones that finished and recorded a "
                       "duration - the only ones any distribution here is "
                       "computed from."},
    "excluded": {
        "description": "What was left out and why, counted by reason. "
                       "Published rather than dropped: \"we had nine "
                       "runs\" and \"we had nine and threw two away\" "
                       "are different claims (UX-156).",
        "properties": {
            "count": {
                QUANTITY: "count",
                "description": "Snapshots excluded from every distribution."},
            "by_reason": {"description": "How many were excluded for "
                                         "each distinct reason."},
        },
    },
    "contract_composition": {
        QUESTION: 'Were these runs written under the same definitions?',
        "description": "Which contract sets the aggregated runs were "
                       "produced under (UX-253). A store can hold runs "
                       "from several builds of `bga`, and \"we "
                       "aggregated thirty runs\" and \"we aggregated "
                       "thirty runs written under two different "
                       "definitions of the fields\" are different "
                       "claims. The rule is UX-250's, applied to a set: "
                       "what decides comparability is movement in the "
                       "contracts this document *reads*, never the "
                       "package version.",
        "properties": {
            "sets": {"description": "Each distinct contract set found, "
                                    "with how many runs carry it, "
                                    "commonest first."},
            "unstamped_runs": {
                QUANTITY: "count",
                "description": "Runs whose producer recorded no "
                               "contracts - every artifact predating "
                               "UX-249. An explicit unknown, never "
                               "read as agreement."},
            "reads": {"description": "The contracts this document "
                                     "itself reads. A set that moved "
                                     "one of these makes its runs "
                                     "unreadable here; a set that moved "
                                     "anything else does not."},
            "mixed": {"description": "Whether more than one contract "
                                     "set is present."},
        },
    },
    "host_classes": {
        QUESTION: 'What does a build cost on each machine?',
        "description": "One entry per host class - the grouping "
                       "UX-186's compared fields already distinguish. "
                       "Durations are never scaled across classes.",
        "items": {
            "properties": {
                "host_class": {"description": "CPU model, core count and "
                                              "memory, joined - the label "
                                              "two runs must share to be "
                                              "aggregated together."},
                "host_manifest": {"description": "The full manifest of "
                                                 "the first run in this "
                                                 "class, or null where "
                                                 "the captures predate "
                                                 "it."},
                "runs": {
                    QUANTITY: "count",
                    "description": "Finished runs in this class."},
                "duration_us": _DISTRIBUTION,
                "cache_hit_rate": _DISTRIBUTION,
                "cores_busy": _DISTRIBUTION,
                "peak_rss_mb": _DISTRIBUTION,
                "snapshot_bytes": _DISTRIBUTION,
                "total_bytes": {
                    QUANTITY: "bytes",
                    "description": "What this class's snapshots weigh on disk, "
                                   "summed."},
                "stamps": {"description": "Which snapshots these are, so "
                                          "a figure can be traced to the "
                                          "runs behind it."},
                "shortfall": {
                    "description": "Present instead of a distribution "
                                   "when the class has fewer than "
                                   "`compare.MIN_BASELINE_RUNS` finished "
                                   "runs. Names what is missing rather "
                                   "than publishing a p95 of two "
                                   "samples."},
                "resource_shortfall": {
                    "description": "Present instead of `cores_busy` and "
                                   "`peak_rss_mb` when no run in this "
                                   "class carries them. UX-296: the "
                                   "scalars are written beside the "
                                   "Plane 2 report at capture time, so a "
                                   "snapshot older than that sidecar has "
                                   "none - and no reader parses a "
                                   "gigabyte of capture to find out."},
            },
            "required": ["host_class", "runs"],
        },
    },
    "blended": {
        "description": "One distribution across every class. `null` "
                       "unless the store holds a single class, or the "
                       "caller passed --blend and took the mixed claim "
                       "themselves.",
        "properties": {
            "runs": {
                QUANTITY: "count",
                "description": "Finished runs across all classes."},
            "mixes": {
                QUANTITY: "count",
                "description": "How many host classes were mixed. 1 means "
                               "nothing was."},
            "duration_us": _DISTRIBUTION,
            "cache_hit_rate": _DISTRIBUTION,
            "cores_busy": _DISTRIBUTION,
            "peak_rss_mb": _DISTRIBUTION,
            "snapshot_bytes": _DISTRIBUTION,
            "total_bytes": {
                QUANTITY: "bytes",
                "description": "What every class's snapshots weigh on disk, "
                               "summed."},
        },
    },
    "store_bytes": {
        QUESTION: "What is this store costing me?",
        RAIL: "raw",
        "description": "What `.bga/runs` weighs. UX-300: published at "
                       "the document level rather than inside `blended`, "
                       "because a duration measured on two machines is "
                       "two populations and a byte is a byte - a reader "
                       "asking what their disk holds should not have to "
                       "pass --blend to be told.",
        "properties": {
            "total": {
                QUANTITY: "bytes",
                "description": "Every snapshot this store holds, including the "
                               "ones excluded from the distributions: a "
                               "capture that failed is not a sample, and still "
                               "occupies its disk."},
            "snapshots": {
                QUANTITY: "count",
                "description": "How many snapshots that total is spread over, "
                               "finished or not."},
            "measured_total": {
                QUANTITY: "bytes",
                "description": "The subset that did finish - what the "
                               "distributions above are computed over."},
            "note": {"description": "What the figures mean, and what "
                                    "recovers the space."},
        },
    },
    "refusal": {
        "description": "Why no blended figure is published, when none "
                       "is. UX-186's grammar: durations are not scaled "
                       "across machines, so a mixed distribution is a "
                       "claim the tool declines to make on its own.",
        "properties": {
            "check": {"description": "Which check refused - the name a "
                                     "caller matches on rather than the "
                                     "prose."},
            "classes": {
                QUANTITY: "count",
                "description": "How many host classes the store holds."},
            "sentence": {"description": "The refusal in words, naming "
                                        "the classes and the flag that "
                                        "overrides it."},
        },
    },
}


_STORE_HINTS = {
    "total_bytes": {
        QUANTITY: "bytes",
        "description": "What the stored snapshots occupy on disk, together."},
    "count": {
        QUANTITY: "count",
        "description": "Snapshots held. The length of every trend drawn from "
                       "this store."},
    # UX-203: duration leads, because "is this project drifting" is a
    # question about time. Size is still here - it is what the store
    # warning is about - but it stopped being the answer.
    "snapshots": {COLUMNS: ["stamp", "total_duration_us", "verdict_kind",
                            "cache_hit_rate", "bytes", "alias",
                            "incomplete_reason"],
                  "items": {
                      "properties": {
                          # UX-234: the host each snapshot was measured
                          # on, so a trend can mark a point taken on a
                          # different machine rather than drawing it as
                          # if the series were homogeneous.
                          "host_class": {
                              "description": "CPU model, core count and "
                                             "memory of the machine this "
                                             "snapshot was measured on, "
                                             "as the single label "
                                             "UX-186's compared fields "
                                             "reduce to. The label rather "
                                             "than the manifest: this row "
                                             "is drawn for every snapshot "
                                             "on every `bga view`. "
                                             "`store-aggregate/v1` "
                                             "carries the full manifest "
                                             "per class."},
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
    STORE_AGGREGATE: lambda: _document(
        STORE_AGGREGATE, "bga snapshot --aggregate --format json",
        _STORE_AGGREGATE_REQUIRED,
        "A store as a distribution rather than as a list: what a build "
        "of this project costs, how much it varies, what its p95 is and "
        "what it draws, per host class. Incomplete captures are "
        "excluded and counted; a mix of machines is refused rather than "
        "blended, because durations are not scaled across hosts.",
        hints=_STORE_AGGREGATE_HINTS),
    SWEEP: lambda: _document(
        SWEEP, "bga sweep RUN --format json",
        _SWEEP_REQUIRED,
        "What more capacity would buy: one makespan per capacity tried, "
        "the knee past which more buys little, and the capacities where "
        "the model contradicted itself. A replay over already-observed "
        "durations, so the caveat travels with the numbers rather than "
        "beside them.",
        hints=_SWEEP_HINTS),
    WHATIF: lambda: _document(
        WHATIF, "bga whatif RUN --element A --element B",
        _WHATIF_REQUIRED,
        "What the build would drop to if a chosen set of elements were "
        "fixed together - one longest-path recompute with each of them "
        "zeroed, never a sum of their individual savings. Refused, with "
        "the reason, for an empty selection or an element this run "
        "cannot project.",
        hints=_WHATIF_HINTS),
}


def names() -> List[str]:
    """Every schema this tool produces, newest contract first."""
    return sorted(_SCHEMAS)


def schema(name: str) -> dict:
    """The JSON Schema for one output, by its `schema` value.

    The lookup and the build are separate statements on purpose. They
    were one - `return _SCHEMAS[name]()` under a single `except
    KeyError` - and a `KeyError` raised *inside* a document's builder
    came back as "unknown schema `sweep/v1` - this tool produces ...,
    `sweep/v1`, ...", which names the thing it says it does not know.
    `UX-339` hit it: a contract whose hints describe a key its required
    map no longer has raises from `_document`, and that is a defect in
    the contract, not a missing one.
    """
    try:
        build = _SCHEMAS[name]
    except KeyError:
        raise KeyError(
            f"unknown schema {name!r} - this tool produces "
            f"{', '.join(names())}") from None
    return build()


def critical_path_uids(signals: dict) -> list:
    """The run's critical path, in order, from the one place it lives.

    `UX-288`: `signals.critical_path` used to publish exactly this and
    `signals.critical_path_detail` published it again with columns -
    measured identical, order included, on the 1,202-element run. The
    bare list is gone and this is the projection every reader that
    wanted it now shares, so "the path" has one definition rather than
    two that could drift.
    """
    signals = signals or {}
    detail = signals.get('critical_path_detail') or []
    if detail:
        return [entry.get('element_uid') for entry in detail
                if isinstance(entry, dict) and entry.get('element_uid')]
    # An `analyze/v1` document, or a run directory written by one. `bga`
    # reads its own past output (`UX-249`) and `bga compare` reads two
    # runs at once, so a v2 reader that could not read a v1 path would
    # break the loop this tool exists for. The bare list is gone from
    # what v2 *writes*; it is still understood when read.
    return list(signals.get('critical_path') or [])


def choke_point_uids(bottleneck: dict) -> list:
    """The graph's choke points, ranked, from the one place they live.

    `UX-288`: `structural.bottleneck` published `choke_points` (ranked
    uids) and `choke_point_impact` (the same uids, valued) - one
    membership twice, nine elements each on the macro/micro run. `v2`
    publishes one ordered list of records; this reads either that or an
    `analyze/v1` document's bare list, for the same reason
    `critical_path_uids` does.
    """
    entries = (bottleneck or {}).get('choke_points') or []
    return [entry.get('element_uid') if isinstance(entry, dict) else entry
            for entry in entries]


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
