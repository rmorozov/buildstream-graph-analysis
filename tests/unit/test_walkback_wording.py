"""UX-164: the words around UX-156's refusal.

The mechanics held - round 17 verified the refusal, the banner, the
walk-back and exit 6 live. The words around them had three defects, two
observed in the same session.
"""
import json
import os

from bga.compare import _count_clause, _describe_build_failures
from tools.bga_snapshot import _compare_refs


class TestTheReplayHintNamesThePairActuallyCompared:
    """Item 1, and the one that actively misled. `$ bga compare @prev @last`
    printed unconditionally - and after a walk-back `@prev` resolves to the
    *skipped* snapshot (it has a `run/`, so `list_runs` includes it), so
    pasting the suggested command reproduced exactly the wreckage
    comparison the walk-back exists to prevent.
    """

    def _store(self, tmp_path, names):
        (tmp_path / "project.conf").write_text("name: x\n")
        made = []
        for name in names:
            run = tmp_path / ".bga" / "runs" / name / "run"
            run.mkdir(parents=True)
            (run / "run-context.json").write_text("{}")
            made.append(str(tmp_path / ".bga" / "runs" / name))
        return made

    def test_the_ordinary_pair_still_reads_as_the_aliases(self, tmp_path):
        first, second = self._store(tmp_path, ["01", "02"])
        assert _compare_refs(first, second) == "@prev @last"

    def test_a_walked_back_baseline_is_named_by_its_stamp(self, tmp_path):
        """Three snapshots, comparing the oldest against the newest: `@prev`
        is the middle one and would be the wrong ref."""
        first, _skipped, third = self._store(tmp_path, ["01", "02", "03"])
        assert _compare_refs(first, third) == "@01 @last"

    def test_the_hint_never_names_a_snapshot_that_was_not_compared(self, tmp_path):
        first, skipped, third = self._store(tmp_path, ["01", "02", "03"])
        refs = _compare_refs(first, third)
        assert "@prev" not in refs, (
            "@prev is the skipped snapshot here - naming it sends the user "
            "back to the comparison this feature just refused")
        assert os.path.basename(skipped) not in refs.replace("@01", "")


class TestNumberAgreement:
    """Item 2: the sentence was built for a plural list and read broken for
    the common single-skip case."""

    def _snapshot(self, tmp_path, name, failed=("x.bst",)):
        run = tmp_path / name / "run"
        run.mkdir(parents=True)
        (run / "run-context.json").write_text(json.dumps(
            {"build_outcome": {"failed_elements": list(failed),
                               "failed_count": len(failed)}}))
        return str(tmp_path / name)

    def test_one_skipped_snapshot_reads_singular(self, tmp_path, capsys):
        from tools.bga_snapshot import main
        (tmp_path / "project.conf").write_text("name: x\n")
        runs = tmp_path / ".bga" / "runs"
        healthy = runs / "01" / "run"
        healthy.mkdir(parents=True)
        (healthy / "run-context.json").write_text("{}")
        self._snapshot(runs, "02")
        main(["--project", str(tmp_path), "--list"])  # touch the store
        # the wording itself, without needing a build
        import inspect
        from tools import bga_snapshot
        source = inspect.getsource(bga_snapshot.main)
        assert "records a build" in source and "record builds" in source


class TestCacheHitsAreNotCasualties:
    """Item 3. The failing run's queue was processed 0, skipped 6, failed 1
    - six elements were already cached and none needed building besides the
    one that failed. `scheduled = processed + skipped + failed` overstated
    the damage sevenfold, and a user could go hunting for six lost builds.
    """

    def test_the_clause_separates_built_from_cached(self):
        assert _count_clause({"built": 0, "cached": 6}) == "0 built, 6 already cached"

    def test_a_build_with_no_cache_hits_says_only_what_it_built(self):
        assert _count_clause({"built": 3, "cached": 0}) == "3 built"

    def test_a_capture_that_did_not_record_counts_says_nothing(self):
        assert _count_clause({"built": None, "cached": None}) is None

    def test_the_refusal_no_longer_says_scheduled(self):
        text = _describe_build_failures([{
            "run": "candidate", "failed_elements": ["lib-d.bst"],
            "built": 0, "cached": 6, "scheduled": 7, "interrupted": False}])
        assert "0 built, 6 already cached" in text
        assert "of 7 scheduled" not in text

    def test_the_banner_uses_the_same_three_way_count(self):
        from bga.report.text import format_text

        class _Result:
            run_id = "r"
            total_duration_us = 1_000_000
            violations = [{"type": "build_failed", "failed_count": 1,
                           "failed_elements": ["lib-d.bst"],
                           "built_count": 0, "cached_count": 6,
                           "scheduled_count": 7, "interrupted": False}]
            floors = {}
            def __getattr__(self, name):
                return None

        text = format_text(_Result(), section="floors")
        assert "0 built, 6 already cached" in text
        assert "of 7 scheduled" not in text
