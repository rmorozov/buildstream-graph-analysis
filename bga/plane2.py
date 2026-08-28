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
and stamps itself `plane2/v2`. The records live where they were always
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

SCHEMA = "plane2/v2"

# The unstamped shape every capture wrote before `UX-297`: the same
# aggregates, plus the record list. Named rather than left as "the old
# one" because a reader meeting either has to be able to say which, and
# an id is the only thing a machine can compare.
LEGACY_SCHEMA = "plane2/v1"

# Read, never written. `bga.contracts` inventories it as superseded, so
# a release can say which shapes it still opens as well as which it
# emits - an old store is full of the first kind.
SUPERSEDED = (LEGACY_SCHEMA,)

RECORDS_KEY = "processes"


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
