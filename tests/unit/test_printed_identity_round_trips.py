"""UX-178: the tool's own output, pasted as its own input.

Round 19, live: the Shared Sources table printed
`gitlab.example.com/org/monorepo`, and `bga blast` on that exact string
answered *"Resolved as a path / Nothing in this run sources it"* -
a confident false "rebuilds nothing" on the monorepo question the
feature exists to answer, because the table prints the normalized
scheme-less identity and the url detector wanted a scheme.

The guard here is the round-trip itself: render the table, take the
cell verbatim, ask the query, compare the numbers.
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

from bga import sources
from bga.blast import blast, classify_target, format_blast_text, known_identity
from bga.report.text import _format_resource_blast

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN = os.path.join(REPO_ROOT, "tests", "fixtures", "golden", "mixed_task_kinds")
MONO = "https://gitlab.example.com/org/monorepo.git"


def _run_with(tmp_path, inventory=None, name="run"):
    run = tmp_path / name
    shutil.copytree(GOLDEN, run)
    os.remove(run / "expected_output.json")
    if inventory is not None:
        (run / "sources.json").write_text(json.dumps(inventory, indent=2))
    return run


def _monorepo_inventory():
    resource = {"kind": "git", "identity": sources.normalize_url(MONO),
                "declared": MONO, "keying": "ref", "staged_at": "src"}
    return sources.build_inventory({
        "lib.bst": [dict(resource, staged_at="src/lib")],
        "extra.bst": [dict(resource, staged_at="src/extra")],
    })


class _Result:
    def __init__(self, blast_payload):
        self.resource_blast = blast_payload


class TestTheTableCellIsAValidQuery:
    def _table_cell(self, rows):
        text = "\n".join(_format_resource_blast(_Result({
            'rows': rows, 'element_count': 4, 'headline': None, 'unreadable': {},
        })))
        # The first column of the first data row - what a reader copies.
        for line in text.splitlines():
            match = re.match(r"^  (\S+)\s+\d+\s", line)
            if match and match.group(1) != "resource":
                return match.group(1), text
        raise AssertionError(f"no resource row in:\n{text}")

    def test_the_printed_cell_round_trips_through_blast(self, tmp_path):
        """The defect, as a guard: paste the cell, get the same numbers."""
        inventory = _monorepo_inventory()
        run = _run_with(tmp_path, inventory)
        from bga.graph.edg import compute_reachability
        from bga.ingest.loader import load_all
        _ctx, graph, _trace = load_all(run)
        downstream, _ = compute_reachability(graph)
        kinds = {e.uid: (e.element_kind or "unknown") for e in graph.elements}
        rows = sources.resource_blast(inventory, downstream, kinds, {})

        cell, table = self._table_cell(rows)
        assert cell == "gitlab.example.com/org/monorepo", table

        answer = blast(run, cell, project_dir=str(tmp_path))
        assert answer["resolved_as"] == "url", format_blast_text(answer)
        assert answer["direct_count"] == rows[0]["direct_count"]
        assert answer["blast_count"] == rows[0]["blast_count"]
        assert "rebuilds nothing here" not in format_blast_text(answer)

    def test_the_scheme_bearing_form_still_works(self, tmp_path):
        run = _run_with(tmp_path, _monorepo_inventory())
        answer = blast(run, MONO, project_dir=str(tmp_path))
        assert answer["resolved_as"] == "url" and answer["direct_count"] == 2

    def test_an_exact_match_still_reports_the_other_readings(self, tmp_path):
        """Deciding the answer is not the same as hiding the ambiguity."""
        inventory = sources.build_inventory({
            "lib.bst": [{"kind": "local", "identity": "lib.bst",
                         "declared": "lib.bst", "keying": "content",
                         "staged_at": None}],
        })
        run = _run_with(tmp_path, inventory)
        answer = blast(run, "lib.bst", project_dir=str(tmp_path))
        assert answer["resolved_as"] == "path"
        assert "element" in answer["also_matched"]

    def test_a_name_the_inventory_does_not_know_falls_through(self, tmp_path):
        run = _run_with(tmp_path, _monorepo_inventory())
        answer = blast(run, "base.bst", project_dir=str(tmp_path))
        assert answer["resolved_as"] == "element"
        assert answer["direct_elements"] == ["base.bst"]

    def test_known_identity_matches_both_spellings(self):
        inventory = _monorepo_inventory()
        assert known_identity(inventory, "gitlab.example.com/org/monorepo")
        assert known_identity(inventory, MONO)
        assert known_identity(inventory, "gitlab.example.com/org/other") is None


class TestTheAdjacentEdges:
    def _blast(self, run, target, *extra):
        return subprocess.run(
            [sys.executable, "-m", "bga.cli", "blast", target, str(run), *extra],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )

    def test_a_directory_that_is_not_a_run_gets_a_sentence_not_a_traceback(
            self, tmp_path):
        """The likeliest slip: `<snapshot>/` where `<snapshot>/run` was
        meant. `analyze` prints a sentence for the same mistake, and
        UX-172's log claimed exit 2 for it."""
        snapshot = tmp_path / "20260820T120000Z"
        (snapshot / "run").mkdir(parents=True)
        shutil.copyfile(os.path.join(GOLDEN, "graph.json"),
                        snapshot / "run" / "graph.json")

        done = self._blast(snapshot, "base.bst")
        assert done.returncode == 2, done.stdout + done.stderr
        assert "Traceback" not in done.stderr, done.stderr
        assert "is not a run directory" in done.stderr
        assert "<snapshot>/run" in done.stderr

    def test_a_name_that_is_no_element_says_so(self, tmp_path):
        run = _run_with(tmp_path)
        answer = blast(run, "typo.bst", project_dir=str(tmp_path))
        text = format_blast_text(answer)
        assert "No element of that name is in this run" in text
        assert "rebuilds nothing here" not in text

    def test_an_element_that_really_rebuilds_nothing_says_that_instead(
            self, tmp_path):
        run = _run_with(tmp_path)
        answer = blast(run, "app.bst", project_dir=str(tmp_path))
        text = format_blast_text(answer)
        # `app.bst` exists and is a leaf: it rebuilds itself and nothing
        # else, which is a different sentence from "no such element".
        assert "No element of that name" not in text
        assert answer["direct_count"] == 1

    def test_a_deleted_top_level_file_is_read_as_a_path(self, tmp_path):
        """No `/` to recognise it by - only the inventory can say."""
        inventory = sources.build_inventory({
            "lib.bst": [{"kind": "local", "identity": ".", "declared": ".",
                         "keying": "content", "staged_at": None}],
        })
        assert "path" in classify_target("README.md", str(tmp_path), inventory)
        assert "path" not in classify_target("README.md", str(tmp_path), {})

    def test_it_is_a_url_not_an_url(self, tmp_path):
        run = _run_with(tmp_path, _monorepo_inventory())
        text = format_blast_text(blast(run, MONO, project_dir=str(tmp_path)))
        assert "Resolved as a url" in text
        assert "an url" not in text


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
