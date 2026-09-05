"""UX-389: fourteen of twenty-five Plane 2 blocks reached no browser.

Counted against an all-planes capture of
`examples/06-macro-micro-optimization` when this was filed:

```text
plane2 blocks in the capture            25
  a key in analyze/v4                    6
  reaching the page through the join     6
  terminal only                         14
```

The fourteen were the *did the instrument see everything* questions -
whether the ptrace spine ran, how many processes were traced, how long
the hook was watching, which elements could be hiding a static binary.
A reader in a browser saw a per-element attribution table with no way
to learn that `spine_policy.policy` was `off`, so every CPU figure
under it was a floor rather than a measurement. `UX-107` made that
distinction law for a *process*; nothing had applied it to the capture.

The gap grew every round because nothing held the two ends together:
`UX-370` carried three blocks, `UX-383` three more, and `UX-385` added
a fifteenth terminal-only block in the same round this was filed.

**Three destinations, and silence is not one of them.** Every block of
a `plane2/v3` report declares one in `bga/plane2.py`: a key of
`analyze/v4`, a field on an `element_join` row (`UX-382`'s placement
rule), or terminal-only *with the reason written down*. This file is
what makes the declaration binding - and it reads the blocks off a real
committed report rather than off the list, so the next block added to
the capture arrives with no entry and fails here.
"""
import json
import os
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from bga import plane2

REPORT = REPO / "tests/fixtures/macro_micro/plane2.json"
RUN = REPO / "tests/fixtures/macro_micro/run"


@pytest.fixture(scope="module")
def report():
    return json.loads(REPORT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def payload():
    done = subprocess.run(
        [sys.executable, "-m", "bga.cli", "analyze", str(RUN),
         "--format", "json"],
        capture_output=True, text=True, cwd=REPO, timeout=180,
        env=dict(os.environ, PYTHONPATH=str(REPO)))
    assert done.returncode == 0, done.stderr[-3000:]
    return json.loads(done.stdout)


def _resolve(payload, path):
    """The value at a dotted payload path, or `KeyError`'s stand-in."""
    node = payload
    for step in path.split("."):
        if not isinstance(node, dict) or step not in node:
            return None
        node = node[step]
    return node


class TestTheInventoryCoversTheReport:
    def test_every_block_the_capture_writes_has_an_entry(self, report):
        """Read off the report, not off the list.

        A guard that only sees what it was told about cannot catch the
        next instance of the defect it was written for - which is
        exactly how `commands_not_observed` became the fifteenth
        terminal-only block.
        """
        missing = sorted(set(report) - set(plane2.DESTINATIONS)
                         - {"schema", plane2.RECORDS_KEY})
        assert missing == [], (
            f"{len(missing)} Plane 2 block(s) with no declared "
            f"destination: {missing}. Say where each one goes - a "
            f"payload key, a join field, or terminal-only with the "
            f"reason - in `bga/plane2.py`")

    def test_the_inventory_names_nothing_the_report_lacks(self, report):
        """The other direction: a stale entry is a lie about the capture.

        `resource_pressure` is the deliberate exception - `UX-379` added
        it to the hook and this fixture predates the rusage fields, so
        it is declared and absent here.
        """
        stale = sorted(set(plane2.DESTINATIONS) - set(report)
                       - {"resource_pressure"})
        assert stale == [], (
            f"declared destinations for blocks no capture writes: {stale}")

    def test_every_destination_is_one_of_three(self):
        kinds = {kind for kind, _where, _why in plane2.DESTINATIONS.values()}
        assert kinds <= {plane2.PAYLOAD, plane2.JOIN, plane2.TERMINAL}

    def test_a_terminal_only_block_carries_its_reason(self):
        """Silence is what produced fourteen.

        A wildcard "the rest is terminal-only" would pass every other
        clause here and give a reader nothing, so each entry states why
        that block stops at the terminal.
        """
        for block, (kind, where, why) in plane2.DESTINATIONS.items():
            if kind != plane2.TERMINAL:
                continue
            assert not where, (block, where)
            assert len(why.split()) >= 12, (
                f"`{block}` is declared terminal-only with a reason of "
                f"{len(why.split())} words: {why!r}")


class TestTheDeclaredDestinationsAreReal:
    """A declaration nothing checks is a comment. These resolve it."""

    def test_every_payload_destination_resolves(self, payload, report):
        """Only for the blocks this capture actually wrote.

        `resource_pressure` is declared and absent here - the fixture
        predates `UX-379`'s rusage fields - so asking the payload for
        it would be asking the carry to invent one.
        """
        unresolved = []
        for block, (kind, where, _why) in plane2.DESTINATIONS.items():
            if kind != plane2.PAYLOAD or report.get(block) is None:
                continue
            if _resolve(payload, where) is None:
                unresolved.append(f"{block} -> {where}")
        assert unresolved == [], (
            f"declared to reach the payload and did not: {unresolved}")

    def test_every_join_destination_is_a_field_of_a_row(self, payload):
        rows = payload.get("element_join") or []
        assert rows, "the fixture no longer joins the two planes"
        fields = set().union(*(set(row) for row in rows))
        for block, (kind, where, _why) in plane2.DESTINATIONS.items():
            if kind != plane2.JOIN:
                continue
            assert where in fields, (
                f"`{block}` is declared to land on `element_join[].{where}`, "
                f"which no row carries")


class TestTheCaptureSaysWhatItCouldSee:
    """The six blocks the Required Fix puts first, in the payload."""

    #: Each one, and the question it answers about the *instrument*
    #: rather than about the build.
    ASKED = {
        "spine_policy": "did the ptrace spine run",
        "process_count": "how many processes were traced at all",
        "max_concurrency": "what peak parallelism the hook observed",
        "wall_span_us": "how long the hook was watching",
        "static_census": "which elements could hide a static binary",
    }

    def test_they_are_in_the_coverage_block(self, payload):
        coverage = payload["plane2_coverage"]
        for key in self.ASKED:
            assert key in coverage, (
                f"`{key}` still reaches no browser - it answers "
                f"\"{self.ASKED[key]}\", which changes how every number "
                f"under it is read")

    def test_the_spine_policy_is_the_one_this_capture_ran(self, payload):
        """Not a placeholder: this fixture's spine really was off.

        Which is the case that matters - a reader of its CPU figures is
        looking at the hook's floor, and until now the page could not
        tell them so.
        """
        assert payload["plane2_coverage"]["spine_policy"] == {
            "policy": "off", "sandboxes": 9, "spine_traced": 0}

    def test_the_two_caveats_travel_with_what_they_qualify(self, payload):
        """A number whose caveat stayed behind is the same defect."""
        coverage = payload["plane2_coverage"]
        assert "excluded from max_concurrency" in coverage["open_records_note"]
        assert "LD_PRELOAD" in coverage["static_binary_disclaimer"]

    def test_the_span_is_microseconds_like_every_other_duration(self, payload):
        """`wall_span_s` is renamed on the way in, and converted.

        The payload has one unit for a duration, and a key spelling
        `_s` beside neighbours spelling `_us` is the label `UX-351` is
        about.
        """
        report = json.loads(REPORT.read_text(encoding="utf-8"))
        assert payload["plane2_coverage"]["wall_span_us"] == round(
            report["wall_span_s"] * 1_000_000)

    def test_the_census_leaves_its_per_element_working_behind(self, payload):
        """`UX-288`, on a map that would be the element population again.

        `static_census.per_element` is one bookkeeping record per
        element - the census's working, not its answer.
        `elements_at_risk` is what the block exists to say.
        """
        census = payload["plane2_coverage"]["static_census"]
        assert "elements_at_risk" in census
        assert "per_element" not in census

    def test_a_report_without_a_block_publishes_no_empty_one(self):
        """`UX-388`'s distinction, at the carry.

        Absent is not empty: a capture that never ran the census must
        not gain a census key saying nothing.
        """
        assert plane2.coverage_additions({"process_count": 7}) == {
            "process_count": 7}
        assert plane2.coverage_additions({}) == {}
        assert plane2.coverage_additions(None) == {}
