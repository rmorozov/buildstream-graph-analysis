"""UX-241: the trigger for a review is measured, not remembered.

`UX-233` fixed the architecture document once and guarded the
mechanical half — every published schema id must appear in the spec and
the architecture inventory. What no guard can catch is a *chapter* that
describes a mechanism the code no longer has, and that is the half that
went a whole axis out of date: the viewer ran from `UX-193` to
`UX-226`, 34 closed rows, with nothing in the process to notice.

Feature audits happen on a cadence here. Documentation review did not,
and the asymmetry is the finding. So the cadence is a number in the
tree: this guard reddens when more than `MAX_ROWS_BETWEEN_REVIEWS`
scenarios have closed since the last row of the review log.

It measures *distance since*, never whether a chapter is true. That
part is judgment and stays judgment.
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
REVIEW_LOG = REPO / "docs/audits/architecture-review.md"
CLOSED = REPO / "docs/backlog/scenarios/closed.md"

# The bound, argued in the review document rather than guessed: below
# the 34-row drift that was actually missed, and far enough above one
# round that an ordinary range does not trip it.
MAX_ROWS_BETWEEN_REVIEWS = 25

_LOG_ROW = re.compile(
    r"^\|\s*(\d+)\s*\|\s*([\d-]+)\s*\|\s*(\d+)\s*\|\s*`([0-9a-f]+)`\s*\|")


def _log_rows():
    rows = []
    for line in REVIEW_LOG.read_text(encoding="utf-8").splitlines():
        match = _LOG_ROW.match(line)
        if match:
            rows.append({"n": int(match.group(1)), "date": match.group(2),
                         "rows_at_review": int(match.group(3)),
                         "commit": match.group(4)})
    return rows


def _closed_now():
    """Rows in `closed.md`, which is the ledger `UX-232` made it.

    Closed rows rather than commits: one round is anywhere from one to
    nine commits, the count is in the tree so the guard needs no git,
    and it gives the same answer on every machine.
    """
    return sum(1 for line in CLOSED.read_text(encoding="utf-8").splitlines()
               if line.startswith("| UX-"))


class TestTheReviewIsARoundType:
    def test_the_review_document_exists_and_says_what_a_review_is(self):
        text = REVIEW_LOG.read_text(encoding="utf-8")
        for part in ("**input**", "**output**", "**done when**"):
            assert part in text, f"the review document does not say {part}"
        assert "## The checklist" in text

    def test_the_stream_table_carries_it(self):
        """A round type nobody is told about is not a round type."""
        guide = (REPO / "docs/contributing/fixing-guide.md").read_text(
            encoding="utf-8")
        body = guide.split("## 6a. Which kind of session is this?", 1)[1]
        body = body.split("\n## ", 1)[0]
        assert "**review**" in body, (
            "section 6a does not list review beside the other streams")

    def test_a_review_produces_no_code(self):
        """The rule that keeps a review a review. A session that fixes
        what it finds stops being able to see the next thing."""
        text = REVIEW_LOG.read_text(encoding="utf-8")
        assert "produces no code" in text


class TestTheDistanceIsMeasured:
    def test_the_log_has_at_least_one_parseable_row(self):
        rows = _log_rows()
        assert rows, (
            "the review log has no row this guard can read; the table is "
            "`| n | date | closed rows at review | `commit` | findings |`")
        assert [r["n"] for r in rows] == list(range(1, len(rows) + 1))

    def test_the_last_review_is_not_too_far_back(self):
        rows = _log_rows()
        last = rows[-1]
        distance = _closed_now() - last["rows_at_review"]
        assert distance >= 0, (
            f"review {last['n']} records {last['rows_at_review']} closed rows "
            f"and closed.md has {_closed_now()} — the log is ahead of the "
            f"tree, which means a row was recorded before it closed")
        assert distance <= MAX_ROWS_BETWEEN_REVIEWS, (
            f"{distance} scenarios have closed since review {last['n']} "
            f"({last['date']}), against a bound of "
            f"{MAX_ROWS_BETWEEN_REVIEWS}. Run a review: the checklist is in "
            f"docs/audits/architecture-review.md.")

    def test_the_bound_is_argued_where_a_reader_will_look(self):
        """Two copies of one number is the drift this repository fixes
        more often than anything else, so the document has to state the
        same bound this module enforces."""
        text = REVIEW_LOG.read_text(encoding="utf-8")
        assert f"**{MAX_ROWS_BETWEEN_REVIEWS} scenarios**" in text, (
            f"the review document does not state the bound of "
            f"{MAX_ROWS_BETWEEN_REVIEWS} this guard enforces")

    def test_the_first_review_named_what_it_found(self):
        """A review that files nothing and says nothing is a review
        that did not happen. Its findings column is not allowed to be
        empty."""
        text = REVIEW_LOG.read_text(encoding="utf-8")
        for row in _log_rows():
            line = next(l for l in text.splitlines()
                        if _LOG_ROW.match(l)
                        and int(_LOG_ROW.match(l).group(1)) == row["n"])
            findings = line.strip().strip("|").split("|")[4].strip()
            assert findings and findings != "—", (
                f"review {row['n']} names no findings and no explicit none")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
