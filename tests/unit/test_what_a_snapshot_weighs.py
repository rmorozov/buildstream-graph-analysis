"""UX-300: sizes become facts the tool states and decisions read.

One field snapshot reached ~2 GB. Five nightly captures are a quota
incident scheduled in advance, and until this the store's only size
affordances were a warning that fires once past 2 GB and a `--list` you
have to already be worried to run. The retention thinking dated from
kilobyte snapshots.

**The measurement that re-argues the raw-log default.** `UX-188` kept
the raw Plane 2 log by default because it measured 8-12% of a capture.
Re-measured here at 200,000 processes, the *compression* is unchanged -
52.0 MB of log becomes 4.68 MB, 9.0% - but what it is a fraction **of**
moved: `UX-297` took the per-process records out of the report, so a
snapshot is now

```text
plane2.log.gz     4,679,800 B    99.0%
plane2.json          43,879 B     0.9%
run/                  1,599 B     0.0%
build.log               702 B     0.0%
                  -----------
                  4,725,980 B
```

The raw log is no longer a fraction of a snapshot beside a large
report. It **is** the snapshot. The default stands - it is the ground
truth the timeline is rendered from and the only place a per-process
fact still lives - but the sentence a capture prints had to change with
it, because `--no-keep-raw` now looks like a small saving and is the
whole one.
"""
import pytest

from bga import run_store, store_aggregate
from tools.bga_snapshot import over_budget, parse_size


class TestASizeCanBeTyped:
    """`--max-store 2G`. Binary multiples, because that is what
    `human_bytes` prints - a figure read off one command has to be
    typeable into the other."""

    @pytest.mark.parametrize("text,expected", [
        ("1024", 1024), ("8k", 8192), ("500M", 500 * 1024 ** 2),
        ("2G", 2 * 1024 ** 3), ("2GB", 2 * 1024 ** 3),
        ("1.5G", int(1.5 * 1024 ** 3)), ("1T", 1024 ** 4),
    ])
    def test_it_reads_what_a_person_writes(self, text, expected):
        assert parse_size(text) == expected

    @pytest.mark.parametrize("text", ["", "big", "2X", "-1G"])
    def test_it_refuses_what_it_cannot_read(self, text):
        with pytest.raises(ValueError) as raised:
            parse_size(text)
        assert "--max-store" in str(raised.value) or "negative" in str(raised.value)

    def test_the_two_commands_agree_on_a_figure(self):
        """`human_bytes` prints it, `parse_size` reads it. If they used
        different multiples a user would type in what they were shown
        and get a different store."""
        assert parse_size("2G") == 2 * 1024 ** 3
        assert run_store.human_bytes(2 * 1024 ** 3).startswith("2")


class TestTheBudgetIsMetOutOfWhatIsFree:
    """The keep-set is not negotiable: `@last` and `@prev` are what the
    next comparison reads, so a budget is met from what is left."""

    @staticmethod
    def _sizes(**pairs):
        return lambda path: pairs[path]

    def test_it_deletes_oldest_first_until_it_is_under(self):
        doomed = over_budget(["a", "b", "c", "d"], budget=25, protected=set(),
                             size_of=self._sizes(a=10, b=10, c=10, d=10))
        assert doomed == ["a", "b"]

    def test_it_stops_as_soon_as_the_budget_is_met(self):
        doomed = over_budget(["a", "b", "c"], budget=25, protected=set(),
                             size_of=self._sizes(a=10, b=10, c=10))
        assert doomed == ["a"]

    def test_it_never_takes_a_protected_snapshot(self):
        doomed = over_budget(["a", "b", "c"], budget=5, protected={"b", "c"},
                             size_of=self._sizes(a=10, b=10, c=10))
        assert doomed == ["a"], (
            "the budget was met by deleting what the next comparison reads")

    def test_a_store_that_cannot_reach_the_budget_says_so_by_stopping(self):
        """Rather than emptying itself. The item prices; it does not
        delete beyond what it was asked for."""
        doomed = over_budget(["a", "b"], budget=1, protected={"a", "b"},
                             size_of=self._sizes(a=10, b=10))
        assert doomed == []

    def test_a_store_already_under_loses_nothing(self):
        doomed = over_budget(["a", "b"], budget=100, protected=set(),
                             size_of=self._sizes(a=10, b=10))
        assert doomed == []


class TestTheAggregateReportsWhatTheStoreWeighs:

    @pytest.fixture
    def rows(self):
        return [
            {"stamp": "20260101T000000Z", "path": "/s/1", "bytes": 4_000_000,
             "total_duration_us": 1_000_000, "host_class": "one",
             "outcome": "ok", "cache_hit_rate": 0.5},
            {"stamp": "20260102T000000Z", "path": "/s/2", "bytes": 6_000_000,
             "total_duration_us": 1_200_000, "host_class": "one",
             "outcome": "ok", "cache_hit_rate": 0.6},
            {"stamp": "20260103T000000Z", "path": "/s/3", "bytes": 9_000_000,
             "total_duration_us": 1_100_000, "host_class": "one",
             "outcome": "ok", "cache_hit_rate": 0.7},
        ]

    def _document(self, rows, monkeypatch):
        monkeypatch.setattr(store_aggregate, "_manifest_of", lambda _p: None)
        return store_aggregate.aggregate(
            {"project": "/project", "snapshots": rows})

    def test_the_store_total_is_published_at_the_document_level(
            self, rows, monkeypatch):
        """Not inside `blended`: every other blended figure is refused
        across host classes because a duration measured on two machines
        is two populations. A byte is a byte."""
        document = self._document(rows, monkeypatch)
        assert document["store_bytes"]["total"] == 19_000_000
        assert document["store_bytes"]["snapshots"] == 3

    def test_a_capture_that_failed_still_occupies_its_disk(
            self, rows, monkeypatch):
        """The distinction the item is about: a run excluded from every
        distribution for failing is not a sample, and is still on the
        disk. The two totals say which is which."""
        rows = rows + [{"stamp": "20260104T000000Z", "path": "/s/4",
                        "bytes": 5_000_000, "outcome": "failed",
                        "host_class": "one"}]
        document = self._document(rows, monkeypatch)
        assert document["store_bytes"]["total"] == 24_000_000
        assert document["store_bytes"]["measured_total"] == 19_000_000
        assert document["measured"] == 3 and document["snapshots"] == 4

    def test_the_class_carries_the_distribution_not_just_the_sum(
            self, rows, monkeypatch):
        """"Which capture is the big one" is answered by a p95 against a
        median, not by a total."""
        entry = self._document(rows, monkeypatch)["host_classes"][0]
        assert entry["total_bytes"] == 19_000_000
        sizes = entry["snapshot_bytes"]
        assert sizes["median"] == 6_000_000
        assert sizes["max"] == 9_000_000
        assert sizes["min"] == 4_000_000

    def test_the_text_says_it_on_the_second_line(self, rows, monkeypatch):
        rendered = store_aggregate.render(self._document(rows, monkeypatch))
        assert "on disk" in rendered[2], rendered[:4]
        assert any("Snapshot size" in line for line in rendered), rendered

    def test_the_contract_declares_every_field(self):
        from bga import schemas

        node = schemas.schema(schemas.STORE_AGGREGATE)["properties"]
        store_bytes = node["store_bytes"]
        for key in ("total", "snapshots", "measured_total", "note"):
            assert key in store_bytes["properties"], key
        klass = node["host_classes"]["items"]["properties"]
        assert "snapshot_bytes" in klass and "total_bytes" in klass


class TestTheCaptureSaysWhatItJustWrote:

    def test_it_states_the_snapshot_and_the_store(self, tmp_path, capsys):
        from tools.bga_snapshot import _say_what_it_weighs

        project = tmp_path / "project"
        runs = project / ".bga" / "runs"
        snapshot = runs / "20260821T120000Z"
        snapshot.mkdir(parents=True)
        (project / "project.conf").write_text("name: p\n", encoding="utf-8")
        (snapshot / "plane2.json").write_text("{}" * 500, encoding="utf-8")
        (runs / "20260820T120000Z").mkdir()
        (runs / "20260820T120000Z" / "plane2.json").write_text(
            "{}" * 500, encoding="utf-8")

        _say_what_it_weighs(str(snapshot), str(project))
        said = capsys.readouterr().err
        assert "This snapshot:" in said, said
        assert "2 snapshot(s)" in said, said
        assert str(runs) in said, said

    def test_it_names_the_raw_log_when_that_is_what_the_snapshot_is(
            self, tmp_path, capsys):
        """`UX-297` made the raw log 99% of a capture. `--no-keep-raw`
        now looks like a small saving and is the whole one, so the
        sentence says what dropping it costs."""
        from tools.bga_snapshot import RAW_LOG_NAME, _say_what_it_weighs

        project = tmp_path / "project"
        snapshot = project / ".bga" / "runs" / "20260821T120000Z"
        snapshot.mkdir(parents=True)
        (project / "project.conf").write_text("name: p\n", encoding="utf-8")
        (snapshot / RAW_LOG_NAME).write_bytes(b"x" * 100_000)
        (snapshot / "plane2.json").write_text("{}", encoding="utf-8")

        _say_what_it_weighs(str(snapshot), str(project))
        said = capsys.readouterr().err
        assert "raw Plane 2 log" in said, said
        assert "--no-keep-raw" in said, said
        assert "timeline" in said, said

    def test_a_snapshot_that_is_mostly_report_gets_no_such_sentence(
            self, tmp_path, capsys):
        """The clause is about a specific fact - that the log dominates.
        A capture where it does not must not claim it does."""
        from tools.bga_snapshot import RAW_LOG_NAME, _say_what_it_weighs

        project = tmp_path / "project"
        snapshot = project / ".bga" / "runs" / "20260821T120000Z"
        snapshot.mkdir(parents=True)
        (project / "project.conf").write_text("name: p\n", encoding="utf-8")
        (snapshot / RAW_LOG_NAME).write_bytes(b"x" * 1_000)
        (snapshot / "plane2.json").write_text("{" * 100_000, encoding="utf-8")

        _say_what_it_weighs(str(snapshot), str(project))
        said = capsys.readouterr().err
        assert "This snapshot:" in said
        assert "--no-keep-raw" not in said, said


class TestPruneSaysWhatItWouldRecover:

    def _store(self, tmp_path, sizes):
        project = tmp_path / "project"
        runs = project / ".bga" / "runs"
        runs.mkdir(parents=True)
        (project / "project.conf").write_text("name: p\n", encoding="utf-8")
        for index, size in enumerate(sizes):
            snapshot = runs / f"2026010{index + 1}T000000Z"
            (snapshot / "run").mkdir(parents=True)
            (snapshot / "run" / "graph.json").write_text("{}", encoding="utf-8")
            (snapshot / "plane2.json").write_bytes(b"x" * size)
        return project

    def test_a_budget_deletes_the_oldest_and_names_the_bytes(
            self, tmp_path, capsys):
        from tools.bga_snapshot import _prune

        project = self._store(tmp_path, [400_000, 400_000, 400_000, 400_000])
        code = _prune(str(project), keep=None, older_than=None, dry_run=True,
                      max_store=900_000)
        said = capsys.readouterr().out
        assert code == 0
        assert "would delete" in said, said
        assert "would free" in said, said
        assert "would remain" in said, said
        # Nothing was actually removed: this is a dry run.
        assert len(list((project / ".bga" / "runs").iterdir())) == 4

    def test_the_keep_set_survives_a_budget_it_cannot_meet(
            self, tmp_path, capsys):
        from tools.bga_snapshot import _prune

        project = self._store(tmp_path, [400_000, 400_000])
        code = _prune(str(project), keep=None, older_than=None, dry_run=False,
                      max_store=1_000)
        said = capsys.readouterr().out
        assert code == 0
        assert len(list((project / ".bga" / "runs").iterdir())) == 2, (
            "the budget was met by deleting what @last and @prev point at")
        assert "protected by @last/@prev" in said, said

    def test_prune_still_refuses_with_no_rule_at_all(self, tmp_path, capsys):
        from tools.bga_snapshot import main

        project = self._store(tmp_path, [1_000])
        code = main(["--project", str(project), "prune"])
        assert code == 2
        assert "--max-store SIZE" in capsys.readouterr().err
