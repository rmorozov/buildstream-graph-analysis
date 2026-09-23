"""`UX-940`/`UX-990`: which BuildStream version each behaviour claim in
`bga/` and `tools/` was read on.

`tests/bst_claims.json` holds each claim once: where it is written, the
version it was last confirmed against, and where that version's wheel
says it. A claim older than `ci.yml`'s `BST_VERSION` is a warning in
pytest's summary, not a red: nothing but a re-read can clear it, and a
red nobody can clear is what `UX-939` was filed against. A register
that no longer matches the tree is a red, because an edit clears it.
A versioned line that is not a behaviour claim (a fixture's own capture
version, an external convention) is `provenance`, not a claim: named,
so completeness stays per-line, but it does not age.
"""
import copy
import json
import re
import warnings
from pathlib import Path

from tests.unit.test_the_pinned_bst_is_the_documented_one import pinned

REPO = Path(__file__).resolve().parents[2]
REGISTER = REPO / "tests" / "bst_claims.json"
VERSIONED = re.compile(r"\bBuildStream \d+\.\d+\.\d+\b")
FIELDS = {"id", "claim", "sites", "confirmed_on", "confirmed_by", "read"}
PROVENANCE_FIELDS = {"path", "anchor", "reason"}
ROOTS = ("bga", "tools")


class UnconfirmedBehaviourClaim(UserWarning):
    """A claim last read on a BuildStream older than the one CI runs."""


def version(text):
    return tuple(int(part) for part in text.split("."))


def register():
    return json.loads(REGISTER.read_text(encoding="utf-8"))


def claims():
    return register()["claims"]


def provenance():
    return register()["provenance"]


def where(site):
    for number, line in enumerate((REPO / site["path"]).read_text(encoding="utf-8").splitlines(), 1):
        if site["anchor"] in line:
            return f"{site['path']}:{number}"
    return None


def versioned_lines(roots):
    for root in roots:
        for path in (REPO / root).rglob("*.py"):
            rel = str(path.relative_to(REPO))
            for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
                if VERSIONED.search(line):
                    yield rel, number


def unconfirmed(register, pin):
    return [f"{c['id']} ({c['confirmed_on']}) {where(c['sites'][0])}"
            for c in register if version(c["confirmed_on"]) < version(pin)]


def test_every_claim_is_whole():
    register = claims()
    assert register, "the register is empty"
    for claim in register:
        assert set(claim) == FIELDS, f"{claim.get('id')}: fields {sorted(set(claim) ^ FIELDS)}"
        assert claim["sites"], f"{claim['id']}: no site"
        assert re.fullmatch(r"\d+\.\d+\.\d+", claim["confirmed_on"]), claim["id"]
    ids = [c["id"] for c in register]
    assert len(ids) == len(set(ids)), f"duplicate ids: {sorted(ids)}"


def test_every_site_still_carries_its_claim():
    lost = [f"{c['id']}: {s['path']} no longer says {s['anchor']!r}"
            for c in claims() for s in c["sites"]
            if not (REPO / s["path"]).is_file() or where(s) is None]
    assert lost == [], "move the anchor with the sentence, or retire the claim:\n" + "\n".join(lost)


def test_every_provenance_entry_is_whole_and_still_holds():
    entries = provenance()
    for entry in entries:
        assert set(entry) == PROVENANCE_FIELDS, f"{entry.get('path')}: fields {sorted(set(entry) ^ PROVENANCE_FIELDS)}"
    lost = [f"{e['path']} no longer says {e['anchor']!r}"
            for e in entries if not (REPO / e["path"]).is_file() or where(e) is None]
    assert lost == [], "move the anchor with the sentence, or retire the provenance entry:\n" + "\n".join(lost)


def test_every_versioned_line_in_bga_and_tools_is_registered_or_provenance():
    covered = set()
    for c in claims():
        for s in c["sites"]:
            loc = where(s)
            if loc:
                path, _, number = loc.rpartition(":")
                covered.add((path, int(number)))
    for e in provenance():
        loc = where(e)
        if loc:
            path, _, number = loc.rpartition(":")
            covered.add((path, int(number)))
    naming = list(versioned_lines(ROOTS))
    assert naming, "no line in bga/ or tools/ names a BuildStream version - the pattern broke"
    missing = [f"{path}:{number}" for path, number in naming if (path, number) not in covered]
    assert missing == [], f"register or mark provenance in {REGISTER.name}: {missing}"


def test_a_claim_older_than_the_pinned_bst_is_named():
    stale = unconfirmed(claims(), pinned())
    if stale:
        warnings.warn(UnconfirmedBehaviourClaim(
            f"{len(stale)} BuildStream claim(s) last read before ci.yml's {pinned()}; "
            f"re-read each in that wheel and move `confirmed_on` in {REGISTER.name}: "
            + "; ".join(stale)), stacklevel=1)


def test_an_aged_claim_is_the_one_named():
    register = copy.deepcopy(claims())
    register[0]["confirmed_on"] = "2.0.0"
    named = {n.split(" ")[0] for n in unconfirmed(register, pinned())}
    older = {c["id"] for c in register if version(c["confirmed_on"]) < version(pinned())}
    assert register[0]["id"] in named and named == older, (named, older)
