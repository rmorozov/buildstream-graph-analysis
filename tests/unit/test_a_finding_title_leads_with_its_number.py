"""UX-1248: a finding title is at most 100 characters and opens with its number (styleguide §4g).

holds: rules.md#a-finding-title-opens-with-its-number-in-100-characters-styleguide-4g-item-9
"""

import contextlib
import io
import json
import re

import pytest

from bga import schemas
from bga.cli import main
from tests import pages

TITLE_MAX = 100
#: Its wording is UX-1246's; this rule reaches it when that lands.
NOT_YET = {"capacity-recommendation"}
_CAPITALISED_SPAN = re.compile(r"(?<!^)(?<![.:!?] )\b(?:[A-Z][\w-]*\s+){1,}[A-Z][\w-]*")


def _runs(into):
    return {
        "golden": pages.FIXTURES["golden"],
        "macro_micro": pages.snapshot_copy(pages.FIXTURES["macro_micro"], into / "mm"),
        "seed 1": pages.scale_run(into),
        "shared source": pages.shared_resource_run(into / "ss", resources=3),
    }


@pytest.fixture(scope="module")
def titles(tmp_path_factory):
    out = {}
    for name, run in _runs(tmp_path_factory.mktemp("titles")).items():
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(io.StringIO()):
            main(["analyze", str(run), "--format", "json"])
        out[name] = [(f["id"], f["title"]) for f in json.loads(buffer.getvalue())["findings"] if f["id"] not in NOT_YET]
    return out


def _headings():
    return [
        node.get(schemas.QUESTION, "")
        for node in schemas.schema(schemas.ANALYZE)["properties"].values()
        if isinstance(node, dict)
    ]


def test_the_source_blast_finding_is_on_a_page(titles):
    assert "shared-source-blast" in {fid for fid, _t in titles["shared source"]}


def test_a_title_is_short_and_carries_no_url(titles):
    for name, rows in titles.items():
        for fid, title in rows:
            assert len(title) <= TITLE_MAX, f"{name} {fid}: {len(title)} chars: {title}"
            assert "://" not in title, f"{name} {fid}: {title}"


def test_a_title_with_a_number_opens_with_it(titles):
    for name, rows in titles.items():
        for fid, title in rows:
            if re.search(r"\d", title):
                assert re.match(r"[~+-]?\d", title), f"{name} {fid}: {title}"


def test_a_capitalised_name_is_a_heading_the_page_carries(titles):
    headings = " ".join(_headings())
    for name, rows in titles.items():
        for fid, title in rows:
            for span in _CAPITALISED_SPAN.findall(title):
                assert span.strip() in headings, f"{name} {fid}: {span.strip()!r} names no heading: {title}"
