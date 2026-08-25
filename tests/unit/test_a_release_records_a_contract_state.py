"""UX-251: a release records a contract state, and the version is derived.

Measured when this was filed: `bga --version` said `0.1.0`, unmoved
across 29 rounds and 247 scenarios; `git tag` returned nothing; there
was no changelog. A number that has never moved cannot signal that
anything did.

The rule is in `docs/contributing/release-guide.md`: compare the
contract state on the previous release row with the state now, and the
kind falls out — a bumped contract or a removed command is `breaking`,
a new one is `extending`, neither is `patch`. This file checks that the
recorded version increments agree with the recorded states, because a
version somebody picked by feel is a number with no meaning.

The derivation is exercised on synthetic pairs as well as on the real
ledger. With one release row there is no pair to check, and a rule that
only runs once there are two would ship untested and stay untested
until the day it mattered.
"""
import pathlib
import re

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
CHANGELOG = REPO / "CHANGELOG.md"
REVIEWS = REPO / "docs/audits/architecture-review.md"
RELEASE_GUIDE = REPO / "docs/contributing/release-guide.md"

KINDS = ("initial", "breaking", "extending", "patch")

_ROW = re.compile(
    r"^\|\s*\[?(\d+\.\d+\.\d+)\]?[^|]*\|\s*([\d-]+)\s*\|\s*(\d+)\s*\|"
    r"\s*`([0-9a-f]+)`\s*\|\s*(\w+)\s*\|")
_STATE = re.compile(r"```text state\n(.*?)```", re.S)


def _rows():
    rows = []
    for line in CHANGELOG.read_text(encoding="utf-8").splitlines():
        match = _ROW.match(line)
        if match:
            rows.append({"version": match.group(1), "date": match.group(2),
                         "closed_rows": int(match.group(3)),
                         "commit": match.group(4), "kind": match.group(5)})
    return rows


def _states():
    """`{version: {"contracts": [...], "commands": [...]}}`."""
    text = CHANGELOG.read_text(encoding="utf-8")
    states = {}
    for section in text.split("\n## ")[1:]:
        version = section.split(" ", 1)[0].strip()
        block = _STATE.search(section)
        if not block:
            continue
        recorded = {}
        for line in block.group(1).splitlines():
            if ":" in line:
                key, _, rest = line.partition(":")
                recorded[key.strip()] = sorted(rest.split())
        states[version] = recorded
    return states


def _version_tuple(version):
    return tuple(int(part) for part in version.split("."))


def derive(before, after):
    """The kind implied by two recorded states.

    Pure, and deliberately not reading anything: it is the rule, and
    the rule has to be testable against cases the real ledger does not
    contain yet.
    """
    def versions(names):
        return {name.rsplit("/v", 1)[0]: int(name.rsplit("/v", 1)[1])
                for name in names if "/v" in name}

    old_contracts, new_contracts = versions(before["contracts"]), versions(after["contracts"])
    removed = set(old_contracts) - set(new_contracts)
    bumped = {name for name, version in old_contracts.items()
              if name in new_contracts and new_contracts[name] > version}
    gone = set(before["commands"]) - set(after["commands"])
    if removed or bumped or gone:
        return "breaking"
    if (set(new_contracts) - set(old_contracts)
            or set(after["commands"]) - set(before["commands"])):
        return "extending"
    return "patch"


class TestTheLedgerIsWellFormed:
    def test_there_is_at_least_one_release(self):
        assert _rows(), (
            "CHANGELOG.md has no release row this guard can read; the "
            "table is `| version | date | closed rows | `commit` | kind |`")

    def test_every_row_has_a_recorded_state(self):
        states = _states()
        missing = [row["version"] for row in _rows()
                   if row["version"] not in states]
        assert missing == [], (
            f"release(s) with no ```text state``` block: {missing}. The "
            f"derivation reads that block; a row without one records no "
            f"contract state and is a date with a number attached.")

    def test_every_kind_is_one_of_the_four(self):
        wrong = [(row["version"], row["kind"]) for row in _rows()
                 if row["kind"] not in KINDS]
        assert wrong == [], f"unknown release kind(s): {wrong}"

    def test_only_the_oldest_release_may_be_initial(self):
        rows = _rows()
        later = [row["version"] for row in rows[:-1] if row["kind"] == "initial"]
        assert later == [], (
            f"release(s) claiming `initial` with an older release below "
            f"them: {later}")
        assert rows[-1]["kind"] == "initial", (
            "the oldest release row is not `initial`; it has no previous "
            "state to derive from, so it cannot be anything else")

    def test_versions_increase_and_do_not_repeat(self):
        versions = [_version_tuple(row["version"]) for row in _rows()]
        assert versions == sorted(versions, reverse=True), (
            f"release rows are not newest-first: {versions}")
        assert len(set(versions)) == len(versions), "a version is reused"

    def test_the_recorded_state_is_the_real_one_for_the_newest_release(self):
        """The row is a claim about this tree, and this tree can answer."""
        from bga import cli, contracts, tools_dispatch

        newest = _rows()[0]
        state = _states()[newest["version"]]
        assert state["contracts"] == contracts.ids(), (
            f"release {newest['version']} records a contract set that is "
            f"not this tree's:\n  recorded {state['contracts']}\n  real     "
            f"{contracts.ids()}")
        commands = set(tools_dispatch.TOOL_ALIASES)
        for action in cli.create_parser()._subparsers._group_actions:
            if getattr(action, "choices", None):
                commands |= set(action.choices)
        assert state["commands"] == sorted(commands)

    def test_the_package_version_is_the_newest_release(self):
        """Three copies of one number - `bga/__init__.py`,
        `pyproject.toml` and the ledger - which is exactly the shape
        this repository has watched drift five times."""
        from bga import __version__

        newest = _rows()[0]["version"]
        assert __version__ == newest, (
            f"bga.__version__ is {__version__}, the newest release row is "
            f"{newest}")
        pyproject = (REPO / "pyproject.toml").read_text(encoding="utf-8")
        assert f'version = "{newest}"' in pyproject, (
            f"pyproject.toml does not declare {newest}")


class TestTheVersionIsDerived:
    """The rule itself, on cases the ledger does not contain yet.

    Every one of these is a release this repository has not cut. That
    is the point: a derivation first exercised on the day a contract
    breaks is a derivation nobody has ever seen work.
    """

    BASE = {"contracts": ["analyze/v2", "store/v1"],
            "commands": ["analyze", "compare"]}

    def test_an_unchanged_state_is_a_patch(self):
        assert derive(self.BASE, dict(self.BASE)) == "patch"

    def test_a_bumped_contract_is_breaking(self):
        after = {"contracts": ["analyze/v3", "store/v1"],
                 "commands": self.BASE["commands"]}
        assert derive(self.BASE, after) == "breaking"

    def test_a_removed_contract_is_breaking(self):
        after = {"contracts": ["analyze/v2"], "commands": self.BASE["commands"]}
        assert derive(self.BASE, after) == "breaking"

    def test_a_removed_command_is_breaking(self):
        after = {"contracts": self.BASE["contracts"], "commands": ["analyze"]}
        assert derive(self.BASE, after) == "breaking"

    def test_a_new_contract_is_extending(self):
        after = {"contracts": ["analyze/v2", "store/v1", "whatif/v1"],
                 "commands": self.BASE["commands"]}
        assert derive(self.BASE, after) == "extending"

    def test_a_new_command_is_extending(self):
        after = {"contracts": self.BASE["contracts"],
                 "commands": ["analyze", "compare", "whatif"]}
        assert derive(self.BASE, after) == "extending"

    def test_breaking_wins_over_extending(self):
        """A release that both adds and breaks is breaking. The reader
        this protects is the one who upgrades for the new thing."""
        after = {"contracts": ["analyze/v3", "store/v1", "whatif/v1"],
                 "commands": ["analyze", "compare", "blast"]}
        assert derive(self.BASE, after) == "breaking"

    def test_the_ledgers_own_kinds_agree_with_its_states(self):
        rows, states = _rows(), _states()
        wrong = []
        for newer, older in zip(rows, rows[1:]):
            expected = derive(states[older["version"]], states[newer["version"]])
            if newer["kind"] != expected:
                wrong.append(f"{newer['version']}: records {newer['kind']}, "
                             f"its state delta says {expected}")
        assert wrong == [], f"release kind(s) disagreeing with the states: {wrong}"

    def test_the_increment_matches_the_kind(self):
        rows = _rows()
        wrong = []
        for newer, older in zip(rows, rows[1:]):
            new_v, old_v = _version_tuple(newer["version"]), _version_tuple(older["version"])
            minor_moved = new_v[1] > old_v[1]
            if newer["kind"] in ("breaking", "extending") and not minor_moved:
                wrong.append(f"{newer['version']} is {newer['kind']} and did "
                             f"not move MINOR")
            if newer["kind"] == "patch" and minor_moved:
                wrong.append(f"{newer['version']} is a patch and moved MINOR")
        assert wrong == [], wrong


class TestTheReleaseConsumesTheReview:
    """`UX-251` clause 4, and the one argument in Direction 10 that is
    about *not* building something: a release must not become a second
    trigger for documentation review."""

    def test_the_release_guide_says_it_consumes_rather_than_duplicates(self):
        text = RELEASE_GUIDE.read_text(encoding="utf-8")
        assert "consumes the review" in text
        assert "architecture-review.md" in text

    def test_every_release_has_a_review_at_or_after_the_previous_one(self):
        """The documentation half of a release, entirely by reference."""
        review_markers = [
            int(m.group(1)) for m in
            re.finditer(r"^\|\s*\d+\s*\|\s*[\d-]+\s*\|\s*(\d+)\s*\|",
                        REVIEWS.read_text(encoding="utf-8"), re.M)]
        assert review_markers, "the review log has no parseable row"
        rows = _rows()
        unreviewed = []
        for newer, older in zip(rows, rows[1:]):
            if not any(marker >= older["closed_rows"] for marker in review_markers):
                unreviewed.append(
                    f"{newer['version']} was cut with no review at or after "
                    f"closed-row marker {older['closed_rows']}")
        assert unreviewed == [], unreviewed

    def test_the_first_release_names_the_findings_it_carries(self):
        """A release that ships known-open documentation findings says
        so, or "we knew" lives in someone's memory."""
        text = CHANGELOG.read_text(encoding="utf-8")
        assert "Carried findings" in text
        for finding in ("UX-245", "UX-246", "UX-247"):
            assert finding in text, f"{finding} is open and unnamed in the release"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
