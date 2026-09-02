"""UX-297: what a Plane 2 report is, and which shape the one in hand is.

Direction 15's rules 2 and 5 - *events are a stream* and *analysis
reads aggregates* - meet the disk here. Until this item the report was
the aggregates **and** the whole per-process record list under
`"processes"`; measured on a 200,000-process capture, that list was
53.2 MB of a 53.2 MB document (99.9%), and no production reader read
it: `correlate`, `analyze` and the store aggregate all read the
per-element reductions sitting beside it. At the field's scale the same
list is ~1.5 GB, parsed at a measured 2.9x bytes-to-RAM by anything
that opened the file.

So a report written from `UX-297` onward carries the reductions alone
and stamps itself `plane2/v3`. The records live where they were always
written: the raw trace log the snapshot keeps (`plane2.log.gz`), which
is what the timeline is rendered from and what
`bst_native_build_tracer.load_records` reads when something genuinely
needs per-process rows.

**One interface for reading.** A store holds captures from before this
item, and they still analyze - the aggregates a legacy monolith carries
are the same aggregates, in the same keys. The only difference a reader
can see is `records_embedded`, which the analysis publishes so that
"this run's report is 1.5 GB" is a fact about the capture rather than a
mystery about the tool.
"""
import os
from typing import Optional

SCHEMA = "plane2/v3"

# `UX-384`: v3 removed `elements` from each `redundant_operations`
# finding. `UX-375` capped that population at 40 rows and the *names
# inside* the rows were the term left over - the one part still
# O(elements). Measured with 40 capped rows and the element count
# varied:
#
# ```text
#  elements  rows  section B  elements B   share
#        40    40     36,901      28,840   78.2%
#       400    40    296,221     288,040   97.2%
#      1200    40    880,341     872,040   99.1%
# ```
#
# `element_count` and `worst_element` were already published beside it
# and are what a consumer reads - `bga correlate`, the only consumer in
# this repository, never opened the list. Removing a published key is
# what makes this a version rather than an addition, on the precedent
# `UX-297` set when it removed the per-process record list for the same
# reason.
PREVIOUS_SCHEMA = "plane2/v2"

# The unstamped shape every capture wrote before `UX-297`: the same
# aggregates, plus the record list. Named rather than left as "the old
# one" because a reader meeting either has to be able to say which, and
# an id is the only thing a machine can compare.
LEGACY_SCHEMA = "plane2/v1"

# Read, never written. `bga.contracts` inventories them as superseded,
# so a release can say which shapes it still opens as well as which it
# emits - an old store is full of both kinds.
SUPERSEDED = (PREVIOUS_SCHEMA, LEGACY_SCHEMA)

RECORDS_KEY = "processes"

# `UX-389`: **where every block of a Plane 2 report goes.**
#
# Counted against an all-planes capture of
# `examples/06-macro-micro-optimization` when this was filed:
#
# ```text
# plane2 blocks in the capture            25
#   a key in analyze/v5                    6
#   reaching the page through the join     6
#   terminal only                         14
# ```
#
# Fourteen of them were the *did the instrument see everything*
# questions - whether the ptrace spine ran, which elements could hide a
# static binary, how long the hook was watching - and a reader in a
# browser had no way to learn that the numbers under the attribution
# table were a floor rather than a measurement. That is `UX-107`'s rule
# one level up: the page cannot say "nobody could look" while the block
# that knows is at a terminal.
#
# The gap grew every round, because nothing held the two ends together:
# `UX-370` moved three blocks, `UX-383` three more, and `UX-385` added
# a fifteenth terminal-only block in the same round it was filed.
#
# So each block declares one of three destinations, and **silence is
# not one of them** - that is what produced fourteen. A block added
# with no entry fails `test_every_plane2_block_has_a_destination.py`,
# which is the whole point of writing the inventory down rather than
# leaving it implied by what `bga/cli.py` happens to copy.
PAYLOAD = "payload"          #: a named key of `analyze/v5`
JOIN = "join"                #: a field on an `element_join` row (`UX-382`)
TERMINAL = "terminal"        #: deliberately terminal-only, with a reason

#: `{block: (destination, where, why)}` for every top-level key a
#: `plane2/v3` report carries. `where` is the payload key or the join
#: field it lands on; for a terminal-only block it is empty and `why`
#: carries the reason.
DESTINATIONS = {
    # --- the run-level measurements the page draws in their own right
    "by_binary": (PAYLOAD, "by_binary", ""),
    "binary_cost": (PAYLOAD, "binary_cost", ""),
    "configure_phase": (PAYLOAD, "configure_phase", ""),
    "cpu_time": (PAYLOAD, "cpu_time", ""),
    "peak_memory": (PAYLOAD, "peak_memory", ""),
    "resource_pressure": (PAYLOAD, "resource_pressure", ""),

    # --- the capture's own identity: what the instrument could see.
    # All six land in `plane2_coverage`, which is the block a reader
    # already opens to ask how much of the build Plane 2 saw - not six
    # new sections scattered among the findings.
    "stream_coverage": (PAYLOAD, "plane2_coverage", ""),
    "spine_policy": (PAYLOAD, "plane2_coverage.spine_policy", ""),
    "process_count": (PAYLOAD, "plane2_coverage.process_count", ""),
    "max_concurrency": (PAYLOAD, "plane2_coverage.max_concurrency", ""),
    # Renamed on the way in, and converted: the payload's one unit
    # for a duration is microseconds (`bga:quantity: duration_us`), and
    # a key that says `_s` while its neighbours say `_us` is the label
    # `UX-351` is about.
    "wall_span_s": (PAYLOAD, "plane2_coverage.wall_span_us", ""),
    "static_census": (PAYLOAD, "plane2_coverage.static_census", ""),
    # The two sentences that qualify the two blocks above them. A
    # number whose caveat stayed at the terminal is the same defect in
    # miniature, so they travel with what they qualify.
    "open_records_note": (PAYLOAD, "plane2_coverage.open_records_note", ""),
    "static_binary_disclaimer": (
        PAYLOAD, "plane2_coverage.static_binary_disclaimer", ""),

    # --- the per-element blocks, on the join row by `UX-382`'s rule
    "per_element_parallelism": (JOIN, "requested_jobs", ""),
    "redundant_operations": (JOIN, "redundancy_count", ""),
    "declared_vs_used": (JOIN, "unused_dependencies", ""),

    # --- terminal-only, on purpose, each with the reason
    "by_element": (
        TERMINAL, "",
        "Processes per element, which is the input the attribution "
        "table is built from rather than an answer of its own - and "
        "`element_join` already carries one row per element. Publishing "
        "it beside them would be `UX-288`'s duplicate population."),
    "element_attribution": (
        TERMINAL, "",
        "How the capture labelled its processes, summarised. Its "
        "`recognized_elements` is the join's own population and its "
        "share is `plane2_coverage.opens_coverage` seen from the other "
        "side; what is left is a debugging view of the labeller."),
    "invocation_correlation": (
        TERMINAL, "",
        "The pid-to-element mapping itself, resolved and ambiguous. "
        "Every join row rests on it, so it is apparatus rather than a "
        "measurement - and it names pids, which mean nothing after the "
        "build that owned them exited."),
    "opens_captured": (
        TERMINAL, "",
        "Per-element open-window bookkeeping (paths, windows, dropped). "
        "`plane2_coverage.opens_coverage` is the run-level answer a "
        "reader needs; the per-element breakdown is for diagnosing a "
        "capture, which is `bga doctor`'s job."),
    "redundant_operations_coverage": (
        TERMINAL, "",
        "What the redundancy scan excluded and why. A caveat on a "
        "population the join already caps (`UX-375`), and the cap is "
        "stated where the rows are."),
    "matched_count": (
        TERMINAL, "",
        "Records matched to an element, before the reductions. "
        "`plane2_coverage.processes` is the same census at the level a "
        "reader asks it."),
    "open_count": (
        TERMINAL, "",
        "Raw open events, which is a size of the trace log rather than "
        "a property of the build - the trace's own size is published "
        "by the capture layout."),
    "wrapped_command_exit_code": (
        TERMINAL, "",
        "Whether the wrapped `bst` command succeeded. Plane 1 publishes "
        "the run's outcome (`UX-156`), and two documents answering that "
        "differently is the disagreement this tool exists not to have."),
}

#: The blocks `coverage_additions` copies into `plane2_coverage`, in
#: the order they are read. Derived from `DESTINATIONS` so the
#: inventory above is the one place the carry is written down.
COVERAGE_ADDITIONS = tuple(
    block for block, (kind, where, _why) in DESTINATIONS.items()
    if kind == PAYLOAD and where.startswith("plane2_coverage."))


def coverage_additions(report: Optional[dict]) -> dict:
    """The capture's own identity, for `plane2_coverage` to carry.

    `UX-389`: six blocks that change how every other number is read -
    whether the spine ran, how many processes were traced, how long the
    hook was watching, which elements could be hiding a static binary -
    plus the two sentences that qualify them. A block the report does
    not carry is left out rather than published empty, which is
    `UX-388`'s distinction between absent and none.
    """
    if not isinstance(report, dict):
        return {}
    carried = {}
    for block in COVERAGE_ADDITIONS:
        value = report.get(block)
        if value is None:
            continue
        name = DESTINATIONS[block][1].split(".", 1)[1]
        if name.endswith("_us"):
            value = int(round(value * 1_000_000))
        elif name == "static_census":
            # The run-level half only. `per_element` is a map keyed by
            # element uid holding one bookkeeping record each - the
            # census's own working, 11 rows of it on this fixture and
            # one per element at any scale. `UX-288`'s rule says a
            # second copy of the element population needs a reason, and
            # "what the census counted per element" is `bga doctor`'s
            # question rather than a reader's; `elements_at_risk` is
            # the answer this block exists to give.
            value = {key: member for key, member in value.items()
                     if key != "per_element"}
        carried[name] = value
    return carried


def shape_of(report: Optional[dict]) -> Optional[str]:
    """Which contract this report is, from the report itself."""
    if not isinstance(report, dict):
        return None
    declared = report.get("schema")
    if isinstance(declared, str) and declared.startswith("plane2/"):
        return declared
    return LEGACY_SCHEMA


def provenance(report: Optional[dict]) -> Optional[dict]:
    """What served this run's Plane 2 numbers, for the payload to carry.

    The item asks that *which path served the data* be stated rather
    than inferred. Both paths publish the same numbers - that equality
    is the migration's guard - so the difference a reader needs is not
    "are these trustworthy" but "why is this file the size it is, and
    what does it still cost to open".
    """
    shape = shape_of(report)
    if shape is None:
        return None
    embedded = RECORDS_KEY in (report or {})
    return {
        "schema": shape,
        "records_embedded": embedded,
        "records": len((report or {}).get(RECORDS_KEY) or []) if embedded else 0,
        "note": (
            "This run's Plane 2 report predates `UX-297` and embeds its "
            "per-process record list, which no published number reads. "
            "The aggregates below are the same either way; the file is "
            "large for a reason that is now historical."
            if embedded else
            "This run's Plane 2 report carries per-element aggregates "
            "only. The per-process records are in the raw trace log the "
            "snapshot keeps, which is what the timeline is built from."
        ),
    }


# UX-296's bound, moved here from `tools/bga_view.py` because `UX-329`
# gave it a second caller and a policy with two copies is a policy that
# will disagree with itself.
#
# The measurement that sets it: one `json.load` of the monolith costs a
# measured **2.9x its bytes** in resident memory. 64 MB of report is
# therefore ~186 MB of transient RSS - the most an interactive command
# should take without being asked, and two orders of magnitude below the
# field capture that started this (1.5 GB of report, ~4.3 GB of RAM,
# ~30 s, twice, before the socket existed).
VIEW_MAX_BYTES = 64 * 1024 * 1024

# UX-329: the absence grammar, split. One sentence pair, three readers.
#
# Before this there was one sentence - "this run kept no raw Plane 2
# log, so there is no timeline to carry" - and it was printed for two
# different situations a reader cannot tell apart from it: a capture
# that never traced anything, and a capture that traced everything and
# dropped the raw log afterwards (`--no-keep-raw`, or a store pruned by
# hand). The first is a machine that could not capture; the second is a
# complete measurement missing only its timeline. `UX-156`'s rule -
# absence is stated, not implied - applied to the plane.
# `UX-362`: this sentence says what it owns and stops. It used to end
# "...no per-process detail **and no timeline**", and the timeline half
# was never Plane 2's to claim: `bga timeline` renders from the wrapped
# BuildStream log, and a Plane 1 capture with no Plane 2 has a timeline,
# a working Perfetto button and an inlined trace. `UX-358`'s fixture is
# exactly that run, and the page carried the button and this denial at
# the same time for two rounds. Whether there is a timeline is
# `run.has_timeline`, which the page reads and the handoff acts on.
NOT_CAPTURED = ("Plane 2 was not captured for this run, so there is no "
                "per-process detail. `bga snapshot -- bst build TARGET` "
                "captures both planes.")
CAPTURED_NO_RAW_LOG = ("Plane 2 was captured - its report is beside this run "
                       "- but the raw trace log it was built from was not "
                       "kept, so there is no timeline to render. `bga "
                       "snapshot` keeps one by default; `--no-keep-raw` and a "
                       "hand-pruned store are the two ways it goes missing.")


DECLINED = ("Plane 2 was captured and this report was asked not to read it "
            "(`--no-plane2`), so every figure below is Plane 1 alone.")


def absence(run_dir: str, declined: bool = False):
    """Which absence this run has, as a sentence, or `None` for none.

    Three states and not two, and the split is the whole item: a reader
    given "no timeline" cannot tell a machine that never captured Plane
    2 from a complete capture whose raw log was dropped, and those are a
    broken machine and a fine measurement respectively.

    It asks the filesystem itself rather than taking a caller's
    boolean - the terminal, the page and the export all call this, and a
    parameter is a way for the three to disagree again.
    """
    from . import run_store

    run_dir = os.path.abspath(run_dir)
    if run_store.sibling_plane2(run_dir) is None:
        return NOT_CAPTURED
    if declined:
        return DECLINED
    if run_store.sibling_raw_log(run_dir) is None:
        return CAPTURED_NO_RAW_LOG
    return None


def attachable(run_dir: str):
    """`(path, refusal)` for the Plane 2 report beside a run directory.

    `UX-329`: one discovery function, three callers. `bga correlate` and
    `bga view` both found the sibling and attached it; `bga analyze`
    required `--plane2` and hinted at nothing - so on a snapshot holding
    a Plane 2 report, `bga analyze @last` published
    `plane2_coverage: null` while `bga view @last` on the same alias
    published it in full, against `bga view --help`'s own promise that
    "the viewer and the terminal can never disagree about what a run
    says".

    `path` is the report to attach, or `None`. `refusal` is the sentence
    to print when there **is** a report and it is not being attached -
    which is the size bound, and is a thing to say rather than a thing
    to do quietly (`UX-194`'s rule for an absent precondition).
    """
    from . import run_store

    path = run_store.sibling_plane2(os.path.abspath(run_dir))
    if path is None:
        return None, None
    try:
        size = os.path.getsize(path)
    except OSError:
        return None, None
    if size <= VIEW_MAX_BYTES:
        return path, None
    return None, (
        f"Plane 2 is {run_store.human_bytes(size)} and this run published no "
        f"analysis, so the report is rendered from Plane 1 alone - parsing it "
        f"here costs about {run_store.human_bytes(int(size * 2.9))} of memory "
        f"(UX-296). `bga snapshot -- bst build TARGET` publishes an analysis "
        f"that carries both planes.")
