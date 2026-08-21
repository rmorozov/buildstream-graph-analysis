"""UX-171: which repository feeds which elements, and what a commit to it costs.

Every blast question this tool could answer started at an element:
"change `core.bst`, and 84 things rebuild". The question a monorepo
actually raises starts one level lower - *"this repo was touched: how
many recipes rebuild?"* - and nothing answered it.

The mechanism, which is why this is worth computing rather than
guessing:

- A **`git` source keys on its ref**. `directory:` says where in the
  sandbox the checkout is staged, not which part of the repository is
  read, so twenty elements sourcing one url with twenty different
  `directory:` values all take a new cache key from *any* commit to
  that repository - including one that touched none of the files they
  stage.
- A **`local` source keys on content**. Only the elements whose staged
  directories contain the touched files rebuild.

The same monorepo consumed those two ways differs by an order of
magnitude in blast, the `.bst` files record which way it is consumed,
and nothing here needs the network or a build to find out.

Everything in this module is a pure function over already-parsed data:
the element YAML the census reader already produces, and the graph the
run directory already carries. `tools/bst_extract_run.py` writes the
inventory into the run directory at extract time, which is the one
moment the project and the run are both in hand.
"""
from typing import Dict, Iterable, List, Optional, Set, Tuple

SCHEMA = "sources/v1"

# How BuildStream keys each source kind, which is what decides blast.
#
# "ref": the source has a ref (a commit, a checksum, a version) that is
#     part of the cache key as a whole. Every element sourcing it
#     rebuilds when that ref moves, whatever it stages from it.
# "content": the key is computed from the staged files themselves, so
#     the blast is exactly the elements whose files changed.
#
# Kinds absent from this map are reported with keying "unknown" rather
# than assumed either way - guessing here would turn a blast estimate
# into a fabrication, and the count of unknown kinds is reported.
KEYING_BY_KIND: Dict[str, str] = {
    # Core BuildStream plugins.
    "git": "ref",
    "bzr": "ref",
    "tar": "ref",
    "zip": "ref",
    "remote": "ref",
    "deb": "ref",
    "pip": "ref",
    "local": "content",
    "patch": "content",
    "workspace": "content",
    # buildstream-plugins, widely used and keyed the same way.
    "git_repo": "ref",
    "git_tag": "ref",
    "git_module": "ref",
    "cargo": "ref",
    "docker": "ref",
}

# Which key of a source stanza names the thing being shared.
_IDENTITY_KEYS = ("url", "path", "location")



# UX-173: kinds that *assemble* rather than build. A `stack` runs no
# commands and a `filter` re-presents what it was given, so a blast of
# 84 where 39 are stacks is not a blast of 84 things that build - and
# the user's first sentence about blast analysis was precisely that it
# ignores element kind.
#
# Unknown kinds count as building, deliberately: overstating what a
# change costs is the safe direction for a number a developer uses to
# decide whether to make it. The report says so where it prints the
# split.
ASSEMBLING_KINDS = frozenset({
    "stack", "import", "filter", "junction", "compose", "link",
})


def is_building_kind(kind: Optional[str]) -> bool:
    return (kind or "unknown") not in ASSEMBLING_KINDS


def split_by_kind(uids, element_kinds: Dict[str, str]) -> Tuple[int, int]:
    """`(building, assembling)` counts for a set of elements.

    `UX-181`: materialised once. The previous version counted the
    argument twice, so a *generator* was exhausted by the first pass and
    yielded a negative assembling count from the second.
    """
    names = list(uids)
    building = sum(1 for uid in names
                   if is_building_kind(element_kinds.get(uid)))
    return building, len(names) - building


def format_kind_split(building: int, assembling: int) -> str:
    """"7 elements (3 that build, 4 that assemble)" - or nothing to add.

    Silent when everything builds, because "(7 that build)" after "7
    elements" is noise; a reader only needs the split where it changes
    the number's meaning.
    """
    total = building + assembling
    if not assembling:
        return f"{total} element(s)"
    return (f"{total} element(s) ({building} that build, "
            f"{assembling} that assemble)")

def keying_of(kind: str) -> str:
    return KEYING_BY_KIND.get(kind, "unknown")


# Schemes whose `://` prefix is decoration on a url this can read. Any
# other scheme is left alone entirely (`UX-181`): rewriting one it does
# not know produced `git+https///host/org/repo` from a perfectly good
# `git+https://host/org/repo.git`, which is a garbage identity *and* the
# halved blast this function exists to prevent.
_KNOWN_SCHEMES = ("https", "http", "ssh", "git", "git+ssh", "git+https",
                  "git+http")


def normalize_url(url: str) -> str:
    """One repository, one identity - conservatively.

    `git@host:org/repo.git` and `https://host/org/repo` are the same
    repository consumed two ways, and an inventory that reported them
    separately would halve the blast it exists to show. Normalisation
    stops at the parts that cannot change which repository is meant:
    scheme, userinfo, a trailing `.git`, a trailing slash, and the
    `host:path` vs `host/path` spelling. Case is left alone below the
    host, because paths on most forges are case-sensitive.

    `UX-181` found both failure directions live. Schemes are matched
    case-insensitively (`HTTPS://Host/Org/Repo` used to fall through the
    scheme strip, and the scp-colon rewrite then fired on the `://`
    itself), and an unknown scheme is returned untouched rather than
    mangled into a new identity.

    `UX-192` corrected `UX-181`'s log, which claimed the scp heuristic
    already applied only to scheme-less forms: it ran on every url, so
    `https://host/a:b/c` - a colon in the *path*, which forges permit -
    became `host/a/b/c`, a second identity for one repository. It now
    genuinely runs only when no scheme was consumed.
    """
    text = url.strip()
    scheme, separator, rest = text.partition("://")
    if separator:
        if scheme.lower() not in _KNOWN_SCHEMES:
            # Not a spelling this can normalise. Returning it as given
            # keeps one identity for one resource, which matters more
            # than folding two spellings of an exotic scheme.
            return text
        text = rest
    if "@" in text.split("/", 1)[0]:
        text = text.split("@", 1)[1]
    # `host:org/repo` (scp-style) becomes `host/org/repo`; a port stays
    # a port, since a numeric segment after the colon is not a path.
    # Only meaningful for the scheme-less form - a scheme's own colon
    # has already been consumed above.
    if not separator:
        host, colon, remainder = text.partition(":")
        if colon and not remainder.split("/", 1)[0].isdigit():
            text = f"{host}/{remainder}"
    if "/" in text:
        head, _, tail = text.partition("/")
        text = head.lower() + "/" + tail
    else:
        text = text.lower()
    text = text.rstrip("/")
    if text.endswith(".git"):
        text = text[:-4]
    return text


def resource_of_source(source) -> Tuple[Optional[dict], Optional[str]]:
    """One `sources:` stanza as `(resource, complaint)`.

    Exactly one of the two is ever set. A stanza this cannot read is
    *named*, not skipped: `UX-160` is the standing lesson that a reader
    which silently drops what it does not understand reports zero and
    looks like an answer.
    """
    if not isinstance(source, dict):
        return None, f"source entry is {type(source).__name__}, not a mapping"
    kind = source.get("kind")
    if not isinstance(kind, str) or not kind:
        return None, "source entry has no `kind`"
    identity = None
    declared = None
    # UX-181: pip sources carry the *index* url, so keying on it groups
    # every pip element in a project into one "repository" and then says
    # "any commit to this rebuilds all of them" about a package index.
    # The package is the resource; the index is context.
    if kind == "pip":
        packages = source.get("packages")
        if isinstance(packages, list) and packages:
            named = sorted(str(p) for p in packages if isinstance(p, (str, int)))
            if named:
                identity = ", ".join(named)
        if identity is None:
            return None, ("`pip` source names no packages - its index url is "
                          "not an identity for one resource")
        # UX-192: the index is not the identity, but dropping it entirely
        # collapsed one package name published on two indexes into one
        # resource - the same over-grouping UX-181 filed, pointing the
        # other way. Kept as a suffix so the package still leads, and
        # out of `declared`, which stays what the recipe wrote.
        declared = identity
        index = source.get("url")
        if isinstance(index, str) and index.strip():
            identity = f"{identity} @ {normalize_url(index)}"
    for key in () if identity else _IDENTITY_KEYS:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            identity = value.strip()
            break
    if identity is None:
        # A source with nothing to share - `bst`'s own `workspace`, or a
        # plugin whose identity lives under a key this does not know.
        return None, f"`{kind}` source has none of {', '.join(_IDENTITY_KEYS)}"
    keying = keying_of(kind)
    normalized = (identity if kind == "pip"
                  else normalize_url(identity) if keying == "ref"
                  else identity.strip("/"))
    resource = {
        "kind": kind,
        "identity": normalized,
        "declared": declared if declared is not None else identity,
        "keying": keying,
        # Where the element stages it. Not part of the identity - that
        # is the whole point of `directory:` on a ref-keyed source.
        "staged_at": source.get("directory") or None,
    }
    return resource, None


def resources_from_element(data: Optional[dict]) -> Tuple[List[dict], List[str]]:
    """`(resources, complaints)` for one parsed `.bst` file."""
    if not isinstance(data, dict):
        return [], ["element file could not be read"]
    stanzas = data.get("sources")
    if stanzas is None:
        return [], []
    if not isinstance(stanzas, list):
        return [], ["`sources` is not a list"]
    resources: List[dict] = []
    complaints: List[str] = []
    for stanza in stanzas:
        resource, complaint = resource_of_source(stanza)
        if resource is not None:
            resources.append(resource)
        elif complaint:
            complaints.append(complaint)
    return resources, complaints


def build_inventory(per_element: Dict[str, List[dict]],
                    complaints: Optional[Dict[str, List[str]]] = None) -> dict:
    """The on-disk shape, `sources/v1`."""
    return {
        "schema": SCHEMA,
        "elements": {uid: list(resources) for uid, resources in sorted(per_element.items())},
        "unreadable": {uid: list(notes) for uid, notes in sorted((complaints or {}).items())},
    }


def resource_key(resource: dict) -> Tuple[str, str]:
    """The pair a resource is grouped by: its kind and its identity.

    Public since `UX-192`, because `bga blast` grouped by identity alone
    and so disagreed with the table it was printed beside.
    """
    return resource.get("kind", "?"), resource.get("identity", "?")


_resource_key = resource_key


def elements_by_resource(inventory: dict) -> Dict[Tuple[str, str], List[str]]:
    """`(kind, identity) -> [element uid]`, sorted, from an inventory."""
    grouped: Dict[Tuple[str, str], List[str]] = {}
    for uid, resources in (inventory.get("elements") or {}).items():
        for resource in resources or []:
            grouped.setdefault(_resource_key(resource), []).append(uid)
    return {key: sorted(set(uids)) for key, uids in grouped.items()}


def resource_blast(inventory: dict,
                   downstream: Dict[str, Set[str]],
                   element_kinds: Dict[str, str],
                   element_durations_s: Optional[Dict[str, float]] = None,
                   minimum_elements: int = 2) -> List[dict]:
    """One row per resource more than one element sources.

    `downstream[uid]` is everything a change to `uid` forces to rebuild,
    which the graph already computes (`compute_reachability`). The blast
    of a resource is the union of its direct elements and all of their
    closures - a union, because two elements sourcing one repository
    usually share most of their downstream.

    Cost is `unmeasured` rather than `0` when the run has no duration
    for an element: this is the same distinction the rest of the tool
    keeps between "measured as nothing" and "not measured".
    """
    durations = element_durations_s or {}
    rows: List[dict] = []
    for (kind, identity), direct in elements_by_resource(inventory).items():
        if len(direct) < minimum_elements:
            continue
        blast: Set[str] = set(direct)
        for uid in direct:
            blast |= set(downstream.get(uid) or ())
        by_kind: Dict[str, int] = {}
        for uid in sorted(blast):
            by_kind[element_kinds.get(uid, "unknown")] = \
                by_kind.get(element_kinds.get(uid, "unknown"), 0) + 1
        building, assembling = split_by_kind(blast, element_kinds)
        measured = [durations[uid] for uid in blast if uid in durations]
        staged = sorted({r.get("staged_at") for uid in direct
                         for r in (inventory.get("elements") or {}).get(uid, [])
                         if _resource_key(r) == (kind, identity)} - {None})
        rows.append({
            "kind": kind,
            "identity": identity,
            "keying": keying_of(kind),
            "direct_elements": direct,
            "direct_count": len(direct),
            "blast_elements": sorted(blast),
            "blast_count": len(blast),
            "by_element_kind": dict(sorted(by_kind.items(), key=lambda kv: (-kv[1], kv[0]))),
            # UX-173: of the blast, how much of it actually builds.
            "building_count": building,
            "assembling_count": assembling,
            "measured_seconds": sum(measured) if measured else None,
            "measured_elements": len(measured),
            "staged_at": staged,
        })
    rows.sort(key=lambda row: (-(row["measured_seconds"] or 0), -row["blast_count"],
                               row["identity"]))
    return rows


def keying_clause(row: dict) -> str:
    """The sentence that turns a count into a decision.

    `UX-181`: the wording comes from the *kind*, because "any commit to
    this" is the right sentence about a repository and the wrong one
    about a pinned package version or a tarball.
    """
    if row.get("kind") == "pip":
        return ("keys on the pinned version: a version bump rebuilds every "
                "element that installs this package")
    if row.get("kind") in ("tar", "zip", "remote", "deb"):
        return ("keys on the archive's ref: republishing it rebuilds every "
                "element that unpacks it")
    if row["keying"] == "ref":
        return ("keys on ref: any commit to this rebuilds all of them, "
                "whatever each one stages")
    if row["keying"] == "content":
        return "keys on content: only the elements whose files changed rebuild"
    return f"keying unknown for `{row['kind']}` sources - blast not estimated"


# When one ref-keyed resource's blast covers this much of the graph, the
# headline says so. Not tuned: it is the point at which "a commit to one
# repository rebuilds most of the project" stops being a detail and
# becomes the project's dominant rebuild characteristic, and it is
# stated here so a reader can disagree with the number rather than
# having to find it.
MONOREPO_SHARE = 0.5


def format_work(seconds: float) -> str:
    """Seconds, minutes or hours, whichever the number actually is.

    A headline that says "0.0h" about a 22s build has spent a sentence
    to say nothing; one that says "6.1h" about a real one is the whole
    point of measuring.
    """
    if seconds >= 3600:
        return f"{seconds / 3600:.1f}h"
    if seconds >= 120:
        return f"{seconds / 60:.0f}m"
    return f"{seconds:.0f}s"


def monorepo_headline(rows: List[dict], element_count: int,
                      share: float = MONOREPO_SHARE) -> Optional[str]:
    """One sentence, when one repository dominates the graph's rebuilds."""
    if not element_count:
        return None
    for row in rows:
        if row["keying"] != "ref":
            continue
        covered = row["blast_count"] / element_count
        if covered < share:
            continue
        cost = ""
        if row["measured_seconds"]:
            cost = f", {format_work(row['measured_seconds'])} of measured build work"
        return (f"One repository decides most of this build: any commit to "
                f"{row['identity']} rebuilds {row['blast_count']} of "
                f"{element_count} elements ({covered:.0%}{cost}), because its "
                f"{row['direct_count']} direct elements key on its ref rather "
                f"than on the files they stage.")
    return None


def load_inventory(path) -> Optional[dict]:
    """Read a `sources/v1` file, or `None` when there is not one.

    A run captured before `UX-171` has no inventory, and that is not an
    error: the resource section is simply absent, the same way it is
    absent for a project with nothing shared.
    """
    import json
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return None
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        return None
    return data


def iter_resource_identities(inventory: dict) -> Iterable[Tuple[str, str]]:
    return elements_by_resource(inventory).keys()
