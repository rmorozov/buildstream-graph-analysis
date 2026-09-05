"""UX-547: the fixture differ names key order, and names it as order.

`differences()` compared both sides with `json.dumps(sort_keys=True)`,
so a committed fixture could carry a different key order from the one
the analyzer emits and the check stayed green:

```text
emitted   occupancy: ['average_concurrency', ..., 'peak_resource_occupancy']
committed occupancy: ['peak_resource_occupancy', ..., 'average_concurrency']
differences(): []
```

`UX-535` refreshed a fixture and its `git diff` carried a latent
`value`/`resolved` reordering nobody asked for, mixed in with the three
keys it did mean to change. The instrument a round uses to confirm its
change is the only one could not see that axis.

Order is reported, and reported as its own line - a reordered document
is not a document with a different value in it, and a differ that
called every change "order drift" would have discriminated nothing.
Order is still not a contract; `UX-302` owns payload shape.
"""
import functools
import json
import pathlib
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import dev_refresh_analysis as refresh

BLOCK = "occupancy"


@functools.cache
def _emitted():
    """One analyzer run, shared: the harness needs the real document,
    not a hand-written one, or it would be asserting about its own."""
    return refresh.FIXTURES[-1].analysed()


def _stand_in(make_held):
    real = _emitted()
    proto = refresh.FIXTURES[-1]

    class StandIn:
        name, token, into = proto.name, proto.token, proto.into
        analysed = staticmethod(lambda: real)
        committed = staticmethod(lambda: make_held(real))

    return StandIn


def _reordered(real):
    """Same keys, same values, one block written backwards."""
    held = dict(real)
    held[BLOCK] = dict(reversed(list(real[BLOCK].items())))
    return held


def _revalued(real):
    """Same order, one number moved."""
    held = json.loads(json.dumps(real))
    held[BLOCK]["idle_us"] += 1
    return held


def _values(found):
    return [(where, what) for where, what in found
            if refresh.ORDER_DRIFT not in what]


def _orders(found):
    return [(where, what) for where, what in found
            if refresh.ORDER_DRIFT in what]


def test_a_reordered_block_is_named_and_is_not_a_value_difference():
    """The acceptance test: keys reordered, values identical."""
    found = refresh.differences(_stand_in(_reordered))
    assert _orders(found), (
        f"one block reversed and the differ reported {found} - the "
        f"committed order is invisible to it")
    assert [where for where, _ in _orders(found)] == [f"$.{BLOCK}"], found
    assert _values(found) == [], (
        f"a reordering was reported as a difference in value: {found}")


def test_a_changed_value_is_still_a_value_difference():
    """A differ that answers "order drift" to everything has told a
    round nothing about which half of its diff is its own."""
    found = refresh.differences(_stand_in(_revalued))
    assert (BLOCK, "differs") in found, found
    assert _orders(found) == [], (
        f"one number moved and the differ called it order drift: {found}")


@pytest.mark.parametrize(
    "fixture", refresh.FIXTURES, ids=lambda f: f.name.split("/")[-1])
def test_every_committed_fixture_is_in_the_emitted_order(fixture):
    """The decision `UX-547` had to make: the fixtures are held in the
    emitted order, not excused from it. Both were already there when
    this landed (0 sites), so nothing was rewritten; `--write` is what
    puts a drifted one back."""
    drift = refresh.order_drift(fixture.analysed(), fixture.committed())
    assert drift == [], (
        f"{fixture.name} is committed in a different key order from the "
        f"one the analyzer emits, at {[where for where, _, _ in drift]}\n"
        f"    python3 tools/dev_refresh_analysis.py --write {fixture.name}")


class TestTheOrderSurvivesTheLoader:
    """Both sides reach `differences()` through `json.loads`, which
    keeps insertion order on CPython 3.7+. If it ever stopped, the
    order line above would be reading its own construction."""

    def test_the_parse_keeps_the_order_the_text_had(self):
        text = '{"b": 1, "a": 2, "c": {"z": 0, "y": 0}}'
        assert list(json.loads(text)) == ["b", "a", "c"]
        assert list(json.loads(text)["c"]) == ["z", "y"]

    def test_the_committed_file_is_read_in_its_own_order(self):
        fixture = refresh.FIXTURES[-1]
        text = fixture.into.read_text(encoding="utf-8")
        first = [line.split('"')[1] for line in text.splitlines()[1:4]]
        assert list(fixture.committed())[:3] == first
