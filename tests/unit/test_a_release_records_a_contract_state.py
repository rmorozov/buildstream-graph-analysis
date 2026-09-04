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
import hashlib
import pathlib
import re
import subprocess

import pytest

REPO = pathlib.Path(__file__).resolve().parents[2]
CHANGELOG = REPO / "CHANGELOG.md"
REVIEWS = REPO / "docs/audits/architecture-review.md"
RELEASE_GUIDE = REPO / "docs/contributing/release-guide.md"

KINDS = ("initial", "breaking", "extending", "patch")

# `UX-339` dropped the `commit` column, for the reason `UX-332` dropped
# it from the review log: the one hash it carried was not reachable from
# `origin/main`, so it named a commit on one machine. A release row also
# cannot carry its own commit's hash, because the hash covers the row.
_ROW = re.compile(
    r"^\|\s*\[?(\d+\.\d+\.\d+)\]?[^|]*\|\s*([\d-]+)\s*\|\s*(\d+)\s*\|"
    r"\s*(\w+)\s*\|")
_STATE = re.compile(r"```text state\n(.*?)```", re.S)


def _rows():
    rows = []
    for line in CHANGELOG.read_text(encoding="utf-8").splitlines():
        match = _ROW.match(line)
        if match:
            rows.append({"version": match.group(1), "date": match.group(2),
                         "closed_rows": int(match.group(3)),
                         "kind": match.group(4)})
    return rows


#: What a state block records. The digest covers these, in this order,
#: so a reordering is not a change and an edit is.
STATE_KEYS = ("contracts", "commands")


def state_digest(recorded):
    """`UX-550`: twelve hex characters over one release's recorded state."""
    payload = "\n".join(f"{key}: {' '.join(sorted(recorded[key]))}"
                        for key in STATE_KEYS)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:12]


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
            "table is `| version | date | closed rows | kind |`")

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

    def test_a_superseded_release_is_frozen_by_a_digest(self):
        """`UX-550`: the newest row is checked against the tree, which
        is satisfiable two ways - cut a release, or rewrite the last
        row. For five rounds the second was cheaper: `0.3.0`'s block
        was edited by five commits, none of them a release, and five
        contracts that did not exist on its date ended up inside it. A
        row stops being the newest and gains a digest; an edit after
        that reddens.
        """
        states = _states()
        missing = [row["version"] for row in _rows()[1:]
                   if "digest" not in states[row["version"]]]
        assert missing == [], (
            f"superseded release(s) recording no digest: {missing}. A "
            f"released row is frozen when the next one is cut - see "
            f"docs/contributing/release-guide.md")

    def test_a_superseded_releases_state_matches_its_digest(self):
        """The mutation the clause above cannot see on its own: the
        contract list edited after the release shipped.

        The digest does not make the block unwritable - nothing in a
        text file is - but it makes an edit fail rather than pass, and
        rewriting it too is a deliberate act rather than the cheapest
        path.
        """
        states = _states()
        wrong = []
        for row in _rows()[1:]:
            recorded = states[row["version"]]
            if "digest" not in recorded:
                continue
            real = state_digest(recorded)
            if recorded["digest"] != [real]:
                wrong.append(
                    f"{row['version']}: records digest "
                    f"{' '.join(recorded['digest'])}, its state hashes to "
                    f"{real}")
        assert wrong == [], (
            f"a shipped release's recorded state has been edited since it "
            f"was written: {wrong}")

    def test_the_newest_release_carries_no_digest(self):
        """The decision, asserted rather than assumed. The newest row is
        the one the tree answers for, so freezing it as well would give
        that check a second way to be satisfied - edit the state, edit
        the digest - which is the defect this item was filed for.
        """
        newest = _rows()[0]["version"]
        assert "digest" not in _states()[newest], (
            f"release {newest} is the newest row and carries a digest; "
            f"when the tree moves past it the answer is a new row")

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


#: `UX-633`: tags kept on purpose whose commit `main` cannot reach.
#: `v0.2.0` names `3ebe7e1b5` - a lineage that set `0.2.0` and never
#: merged; `pyproject.toml` enters this history at `bc15935`, which
#: sets `0.3.0`. Named here rather than excluded behind a version
#: floor, which would swallow the next one silently.
UNREACHABLE_BY_DECISION = {"v0.2.0"}


def _git(*argv):
    done = subprocess.run(("git",) + argv, capture_output=True, text=True,
                          cwd=REPO, timeout=60)
    return done.returncode, done.stdout.strip()


class TestEveryVersionedReleaseIsTagged:
    """`UX-597`: step 8 of the release guide cuts a tag, and until this
    round nothing read one - so it went unexecuted for three releases.

    Reachability is a clause of its own because `UX-339` removed the
    review log's commit column for exactly this: a ref that names a
    commit no clone can reach is a ref that names one machine.
    """

    def _require_tags(self):
        code, out = _git("tag", "--list", "v*")
        if code != 0 or not out:
            pytest.skip(
                "this checkout carries no release tag, so there is nothing "
                "to read; CI fetches them (the clause below holds that)")
        return out.splitlines()

    def test_ci_asks_for_the_tags_this_class_reads(self):
        """Without `fetch-tags`, `actions/checkout` brings none, every
        clause below skips, and the class is green on the one machine
        that cannot check it - `UX-213`'s shape."""
        workflow = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        assert "fetch-tags: true" in workflow, (
            "ci.yml's checkout does not ask for tags, so the release-tag "
            "clauses skip on CI and guard nothing there")

    def test_there_is_more_than_one_row_to_check(self):
        """Non-vacuity: with one row the clauses below are one assertion
        about one string, and an empty list passes all of them."""
        assert len(_rows()) >= 2, (
            f"only {len(_rows())} release row(s); the clauses below are "
            f"not exercised")

    def test_every_versioned_release_has_its_tag(self):
        tags = set(self._require_tags())
        missing = [row["version"] for row in _rows()
                   if f"v{row['version']}" not in tags]
        assert missing == [], (
            f"release row(s) with no tag: {missing}. Release guide step 8 "
            f"cuts `v<version>` on the commit that sets it")

    def test_every_tag_names_the_commit_that_set_its_version(self):
        self._require_tags()
        wrong = []
        for row in _rows():
            tag = f"v{row['version']}"
            code, text = _git("show", f"{tag}:pyproject.toml")
            found = re.search(r'^version = "(.*)"', text, re.M)
            if code != 0 or not found:
                wrong.append(f"{tag}: no pyproject.toml at that commit")
            elif found.group(1) != row["version"]:
                wrong.append(
                    f"{tag} names a commit whose pyproject.toml says "
                    f"{found.group(1)}, not {row['version']}")
        assert wrong == [], wrong

    def test_every_release_tag_is_reachable_from_here(self):
        """A tag on a commit this history cannot reach hands a reader
        code that was never shipped (`UX-339`)."""
        self._require_tags()
        unreachable = []
        for row in _rows():
            tag = f"v{row['version']}"
            if tag in UNREACHABLE_BY_DECISION:
                continue
            code, _ = _git("merge-base", "--is-ancestor", tag, "HEAD")
            if code != 0:
                unreachable.append(tag)
        assert unreachable == [], (
            f"release tag(s) naming a commit no clone of this branch can "
            f"reach: {unreachable}. Either the tag moves, or it joins "
            f"UNREACHABLE_BY_DECISION with its reason")

    def test_each_named_exception_still_needs_naming(self):
        """`UX-633`: an exemption that has stopped applying is a hole in
        the clause above wearing a reason. It comes out when it does."""
        tags = set(self._require_tags())
        stale = []
        for tag in sorted(UNREACHABLE_BY_DECISION):
            if tag not in tags:
                stale.append(f"{tag}: named here and no such tag")
            elif _git("merge-base", "--is-ancestor", tag, "HEAD")[0] == 0:
                stale.append(f"{tag}: reachable now, so drop the exemption")
        assert stale == [], stale


#: `UX-634`: where a release section's head stops. Everything above it
#: is what the GitHub release description is cut from.
_HEAD_ENDS = "**Contract delta:**"

#: A head longer than this is not a description a reader skims - the
#: three shipped heads measure 9, 16 and 6 non-blank lines.
MAX_HEAD_LINES = 24


def _release_heads():
    """`{version: [lines]}` - each section's prose head, title excluded."""
    text = CHANGELOG.read_text(encoding="utf-8").splitlines()
    heads, version, collecting = {}, None, False
    for line in text:
        found = re.match(r"^## (\d+\.\d+\.\d+) ", line)
        if found:
            version, collecting = found.group(1), True
            heads[version] = []
            continue
        if version is None or not collecting:
            continue
        if line.startswith(_HEAD_ENDS) or line.startswith("## "):
            collecting = False
            continue
        heads[version].append(line)
    return heads


class TestEveryReleaseCarriesItsOwnDescription:
    """`UX-634`: step 8 publishes the head step 5 wrote.

    The description is **cut** from `CHANGELOG.md`, so what this checks
    is that there is something to cut: a section opening with a table
    or a bare list leaves the publisher writing a second copy, which is
    the drift `UX-252` refused for the body.
    """

    def test_the_guide_says_the_description_is_cut_not_written(self):
        text = RELEASE_GUIDE.read_text(encoding="utf-8")
        assert "GitHub release" in text, (
            "the release guide never mentions publishing the tag, so step 8 "
            "stops at a bare ref (`UX-634`)")
        assert re.search(r"cut from\s+`CHANGELOG\.md`", text), (
            "the guide does not say the description is cut from CHANGELOG.md; "
            "without that it is a second copy that drifts (`UX-252`)")

    def test_every_release_section_has_a_head_to_cut(self):
        heads = _release_heads()
        assert heads, "no release section parsed out of CHANGELOG.md"
        empty = [version for version, lines in heads.items()
                 if not any(line.strip() for line in lines)]
        assert empty == [], (
            f"release section(s) with no prose head: {empty}. Step 5 writes "
            f"one and step 8 publishes it")

    def test_a_head_opens_with_prose_rather_than_a_table(self):
        """A section whose first non-blank line is a table row or a list
        item has nothing a release description can open with."""
        offenders = []
        for version, lines in _release_heads().items():
            first = next((line for line in lines if line.strip()), "")
            if first.startswith(("|", "- ", "* ", "#", "```")):
                offenders.append(f"{version}: {first[:40]!r}")
        assert offenders == [], offenders

    def test_a_head_is_short_enough_to_be_a_description(self):
        long = {version: len([ln for ln in lines if ln.strip()])
                for version, lines in _release_heads().items()
                if len([ln for ln in lines if ln.strip()]) > MAX_HEAD_LINES}
        assert long == {}, (
            f"release head(s) over {MAX_HEAD_LINES} non-blank lines: {long}. "
            f"That is a body, and step 6 generates the body")

    def test_more_than_one_head_is_being_checked(self):
        """Non-vacuity: an empty parse passes all three clauses above."""
        assert len(_release_heads()) >= 2, (
            f"only {len(_release_heads())} release head(s) parsed; the "
            f"clauses above are not exercised")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
