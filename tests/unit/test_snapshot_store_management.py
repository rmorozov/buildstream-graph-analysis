"""UX-159: the quiet minutes and growing gigabytes of a big snapshot.

Two small-project comforts stop holding once one capture is a multi-hour
session: bga's own phases are silent (so the user cannot tell "working"
from "hung"), and the store grows without bound behind a 2 GB warning
whose only advice was to delete directories by hand - with no size in
`--list` to say *which* directory, and no command that deletes anything.
"""
import json
import os
import time

import pytest

from bga import run_store
from tools.bga_snapshot import _protected, _prune, main


def _snapshot(project, name, files=(("plane2.json", "x" * 1000),), failed=()):
    run = os.path.join(project, ".bga", "runs", name, "run")
    os.makedirs(run, exist_ok=True)
    with open(os.path.join(run, "run-context.json"), "w", encoding="utf-8") as h:
        json.dump({"build_outcome": {"failed_elements": list(failed),
                                     "failed_count": len(failed)}}, h)
    for filename, content in files:
        with open(os.path.join(project, ".bga", "runs", name, filename),
                  "w", encoding="utf-8") as handle:
            handle.write(content)
    return os.path.join(project, ".bga", "runs", name)


@pytest.fixture
def project(tmp_path):
    (tmp_path / "project.conf").write_text("name: x\n")
    return str(tmp_path)


class TestSizesAreVisible:
    def test_a_snapshots_size_is_the_sum_of_its_files(self, project):
        path = _snapshot(project, "01", files=(("a", "x" * 100), ("b", "y" * 50)))
        # plus the run-context.json the helper writes
        assert run_store.snapshot_size_bytes(path) > 150

    def test_the_store_total_is_the_sum_of_its_snapshots(self, project):
        _snapshot(project, "01")
        _snapshot(project, "02")
        total = run_store.store_size_bytes(project)
        parts = sum(run_store.snapshot_size_bytes(p)
                    for p in run_store.list_snapshots(project))
        assert total == parts

    @pytest.mark.parametrize("size,expected", [
        (0, "0B"), (512, "512B"), (2048, "2.0K"),
        (5 * 1024 ** 2, "5.0M"), (3 * 1024 ** 3, "3.0G"),
    ])
    def test_sizes_read_the_way_du_prints_them(self, size, expected):
        assert run_store.human_bytes(size) == expected

    def test_list_shows_a_size_per_snapshot_and_a_total(self, project, capsys):
        _snapshot(project, "01")
        _snapshot(project, "02")
        main(["--project", project, "--list"])
        out = capsys.readouterr().out
        assert out.count("K") >= 2 or out.count("B") >= 2
        assert "total" in out


class TestPruneDeletesButNotTheOnesInUse:
    def test_keep_n_deletes_the_rest(self, project, capsys):
        for name in ("01", "02", "03", "04", "05"):
            _snapshot(project, name)
        _prune(project, keep=2, older_than=None, dry_run=False)
        assert len(run_store.list_snapshots(project)) == 2

    def test_it_never_deletes_last_or_prev(self, project):
        """A prune that removes the baseline turns the next comparison into
        a first-snapshot message."""
        for name in ("01", "02", "03"):
            _snapshot(project, name)
        _prune(project, keep=0, older_than=None, dry_run=False)
        remaining = [os.path.basename(p) for p in run_store.list_snapshots(project)]
        assert remaining == ["02", "03"], "@prev and @last must survive"

    def test_the_dead_baseline_key_is_gone(self, project):
        """UX-167 decided it: nothing in production ever wrote
        `config["baseline"]`, so the protection guarded a phantom. Only
        prune's own test set it. Protecting the walk-back's actual target
        (below) covers what it was for."""
        for name in ("01", "02", "03"):
            _snapshot(project, name)
        run_store.write_config(project, {"baseline":
                                         os.path.join(project, ".bga", "runs", "01")})
        assert os.path.join(project, ".bga", "runs", "01") not in _protected(project)
        import inspect

        from tools import bga_snapshot
        assert '"baseline"' not in inspect.getsource(bga_snapshot._protected)

    def test_the_newest_healthy_run_survives_two_unhealthy_aliases(self, project):
        """UX-167's headline. Round 17 hit this live: with a failed run and
        an interrupted run as the two newest, `--keep 2` protected exactly
        those and offered to delete the store's only healthy snapshot -
        the one UX-156's walk-back needs as the next baseline."""
        _snapshot(project, "01")                       # healthy
        _snapshot(project, "02", failed=["lib-d.bst"])  # failed
        broken = os.path.join(project, ".bga", "runs", "03", "run")
        os.makedirs(broken)
        with open(os.path.join(broken, "run-context.json"), "w") as handle:
            json.dump({"build_outcome": {"failed_elements": [], "failed_count": 0,
                                         "interrupted": True}}, handle)

        _prune(project, keep=2, older_than=None, dry_run=False)

        survivors = [os.path.basename(p) for p in run_store.list_snapshots(project)]
        assert "01" in survivors, (
            "the only healthy run is what the walk-back would compare against")
        assert survivors == ["01", "02", "03"]

    def test_a_store_of_healthy_runs_prunes_exactly_as_before(self, project):
        """The extra directory is kept only when the aliased two are
        unhealthy, so the ordinary case is unchanged."""
        for name in ("01", "02", "03", "04"):
            _snapshot(project, name)
        _prune(project, keep=2, older_than=None, dry_run=False)
        assert [os.path.basename(p)
                for p in run_store.list_snapshots(project)] == ["03", "04"]

    def test_husks_go_first_and_are_counted_separately(self, project, capsys):
        """A snapshot with no run directory is not in `list_runs`, not
        aliased, and not useful - and `--keep 2` used to leave it standing
        while deleting run-bearing snapshots."""
        for name in ("01", "02", "03"):
            _snapshot(project, name)
        os.makedirs(os.path.join(project, ".bga", "runs", "04"))  # husk

        _prune(project, keep=2, older_than=None, dry_run=False)

        survivors = [os.path.basename(p) for p in run_store.list_snapshots(project)]
        assert "04" not in survivors, "the husk should go first"
        assert survivors == ["02", "03"]
        assert "held no run directory" in capsys.readouterr().out

    def test_older_than_deletes_by_age(self, project):
        old = _snapshot(project, "01")
        _snapshot(project, "02")
        _snapshot(project, "03")
        ancient = time.time() - 30 * 86400
        os.utime(old, (ancient, ancient))
        _prune(project, keep=None, older_than=7, dry_run=False)
        assert "01" not in [os.path.basename(p)
                            for p in run_store.list_snapshots(project)]

    def test_dry_run_deletes_nothing_but_says_what_would_go(self, project, capsys):
        for name in ("01", "02", "03", "04"):
            _snapshot(project, name)
        _prune(project, keep=2, older_than=None, dry_run=True)
        assert len(run_store.list_snapshots(project)) == 4
        out = capsys.readouterr().out
        assert "would delete" in out and "would free" in out

    def test_it_reports_what_it_freed(self, project, capsys):
        for name in ("01", "02", "03"):
            _snapshot(project, name)
        _prune(project, keep=2, older_than=None, dry_run=False)
        assert "freed" in capsys.readouterr().out

    def test_prune_without_a_rule_refuses_rather_than_guessing(self, project, capsys):
        _snapshot(project, "01")
        assert main(["--project", project, "prune"]) == 2
        assert "Nothing was deleted" in capsys.readouterr().err
        assert len(run_store.list_snapshots(project)) == 1

    def test_prunes_own_flags_survive_the_remainder_parser(self, project):
        """`cmd` is argparse.REMAINDER, so everything after the first
        positional is swallowed verbatim - which is what the wrapped build
        needs and what a subcommand does not. `--keep` reached `_prune` as
        None before this was handled."""
        for name in ("01", "02", "03", "04"):
            _snapshot(project, name)
        assert main(["--project", project, "prune", "--keep", "2"]) == 0
        assert len(run_store.list_snapshots(project)) == 2

    def test_an_empty_store_is_not_an_error(self, project, capsys):
        assert _prune(project, keep=2, older_than=None, dry_run=False) == 0


class TestTheSizeWarningNamesTheCommand:
    def test_it_no_longer_advises_hand_deletion(self):
        import inspect

        from tools import bga_snapshot
        source = inspect.getsource(bga_snapshot._warn_if_large)
        assert "prune" in source
        assert "Delete snapshot directories you no longer need" not in source
