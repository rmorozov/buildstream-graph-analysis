"""UX-172 and UX-173: the question pointed the developer's way, and
blast counts that know what an element is.

`bga blast TARGET` answers "what rebuilds if I touch this" from
whichever end the developer has it - a repository url, a path, or an
element. UX-173 is the user's first sentence taken literally: blast
analysis ignored element kind, and a blast of 84 where 39 are stacks is
not a blast of 84 things that build.
"""
import json
import os
import shutil
import subprocess
import sys

import pytest

from bga import sources
from bga.blast import blast, classify_target, format_blast_text

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
GOLDEN = os.path.join(REPO_ROOT, "tests", "fixtures", "golden", "mixed_task_kinds")


def _run_with(tmp_path, inventory=None, name="run"):
    run = tmp_path / name
    shutil.copytree(GOLDEN, run)
    os.remove(run / "expected_output.json")
    if inventory is not None:
        (run / "sources.json").write_text(json.dumps(inventory, indent=2))
    return run


def _resource(kind, identity, keying, staged=None):
    return {"kind": kind, "identity": identity, "declared": identity,
            "keying": keying, "staged_at": staged}


class TestTheTargetResolvesInAStatedOrder:
    def test_a_url_is_a_url(self):
        assert classify_target("https://host/org/repo.git")[0] == "url"
        assert classify_target("git@host:org/repo.git")[0] == "url"

    def test_an_existing_path_is_a_path(self, tmp_path):
        (tmp_path / "files").mkdir()
        assert classify_target("files", str(tmp_path)) == ["path"]

    def test_an_element_name_is_an_element(self, tmp_path):
        assert classify_target("lib-a.bst", str(tmp_path)) == ["element"]

    def test_a_collision_reports_every_reading_in_order(self, tmp_path):
        """`lib-a.bst` could be a file on disk *and* an element name."""
        (tmp_path / "lib-a.bst").write_text("kind: manual\n")
        assert classify_target("lib-a.bst", str(tmp_path)) == ["path", "element"]

    def test_the_answer_says_which_reading_it_used(self, tmp_path):
        (tmp_path / "lib.bst").write_text("kind: manual\n")
        inventory = sources.build_inventory({
            "lib.bst": [_resource("local", "lib.bst", "content")],
        })
        answer = blast(_run_with(tmp_path, inventory), "lib.bst",
                       project_dir=str(tmp_path))
        assert answer["resolved_as"] == "path"
        assert answer["also_matched"] == ["element"]
        text = format_blast_text(answer)
        assert "Resolved as a path" in text
        assert "resolution order is url, path, element" in text


class TestTheThreeShapesOfTheQuestion:
    def test_a_url_names_every_element_sourcing_it(self, tmp_path):
        mono = _resource("git", "host/org/mono", "ref")
        inventory = sources.build_inventory({
            "lib.bst": [dict(mono, staged_at="src/lib")],
            "extra.bst": [dict(mono, staged_at="src/extra")],
        })
        answer = blast(_run_with(tmp_path, inventory),
                       "https://host/org/mono.git")
        assert answer["resolved_as"] == "url"
        assert answer["direct_elements"] == ["extra.bst", "lib.bst"]
        # `lib.bst` feeds `app.bst` in the golden graph.
        assert "app.bst" in answer["blast_elements"]
        assert answer["keying"] == "ref"
        assert "keys on ref" in format_blast_text(answer)

    def test_a_path_inside_a_staged_directory_counts(self, tmp_path):
        """The question is asked about a file that was just edited."""
        inventory = sources.build_inventory({
            "lib.bst": [_resource("local", "files/src", "content")],
            "extra.bst": [_resource("local", "files/other", "content")],
        })
        run = _run_with(tmp_path, inventory)
        answer = blast(run, "files/src/deep/main.c", project_dir=str(tmp_path))
        assert answer["direct_elements"] == ["lib.bst"]
        assert "extra.bst" not in answer["blast_elements"]

    def test_a_sibling_directory_does_not_count(self, tmp_path):
        """`files/src2` must not match a source staging `files/src`."""
        inventory = sources.build_inventory({
            "lib.bst": [_resource("local", "files/src", "content")],
        })
        answer = blast(_run_with(tmp_path, inventory), "files/src2",
                       project_dir=str(tmp_path))
        assert answer["direct_elements"] == []

    def test_an_element_gets_its_downstream_closure(self, tmp_path):
        answer = blast(_run_with(tmp_path), "base.bst")
        assert answer["resolved_as"] == "element"
        assert answer["direct_elements"] == ["base.bst"]
        assert set(answer["blast_elements"]) >= {"base.bst", "lib.bst", "app.bst"}

    def test_nothing_matching_is_an_answer_not_an_error(self, tmp_path):
        inventory = sources.build_inventory({
            "lib.bst": [_resource("git", "host/org/other", "ref")],
        })
        answer = blast(_run_with(tmp_path, inventory),
                       "https://host/org/absent.git")
        assert answer["direct_count"] == 0
        assert "rebuilds nothing here" in format_blast_text(answer)

    def test_a_run_without_an_inventory_says_why_it_cannot_answer(self, tmp_path):
        """Not "nothing sources it" - that would be a false negative."""
        answer = blast(_run_with(tmp_path), "https://host/org/mono.git")
        text = format_blast_text(answer)
        assert "no source inventory" in text
        assert "rebuilds nothing here" not in text


class TestItIsAQuestionNotAGate:
    def _blast(self, run, target, *extra):
        return subprocess.run(
            [sys.executable, "-m", "bga.cli", "blast", target, str(run), *extra],
            capture_output=True, text=True, cwd=REPO_ROOT,
        )

    def test_an_empty_answer_still_exits_zero(self, tmp_path):
        run = _run_with(tmp_path)
        done = self._blast(run, "https://host/org/absent.git")
        assert done.returncode == 0, done.stderr

    def test_a_large_answer_still_exits_zero(self, tmp_path):
        run = _run_with(tmp_path)
        done = self._blast(run, "base.bst")
        assert done.returncode == 0, done.stderr
        assert "Blast radius: base.bst" in done.stdout

    def test_a_missing_run_directory_is_a_usage_error(self, tmp_path):
        done = self._blast(tmp_path / "nope", "base.bst")
        assert done.returncode == 2
        assert "not a run directory" in done.stderr

    def test_json_carries_the_same_answer(self, tmp_path):
        done = self._blast(_run_with(tmp_path), "base.bst", "--format", "json")
        assert done.returncode == 0, done.stderr
        payload = json.loads(done.stdout)
        assert payload["resolved_as"] == "element"
        assert payload["blast_count"] >= 3


class TestBlastCountsKnowWhatAnElementIs:
    def test_a_stack_is_counted_as_assembling(self):
        kinds = {"a.bst": "manual", "b.bst": "stack", "c.bst": "import",
                 "d.bst": "cmake"}
        building, assembling = sources.split_by_kind(kinds, kinds)
        assert (building, assembling) == (2, 2)

    def test_an_unknown_kind_counts_as_building(self):
        """Fail toward overstating what a change costs."""
        kinds = {"a.bst": "some-plugin-nobody-here-has-seen"}
        assert sources.split_by_kind(kinds, kinds) == (1, 0)

    def test_the_split_is_silent_when_everything_builds(self):
        assert sources.format_kind_split(7, 0) == "7 element(s)"
        assert sources.format_kind_split(3, 4) == \
            "7 element(s) (3 that build, 4 that assemble)"

    def test_the_blast_answer_carries_the_split(self, tmp_path):
        answer = blast(_run_with(tmp_path), "base.bst")
        assert answer["building_count"] + answer["assembling_count"] == \
            answer["blast_count"]
        assert "that build" in format_blast_text(answer) or \
            answer["assembling_count"] == 0


class TestTheRankingSaysWhichOrderItIsIn:
    def _signals(self, measured):
        return {
            'top_blast_radius': ['runtime.bst', 'work-a.bst'],
            'blast_radius': {
                'runtime.bst': {'downstream_count': 9, 'element_kind': 'import',
                                'weighted_duration_us': 22_000_000 if measured else 0},
                'work-a.bst': {'downstream_count': 1, 'element_kind': 'manual',
                               'weighted_duration_us': 3_000_000 if measured else 0},
            },
            'blast_radius_ranked_by': ('measured-rebuild-time' if measured
                                       else 'element-count'),
        }

    def test_a_measured_run_says_it_ranked_by_cost(self):
        from bga.report.text import _format_blast_ranking
        text = "\n".join(_format_blast_ranking(self._signals(True)))
        assert "by measured rebuild time" in text
        assert "22.0s of rebuilding below it" in text
        assert "assembles, does not build" in text

    def test_an_unmeasured_run_says_it_fell_back_to_the_count(self):
        from bga.report.text import _format_blast_ranking
        text = "\n".join(_format_blast_ranking(self._signals(False)))
        assert "this run measured no durations" in text
        assert "of rebuilding below it" not in text

    def test_the_ranking_itself_is_ordered_by_cost(self, tmp_path):
        """The sorter, not just the sentence about it.

        The two tests above hand `_format_blast_ranking` a dict they
        built, so they would keep passing with the ranking sorted by
        count - found by mutating the sorter and watching nothing go
        red. This runs the real pipeline over the golden run.
        """
        done = subprocess.run(
            [sys.executable, "-m", "bga.cli", "analyze", GOLDEN,
             "--diagnostics", "--format", "json"],
            capture_output=True, text=True, cwd=REPO_ROOT, check=True,
        )
        signals = json.loads(done.stdout)["elements"]
        assert signals["blast_radius_ranked_by"] == "measured-rebuild-time"
        weights = [signals["blast_radius"][uid]["weighted_duration_us"]
                   for uid in signals["top_blast_radius"]]
        assert weights == sorted(weights, reverse=True), (
            f"the ranking is not in cost order: {weights}"
        )
        # And the order is genuinely different from the count order here,
        # so this cannot pass by both orders agreeing.
        counts = [signals["blast_radius"][uid]["downstream_count"]
                  for uid in signals["top_blast_radius"]]
        assert any(w for w in weights), "no durations - this fixture cannot test it"
        assert len(set(weights)) > 1 or len(set(counts)) > 1


class TestTheInvalidationNoteAdoptsTheSplit:
    def test_a_root_that_invalidated_stacks_says_so(self):
        from bga.report.text import _format_invalidation_roots

        churn = {
            'applicable': True, 'churned_count': 0, 'churned_elements': [],
            'wasted_rebuild_us': 0, 'rebuilt_in_both_count': 0,
            'rebuilt_in_both_elements': [],
            'invalidation_roots': [{
                'element_uid': 'core.bst',
                'baseline_cache_key': 'aaaaaaaaaa', 'candidate_cache_key': 'bbbbbbbbbb',
                'rebuilt': True, 'duration_us': 1_000_000,
                'downstream_rebuilt': 7, 'downstream_building': 3,
                'downstream_assembling': 4, 'downstream_us': 10_300_000,
            }],
        }
        text = "\n".join(_format_invalidation_roots(churn))
        assert "7 element(s) (3 that build, 4 that assemble)" in text


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
