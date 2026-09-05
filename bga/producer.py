"""UX-249: an artifact says what produced it.

`bga` reads its own past output as input — `@last`/`@prev`, the
baseline set, `cache-trend`, `store-aggregate` all open artifacts
written by whatever `bga` was installed at the time, which on a project
six months old is not the one running now. Measured when this was
filed, `__version__` was read in exactly two places, both the
`--version` string, and written into nothing: a `run-context.json` from
round 3 and one from round 29 were indistinguishable to the tool
reading them both.

This repository is already strict about comparability and strict in the
right way — `bga compare` **refuses** two runs from different hosts
(`UX-186`) and refuses a caches-off run against a caches-on one, with
an exit code of its own, because "not comparable" and "comparable and
equal" must not look alike. Producer identity is the same kind of axis
with nothing watching it.

Two decisions worth stating, because both are the opposite of the
obvious one:

**The whole contract set is recorded, not the subset this artifact
depends on.** Enumerating a document's real dependencies at write time
is easy to get subtly wrong and impossible to correct afterwards; the
full set is unambiguous, is nine short strings, and lets a *reader*
compute whichever subset its question needs. The policy then lives in
one place (`UX-250`) rather than being frozen into every writer.

**The version here is provenance, not compatibility.** Direction 10
argues it out: a single package number is a lossy summary of nine
independent contracts, so comparing versions would refuse across
upgrades that moved nothing. What a reader compares is the contract
set; the version is how a human finds the build that wrote it.
"""
import contextlib
from typing import Optional

from . import __version__

PRODUCER_KEY = "producer"
TOOL = "bga"

# What a reader gets for an artifact written before this landed, which
# is every artifact in every store today. Named rather than `None` at
# each call site: "we do not know" is a state with consequences, and a
# state with consequences deserves a word.
UNSTAMPED = "unstamped"


def stamp() -> dict:
    """The block to write into an artifact that will be re-read.

    Deliberately flat and self-describing. A reader five versions from
    now has this and nothing else.
    """
    from . import contracts

    return {
        "tool": TOOL,
        "version": __version__,
        "contracts": contracts.ids(),
    }


def add(artifact: dict) -> None:
    """Stamp `artifact` in place, the way `add_host_manifest` does.

    Best-effort by the same rule as the host manifest: provenance must
    never fail a capture. A run directory that could not enumerate its
    own contracts is still a run directory, and reads back as
    `UNSTAMPED`, which is a state this codebase handles.
    """
    with contextlib.suppress(Exception):
        artifact[PRODUCER_KEY] = stamp()


def read(artifact: Optional[dict]) -> Optional[dict]:
    """The stamp, or `None` when the artifact predates stamping."""
    if not isinstance(artifact, dict):
        return None
    found = artifact.get(PRODUCER_KEY)
    return found if isinstance(found, dict) else None


def version_of(artifact: Optional[dict]) -> str:
    """The producing version, or `UNSTAMPED`."""
    found = read(artifact)
    version = (found or {}).get("version")
    return version if isinstance(version, str) and version else UNSTAMPED


def contracts_of(artifact: Optional[dict]) -> Optional[list[str]]:
    """The contract set recorded, or `None` if there is no stamp.

    `None` and `[]` are different answers and both occur: no stamp at
    all, versus a stamp written by a build whose enumeration failed.
    Collapsing them would let the second read as agreement with
    anything.
    """
    found = read(artifact)
    if found is None:
        return None
    recorded = found.get("contracts")
    if not isinstance(recorded, list):
        return None
    return [name for name in recorded if isinstance(name, str)]


def describe(artifact: Optional[dict]) -> str:
    """One phrase for a report line."""
    found = read(artifact)
    if found is None:
        return f"{UNSTAMPED} (written before {TOOL} recorded its own version)"
    tool = found.get("tool") or "unknown tool"
    return f"{tool} {version_of(artifact)}"


# What a comparison of two runs actually reads. Contract movement
# *outside* this set is real and is still not a reason to refuse two
# runs a `compare` never touches - `whatif/v1` moving does not make two
# durations incomparable. Named rather than "every contract", because
# refusing on everything is how a refusal that fires constantly gets
# switched off, and a switched-off refusal is worth less than none.
COMPARISON_CONTRACTS = ("analyze/v2", "compare/v1", "host/v1")   # UX-288


def _by_name(names):
    return {name.rsplit("/v", 1)[0]: name for name in names if "/v" in name}


def comparison_movement(baseline: Optional[dict],
                        candidate: Optional[dict]) -> list[str]:
    """Contracts a comparison reads that moved between two producers.

    Empty when the two agree, when either is unstamped, or when the
    only contracts that moved are ones a comparison never opens.

    The unstamped case returns empty **deliberately**: every artifact
    written before `UX-249` lacks a stamp, and refusing them would make
    the feature's arrival delete everyone's history. `describe` is what
    names the absence; this only answers "did something a comparison
    depends on change".
    """
    before, after = contracts_of(baseline), contracts_of(candidate)
    if not before or not after:
        return []
    old, new = _by_name(before), _by_name(after)
    relevant = {name.rsplit("/v", 1)[0] for name in COMPARISON_CONTRACTS}
    return sorted(
        f"{old[name]} → {new[name]}"
        for name in relevant & set(old) & set(new)
        if old[name] != new[name])


def comparison_note(baseline: Optional[dict],
                    candidate: Optional[dict]) -> Optional[str]:
    """The sentence for a pair whose producers differ but still compare.

    `None` when both are stamped by the same version - the common case,
    and one nobody needs a line about.
    """
    before, after = version_of(baseline), version_of(candidate)
    if before == after and before != UNSTAMPED:
        return None
    if before == UNSTAMPED and after == UNSTAMPED:
        return ("neither run records which `bga` measured it (both predate "
                "the producer stamp), so whether one tool measured both "
                "cannot be checked")
    if UNSTAMPED in (before, after):
        which = "baseline" if before == UNSTAMPED else "candidate"
        return (f"the {which} does not record which `bga` measured it, so "
                f"whether one tool measured both cannot be checked")
    return (f"measured by different builds ({before} and {after}); no "
            f"contract a comparison reads moved between them")
