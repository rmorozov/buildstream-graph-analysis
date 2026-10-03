"""UX-1311: a `public: bga: jobserver-auth:` annotation on a junctioned
element reaches the shim, which names the element without its junction."""

import json

import pytest

from tools.bst_native_build_tracer import FIELD_SEP, RECORD_SEP, _claim_short_names, _parse_jobserver_show_records
from tools.native_trace.bwrap_shim import _annotation_style, element_from_build_root


def _record(name, style=None):
    public = f"bga:\n  jobserver-auth: {style}\n" if style else "{}"
    return FIELD_SEP.join([name, "make", "{}", public, "[]", "[]"]) + RECORD_SEP


def _resolve(tmp_path, monkeypatch, records, short):
    auth_map = _parse_jobserver_show_records("".join(records))[2]
    path = tmp_path / "auth.json"
    path.write_text(json.dumps(auth_map))
    monkeypatch.setenv("BST_TRACE_ELEMENT_AUTH_MAP", str(path))
    return _annotation_style(element_from_build_root(f"buildstream/proj/{short}"))


def test_a_junctioned_annotation_resolves_by_its_short_name(tmp_path, monkeypatch):
    got = _resolve(tmp_path, monkeypatch, [_record("toolchain.bst:my_recipe.bst", "off")], "my_recipe.bst")
    assert got == "off"


def test_the_first_junction_owns_a_short_name_and_a_later_one_is_a_collision(tmp_path, monkeypatch):
    records = [_record("a.bst:x.bst", "fd"), _record("b.bst:x.bst", "off")]
    assert _resolve(tmp_path, monkeypatch, records, "x.bst") == "fd"


def test_an_unannotated_first_junction_keeps_a_later_ones_annotation_off_the_short_name(tmp_path, monkeypatch):
    records = [_record("a.bst:x.bst"), _record("b.bst:x.bst", "off")]
    assert _resolve(tmp_path, monkeypatch, records, "x.bst") is None


@pytest.mark.parametrize("top_first", [True, False])
def test_a_top_level_element_owns_its_name_annotated_or_not(tmp_path, monkeypatch, top_first):
    pair = [_record("x.bst"), _record("a.bst:x.bst", "off")]
    assert _resolve(tmp_path, monkeypatch, pair if top_first else pair[::-1], "x.bst") is None


def test_a_top_level_annotation_beats_a_junctions(tmp_path, monkeypatch):
    records = [_record("a.bst:x.bst", "off"), _record("x.bst", "fd")]
    assert _resolve(tmp_path, monkeypatch, records, "x.bst") == "fd"


@pytest.mark.parametrize(
    ("names", "collisions"),
    [(["x.bst", "a.bst:x.bst"], 0), (["a.bst:x.bst", "x.bst"], 0), (["a.bst:x.bst", "b.bst:x.bst"], 1)],
)
def test_only_two_junctions_sharing_a_short_name_count_as_a_collision(names, collisions):
    assert _claim_short_names(names)[2] == collisions
