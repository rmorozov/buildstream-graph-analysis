"""UX-727: one recognizer for a report under `docs/audits/`, not two.

`UX-685` gave the `walk` skill a fixed head so a guard could tell a
scripted report from a round document; `UX-686`'s release guard needed
the same for a filed finding and reimplemented the parse in a test
file instead of importing one. This module holds the kind->head-labels
table, the kind recogniser, and the `-> UX-NNN` filings a report names
as its own, for both `walk` and `design-review`. Every label regex
uses `\\s+` rather than a literal space: the walk reports' own head
wraps a line across a markdown break (`UX-686`), and a shape regex
that only reads a single space would pass that on a rewrap.
`tools/dev_scenario.py` delegates its `is_walk_report`/
`report_problems` here and keeps their names; `audits_documents` stays
there, being about what the repository tracks, not what a document is.
"""
import re

#: kind -> the head labels that identify a report of that kind, text
#: only. Two-word compounds are what a round document's prose does not
#: say by coincidence at a line's start (`UX-685`).
_HEAD_LABELS = {
    "walk": ("answer key", "per plane", "findings", "friction"),
    "design-review": ("design review", "controls"),
}

#: kind -> (field regex, problem message) required once a report is
#: already recognised as that kind - present in the shape, but not
#: itself part of what names the shape.
_REQUIRED_FIELDS = {
    "walk": ((re.compile(r"(?m)^seed\s"), "no seed line"),
             (re.compile(r"(?m)^rows added\s"), "no answer-key rows added line")),
    "design-review": ((re.compile(r"(?m)^filed\s"), "no filed findings line"),),
}

#: kind -> where its filed findings sit: walk's are a numbered list
#: bounded by the next fixed label; design-review's are the one line
#: named for them.
_FILINGS_FIELD = {
    "walk": re.compile(r"(?ms)^findings\s+(.*?)^rows added\s"),
    "design-review": re.compile(r"(?m)^filed\s+(.*)$"),
}

#: kind -> how a filed id is told from one merely discussed, inside its
#: filings field: walk's list also carries findings judged not
#: actionable, so only an `→`-marked one counts; design-review's field
#: is already the curated set, so every id on it counts.
_EXTRACT = {
    "walk": re.compile(r"→\s*(UX-\d+)"),
    "design-review": re.compile(r"(UX-\d+)"),
}

#: A report's own `Base \`<sha>\`, <date>` sentence - not kind-specific,
#: so it lives beside the recogniser rather than under either kind.
REPORT_DATE = re.compile(r"Base\s+`[0-9a-f]{7,40}`,\s*(\d{4}-\d{2}-\d{2})")

_SHAPES = {kind: tuple(re.compile(rf"(?m)^{re.escape(label)}\s+\S")
                      for label in labels)
          for kind, labels in _HEAD_LABELS.items()}


def report_kind(text):
    """`"walk"`, `"design-review"`, or `None` - the fixed head `text`
    carries."""
    for kind, patterns in _SHAPES.items():
        if all(pattern.search(text) for pattern in patterns):
            return kind
    return None


def is_walk_report(text):
    """Whether `text` follows the `walk` skill's own report shape."""
    return report_kind(text) == "walk"


def filed_findings(text):
    """`{UX-NNN, ...}` a recognised report names as its own - `set()`
    if the kind is unrecognised or its filings field is missing."""
    kind = report_kind(text)
    field = _FILINGS_FIELD.get(kind)
    match = field.search(text) if field else None
    return set(_EXTRACT[kind].findall(match.group(1))) if match else set()


def report_problems(documents):
    """`path: what is missing`, for every recognised `(path, text)`
    lacking a field its kind requires beyond the head that named it."""
    problems = []
    for path, text in documents:
        kind = report_kind(text)
        for pattern, message in _REQUIRED_FIELDS.get(kind, ()):
            if not pattern.search(text):
                problems.append(f"{path}: {message}")
    return problems
