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
from .findings import DIAGNOSES, READERS

# UX-288: v2. Three fields were **removed** - `signals.critical_path`,
# `signals.leaf_analysis.leaves` and `structural.deferrability`'s two
# uid lists - each of which republished element membership already
# published beside it. The versioning rule below is explicit that a
# removal moves the version, and this is the case it was written for.
# `UX-341`: v3. Four spellings of three dimensions left the vocabulary
# and the keys that carried them were renamed with the unit they are
# now in - `measured_us`, `peak_rss_bytes`, `useful_share`,
# `occupancy_share`. Renames are removals, so this is a version move by
# the rule below and not an edit.
# `UX-344`: v4, and the largest move of the four. The `signals` and
# `structural` namespaces are **gone** - every table they held is a
# top-level key, `metrics` and `summary` renamed to `graph_metrics` and
# `graph_summary`, and the six element-keyed maps grouped under
# `elements`, the one table they always were. `provenance` is published
# once per claim at the top level instead of three times inside the
# claims that cite it, and `findings[].evidence.blast_radius` - a slice
# of a population published in full beside it - is gone by `UX-288`'s
# rule. Every one of those is a removal or a rename, which is what this
# version move is for.
ANALYZE = "analyze/v4"
COMPARE = "compare/v2"
BLAST = "blast/v2"
STORE = "store/v1"

# `UX-297`'s convention, one level up: the ids a release still *reads*
# but no longer writes. An old store is full of files stamped with one,
# and the release that can open them has to be able to say so. `bga`
# reads a `v2` analyze document by name - the keys this item renamed
# resolve through `guessQuantity` rather than through a declaration, so
# an old snapshot still renders, with the fallback saying so.
SUPERSEDED = ("analyze/v3", "analyze/v2", "compare/v1", "blast/v1",
              "correlate/v1")
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
CORRELATE = "correlate/v2"

#: `UX-408`: **what `serialized_pairs` is**, written once.
#:
#: The computation (`bga/structural/batching.py`) collects pairs that
#: are **not** independent - same dependency chain - so a reader can see
#: *why* two elements were not batched. The terminal said exactly that.
#: The schema description the page renders said the opposite:
#:
#:     "Pairs that ran one after the other with nothing forcing the
#:      order."
#:
#: A page reader was told these pairs are unforced serialization - free
#: wins - when the computation selected them *because* the order is
#: forced, and would have gone off to "fix" pairs the tool knows cannot
#: be batched. The viewer and the terminal disagreed about the same rows
#: at the caption level, which is the page's own never-disagree property
#: broken.
#:
#: One string, imported by both, rather than a pinned pair: two copies
#: held equal by a guard can still both be edited, and this one drifted
#: for as long as it existed.
#: Short enough to be a terminal caption and a page description both,
#: which is what keeps it one string rather than two that agree today.
SERIALIZED_PAIRS_MEANING = (
    "Pairs on the same dependency chain, so not independently batchable."
)

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
# UX-346: **where a value's sentence lives.** `UX-220` gave every
# declared quantity a sentence and `UX-201` sourced it from here, so it
# cannot drift from the payload. What was never decided is where it
# goes, and the page's answer was "beside the value, always": measured
# on a real boot, 1,479 of the golden page's 3,466 words (43%) and
# 2,312 of macro_micro's 6,283 (37%) were prose identical on every run,
# printed beside a `?` door offering the same sentence again.
#
# The default is now the door. Two classes keep the sentence inline,
# and both are declared here rather than decided per call site, so the
# page cannot drift back:
#
#   `"name"`   - the label invites a reading the value does not have
#                (`useful_share` is a share of *capacity*), or invites
#                none at all (`t_infinity_observed`). The sentence is
#                what makes the number readable, not what enriches it.
#   `"caveat"` - reading the number without the sentence changes what
#                a reader would *do*: a recommendation that is a
#                hypothesis rather than a setting, a `false` that means
#                "not measured" rather than "no", a non-zero that
#                weakens every figure beside it.
#
# Anything else is a description, and a description is one click away.
INLINE = "bga:inline"
INLINE_REASONS = ("name", "caveat")

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

# `UX-361` (styleguide §2d): the two shapes the vocabulary did not have.
#
# A strip shows a distribution and a sparkline shows an ordered series.
# Round 55 counted what that leaves undrawn: 19 of `golden`'s 43
# sections and 29 of `macro_micro`'s 58 carry six or more numbers and
# no marks - `floors` (11 numbers, 558 px, the tool's central claim)
# and `confidence` (28 numbers, 561 px) among them, because a *total
# split into parts* and *values compared on one axis* are neither of
# the two shapes that exist.
#
# Both hints name **published paths**, in the grammar `resolvePath` and
# `bga/provenance.py` both walk, resolved against the document. That is
# Direction 7 in the declaration rather than in a comment: the page
# does not choose the parts, does not compute a remainder, and does not
# pick an axis from the data.
DECOMPOSITION = "bga:decomposition"   # a published total, in published parts
INTERVAL = "bga:interval"             # published values on one axis
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

KEYED_BY = "bga:keyed_by"          # what the map's own keys are

#: The one value `KEYED_BY` takes today. A task uid is
#: `element|kind|phase|attempt` (`bga/ingest/models.py`'s `TaskKey`), and
#: it is right as an *identity* - a retry and a fetch of one element are
#: different rows - and wrong as a *label*: `UX-391` measured
#: `codegen.bst|BUILD|BUILD|0` printed verbatim as a row name, so a
#: reader searching the page for `codegen.bst` did not match it.
#:
#: `UX-374` established that a published key renders as it was
#: published. This is the exception that proves it: the key is still
#: published verbatim as the row's identity, and what the reader sees is
#: the part of it that is a name.
KEYED_BY_TASK_UID = "task_uid"

#: `UX-390`: **the run's own advice about this map's keys lives there.**
#:
#: `attribution` and `attribution_hints` were one population in two
#: `<h2>` sections - the same eight bucket names, a number in one
#: chapter and the sentence explaining it in another, and nothing in
#: either saying they were the same eight things. That is `UX-288`'s
#: one-population rule at section level.
#:
#: Two sentences, not one, and they are different things: the schema's
#: `description` says what a bucket *is* and travels with the contract;
#: the hint says what to do about it **on this run** and is computed -
#: `resource_wait_us`'s names whether this run's capacity checks could
#: run at all. So the hint is not a description, and declaring where it
#: lives is what lets the page draw both on one row without sniffing a
#: key named `<something>_hints`.
EXPLAINED_BY = "bga:explained_by"

PRESET_DIRECTIONS = ("asc", "desc")
# The acceptance bound `UX-289` was filed with: a table that needs more
# than this to answer one question is not a view of the data, it is the
# data. Measured before: the element table carried 13 columns because
# one table had to serve every question.
PRESET_COLUMNS_MAX = 8

# The closed set of quantities. Closed deliberately: an open vocabulary
# is one a renderer cannot be complete against, and a renderer that
# silently falls back to "print the raw number" is what this replaces.
# `UX-341`: and *one member per dimension*. It had nine, and three
# dimensions were spelled more than one way - `seconds` beside
# `duration_us`, `megabytes` and `kilobytes` beside `bytes`, `percent`
# beside `share`. Every tail was derived from its own head, usually by
# a lossy division of a value the tool already held as an integer, and
# a consumer comparing two figures had to know which convention each
# was written under. The renderer still knows the retired spellings
# (`bga/viewer/format.js`); no schema may declare one.
QUANTITIES = (
    "duration_us",   # microseconds; render as a human duration
    "bytes",         # UX-201/UX-215: not megabytes, not kilobytes -
                     # calling a KiB count `bytes` is wrong by 1024x,
                     # which is why the conversion happens at the input
                     # boundary in `bga/units.py` and not in a renderer
    "share",         # 0..1; render as a percentage
    "count",
    "ratio",         # unbounded; render as a multiplier
)

# The dimension each member measures. `UX-341`'s property, stated as
# data so a guard can assert it: no two members may measure one thing,
# which is a rule about the vocabulary rather than a list of four names
# a later round would re-add.
DIMENSIONS = {
    "duration_us": "time",
    "bytes": "memory",
    "share": "bounded fraction",
    "count": "cardinality",
    "ratio": "unbounded multiplier",
}

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
    # `UX-372`: the index over `findings[].reader`.
    "readers": "array",
    "floors": "object",
    "attribution": "object",
    "attribution_hints": "object",
    "occupancy": "object",
    # `UX-344`: what `signals` and `structural` held, each on its own.
    # The order is the order the page reads them in, which is the order
    # a lifted key was declared in inside the namespace it left.
    "elements": "object",
    "element_duration_distribution": "object",
    "blast_radius_distribution": "object",
    "critical_path_detail": "array",
    "optimization_horizon": "array",
    "latent_heavies": "array",
    "wall_clock_share_us": "object",
    "cache": "object",
    "ready_queue": "object",
    "fetch_build_overlap": "object",
    "joint_saving": "object",
    "leaf_analysis": "object",
    "graph_metrics": "object",
    "graph_summary": "object",
    "deferrability": "object",
    "parallelism": "object",
    "bottleneck": "object",
    "sensitivity": "object",
    "serialization_point_risks": "array",
    "batch_opportunities": "object",
    "consolidation_candidates": "array",
    # `UX-344`: one record per claim, beside the claims that carry ids
    # into it. Optional for the reason `producer` is: a section report
    # is not a full document and carries none.
    "provenance": "array",
    "document_shape": "object",
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
    # `UX-370`: what Plane 2 saw the build run, in calls and in CPU.
    # Projected from the Plane 2 report beside the join, so present on
    # exactly the runs the join is - additive, so `analyze/v4` does not
    # bump.
    "by_binary": "object",
    "binary_cost": "array",
    "configure_phase": "object",
    # `UX-383`: the run-level halves of the three blocks `UX-370` left
    # in the terminal. Their per-element halves are fields on an
    # `element_join` row, by `UX-382`'s placement rule - which is also
    # what keeps one population from being drawn four times.
    "cpu_time": "object",
    "peak_memory": "object",
    "resource_pressure": "object",
    # `UX-407`: the one paragraph that names a whole restructuring -
    # the never-read edges, the elements they chain, and a replay of
    # this run without them. Computed by the same join as
    # `element_join` and published by `correlate/v2` under this name,
    # in the same shape: two contracts carrying one finding, not two
    # findings. Present on exactly the runs the join is - additive, so
    # `analyze/v4` does not bump (`UX-190`).
    "restructuring": "array",
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
# UX-229: the chain behind one claim. One shape, because a consumer that
# learns to read one has learned to read all of them.
#
# `UX-344`: and one *place*. It used to be nested in each of the three
# claims that carry one - the diagnosis, every finding, every top action
# - which put the deepest shape in the document (six levels, 81 leaves
# on `macro_micro`) inside the record it explains, and wrote the top
# action's chain as a `see` path into the finding's copy. This is the
# item schema of the published `provenance` list now: one record per
# claim, and the claim carries the id it already carried.
_PROVENANCE = {
    "description": "Why this claim is made: the published fields it was "
                   "read from, the rule that fired, and the trace query "
                   "that deepens it. References into this same document "
                   "rather than copies, so a reader can follow them.",
    "properties": {
        "claim": {"description": "Which claim this explains - a finding "
                                 "id, or `diagnosis` for the headline."},
        "kind": {"description": "Where the claim is published: "
                                "`diagnosis` for the headline, `finding` "
                                "for a row of `findings`."},
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
                    "quantity": {
                        "enum": list(QUANTITIES),
                        "description": "The unit of `value`, resolved "
                                       "from `path`. Here rather than on "
                                       "`value` because a provenance row "
                                       "carries whatever field the rule "
                                       "read, so no single declaration "
                                       "on the key could be right "
                                       "(`UX-343`). Absent where the "
                                       "path names something the schema "
                                       "does not describe."},
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
                "threshold_quantity": {
                    "enum": list(QUANTITIES),
                    "description": "The unit of `threshold`, resolved from "
                                   "the `observed_path` it is compared "
                                   "against. Absent where the rule "
                                   "compares against a quantity the "
                                   "finding computes rather than "
                                   "publishes (`UX-343`)."},
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
    # `UX-372`: and who each finding is for. In this list rather than
    # the conditional one: every finding declares a reader, so a report
    # with findings has readers - the index is a fact about the same
    # list, not about the run. Beside `headline` because it defers to
    # it: the reader who owns the headline's action leads with it.
    "readers",
    "findings", "floors", "capacity_verdict", "attribution",
    "attribution_hints", "occupancy",
    # `UX-344`: the tables `signals` and `structural` used to hold. Only
    # the ones a full report of a *normal* run always carries are here.
    # Measured on the golden run, four are not: `cache` and the two
    # distributions need a population to describe and
    # `fetch_build_overlap` needs both phases, so each is a fact about
    # the run rather than a shortened document - which is the
    # distinction this list exists to keep.
    "elements", "critical_path_detail", "optimization_horizon",
    "latent_heavies", "wall_clock_share_us", "ready_queue", "joint_saving",
    "leaf_analysis", "graph_metrics", "graph_summary", "deferrability",
    "parallelism", "bottleneck", "sensitivity", "batch_opportunities",
    "provenance", "document_shape",
    "utilisation", "confidence", "violations",
)

# UX-215: the keys a full report carries only when `--plane2` was
# given. Kept out of `ANALYZE_FULL_KEYS` because that list is what the
# pin asserts is *always* there, and a run with one plane is still a
# full report.
ANALYZE_PLANE2_KEYS = (
    # `UX-370`: what Plane 2 saw the build *run*, in calls and in CPU.
    "by_binary", "binary_cost", "configure_phase",
    # `UX-383`: the three that were measured, published in `plane2.json`
    # and read by nothing the page draws.
    "cpu_time", "peak_memory", "resource_pressure",
    "plane2_coverage", "element_join", "element_join_coverage",
    # UX-329: the other side of the same conditional. `plane2_absence`
    # is present exactly when the three above are not, so it belongs in
    # the same list for the same reason: a full report is full with
    # either, and the pin must not demand both.
    "plane2_absence",
)

# `UX-344`: keys a full report carries when the run has something to put
# in them. `signals` was always present because *something* in it always
# was; lifted, four of its tables answer questions a given run may not
# raise - there is no cache table without a cache, no duration or blast
# distribution without a population to describe, and no fetch/build
# overlap without both phases. Kept out of `ANALYZE_FULL_KEYS` for the
# reason `ANALYZE_PLANE2_KEYS` is: that list is what the pin asserts is
# *always* there, and a report missing one of these is still full.
ANALYZE_RUN_DEPENDENT_KEYS = (
    "cache", "element_duration_distribution", "blast_radius_distribution",
    "fetch_build_overlap", "consolidation_candidates",
    "serialization_point_risks",
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
    "measured_us": "",
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
    {"key": "peak_rss_bytes", "title": "Peak RSS",
     "quantity": "bytes", "sortable": True},
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
            "wall_us": {
                QUANTITY: "duration_us",
                "description": "Wall-clock those processes spanned."},
        }},
    "serial_binary": {
        "description": "The binary whose work ran one process at a time.",
        "properties": {
            "cpu_us": {
                QUANTITY: "duration_us",
                "description": "CPU time this binary used while running one "
                               "process at a time."},
            "wall_us": {
                QUANTITY: "duration_us",
                "description": "Wall-clock it spanned doing so - close to "
                               "`cpu_us` is the tell."},
        }},
    "worst_redundancy": {
        "description": "The repeated work this element paid for most.",
        "properties": {
            "occurrence_count": {
                QUANTITY: "count",
                "description": "How many times the repeated work ran."},
            "total_duration_us": {
                QUANTITY: "duration_us",
                "description": "Wall-clock the repeated work cost across all "
                               "its occurrences."},
            "max_element_duration_us": {
                QUANTITY: "duration_us",
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
    "on_critical_path": {
        "type": "boolean",
        "description": "Whether this element is on the chain that sets the "
                       "run's finish time. `UX-382`: the second of the "
                       "join's two denormalised Plane 1 facts, and the one "
                       "that hides - it is "
                       "`elements.criticality_probability[<uid>]"
                       ".observed_critical` under a different name, so a "
                       "count of attributes appearing in both shapes does "
                       "not see it. The map is the authority; the resolved "
                       "element record takes it from there."},
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
        "description": "How many elements a change here rebuilds. `UX-382`: "
                       "the one attribute in both of the entity's shapes, "
                       "and an int here where `elements.blast_radius[<uid>]` "
                       "is a record - this is that record's own "
                       "`downstream_count`, denormalised so the join table "
                       "can sort on it. The map is the authority; the "
                       "resolved element record takes it from there."},
    "cores_busy": {
        INLINE: "name",
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
    "peak_rss_bytes": {
        QUANTITY: "bytes",
        "description": "The largest single process's resident memory, "
                       "which is what a builder count has to be "
                       "multiplied against. A **maximum**: adding two "
                       "elements' peaks claims they overlapped, which "
                       "this cannot say - unlike the counters below, "
                       "which are sums and may be added (`UX-383`)."},
    # `UX-383`: the CPU quantity beside `cores_busy`'s ratio, and
    # `UX-379`'s three pressure axes. All four counters are summed over
    # the element's processes - the opposite of `peak_rss_bytes` above,
    # and the reason each says which it is here rather than leaving a
    # reader to guess from the name.
    "cpu_us": {
        QUANTITY: "duration_us",
        "description": "CPU this element's own processes burned. "
                       "`cores_busy` is the rate and this is the "
                       "quantity: an element can be CPU-bound and "
                       "cheap, or idle and enormous, and a reader "
                       "chasing one is not chasing the other."},
    "read_bytes": {
        QUANTITY: "bytes",
        "description": "Block-layer reads summed over this element's "
                       "processes - what reached the device. Zero is a "
                       "measurement rather than a gap: a read served "
                       "from the page cache never got there."},
    "written_bytes": {
        QUANTITY: "bytes",
        "description": "Block-layer writes summed the same way, which "
                       "is what separates an element that was slow "
                       "writing from one that was slow computing."},
    "major_faults": {
        QUANTITY: "count",
        "description": "Faults that went to disk, summed - the page "
                       "pressure a memory-starved host produces, and "
                       "the signal that a build is swapping rather "
                       "than working."},
    "involuntary_switches": {
        QUANTITY: "count",
        "description": "The run queue preempting a process that still "
                       "had work, summed. It rises with "
                       "oversubscription, which is how an element "
                       "slowed by its siblings is told from one slowed "
                       "by its own work."},
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
    "hit_share": ("share",
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
    "target_closure_hit_share": ("share",
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
    "envelope_bytes": ("bytes",
        "Peak resident memory the run would need at the recommended "
        "builder count."),
    "host_memory_bytes": ("bytes",
        "Memory the host reported, which the memory ceiling is computed against."),
    "cores_busy": ("ratio",
        "CPU-seconds per wall-second inside the element - how much "
        "parallelism its own build actually achieved."),
    "measured_us": ("duration_us",
        "Wall-clock actually measured, as opposed to estimated."),
}

# `UX-346`: the evidence keys whose sentence stays beside the number,
# by the same two rules the schema nodes use - a label that invites the
# wrong reading, or a caveat that changes what a reader would do. A
# finding is the one place on the page a reader acts from, so a denial
# printed one click away is a denial nobody meets.
_EVIDENCE_INLINE = {
    "share_of_path": "name",             # not of wall-clock
    "share_of_host": "name",             # not of what the build asked for
    "path_us": "name",                   # the chain, not the wall-clock
    "criticality_probability": "name",   # not a certainty
    "sum_of_individual_us": "caveat",    # double-counts the overlap
}
# `certified_headroom_us` was a sixth candidate and is deliberately not
# here: `decision.certified_headroom_us` carries a different sentence
# for the same name - "repeated here from `floors`" rather than a
# caveat - and a name that renders inline in one block and behind a
# door in another is the drift `UX-341` forbids under a new heading.
# One name, one treatment, or neither.

EVIDENCE_QUANTITIES = {
    key: ({QUANTITY: quantity, "description": sentence}
          | ({INLINE: _EVIDENCE_INLINE[key]} if key in _EVIDENCE_INLINE else {}))
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
    # `UX-341`: `change` used to be here as a `share` *and* on
    # `capacity_recommendation` as a count of builders. One name, two
    # dimensions - so the count was renamed for what it counts, and the
    # share went with it, because after the rename nothing emitted a
    # finding key called `change` at all.
    "builders_change": {
        QUANTITY: "count", DIRECTION: "higher_is_better", INLINE: "name",
        "description": "`recommended_builders` minus `builders`, signed - "
                       "negative means the run asked for more than something "
                       "can serve."},
    # `UX-344`: `findings[].evidence.blast_radius` is gone - it was a
    # slice of `elements.blast_radius`, keyed by element uid, published
    # a second time inside the finding that names those elements. What
    # is left of that evidence is the distribution below, which is a
    # property of the run and not of any element.
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
            INLINE: "name",
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


# `UX-344`: the views over the one element table, now declared on
# `elements` - the key that holds it - rather than on the namespace
# it used to be a row of.
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
_ELEMENT_PRESETS = [
    {"name": "All elements",
     "question": "Which element should I look at?",
     "columns": ["element", "element_durations", "downstream_count",
                 "is_leaf", "observed_critical", "element_kind"],
     "sort": {"column": "element_durations", "direction": "desc"}},
    {"name": "Critical path",
     "question": "Which elements are on the chain that binds?",
     # In the order the chain runs, which is the order the
     # selection is published in - the page does not need to know
     # what a critical path is to draw it in the right order.
     "from": "critical_path_detail",
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
     "from": "bottleneck.choke_points",
     "columns": ["element", "element_durations", "downstream_count",
                 "weighted_duration_us", "element_kind"]},
    {"name": "Latent heavies",
     "question": "What is big and off the chain?",
     "where": {"column": "observed_critical", "equals": False},
     "columns": ["element", "element_durations", "slack",
                 "downstream_count", "risk_score"],
     "sort": {"column": "element_durations", "direction": "desc"}},
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
                 "requested_jobs", "peak_rss_bytes"],
     # Without these the view is `element_durations` under a
     # heading that promises the sandbox, so it is not offered
     # at all on a run that captured no Plane 2.
     "requires": ["cores_busy", "requested_jobs", "peak_rss_bytes"],
     "sort": {"column": "element_durations", "direction": "desc"}},
]

# `UX-344`: the two namespaces, and what stands where they did.
#
# Measured on the emitted `analyze/v3`: 57% of the golden report's
# leaves and 67% of `macro_micro`'s sat deeper than three levels, and
# two of those levels carried nothing at all. `signals` and `structural`
# were maps of *named tables* - neither held a value of its own, and
# both cost every table below them a level. Each table is a top-level
# key now, carrying the `bga:rail` its namespace used to carry for it,
# which is what the reader's rail and `UX-286`'s chapters group by
# anyway.
#
# `metrics` and `summary` are `graph_metrics` and `graph_summary`: at
# the top level they would be two of the most generic names in the
# document, and the page already draws a `summary` section - the run's
# own scalars - that a second one would have collided with.
_STRUCTURAL_TABLES = {
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
            "critical_path_share": {
                QUANTITY: "share",
                "description": "The chain's length over the graph's "
                               "depth - how much of the shape the "
                               "chain accounts for."},
            "serialization_share": {
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
                INLINE: "name",
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
                "description": SERIALIZED_PAIRS_MEANING,
                COLUMNS: [
                    {"key": "first", "title": "Ran first",
                     "role": "element", "sortable": True},
                    {"key": "then", "title": "Ran after it",
                     "role": "element", "sortable": True},
                ]},
        }},
    # `UX-344`: the one table `structural` carried with no declaration
    # at all. A lifted table with no rail lands in "Everything else",
    # which a guard reddens on - so the lift is what made this a gap
    # rather than a silence.
    "consolidation_candidates": {
        "description": "Elements that are always consumed together and "
                       "could be one element. Structural: read from the "
                       "graph's own edges, never from a timing estimate.",
        COLUMNS: [
            {"key": "elements", "title": "Could be one element"},
            {"key": "shared_consumers", "title": "Always consumed by"},
        ]},
}

_SIGNALS_TABLES = {
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
    "wall_clock_share_us": {
        INLINE: "name",
        QUANTITY: "duration_us",
        # `UX-391`: the keys are task uids, not element names. Declared
        # rather than sniffed - the page cannot tell `a.bst|BUILD|BUILD|0`
        # from a binary called that without being told.
        KEYED_BY: KEYED_BY_TASK_UID,
        "additionalProperties": {
            QUANTITY: "duration_us",
            "description": "The wall-clock this task alone is "
                           "responsible for - its marginal share of "
                           "the active window, as time rather than "
                           "as a fraction."},
        "description": "How much of the active window each task "
                       "alone accounts for, in microseconds. Keyed "
                       "by the task's own identity, not by element, "
                       "because one element can run more than one "
                       "task."},
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
            "hit_share": {
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
                    "hit_share": {
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
                    "hit_share": {
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
                # `UX-344`: the caveat `_EVIDENCE_INLINE` already puts on
                # this key inside a finding. Lifting `joint_saving` made
                # the number a row of a section rather than a value
                # nested inside one, and a row draws a door - so the
                # sentence a reader must not miss is declared on both
                # carriers rather than on one.
                INLINE: "caveat",
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
                               "not at all."},
            # `UX-344`: the one map keyed by element uid that declared
            # nothing about its values - found by the clause this item
            # added, not by reading the schema.
            "leaves_detail": {
                "description": "Each leaf, keyed by its element uid.",
                "additionalProperties": {
                    "properties": {
                        "element_kind": {
                            "description": "The kind BuildStream gives "
                                           "this element."},
                        "is_structural_kind": {
                            "description": "Whether its dependents are "
                                           "the graph's shape rather "
                                           "than a task - a `stack` or "
                                           "an `import`."},
                        "is_potentially_deferrable": {
                            "description": "Whether nothing in this run "
                                           "waited on it, so building it "
                                           "later would have cost the "
                                           "makespan nothing."},
                        "deferral_risk": {
                            "description": "How safe deferring it looks: "
                                           "`low`, `medium` or `high`."},
                    }}}}},
}

# `UX-407`: the restructuring synthesis, declared **once** for the two
# contracts that carry it.
#
# `correlate/v2` published it from the day `UX-82` was built and
# `analyze/v4` now does too, from the same join and in the same shape.
# One declaration rather than two, because two copies of a shape a
# guard holds equal can still both be edited in one commit - the
# lesson `UX-408` paid for one round earlier with a caption and a
# description that said opposite things.
#
# Each row is a *group*: a set of elements chained by declared build
# edges that Plane 2 measured never-read, and a replay of this run
# without them. The edges are the table (`from` -> `to`, named by
# `UX-290`'s tuple rule rather than `#1`/`#2`); the projection is the
# sentence.
_RESTRUCTURING_EDGE_COLUMNS = [
    {"key": "from", "title": "Staged by", "role": "element"},
    {"key": "to", "title": "Never read by", "role": "element"},
]

_RESTRUCTURING_ITEM_PROPERTIES = {
    "id": {"type": "string",
           "description": "Which synthesis this is. One id today - "
                          "`unread-gating-chain`."},
    "severity": {"type": "string", "enum": list(SEVERITIES)},
    "elements": {
        "type": "array",
        "description": "The elements the unread edges chain together. "
                       "Fanning them out is what the projection below "
                       "replays."},
    "edges": {
        "type": "array",
        COLUMNS: _RESTRUCTURING_EDGE_COLUMNS,
        "description": "Each declared build edge Plane 2 measured "
                       "never-read: the second element opened no file "
                       "the first staged. Evidence, not a verdict - a "
                       "runtime-only dependency looks identical here."},
    "projection": {
        "type": ["object", "null"],
        "properties": {
            "replayed_baseline_us": {
                QUANTITY: "duration_us",
                "description": "This run replayed as it ran, so the "
                               "pair below is one replay against "
                               "another rather than a replay against "
                               "a measurement."},
            "projected_us": {
                QUANTITY: "duration_us",
                "description": "The same replay with those edges "
                               "removed - same durations, same "
                               "capacity."},
            "saving_us": {
                QUANTITY: "duration_us",
                "description": "The difference. A replay of this run's "
                               "durations, not a re-capture."},
            "capacities": {
                # Keyed by resource name (`PROCESS`, `DOWNLOAD`,
                # `UPLOAD`), so the unit is declared once for the map
                # rather than per key - `UX-343`'s rule for a map keyed
                # by data.
                "additionalProperties": {
                    QUANTITY: "count",
                    "description": "Concurrent slots of this resource."},
                "description": "The scheduler capacities the replay "
                               "held fixed. Changing them is a different "
                               "question, and `bga whatif` is where it "
                               "is asked."},
        },
    },
}

_RESTRUCTURING_HINT = {
    QUESTION: 'Which dependency edges are never read?',
    RAIL: "act",
    # `elements` is published and **not** drawn: it is the union of the
    # edge endpoints (`bga/correlate.py` builds it as exactly that), so
    # a column for it is the same population as the edge table beside
    # it - `UX-338`'s rule, and `UX-288`'s sweep says so on the payload
    # too. A consumer that wants the set has the key; a reader has the
    # table it is the endpoints of.
    COLUMNS: [
        {"key": "severity", "title": "Severity"},
        {"key": "edges", "title": "Unread edges"},
        {"key": "projection", "title": "Replayed without them"},
    ],
    "items": {"type": "object", "properties": _RESTRUCTURING_ITEM_PROPERTIES,
              "required": ["id", "severity", "elements", "edges"]},
    "description": "The conclusion the per-element `unused_dependencies` "
                   "rows jointly support: these elements form a chain "
                   "whose every internal declared edge went unread, so "
                   "fanning them out is one change rather than seven. "
                   "Worth *checking* whether those edges are needed at "
                   "build time - each one is evidence, not a verdict.",
}

_ANALYZE_HINTS = {
    "timestamp_agreement": {
        QUESTION: 'Do the two planes agree about the clock?', RAIL: 'prove',
        # `UX-343`: this block is entirely durations and counts, and
        # said so nowhere - nine leaves, no unit. `UX-341` then took the
        # four `_s` members to microseconds; declaring them first is
        # what made that a rename rather than a guess.
        "properties": {
            "resolution_us": {
                QUANTITY: "duration_us",
                "description": "The finest interval the two planes' clocks can "
                               "tell apart."},
            "shortest_task_us": {
                QUANTITY: "duration_us",
                "description": "The shortest task measured - the case the "
                               "resolution above matters most for."},
            "worst_excess_us": {
                QUANTITY: "duration_us",
                "description": "The largest amount by which one plane's "
                               "duration exceeded the other's."},
            "worst_shortfall_us": {
                QUANTITY: "duration_us",
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
                INLINE: "name",
                QUANTITY: "duration_us",
                "description": "When the capture began, as microseconds "
                               "since the epoch. A point in time rather "
                               "than a span - the unit is the same and "
                               "the reading is not."},
            "host_manifest": {"properties": {
                "cpu_count": {
                    QUANTITY: "count",
                    "description": "Cores the host reported, which the CPU ceiling is computed against."},
                "memory_bytes": {
                    QUANTITY: "bytes",
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
                INLINE: "name",
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
                INLINE: "name",
                QUANTITY: "count",
                "description": "Cores the host reported. The ceiling the "
                               "CPU constraint is computed against, and "
                               "the reason a recommendation is about this "
                               "machine rather than about the graph "
                               "alone."},
            "cores_busy": {
                INLINE: "name",
                QUANTITY: "ratio",
                "description": "Cores drawn on average across the whole "
                               "run, from Plane 2 - CPU-seconds per "
                               "wall-second, which is the same measurement "
                               "`element_join[].cores_busy` publishes and "
                               "so carries the same unit (UX-341: this "
                               "declared `count` and that declared "
                               "`ratio`). An average, not a peak: during "
                               "the parallel stretch each element draws "
                               "more, so the CPU ceiling below is "
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
                INLINE: "caveat",
                QUANTITY: "count",
                "description": "What the binding constraint allows. A "
                               "hypothesis to time, not a setting to "
                               "apply - see `caveat`."},
            "builders_change": {
                QUANTITY: "count", DIRECTION: "higher_is_better",
                "description": "`recommended_builders` minus `builders`, "
                               "signed - negative means the run asked for "
                               "more than something can serve. UX-341: "
                               "named for what it counts, because "
                               "`findings[].evidence.change` is a share and "
                               "one name may not mean two things."},
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
                INLINE: "caveat",
                "description": "Whether the run asked for more parallelism "
                               "than the host could serve. False also when "
                               "the checks did not run - read `checks_ran` "
                               "before reading this."},
            "undersubscribed": {
                INLINE: "caveat",
                "description": "Whether the host could have served more "
                               "parallelism than the run asked for. Carries "
                               "the same caveat as `oversubscribed`."},
            "checks_ran": {
                INLINE: "caveat",
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
    # `UX-344`: every claim's chain, once, beside the claims.
    "provenance": {
        QUESTION: 'Why does bga believe this?',
        RAIL: 'prove',
        "description": "One record per claim this report makes: the "
                       "published fields it was read from, the rule that "
                       "fired, and the trace query that deepens it. "
                       "`claim` is the finding's own id, or `diagnosis` "
                       "for the headline.",
        COLUMNS: [
            {"key": "claim", "title": "Claim", "sortable": True},
            {"key": "kind", "title": "Published as", "sortable": True},
        ],
        "items": _PROVENANCE,
    },
    # `UX-344`: what this document's own shape measures, published with
    # it. The depth this item was filed against had to be measured by
    # writing a script against two fixtures; the next round reads it off
    # the document. Counts itself, so a consumer that re-measures gets
    # these numbers back.
    "document_shape": {
        QUESTION: 'How deep is this document?',
        RAIL: 'raw',
        "description": "How deeply this document nests, measured on the "
                       "document as published. A container step counts a "
                       "level, so `findings[].evidence.rows[].duration_us` "
                       "is six.",
        "properties": {
            "leaves": {
                QUANTITY: "count",
                "description": "Every value that is not a container."},
            "deepest_depth": {
                QUANTITY: "count",
                "description": "How many levels down the deepest leaf in "
                               "this document sits."},
            "deepest_path": {
                "description": "One path that reaches it, with `[]` for a "
                               "list step."},
            "deeper_than_three": {
                QUANTITY: "count",
                "description": "Leaves more than three levels down - the "
                               "count `UX-344` was filed on."},
            "deeper_than_three_share": {
                QUANTITY: "share",
                "description": "Those leaves as a share of all of them."},
        },
    },
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
                INLINE: "name",
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
    "attribution": {
        QUESTION: 'Where did the wall-clock go?', RAIL: 'act',
        # `UX-396`: the section that asks where the wall-clock went,
        # drawing where it went. Eight published buckets of one
        # published total, and they sum to it exactly - on
        # `macro_micro`, 43,200,000 + 2,717,000 + 216,000 =
        # 46,133,000 = `total_duration_us` - so the page lays out
        # numbers it was handed rather than working out a remainder.
        # `UX-361`'s instrument, on the section `UX-303` says wants
        # its shape before its rows.
        DECOMPOSITION: {
            "total": "total_duration_us",
            "quantity": "duration_us",
            "parts": [
                {"path": "attribution.execution_on_chain_us",
                 "key": "execution", "label": "work on the chain"},
                {"path": "attribution.dependency_wait_us",
                 "key": "dependency", "label": "waiting upstream"},
                {"path": "attribution.resource_wait_us",
                 "key": "resource", "label": "capacity full"},
                {"path": "attribution.scheduler_wait_us",
                 "key": "scheduler", "label": "nothing dispatched"},
                {"path": "attribution.idle_us",
                 "key": "idle", "label": "nothing ready"},
                {"path": "attribution.retry_wait_us",
                 "key": "retry", "label": "retries"},
                {"path": "attribution.untracked_head_us",
                 "key": "head", "label": "before the first task"},
                {"path": "attribution.untracked_tail_us",
                 "key": "tail", "label": "after the last"},
            ],
        },
        # `UX-390`: and the run's advice for each bucket, drawn on the
        # bucket's own row rather than in a second section over the
        # same eight names.
        EXPLAINED_BY: "attribution_hints",
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
        # `UX-361`: the tool's central claim, drawn. Both parts and the
        # total are published fields and they sum to it exactly -
        # 43,200,000 + 2,933,000 = 46,133,000 on `macro_micro` - so the
        # page lays out three numbers it was handed rather than working
        # out what is left over.
        DECOMPOSITION: {
            "total": "total_duration_us",
            "quantity": "duration_us",
            "parts": [
                {"path": "floors.t_infinity_observed",
                 "key": "chain", "label": "critical path"},
                {"path": "headline.scheduling_gap_us",
                 "key": "gap", "label": "off the path"},
            ],
            "mark": {"path": "floors.lb", "key": "lb",
                     "label": "certified lower bound"},
        },
        "description": "Lower bounds this run certifies: what no schedule "
                       "of the same recorded work could have beaten. "
                       "Floors, not forecasts - beating one needs the "
                       "graph or the work to change, not the scheduler.",
        "properties": {
            "t_infinity_observed": {
                INLINE: "name",
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
                QUANTITY: "share",
                "description": "Makespan against the certified floor. `LB / "
                               "horizon`, so it is bounded at 1 - a share "
                               "against a bound this run proved, never "
                               "against an ideal build. UX-341: the finding "
                               "that quotes this declared `share` while the "
                               "floor itself declared `ratio`; one number "
                               "cannot have two units."},
            "occupancy_share": {
                QUANTITY: "share",
                "description": "Slot-time used as a share of slot-time "
                               "available. Unlike the efficiency score it "
                               "falls when independent work is serialized."},
            "t_infinity_cold": {
                INLINE: "caveat",
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
    # `UX-372`: who this run has something to say to.
    #
    # The page had one reader. It opened "What should I do?" and
    # answered it once - and on `macro_micro` the three top actions are
    # the same advice three times (shorten this element, then that one,
    # then the third), which serves R1 and nobody else. The CI owner's
    # lever, `capacity-recommendation`, was finding nine of eleven.
    #
    # `leads_with` is the *producer's* decision about a reader's biggest
    # lever, for Direction 7's reason: a page that ranked severities of
    # its own would be a second decision-maker, and the terminal and the
    # CI comment would route differently from the report.
    "readers": {
        QUESTION: 'Who does this run have something to say to?',
        RAIL: 'decide',
        COLUMNS: [
            {"key": "label", "title": "Reader", "sortable": False},
            {"key": "question", "title": "Their question",
             "sortable": False},
            {"key": "leads_with", "title": "Leads with", "sortable": False},
        ],
        "items": {
            "type": "object",
            "properties": {
                "id": {"type": "string",
                       "enum": [uid for uid, _r, _l, _q in READERS],
                       "description": "The reader, by `roles.md` id."},
                "role": {"type": "string",
                         "description": "That reader's row in "
                                        "`docs/design/roles.md` - `R1` "
                                        "through `R5` - so the payload "
                                        "and the role model share one "
                                        "vocabulary rather than two."},
                "label": {"type": "string",
                          "description": "What this reader would say "
                                         "about themselves, in the "
                                         "first person. The selector's "
                                         "option text."},
                "question": {"type": "string",
                             "description": "The question this reader "
                                            "came with, which is what "
                                            "the page answers when they "
                                            "say who they are."},
                "leads_with": {"type": "string",
                               "description": "The id of the finding "
                                              "that is this reader's "
                                              "biggest lever on this "
                                              "run: highest severity, "
                                              "then published order."},
                "findings": {"type": "array",
                             "description": "Every finding id serving "
                                            "this reader, in published "
                                            "order. `leads_with` is one "
                                            "of these."},
            },
            "required": ["id", "role", "label", "question", "leads_with"],
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
                # `UX-368`: the query that shows this finding in the
                # timeline, by id into `questions.js`'s library.
                #
                # Published on the finding rather than left one join
                # away. `UX-229` put the mapping on the provenance
                # record; `UX-344` moved the records out of the
                # findings into one list - and `trace_context.js` went
                # on reading `finding.provenance.trace_query`, a path
                # the payload had stopped having. Measured on
                # `tests/fixtures/with_timeline`, whose handoff works:
                # four findings earn an Investigate button and **zero**
                # were drawn. A field a consumer has to join two lists
                # to reach is a field the consumer stops reaching.
                #
                # Null where no query answers this finding, which is
                # `UX-321`'s rule: the absence is published, not left
                # to be inferred from an empty control.
                "trace_query": {
                    "type": ["string", "null"],
                    "description": "The `questions.js` query id that "
                                   "shows this finding in the "
                                   "timeline, or null where none "
                                   "does. The same mapping "
                                   "`provenance[].trace_query` "
                                   "carries, on the object a reader "
                                   "is looking at."},
                # `UX-372`: which of `docs/design/roles.md`'s readers
                # this finding is for. Declared, never derived: the
                # page routes by lookup, and a consumer asking what
                # this run says to the person who owns the machines
                # gets an answer without re-ranking severities of its
                # own (Direction 7).
                "reader": {
                    "type": ["string", "null"],
                    "enum": [uid for uid, _r, _l, _q in READERS] + [None],
                    "description": "The reader this finding serves, by "
                                   "`roles.md` id, or null where the "
                                   "finding is for everyone. `readers` "
                                   "is the index over these."},
            },
            "required": ["id", "severity", "title"],
        },
    },
    "confidence": {
        QUESTION: 'How much of this can be believed?',
        RAIL: 'prove',
        # `UX-361`: five published scores on one axis, so a reader sees
        # which one is the weak leg rather than reading five numbers
        # and holding them in their head. The axis is 0..1 because a
        # share's axis is 0..1, not because of anything in the data -
        # a mark that moved when another one did would be a picture of
        # this run rather than of the scores.
        INTERVAL: {
            "quantity": "share", "low": 0, "high": 1,
            "marks": [
                {"path": "confidence.primary",
                 "key": "primary", "label": "confidence"},
                {"path": "confidence.provenance_score",
                 "key": "provenance", "label": "provenance"},
                {"path": "confidence.coverage_score",
                 "key": "coverage", "label": "coverage"},
                {"path": "confidence.model_score",
                 "key": "model", "label": "model"},
                {"path": "confidence.attribution_score",
                 "key": "attribution", "label": "attribution"},
            ],
        },
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
                "description": "The share of the task time this run "
                               "recorded that the normalised timeline "
                               "accounts for. Below one, some of the "
                               "recorded time did not survive "
                               "normalisation - start-clamping shrinks "
                               "a task that began before its "
                               "dependencies finished."},
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
    "restructuring": _RESTRUCTURING_HINT,
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
            "chain_share": {
                QUANTITY: "share",
                "description": "The critical path as a share of wall-clock - "
                               "the number the diagnosis is decided by."},
            "chain_bound_share": {
                QUANTITY: "share",
                "description": "The threshold `chain_share` is compared "
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
    "plane2_absence": {
        QUESTION: 'Why is Plane 2 not in this report?',
        RAIL: 'prove',
        "description": "One of three sentences (bga/plane2.py): the plane "
                       "was never captured, or it was captured and its raw "
                       "log was not kept, or this analysis was told to "
                       "ignore it. Absent when Plane 2 is here.",
    },
    # `UX-370`: what the build spent its time **running**.
    #
    # Round 58 asked what cmake configure costs and what generating a
    # test image costs, in calls and in seconds. Plane 2 measures the
    # first; the numbers sat in `plane2.json` beside the run and the
    # page carried the binary *names* and none of the figures. These
    # three are that answer, declared so the generic renderer draws
    # them as quantities rather than as a wall of bare integers.
    "by_binary": {
        QUESTION: 'What did this build actually run, and how often?',
        RAIL: 'act',
        QUANTITY: "count",
        "description": "Every binary Plane 2 saw exec, and how many "
                       "times the whole run ran it. The frequency half "
                       "of the question; `binary_cost` is the time "
                       "half, per element.",
        "additionalProperties": {QUANTITY: "count"},
    },
    "binary_cost": {
        QUESTION: 'Which binaries cost this build its time?',
        RAIL: 'act',
        COLUMNS: ["element", "binary", "calls", "cpu_us", "cpu_share"],
        "description": "One row per element and binary Plane 2 saw it "
                       "run: how many calls, and what they cost. Two "
                       "questions in one table because they disagree - "
                       "a process-storm is many cheap calls and a "
                       "compiler is few expensive ones, and a reader "
                       "chasing one is not chasing the other. An "
                       "element Plane 2 saw no process for contributes "
                       "no rows; `plane2_coverage` is where that is "
                       "stated.",
        "items": {
            "properties": {
                "element": {"description": "The element that ran it."},
                "binary": {"description": "The executable name, as it "
                                          "was exec'd."},
                "calls": {QUANTITY: "count",
                          "description": "How many times this element "
                                         "ran this binary."},
                "cpu_us": {QUANTITY: "duration_us",
                           "description": "CPU across those calls. Null "
                                          "for a binary ranked by count "
                                          "alone - it was too cheap to "
                                          "reach the CPU ranking."},
                "cpu_share": {QUANTITY: "share",
                              "description": "That CPU as a share of "
                                             "this element's measured "
                                             "CPU."},
                "wall_us": {QUANTITY: "duration_us",
                            "description": "Wall-clock those calls "
                                           "spanned. Plane 2 publishes "
                                           "it in seconds; converted at "
                                           "the boundary, because the "
                                           "vocabulary carries one time "
                                           "member and it is "
                                           "microseconds."},
            },
        },
    },
    "cpu_time": {
        QUESTION: 'What did the whole build cost in CPU?',
        RAIL: 'prove',
        "description": "The run-level totals beside `element_cpu_time`, "
                       "and the sentence that says what a CPU figure "
                       "here is and is not.",
        "properties": {
            "total_cpu_us": {QUANTITY: "duration_us",
                             "description": "CPU across every measured "
                                            "process in the build."},
            "measured_processes": {
                QUANTITY: "count",
                "description": "How many processes that CPU was read "
                               "from."},
            "unmeasured_processes": {
                QUANTITY: "count",
                "description": "How many it could not be read from - a "
                               "signal death or an exec replacement "
                               "leaves no rusage behind."},
            "spine_sourced_processes": {
                QUANTITY: "count",
                "description": "Of the measured, how many came from the "
                               "ptrace spine rather than the hook."},
            "note": {"description": "What a CPU figure here means, in a "
                                    "sentence - `UX-346`'s door."},
        },
    },
    "peak_memory": {
        QUESTION: 'What does a peak-memory figure here mean?',
        RAIL: 'prove',
        "description": "The sentence beside `element_peak_memory`. It "
                       "carries no totals on purpose: there is no "
                       "run-level peak to publish, because summing "
                       "per-process maxima would state something the "
                       "measurement cannot support.",
        "properties": {
            "note": {"description": "What a peak figure is, and what "
                                    "adding two of them would claim."},
        },
    },
    "resource_pressure": {
        QUESTION: 'How much of the build did the pressure counters cover?',
        RAIL: 'prove',
        "description": "The run-level coverage beside "
                       "`element_resource_pressure`, and the sentence "
                       "that says what each counter is.",
        "properties": {
            "measured": {QUANTITY: "count",
                         "description": "Processes across the build "
                                        "whose counters were read."},
            "unmeasured": {QUANTITY: "count",
                           "description": "Processes across the build "
                                          "whose counters were not."},
            "note": {"description": "What each counter measures, in a "
                                    "sentence."},
        },
    },
    "configure_phase": {
        QUESTION: 'What does configuring cost, before anything is built?',
        RAIL: 'act',
        "description": "The share of CPU spent in configure work rather "
                       "than in building. A floor, for the reason "
                       "`note` gives.",
        "properties": {
            "available": {
                "description": "False where nothing classified as "
                               "configure work."},
            "configure_cpu_us": {
                QUANTITY: "duration_us",
                "description": "CPU spent in configure work across the "
                               "whole run - summed over processes, so "
                               "it exceeds wall-clock where they ran "
                               "in parallel."},
            "configure_share": {
                QUANTITY: "share",
                "description": "That CPU as a share of all CPU Plane 2 "
                               "saw. A floor, for the reason `note` "
                               "gives."},
            "total_cpu_us": {
                QUANTITY: "duration_us",
                "description": "All CPU Plane 2 saw, configure and "
                               "build together - the denominator "
                               "`configure_share` is a share of."},
            # `UX-346`: the caveat is the door's sentence, not a
            # paragraph in the middle of the numbers. It is what makes
            # the share a floor rather than a measurement.
            "note": {
                "description": "How a process is classified as "
                               "configure work, and why the share is a "
                               "floor rather than a total."},
        },
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
                INLINE: "caveat",
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
            # `UX-389`: the capture's own identity, carried here
            # rather than left at a terminal. Six blocks that change
            # how every number under them is read - a reader looking
            # at an attribution table had no way to learn that the
            # spine never ran, so those numbers are a floor rather
            # than a measurement.
            "process_count": {
                QUANTITY: "count",
                "description": "Processes the capture traced at all. "
                               "The population every per-element "
                               "reduction is drawn from."},
            "max_concurrency": {
                QUANTITY: "count",
                "description": "The peak number of traced processes "
                               "alive at once. A process with no "
                               "observed exit is excluded rather than "
                               "assumed to run for ever - the "
                               "sentence beside this says why."},
            "wall_span_us": {
                QUANTITY: "duration_us",
                "description": "The window the hook was actually "
                               "watching. Shorter than the build means "
                               "part of it ran uninstrumented."},
            "spine_policy": {
                "description": "Whether the ptrace spine ran, and over "
                               "how many sandboxes. With `policy: off` "
                               "every CPU figure below is the hook's "
                               "alone, which is a floor.",
                "properties": {
                    "policy": {
                        INLINE: "name",
                        "description": "`off`, `on` or `auto` - what "
                                       "the capture was asked for."},
                    "sandboxes": {
                        QUANTITY: "count",
                        "description": "Sandboxes the build ran."},
                    "spine_traced": {
                        QUANTITY: "count",
                        "description": "How many of them the spine "
                                       "actually attached to."},
                },
            },
            "static_census": {
                "description": "Which elements could be hiding a "
                               "statically-linked binary the hook can "
                               "never see. Read from the project's own "
                               "sources before anything runs.",
                "properties": {
                    "elements_at_risk": {
                        "description": "Elements whose local sources "
                                       "carry an ELF executable with no "
                                       "PT_INTERP."},
                },
            },
            "open_records_note": {
                "description": "Why a process may be missing from "
                               "`max_concurrency` - the caveat that "
                               "belongs beside the number rather than "
                               "at a terminal."},
            "static_binary_disclaimer": {
                "description": "What LD_PRELOAD cannot see, in the "
                               "capture's own words. The census above "
                               "bounds it; this says what is being "
                               "bounded."},
            # UX-297: which shape of Plane 2 report served these
            # numbers. Not a qualifier on them - both shapes publish
            # the same aggregates - but the answer to "why is this
            # capture's report a gigabyte".
            "source": {
                "description": "Which Plane 2 report shape this run's "
                               "numbers came from. `plane2/v3` is a "
                               "report about one build - run-level "
                               "measurements, with the per-element "
                               "reductions among them (`UX-386`); the "
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
                                       "`plane2/v2` and `plane2/v3`."},
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
            # `element_join[].peak_rss_bytes` is the published
            # peak-memory field (`UX-341` retired `megabytes` and
            # `kilobytes`; the payload is in bytes).
            "cpu_accounting_available": {
                INLINE: "caveat",
                "description": "Whether the run recorded enough to account "
                               "for its slot-time at all. When false every "
                               "figure below is absent, not zero."},
            "effective_cpus": {
                INLINE: "name",
                QUANTITY: "count",
                "description": "The capacity this accounting divides by. "
                               "Builder slots as recorded, not host cores."},
            "effective_cpus_source": {
                INLINE: "caveat",
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
                INLINE: "caveat",
                QUANTITY: "duration_us",
                "description": "Slot-time no bucket claimed. Non-zero here "
                               "is a gap in the record, and it weakens "
                               "every share this object publishes."},
            "reconciliation_error_share": {
                QUANTITY: "share",
                "description": "That gap as a share of capacity. The honesty "
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
            "useful_share": {
                INLINE: "name",
                QUANTITY: "share",
                "description": "Slot-time that did work kept, as a share "
                               "of capacity. Not a share of wall-clock."},
            "idle_share": {
                QUANTITY: "share",
                "description": "Slot-time with nothing to run. Bounded "
                               "below by the graph's shape, so it is never "
                               "entirely recoverable."},
            "wasted_share": {
                QUANTITY: "share",
                "description": "Slot-time spent on work that was then "
                               "thrown away - retries and rebuilds. This "
                               "is the recoverable share."},
        },
    },
}

# `UX-344`: where each lifted table went, and the question it answers
# now that it has a heading of its own.
#
# A table that was a row of `signals` inherited its namespace's rail and
# question; standing on its own it needs both. The rail is the one its
# namespace carried unless the table is plainly somewhere else - the
# ready queue is about the machine, not about which element to fix - and
# `UX-286`'s chapters place a section by its rail when the chapter table
# does not name it, so this is also what decides where each one lands.
_LIFTED_HINTS = {
    # From `structural`. The graph's shape, whatever the run did with it.
    "graph_metrics": ('investigate', 'What shape is this dependency graph?'),
    "graph_summary": ('investigate', 'What shape is this graph, in one line?'),
    "bottleneck": ('investigate', 'What does everything wait on?'),
    "parallelism": ('investigate', 'How wide can this graph run?'),
    "sensitivity": ('investigate', 'How much faster could this graph go?'),
    "deferrability": ('investigate', 'What could be built later, or not at all?'),
    "batch_opportunities": ('investigate', 'What could be built together?'),
    "consolidation_candidates": ('investigate', 'What could be merged?'),
    "serialization_point_risks": ('investigate', 'What forces this run to serialize?'),
    # From `signals`. What this run's own durations say about the graph.
    "critical_path_detail": ('act', 'Which elements are on the chain that binds?'),
    "optimization_horizon": ('act', 'What is fixing each element in turn worth?'),
    "latent_heavies": ('act', 'What is big and off the chain?'),
    "joint_saving": ('act', 'What is fixing these together worth?'),
    "cache": ('act', 'How much of this run came from the cache?'),
    "fetch_build_overlap": ('act', 'Did fetching wait for building?'),
    "wall_clock_share_us": ('prove', 'How much of the run did each task hold?'),
    "ready_queue": ('prove', 'How much work was waiting to start?'),
    "leaf_analysis": ('investigate', 'Which elements does nothing wait on?'),
    "element_duration_distribution":
        ('investigate', "How are this run's element durations spread?"),
    "blast_radius_distribution":
        ('investigate', 'How are blast radii spread across this graph?'),
}

# The element population, as one key rather than six.
#
# `UX-268` joined the six element-keyed maps into one row per element
# for the reader and `UX-289` gave that table its views - and to do it
# the page kept **its own list** of which signals were element-keyed,
# because the document did not say. Lifting the six to the top level
# would have published one population as six sections, which is the
# defect `UX-338` was filed against. So the grouping is published: these
# are one table, and the page reads which columns it has rather than
# remembering them.
#
# `zero_slack_share`, `top_blast_radius` and `blast_radius_ranked_by`
# are here for the same reason - each describes the population rather
# than any one element, and a scalar at the top level would be drawn
# into the run-identity summary beside the run id.
ELEMENT_KEYED = ("element_durations", "slack", "downstream_count",
                 "unweighted_depth", "blast_radius",
                 "criticality_probability")

# `UX-382`: the element entity has two shapes, and this is the key that
# joins them. The maps above are keyed by it and `element_join`'s rows
# name it in a field - conventionally the same identifier until this
# said so. `UX-216` made every element one object for the reader; this
# makes it one object for the schema, which is what lets a guard hold
# the two populations against each other.
ELEMENT_KEY = "element"

# And the rule for which shape a new attribute goes in, written beside
# the two declarations it governs rather than in a task file nobody
# reads. It is not scalar-versus-structured - ten of the join's
# eighteen fields are scalars - it is what the attribute needs to
# exist.
ELEMENT_PLACEMENT_RULE = (
    "An attribute the analysis knows from the graph and Plane 1 alone "
    "is a map under `elements`, keyed by the element uid: it is on "
    "every capture, and `additionalProperties` declares its value type "
    "once for a population of any size (`UX-343`). An attribute that "
    "needs Plane 2 to exist is a field on an `element_join` row, which "
    "is present only where a capture supplied a Plane 2 report - there "
    "is no join with one plane. A Plane 1 value repeated on a join row "
    "is a denormalisation the join table needs to sort on; it is "
    "declared as one, held equal to the map it came from, and the "
    "resolved element record takes the map's. There are two: "
    "`blast_radius`, which is `elements.blast_radius[<uid>]"
    ".downstream_count`, and `on_critical_path`, which is "
    "`elements.criticality_probability[<uid>].observed_critical`.")
ELEMENT_POPULATION = ELEMENT_KEYED + ("zero_slack_share", "top_blast_radius",
                                      "blast_radius_ranked_by")

_ELEMENTS = {
    QUESTION: 'Which element should I look at?',
    RAIL: 'act',
    PRESETS: _ELEMENT_PRESETS,
    "description": "Every element this run built or restored, with what "
                   "the graph and the schedule each say about it. One "
                   "row per element; the views below name the columns "
                   "that answer one question.",
    "properties": {
        **{name: _SIGNALS_TABLES[name] for name in ELEMENT_KEYED
           if name in _SIGNALS_TABLES},
        "zero_slack_share": _SIGNALS_TABLES["zero_slack_share"],
        # `UX-344`: the two the namespace never declared. A member with
        # no node renders from `guessQuantity`'s name-sniff, which is
        # the gap `UX-343` closed everywhere else - and the census
        # caught both the moment they moved.
        "top_blast_radius": {
            "description": "The elements whose change rebuilds the most, "
                           "in that order. A ranking over the population "
                           "below, so the order is the information - the "
                           "records themselves are in `blast_radius`."},
        "blast_radius_ranked_by": {
            "description": "What the ranking above was computed from: "
                           "`measured-rebuild-time` weights each "
                           "dependent by how long it took in this run, "
                           "`downstream-count` counts them."},
    },
}

_RENAMED = {"metrics": "graph_metrics", "summary": "graph_summary"}

_ANALYZE_HINTS["elements"] = _ELEMENTS
for _table, _node in list(_STRUCTURAL_TABLES.items()) + list(_SIGNALS_TABLES.items()):
    _key = _RENAMED.get(_table, _table)
    if _key in ELEMENT_POPULATION:
        continue
    # `KeyError` rather than a default: a table added to either block
    # with no question and no rail would land in `UX-286`'s "Everything
    # else", and the guard that asserts that chapter is empty would name
    # the page rather than the contract.
    _rail, _question = _LIFTED_HINTS[_key]
    _ANALYZE_HINTS[_key] = {QUESTION: _question, RAIL: _rail, **_node}

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
            "efficiency_share": {
                QUANTITY: "share",
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
    "attribution_deltas": {
        DIRECTION: "lower_is_better",
        # UX-341: declared, and in one unit per dimension. These six
        # were the last numbers in this document with no declaration at
        # all, and three of them were 0..100 while every other bounded
        # fraction the tool publishes is 0..1.
        "additionalProperties": {"properties": {
            "baseline_us": {
                QUANTITY: "duration_us",
                "description": "What this category cost in the baseline "
                               "run."},
            "candidate_us": {
                QUANTITY: "duration_us",
                "description": "What it cost in the candidate run."},
            "delta_us": {
                QUANTITY: "duration_us", DIRECTION: "lower_is_better",
                "description": "Candidate minus baseline, in absolute "
                               "time - negative is faster."},
            "baseline_share": {
                QUANTITY: "share",
                "description": "That baseline cost as a share of the "
                               "baseline run's own total."},
            "candidate_share": {
                QUANTITY: "share",
                "description": "And as a share of the candidate run's "
                               "own total, which is a different total."},
            "delta_share": {
                QUANTITY: "share", DIRECTION: "lower_is_better",
                "description": "The change in that share. A category can "
                               "grow in absolute time and shrink here, "
                               "which is why both are published."},
        }},
    },
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
    "measured_us": {
        QUANTITY: "duration_us",
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
            {"key": "measured_us", "title": "Measured",
             "quantity": "duration_us", "sortable": True},
        ],
        "items": {
            "properties": {
                "depth": {
                    QUANTITY: "count",
                    "description": "Hops from the direct consumers, "
                                   "breadth-first."},
                "measured_us": {
                    QUANTITY: "duration_us",
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
                "peak_rss_bytes": _DISTRIBUTION,
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
                                   "`peak_rss_bytes` when no run in this "
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
            "peak_rss_bytes": _DISTRIBUTION,
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
                                          INLINE: "name",
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
    "restructuring": _RESTRUCTURING_HINT,
    "granularity": {
        QUESTION: 'Which elements pay more sandbox tax than they build?',
        RAIL: "act",
    },
    "memory_envelope": {
        QUESTION: 'How much memory would more builders need?',
        RAIL: "prove",
        "properties": {
            "host_memory_bytes": {
                QUANTITY: "bytes",
                "description": "Memory the host reported. The ceiling the "
                               "envelope below is judged against."},
            "builders": {
                INLINE: "name",
                QUANTITY: "count",
                "description": "The builder count this envelope is "
                               "computed for."},
            "elements_measured": {
                QUANTITY: "count",
                "description": "Elements whose peak memory was actually "
                               "measured. The envelope is a bound over "
                               "these, and says nothing about the rest."},
            "largest_element_peak_bytes": {
                QUANTITY: "bytes",
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


def quantity_for_path(path, document=None):
    """The declared unit of the value a provenance path names, or None.

    `UX-343`: `provenance.evidence[].value` is whatever field the rule
    read, so no single declaration on that key can be right - it was the
    one shape in the report that genuinely could not carry a unit, and
    forty-two of its leaves reached the reader as bare numbers. The
    unit *is* knowable: `path` names the field, and the field is
    declared. So the row carries the answer rather than the key
    pretending to.

    The walk resolves the way the page does - `properties`, then a
    `bga:columns` entry, then `additionalProperties` - because a second
    resolution order would disagree with the renderer about exactly the
    fields that are hardest to check by eye.
    """
    node = schema(document or ANALYZE)
    for segment in _path_segments(path):
        if node is None:
            return None
        node = _descend(node, segment)
    return (node or {}).get(QUANTITY) if isinstance(node, dict) else None


def _path_segments(path: str):
    """`a.b[2].c[id=x].d` -> the names, with subscripts as `None`.

    Scanned rather than split on `.`, because a subscript's contents can
    contain one: `signals.element_durations[app.bst]` is a map keyed by
    an element uid, and splitting first turns that into two nonsense
    segments that resolve to nothing.

    A subscript selects *within* a collection, so it descends through
    whatever the collection says it holds rather than naming a key.
    """
    name, depth = "", 0
    for char in path:
        if char == "[":
            if depth == 0:
                if name:
                    yield name
                name = ""
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                yield None
        elif char == "." and depth == 0:
            if name:
                yield name
            name = ""
        elif depth == 0:
            name += char
    if name:
        yield name


def _descend(node: dict, segment):
    if not isinstance(node, dict):
        return None
    if segment is None:
        # A subscript selects *within* a collection. Three ways a
        # collection says what it holds: `items` for a list of records,
        # `additionalProperties` for a map keyed by data, and - for a
        # table that declares its columns instead - nothing at all, so
        # the row resolves against the same node the columns are on.
        items = node.get("items")
        if isinstance(items, dict):
            return items
        extra = node.get("additionalProperties")
        if isinstance(extra, dict):
            return extra
        return node if node.get(COLUMNS) else None
    properties = node.get("properties")
    if isinstance(properties, dict) and segment in properties:
        return properties[segment]
    for spec in node.get(COLUMNS) or ():
        if isinstance(spec, dict) and spec.get("key") == segment:
            return {QUANTITY: spec["quantity"]} if spec.get("quantity") else {}
    extra = node.get("additionalProperties")
    if isinstance(extra, dict):
        return extra
    items = node.get("items")
    if isinstance(items, dict):
        return _descend(items, segment)
    return None


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


def critical_path_uids(document: dict) -> list:
    """The run's critical path, in order, from the one place it lives.

    `UX-288`: `signals.critical_path` used to publish exactly this and
    `signals.critical_path_detail` published it again with columns -
    measured identical, order included, on the 1,202-element run. The
    bare list is gone and this is the projection every reader that
    wanted it now shares, so "the path" has one definition rather than
    two that could drift.

    `UX-344`: takes the document, which is where `critical_path_detail`
    lives now. A `signals` block from an `analyze/v3` payload still
    resolves, because the lookup is by key and that block had the same
    one.
    """
    signals = document or {}
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
