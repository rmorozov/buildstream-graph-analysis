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
