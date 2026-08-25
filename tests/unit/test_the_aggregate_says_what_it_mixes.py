"""UX-253: an aggregate names the contract sets it is made of.

`UX-250` settled the two-run case: `bga compare` refuses when a
contract the comparison *reads* moved between the two producers, never
on the version number. Its clause 2 asked for the many-run case, and
that half was deliberately not implemented — because the two-run rule
does not generalise by itself, and guessing would ship a rule nobody
argued in the command whose whole job is to say what a body of history
means.

**The argument, settled here.** `UX-234` refuses to blend across *host
classes* and publishes per-class figures instead. A contract set is
**not** the same kind of thing:

- A host class partitions runs into populations that must not be
  pooled — durations from a fast machine and a slow one are
  incomparable, so a blended number would mean nothing.
- A moved read-contract makes a run's fields *absent or differently
  defined*. The run cannot be **read**, rather than being read and
  meaning something else. That is an exclusion, not an
  incomparability.

So the many-run rule is the two-run rule applied to a set, and the
answers to the three questions the item posed are:

1. *One distribution with a caveat, or two?* One — over the runs whose
   read-contracts agree — plus the composition, always published. A
   contract set is not a population.
2. *If the minority is excluded, what is the minority?* Whatever
   disagrees with the **newest** state. Not "fewer runs" and not
   "older": the newest is the one the reader is holding.
3. *Host-class exclusion, or `MIN_BASELINE_RUNS` refusal?* The
   exclusion's *mechanism* — counted, named, with a reason — but not
   the host class's refusal, because the runs are not incomparable.
"""
import json
import pathlib

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]


def _snapshot(root, name, contracts, duration_us=1_000_000):
    """A snapshot directory carrying a producer stamp, or none."""
    from bga import run_store

    snapshot = root / name
    run = snapshot / run_store.RUN_SUBDIR
    run.mkdir(parents=True)
    report = {"total_duration_us": duration_us}
    if contracts is not None:
        report["producer"] = {"tool": "bga", "version": "0.2.0",
                              "contracts": list(contracts)}
    (run / "report.json").write_text(json.dumps(report))
    return {"path": str(snapshot), "total_duration_us": duration_us,
            "cache_hit_rate": 0.5, "host_class": "x86_64/linux",
            "snapshot": name, "stamp": f"2026-08-24T0{len(name)}:00:00Z"}


class TestTheCompositionIsPublished:
    def test_one_contract_set_says_so(self, tmp_path):
        from bga.store_aggregate import _contract_composition

        rows = [_snapshot(tmp_path, f"s{i}", ["analyze/v2", "store/v1"])
                for i in range(3)]
        out = _contract_composition(rows)
        assert out["mixed"] is False
        assert out["sets"] == [
            {"contracts": ["analyze/v2", "store/v1"], "runs": 3}]
        assert out["unstamped_runs"] == 0

    def test_two_contract_sets_are_both_named(self, tmp_path):
        """The discriminating case: a minority set that a reader would
        otherwise never see."""
        from bga.store_aggregate import _contract_composition

        rows = [_snapshot(tmp_path, f"old{i}", ["analyze/v2"]) for i in range(2)]
        rows += [_snapshot(tmp_path, f"new{i}", ["analyze/v2", "store/v1"])
                 for i in range(7)]
        out = _contract_composition(rows)
        assert out["mixed"] is True
        assert [entry["runs"] for entry in out["sets"]] == [7, 2], out
        assert out["sets"][0]["contracts"] == ["analyze/v2", "store/v1"], (
            "the commonest set is not first, so a reader cannot tell which "
            "is the minority")

    def test_an_unstamped_run_is_an_explicit_unknown(self, tmp_path):
        """Every artifact predating `UX-249` carries no producer.
        Counting them as agreeing would make the stamp's arrival delete
        the history it protects."""
        from bga.store_aggregate import _contract_composition

        rows = [_snapshot(tmp_path, "a", None),
                _snapshot(tmp_path, "b", ["analyze/v2"])]
        out = _contract_composition(rows)
        assert out["unstamped_runs"] == 1
        assert out["mixed"] is False, (
            "an unstamped run was counted as a second contract set - it is "
            "an unknown, not a disagreement")

    def test_it_names_the_contracts_it_reads(self):
        """The half that makes the rest meaningful: `whatif/v1` moving
        changes nothing about a duration distribution, and a composition
        that did not say which contracts matter would imply it did."""
        from bga.store_aggregate import AGGREGATE_READS, _contract_composition

        out = _contract_composition([])
        assert out["reads"] == list(AGGREGATE_READS)
        assert "analyze/v2" in out["reads"]
        assert "whatif/v1" not in out["reads"]


class TestItRidesWithTheDocument:
    def test_the_aggregate_carries_the_composition(self, tmp_path):
        from bga.store_aggregate import aggregate

        rows = [_snapshot(tmp_path, f"s{i}", ["analyze/v2", "store/v1"],
                          duration_us=1_000_000 + i)
                for i in range(3)]
        document = aggregate({"project": "p", "snapshots": rows})
        assert "contract_composition" in document
        assert document["contract_composition"]["sets"][0]["runs"] == 3

    def test_the_schema_declares_it(self):
        """`UX-201`: a field the schema does not declare is a field the
        viewer cannot render and a reader cannot look up."""
        from bga import schemas

        sentence = schemas.description(
            schemas.STORE_AGGREGATE, "contract_composition")
        assert "UX-253" in sentence, sentence
        assert "contract set" in sentence
        # And the sub-fields a reader will actually look up.
        assert "explicit unknown" in schemas.description(
            schemas.STORE_AGGREGATE, "contract_composition.unstamped_runs")


class TestTheRuleIsTheOneThatWasArgued:
    def test_it_does_not_refuse_on_the_version(self):
        """`UX-250`'s rule, which this generalises: refusing on the
        package version would fire on every upgrade, including the
        thirty rounds that moved no contract at all."""
        source = (REPO / "bga/store_aggregate.py").read_text(encoding="utf-8")
        block = source.split("def _contract_composition", 1)[1]
        block = block.split("\ndef ", 1)[0]
        assert "version" not in block, (
            "the composition reads the producer's version; UX-250 settled "
            "that comparability follows contract movement, never the number")

    def test_the_argument_is_written_where_the_rule_is(self):
        """A rule with no argument beside it is re-litigated by the next
        round; this one took a whole item to settle."""
        source = (REPO / "bga/store_aggregate.py").read_text(encoding="utf-8")
        head = source.split("AGGREGATE_READS", 1)[0]
        assert "UX-253" in head and "UX-234" in head and "UX-250" in head, (
            "the contract-set rule no longer cites the two precedents it "
            "was argued against")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
