"""UX-916: a capture's report names the sandbox `make` each element was
probed on, so the two branches of `style_for_make_version` are told
apart in the report rather than in the workflow that produced it.

The probe cache is written by the shim and dies with the FIFO, so the
enrichment happens where the decisions file is copied out. These drive
that function directly against a cache written the way a real sandbox
writes one.
"""
import json
import os

from tools.bst_native_build_tracer import write_decisions_with_sandbox_make
from tools.native_trace.bwrap_shim import _make_probe_cache_path


def _decision(element, policy="cmake_meson", kind="cmake"):
    return {"element": element, "max_jobs": 4, "decision": "joined",
            "kind": kind, "policy": policy}


#: What `probe_make` really caches - `make --version`'s whole stdout,
#: copied from `bst-examples`' own run on `33884772`.
REAL_PROBE = (
    "GNU Make 4.4.1\n"
    "Built for x86_64-pc-linux-gnu\n"
    "Copyright (C) 1988-2023 Free Software Foundation, Inc.\n"
    "License GPLv3+: GNU GPL version 3 or later <https://gnu.org/licenses/gpl.html>\n"
    "This is free software: you are free to change and redistribute it.\n"
    "There is NO WARRANTY, to the extent permitted by law.")


def _capture(tmp_path, rows, probes):
    fifo = str(tmp_path / "jobserver")
    captured = str(tmp_path / "captured.jsonl")
    with open(captured, "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")
    for element, version in probes.items():
        with open(_make_probe_cache_path(fifo, element), "w", encoding="utf-8") as handle:
            json.dump({"available": version is not None, "version": version}, handle)
    out = str(tmp_path / "out.jsonl")
    write_decisions_with_sandbox_make(captured, out, fifo)
    return [json.loads(line) for line in open(out, encoding="utf-8")]


class TestTheStyleIsReadableFromTheReport:
    def test_a_4_4_sandbox_reads_fifo(self, tmp_path):
        rows = _capture(tmp_path, [_decision("a.bst")], {"a.bst": "GNU Make 4.4.1"})

        assert rows[0]["sandbox_make"] == "GNU Make 4.4.1"
        assert rows[0]["auth_style"] == "fifo"

    def test_a_4_2_sandbox_reads_fd(self, tmp_path):
        rows = _capture(tmp_path, [_decision("a.bst")], {"a.bst": "GNU Make 4.2.1"})

        assert rows[0]["sandbox_make"] == "GNU Make 4.2.1"
        assert rows[0]["auth_style"] == "fd"

    def test_only_the_first_line_of_make_s_own_output_lands(self, tmp_path):
        """`probe_make` caches `make --version`'s whole stdout, so the
        first CI run to read this key published six lines of GPL notice
        inside one JSON field (`bst-examples` on `33884772`). The style
        still comes off the text the probe stored."""
        rows = _capture(tmp_path, [_decision("a.bst")], {"a.bst": REAL_PROBE})

        assert rows[0]["sandbox_make"] == "GNU Make 4.4.1"
        assert rows[0]["auth_style"] == "fifo"

    def test_two_elements_on_two_makes_are_distinguishable(self, tmp_path):
        """The whole point of the row: one capture, both branches."""
        rows = _capture(
            tmp_path, [_decision("new.bst"), _decision("old.bst")],
            {"new.bst": "GNU Make 4.4.1", "old.bst": "GNU Make 4.2.1"})

        assert {row["element"]: row["auth_style"] for row in rows} == {
            "new.bst": "fifo", "old.bst": "fd"}

    def test_an_unprobed_element_is_written_through_unchanged(self, tmp_path):
        """`None` would say "probed, and the make was absent", which is
        a different fact from "this kind is never probed"."""
        rows = _capture(tmp_path, [_decision("a.bst", policy="make", kind="autotools")], {})

        assert rows[0] == _decision("a.bst", policy="make", kind="autotools")

    def test_a_probe_that_found_no_make_adds_nothing(self, tmp_path):
        rows = _capture(tmp_path, [_decision("a.bst")], {"a.bst": None})

        assert "sandbox_make" not in rows[0]

    def test_the_rows_keep_their_order_and_count(self, tmp_path):
        rows = _capture(
            tmp_path, [_decision(f"e{i}.bst") for i in range(4)],
            {"e1.bst": "GNU Make 4.4.1"})

        assert [row["element"] for row in rows] == [f"e{i}.bst" for i in range(4)]


class TestTheDocumentSaysSo:
    def test_the_cli_guide_names_both_new_keys(self):
        repo = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        guide = open(os.path.join(repo, "docs", "guides", "cli.md"), encoding="utf-8").read()

        assert "sandbox_make" in guide and "auth_style" in guide
