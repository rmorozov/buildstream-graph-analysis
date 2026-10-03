"""`UX-1181`: one instrument reads the page half, in bytes - `view.page_half`.

`export()` reports it, every size guard reads it, and the two tests that
once counted characters count bytes (a raw non-ASCII character moves each
by its UTF-8 width).

Styleguide §3g.
"""

import importlib.util
import pathlib
import re
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from pages import FIXTURES, snapshot_copy

from tools import bga_view as view

HERE = pathlib.Path(__file__).parent
ATTACH = HERE / "test_the_report_you_can_attach.py"
DASH = "—"  # 3 bytes in UTF-8, 1 character


@pytest.fixture(scope="module")
def golden(tmp_path_factory):
    into = tmp_path_factory.mktemp("once")
    path = into / "report.html"
    written = view.export(str(snapshot_copy(FIXTURES["golden"], into)), str(path))
    return path, written, path.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def discipline():
    spec = importlib.util.spec_from_file_location("attach_under_test", ATTACH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.TestTheSizeDiscipline()


def test_export_and_the_instrument_agree_to_the_byte(golden):
    _path, written, html = golden
    assert view.page_half(html) == written["page_bytes"]
    assert written["page_bytes"] + written["data_bytes"] == written["bytes"]


def test_a_non_ascii_character_in_the_page_moves_it_by_its_byte_width(golden):
    _path, written, html = golden
    assert html.count("<body>") == 1
    moved = view.page_half(html.replace("<body>", "<body><!--" + DASH * 10 + "-->"))
    assert moved - written["page_bytes"] == 7 + 10 * 3


def test_the_modules_test_counts_bytes(golden, discipline, tmp_path):
    """2,000 raw dashes in the page half: 2,000 characters, 6,000 bytes against a 4,000 B slack."""
    path, written, html = golden
    discipline.test_the_page_is_the_modules_and_nothing_else((path, written))
    fat = tmp_path / "fat.html"
    fat.write_text(html.replace("<body>", "<body><!--" + DASH * 2000 + "-->"), encoding="utf-8")
    with pytest.raises(AssertionError):
        discipline.test_the_page_is_the_modules_and_nothing_else((fat, written))


def test_the_data_test_counts_bytes(golden, discipline, tmp_path):
    """2,000 raw dashes inside a data block move no reading: every unit in the sum is bytes."""
    path, written, html = golden
    block = '<script type="application/json" id="bga-run">{'
    assert html.count(block) == 1
    raw = tmp_path / "raw.html"
    raw.write_text(html.replace(block, block + '"datum": "' + DASH * 2000 + '", '), encoding="utf-8")
    discipline.test_the_data_is_the_documents_and_the_schemas((raw, written))


def test_no_other_file_splits_the_page_by_its_own_pattern():
    """The data-block pattern is `view._DATA_BLOCK`'s alone: nobody `re.sub`s it out of a page again."""
    own = {ATTACH.parent / "test_a_page_half_is_read_once.py"}
    offenders = []
    for path in [*HERE.glob("*.py"), *(REPO / "tools").glob("*.py")]:
        if path in own or path.name == "bga_view.py":
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"re\.sub\(.{0,160}octet-stream", text, re.S):
            offenders.append(path.name)
    assert not offenders, offenders
    assert not re.search(r"def (_embedded|_page_half)\b|^_DATA\s*=", ATTACH.read_text(encoding="utf-8"), re.M)
