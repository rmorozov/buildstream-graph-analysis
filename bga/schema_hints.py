"""View hints: the `bga:*` vocabulary a schema node carries, and its checker.

Split out of `bga/schemas.py` (`UX-1031`) to hold that file's size cell;
`bga.schemas` re-exports every name here.
"""
from .findings import READERS

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
# UX-643: which of `findings.READERS` a section serves, by their `R1`-`R5`
# ids, so a reader who says who they are gets that section promoted and
# expanded rather than the other four's page. Silent -> no role, and the
# section stays folded under every one of them.
READERS_SERVED = "bga:readers"
# Read off the roster rather than restated: a second list of role ids is
# the vocabulary `UX-214` watched diverge.
READER_ROLES = tuple(_role for _uid, _role, _label, _question in READERS)
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

# `UX-669` (styleguide §1e): an ordered list of *reason, command,
# citation* is a runbook, not a table. §1 sends "array of objects" to a
# table and that is right for a population; this array is three steps a
# reader runs in order, and a table renders the command wrapped over
# three lines in a 310 px cell with its citation beside it as a raw
# key. Declared rather than sniffed, for the reason every other hint
# here is: the page chooses nothing.
RUNBOOK = "bga:runbook"

# `UX-361` (styleguide §2d): the two shapes the vocabulary did not have.
#
# A strip shows a distribution and a sparkline shows an ordered series.
# `UX-361` counted what that leaves undrawn: 19 of `golden`'s 43
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

#: `UX-1031`: every list and data-keyed map says whether it grows with
#: the run. A string names what it grows with (`"elements"`,
#: `"findings"`, a subset's own population...); `False` says it does
#: not, and the node must then carry `maxItems` - a container found
#: undeclared, or growing with no bound, is exactly the defect the
#: styleguide audit measured (91 containers walked, 41 undeclared, 19
#: growing with the run of which 4 undeclared).
GROWS = "bga:grows"

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
COMMAND = "bga:command"            # a scalar array that is one command line
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
    # `UX-613`: events per unit time, and the *only* addition since
    # `UX-341` closed the set. Argued against the rule rather than
    # added beside it: a rate has dimension T-1, which none of the five
    # above measures. `duration_us` is a length of time (400 builds/day
    # would render as "400 microseconds"); `count` is a cardinality
    # with no denominator, and the denominator is what the queueing
    # model turns on; `ratio` is dimensionless, and declaring a
    # dimensioned value dimensionless is the exact defect `UX-341`
    # removed when it retired `seconds`. The member names its time base
    # because `UX-341`'s other half is that one dimension has one unit:
    # a bare `rate` would let builds/day and builds/hour both be
    # `rate`, and a later `rate_per_hour` reddens the dimension guard.
    "rate_per_day",
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
    "rate_per_day": "events per unit time",
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


def _check_grows(document: str, key: str, hint: dict) -> None:
    """`UX-1031`: a container's own growth claim. A string says what it
    grows with; `False` says it does not, and then only `maxItems`
    makes that a claim rather than an omission."""
    grows = hint.get(GROWS)
    if grows is None:
        return
    if grows is not False and not (isinstance(grows, str) and grows.strip()):
        raise ValueError(
            f"{document}.{key}: {GROWS}={grows!r} must be a non-empty "
            f"string naming what it grows with, or False")
    if grows is False and not isinstance(hint.get("maxItems"), int):
        raise ValueError(
            f"{document}.{key}: {GROWS} is False with no maxItems - a "
            f"fixed container states its bound")


def _check_hint(document: str, key: str, hint: dict) -> None:
    """Reject a hint a renderer could not act on.

    Caught here rather than in the viewer because a mistyped quantity is
    invisible at the point of use: the renderer falls through to its
    default and prints a raw number that looks plausible.
    """
    # UX-209: the rail a section belongs to, closed so the TOC can be
    # complete against it - an unknown rail would silently drop a
    # section out of every group.
    if (rail := hint.get(RAIL)) is not None and rail not in RAILS:
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
    _check_grows(document, key, hint)
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

    `{n, min, max, deciles{p10..p90}, p95, p99, mean, is_flat}` is one shape
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
            "mean": {QUANTITY: quantity,
                     "description": f"The mean {noun}; on a heavy tail the "
                                    "mark that most needs the median beside "
                                    "it, which is why the sentence stays on "
                                    "the median."},
            "deciles": {
                "description": "The nine deciles, nearest-rank.",
                "properties": {f"p{step}": rank(step)
                               for step in range(10, 100, 10)}},
        },
    }
