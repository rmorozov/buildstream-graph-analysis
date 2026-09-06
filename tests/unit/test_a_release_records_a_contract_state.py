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


# `UX-686`: the candidate is over-approximated on purpose - the files
# backing `bga.contracts.inventory()` plus the command surface, so
# touching `schemas.py` without moving a `/vN` still counts. Bisecting
# `contracts.ids()` for the exact commit is cheaper to state and more
# expensive to run, and is not worth it here.
_CANDIDATE_FILES = ("bga/bundle.py", "bga/hostinfo.py", "bga/plane2.py",
                    "bga/run_store.py", "bga/schemas.py", "bga/sources.py",
                    "bga/cli.py", "bga/tools_dispatch.py")
_WALK_DATE = re.compile(r"Base\s+`[0-9a-f]{7,40}`,\s*(\d{4}-\d{2}-\d{2})")
_FINDINGS_BLOCK = re.compile(r"(?ms)^findings\s+(.*?)^rows added\s")
_FILED = re.compile(r"→\s*(UX-\d+)")


def candidate_commit_date():
    """`%cs` of the newest commit over `_CANDIDATE_FILES` - `git log -1`,
    over-approximated on purpose (`UX-686`)."""
    code, out = _git("log", "-1", "--format=%cs", "--", *_CANDIDATE_FILES)
    assert code == 0 and out, "no commit touches the candidate file set"
    return out


def walk_covers_candidate(candidate_date, walk_date, filed, closed, carried):
    """The release guide's third condition, pure (`UX-686`): a walk at
    or after the candidate, and every finding it filed closed or
    carried (named in the release's CHANGELOG row)."""
    if walk_date < candidate_date:
        return False
    return all(name in closed or name in carried for name in filed)


class TestTheWalkGateIsDerived:
    """Synthetic pairs, on cases the real ledger does not contain yet -
    no release has been cut through this condition (`UX-686`)."""

    def test_a_walk_before_the_candidate_refuses(self):
        assert walk_covers_candidate(
            "2026-09-06", "2026-09-05", set(), set(), set()) is False

    def test_a_walk_on_the_candidates_date_clears_it(self):
        assert walk_covers_candidate(
            "2026-09-06", "2026-09-06", set(), set(), set()) is True

    def test_a_walk_after_with_its_finding_closed_passes(self):
        assert walk_covers_candidate(
            "2026-09-06", "2026-09-07", {"UX-1"}, {"UX-1"}, set()) is True

    def test_an_open_unnamed_finding_refuses(self):
        assert walk_covers_candidate(
            "2026-09-06", "2026-09-07", {"UX-1"}, set(), set()) is False

    def test_an_open_finding_named_in_the_changelog_passes(self):
        assert walk_covers_candidate(
            "2026-09-06", "2026-09-07", {"UX-1"}, set(), {"UX-1"}) is True


class TestTheReleaseConsumesTheWalk:
    """`UX-686`'s third condition. `UX-727` defers the design-review
    half a walk's report also promises, so this reads the walk only."""

    def test_the_release_guide_names_the_walk_condition(self):
        text = RELEASE_GUIDE.read_text(encoding="utf-8")
        assert "UX-685" in text
        assert "walk" in text.lower()

    def test_the_candidate_commit_is_computable(self):
        assert re.fullmatch(r"\d{4}-\d{2}-\d{2}", candidate_commit_date())

    def test_a_walk_reports_date_and_filings_are_read_from_the_real_tree(self):
        """`is_walk_report`/`audits_documents` (`UX-685`) pick the shape
        and the tracked set; this adds the date and `→ UX-NNN`
        filings on top of both real reports, not reimplemented."""
        from tools.dev_scenario import audits_documents, is_walk_report

        reports = {path: text for path, text in audits_documents()
                   if is_walk_report(text)}
        assert reports, "no walk report under docs/audits/"
        found = {}
        for path, text in reports.items():
            date = _WALK_DATE.search(text)
            assert date, f"{path}: no `Base \\`<hash>\\`, <date>` line"
            block = _FINDINGS_BLOCK.search(text)
            assert block, f"{path}: no findings block"
            found[path] = (date.group(1), set(_FILED.findall(block.group(1))))
        assert found.get("docs/audits/walk-seed-1.md") == ("2026-09-06", {"UX-723"})
        assert found.get("docs/audits/walk-seed-2.md") == (
            "2026-09-06", {"UX-724", "UX-725"})

    def test_every_filed_finding_resolves_to_exactly_one_backlog_row(self):
        """The status half `walk_covers_candidate` needs, derived. Which
        of the two indexes a filing sits in is today's state and moves
        the day it closes; that it sits in exactly one of them is the
        claim - a filing in neither was lost, and one in both is a row
        the move left behind."""
        from tools.dev_scenario import audits_documents, is_walk_report

        indexes = {name: (REPO / f"docs/backlog/scenarios/{name}").read_text(
            encoding="utf-8") for name in ("README.md", "closed.md")}
        filed = set()
        for _, text in audits_documents():
            block = _FINDINGS_BLOCK.search(text) if is_walk_report(text) else None
            if block:
                filed |= set(_FILED.findall(block.group(1)))
        assert filed, "no walk report filed a finding"
        for name in sorted(filed):
            rows = [index for index, text in indexes.items()
                    if re.search(rf"^\| {name} \|", text, re.M)]
            assert len(rows) == 1, f"{name} has rows in {rows or 'neither index'}"


#: `UX-637`: a shallow clone answers reachability from a history that
#: stops at a boundary, and says so to nobody. `UX-633` was filed, a
#: user decision was taken and an exemption shipped on exactly that -
#: `v0.2.0` read as unreachable here and reachable on CI, and CI was
#: right. The clauses below refuse to conclude rather than conclude
#: from a truncated history.
def _shallow():
    return _git("rev-parse", "--is-shallow-repository")[1] == "true"


def _reaches(commit):
    """Is `commit` an ancestor of `HEAD`? By the definition, not the
    predicate: `merge-base` hands back a value the message can carry,
    and `--is-ancestor` only an exit code."""
    code, out = _git("merge-base", commit, "HEAD")
    return (code == 0 and out == commit), (out or "no common ancestor")


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
        if _shallow():
            pytest.skip(
                "this checkout is shallow, so its history stops at a "
                "boundary and reachability here is not the tree's answer")
        unreachable = []
        for row in _rows():
            tag = f"v{row['version']}"
            at = _git("rev-parse", f"{tag}^{{commit}}")[1]
            reaches, base = _reaches(at)
            if not reaches:
                unreachable.append(f"{tag} -> {at} (merge-base: {base})")
        assert unreachable == [], (
            f"release tag(s) naming a commit no clone of this branch can "
            f"reach: {unreachable}. Either the tag moves, or it joins "
            f"UNREACHABLE_BY_DECISION with its reason")

    def test_ci_asks_for_the_history_this_class_reads(self):
        """`UX-637`: the clause above skips on a shallow clone, so the
        machine that runs every commit must not have one. Without
        `fetch-depth: 0` this class would be green everywhere and check
        reachability nowhere - `UX-213`'s shape, one door along from the
        `fetch-tags` clause above."""
        workflow = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        assert "fetch-depth: 0" in workflow, (
            "ci.yml's checkout does not ask for the whole history, so the "
            "reachability clause skips on CI and guards nothing there")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
