"""UX-248: the set of contracts is derived, and two methods agree on it.

`schemas.names()` lists what `bga --schema` can print. That is not the
same set as what `bga` *writes*, and the difference cost nine rounds of
invisibility: `sources/v1` is written to `sources.json` in every run
directory and read back by `load_inventory`, and it appeared in no
registry, no guard and no document.

`bga.contracts.inventory()` derives the set at runtime, from the
package. This file derives it a *second* way — by scanning the source
text for `"<name>/vN"` literals — and asserts the two agree. Two
independent derivations agreeing is worth more than one, and it is the
only way to catch a contract that is stamped by a string literal
nobody bound to a `SCHEMA` constant.
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]

_LITERAL = re.compile(r'"([a-z][a-z0-9-]*/v\d+)"')

# Contract-shaped strings that are not this tool's contracts. Each is a
# shape `bga` *reads* or converts, owned elsewhere - inventorying them
# would claim we version them, which we do not.
NOT_OURS = {
    # The spec's own internal document versions (`trace/v9`,
    # `analysis/v9`): they are the spec's, and Part 32.5 exists
    # precisely because they are not what a consumer pins.
}


def _scanned():
    """`{contract id: files that mention it}` from the source text."""
    found = {}
    for root in ("bga", "tools"):
        for path in sorted((REPO / root).rglob("*.py")):
            for match in _LITERAL.finditer(path.read_text(encoding="utf-8")):
                found.setdefault(match.group(1), set()).add(
                    path.relative_to(REPO).as_posix())
    return {k: v for k, v in found.items() if k not in NOT_OURS}


class TestTheInventoryIsComplete:
    def test_it_finds_more_than_the_printable_registry(self):
        """The measurement this item was filed on. If these ever became
        equal the module would be redundant - and it would mean every
        on-disk shape had become a printable document, which is a
        decision, not a drift."""
        from bga import contracts

        assert len(contracts.ids()) > len(contracts.printable()), (
            "the inventory has stopped covering anything the registry "
            "does not; either a contract was lost or one was promoted")
        assert contracts.unprintable() == ["host/v1", "sources/v1"]

    def test_every_id_in_the_source_is_in_the_inventory(self):
        """The direction that failed before `UX-248`: a contract
        stamped in a module nobody registered."""
        from bga import contracts

        missing = sorted(set(_scanned()) - set(contracts.ids()))
        assert missing == [], (
            f"contract id(s) stamped in the source and absent from "
            f"bga.contracts.inventory(): "
            f"{ {name: sorted(_scanned()[name]) for name in missing} }")

    def test_the_inventory_names_nothing_the_source_does_not(self):
        """The other direction: a retired contract still declared."""
        from bga import contracts

        stale = sorted(set(contracts.ids()) - set(_scanned()))
        assert stale == [], (
            f"bga.contracts.inventory() names contract(s) no source file "
            f"stamps: {stale}")

    def test_every_contract_names_what_owns_it(self):
        from bga import contracts

        for name, owner in sorted(contracts.inventory().items()):
            assert owner.startswith("bga."), f"{name}: {owner}"
            module = REPO / (owner.replace(".", "/") + ".py")
            assert module.exists(), f"{name} claims {owner}, which is not a file"

    def test_an_id_that_is_not_versioned_is_not_a_contract(self):
        """`CONTRACT_ID` is the shape, and the `/vN` is the load-bearing
        half: an id that cannot say it moved is not something a release
        can record a state of."""
        from bga import contracts

        assert contracts.CONTRACT_ID.match("analyze/v2")
        assert contracts.CONTRACT_ID.match("store-aggregate/v12")
        assert not contracts.CONTRACT_ID.match("analyze")
        assert not contracts.CONTRACT_ID.match("analyze/v")
        assert not contracts.CONTRACT_ID.match("Analyze/v1")


class TestTheDerivationIsNotAList:
    def test_a_new_module_declaring_a_schema_joins_without_being_listed(
            self, tmp_path, monkeypatch):
        """The property that makes this different from what it replaced.

        A hand-kept union covers the contracts someone remembered; this
        covers the ones that exist. Proven by creating a module inside
        the package at runtime and confirming the inventory grows.
        """
        import bga
        from bga import contracts

        planted = pathlib.Path(bga.__path__[0]) / "zz_probe_contract.py"
        planted.write_text('SCHEMA = "probe/v3"\n', encoding="utf-8")
        try:
            assert "probe/v3" in contracts.ids(), (
                "a module declaring SCHEMA did not join the inventory - "
                "the derivation is not deriving")
            assert contracts.inventory()["probe/v3"] == "bga.zz_probe_contract"
        finally:
            planted.unlink()
            import sys
            sys.modules.pop("bga.zz_probe_contract", None)

        assert "probe/v3" not in contracts.ids(), (
            "the probe outlived its file, so the inventory is cached and "
            "this test would pass against a stale answer")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
