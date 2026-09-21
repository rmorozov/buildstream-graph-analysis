"""UX-907: what one element's artifact weighs, exactly.

`cache_capacity` carries the ceiling and the volume; nothing carried
what a *single* artifact costs, so R2 could not rank and R5 could not
size. BuildStream 2.8.0 publishes no such number - `%{artifact-cas-digest}`
renders the root `Directory` proto's own length, which on a real cache
reads 165x to 530,682x under the artifact (`UX-907`).

So read the CAS directly. An artifact ref is an `Artifact` proto at
`<cachedir>/artifacts/refs/<project>/<normal_name>/<cache_key>`
(`_context.py:344`, `element.py:3456`); its `files` digest roots a tree
of `Directory` protos under `<cachedir>/cas/objects/<hh>/<rest>`
(`cascache.py:325`), and every `FileNode` carries its blob's
`size_bytes`. Summing them is exact and needs no `bst`, no stat per
file and no protobuf runtime - the same walk `cascache.py:586` does.

Deduplicated by blob hash within one artifact, so a file staged twice
is counted once. Across elements it is *not*: two artifacts sharing a
blob each carry its bytes, because each would need it alone. The run
total is walked with one seen-set and is therefore smaller than the sum
of the parts - `weigh_elements` returns both.
"""
import os
import time
from collections.abc import Iterable, Iterator
from typing import Any, Optional

# Same shape as `cache_capacity.WALK_BUDGET_S`: a truncated sum is not a
# weight, so exceeding the budget is a named outcome, not a smaller number.
WALK_BUDGET_S = 30.0

_VALID = set("0123456789abcdefghijklmnopqrstuvwxyz"
             "ABCDEFGHIJKLMNOPQRSTUVWXYZ-._")


def _fields(buf: bytes) -> Iterator[tuple[int, int, Any]]:
    """`(field_number, wire_type, value)` over a protobuf message.

    Length-delimited fields yield their payload, varints their value;
    the two fixed widths yield their raw bytes because nothing here
    reads one. Enough of the wire format to read `Artifact`, `Directory`
    and `Digest`, and no schema to drift against theirs.
    """
    i, n = 0, len(buf)
    while i < n:
        key, shift = 0, 0
        while True:
            byte = buf[i]
            i += 1
            key |= (byte & 0x7F) << shift
            if not byte & 0x80:
                break
            shift += 7
        num, wire = key >> 3, key & 7
        if wire in (0, 2):
            value, shift = 0, 0
            while True:
                byte = buf[i]
                i += 1
                value |= (byte & 0x7F) << shift
                if not byte & 0x80:
                    break
                shift += 7
            if wire == 0:
                yield num, wire, value
            else:
                yield num, wire, buf[i:i + value]
                i += value
        elif wire == 5:
            yield num, wire, buf[i:i + 4]
            i += 4
        elif wire == 1:
            yield num, wire, buf[i:i + 8]
            i += 8
        else:
            raise ValueError(f"protobuf wire type {wire}")


def _digest(buf: bytes) -> tuple:
    """A REAPI `Digest`: `hash` is field 1, `size_bytes` field 2."""
    hash_, size = None, 0
    for num, wire, value in _fields(buf):
        if num == 1 and wire == 2:
            hash_ = value.decode("utf-8", "replace")
        elif num == 2 and wire == 0:
            size = value
    return hash_, size


def normal_name(element_name: str) -> str:
    """The element name as the ref path spells it: separators to `-`,
    the suffix dropped, anything outside BuildStream's allowed set to
    `_` (`element.py:3440,3456`)."""
    stem = os.path.splitext(element_name.replace(os.sep, "-"))[0]
    return "".join(char if char in _VALID else "_" for char in stem)


def ref_path(cachedir: str, project: str, element_name: str, cache_key: str) -> str:
    """Where BuildStream wrote this element's `Artifact` proto."""
    return os.path.join(cachedir, "artifacts", "refs", project,
                        normal_name(element_name), cache_key)


def read_ref(path: str) -> dict:
    """The digests an `Artifact` proto roots, by name.

    `files` is field 8 and `buildtree` field 12 (`artifact.proto`);
    both are absent from a proto that does not carry them, which is not
    the same as a tree of zero bytes.
    """
    try:
        with open(path, "rb") as handle:
            buf = handle.read()
    except OSError:
        return {}
    wanted = {8: "files", 12: "buildtree"}
    roots = {}
    for num, wire, value in _fields(buf):
        if wire == 2 and num in wanted:
            hash_, size = _digest(value)
            if hash_:
                roots[wanted[num]] = (hash_, size)
    return roots


def _children(buf: bytes) -> Iterator[tuple[bool, tuple]]:
    """`(is_file, digest)` for every node a `Directory` names: `files`
    is field 1 and `directories` field 2, and each node carries its
    `digest` in field 2 of itself."""
    for num, wire, value in _fields(buf):
        if wire != 2 or num not in (1, 2):
            continue
        for sub, subwire, subvalue in _fields(value):
            if sub == 2 and subwire == 2:
                yield num == 1, _digest(subvalue)


def walk_tree(casdir: str, root: tuple, seen: Optional[set] = None,
              deadline: Optional[float] = None) -> tuple:
    """`(own_bytes, new_bytes, dirs_read)`, or `(None, None, n)` when the
    tree could not be walked whole.

    Reads one blob per `Directory` in the tree and none per file: a
    `FileNode` (field 1) already carries its blob's size, and a
    `DirectoryNode` (field 2) its subtree's root. `own_bytes` counts
    every distinct blob in this tree; `new_bytes` counts only those not
    already in `seen`, which the walk then adds - so a run summing
    `new_bytes` gets the cache's real cost and each element still
    reports its whole weight.
    """
    counted: dict = {}
    dirs = 0
    stack = [root]
    while stack:
        if deadline is not None and time.monotonic() > deadline:
            return None, None, dirs
        hash_, size = stack.pop()
        if hash_ in counted:
            continue
        counted[hash_] = size
        try:
            with open(os.path.join(casdir, "objects",
                                   hash_[:2], hash_[2:]), "rb") as handle:
                buf = handle.read()
        except OSError:
            # A ref whose tree is half-evicted: the bytes still in the
            # cache are not the artifact's weight, so refuse the sum.
            return None, None, dirs
        dirs += 1
        for is_file, child in _children(buf):
            if is_file:
                counted.setdefault(child[0], child[1])
            else:
                stack.append(child)
    own = sum(counted.values())
    if seen is None:
        return own, own, dirs
    new = sum(size for hash_, size in counted.items() if hash_ not in seen)
    seen.update(counted)
    return own, new, dirs


def weigh_elements(cachedir: str, project: str, elements: Iterable,
                   budget_s: float = WALK_BUDGET_S) -> dict:
    """Every element's artifact weight, and the run's deduplicated total.

    `elements` is `(element_name, cache_key)` pairs. Each row carries a
    `source`: `cas_walk` when the tree was walked whole, `ref_absent`
    when the element has no artifact in this cache (a cache miss, a
    failure, or an eviction - all of them "nothing to weigh"),
    `incomplete` when a blob under the ref is gone, and
    `budget_exceeded` when the walk ran out of time. Only `cas_walk`
    rows carry bytes.
    """
    casdir = os.path.join(cachedir, "cas")
    deadline = time.monotonic() + budget_s
    shared: set = set()
    rows, unique, dirs = {}, 0, 0
    for element_name, cache_key in elements:
        roots = ({} if not cache_key else
                 read_ref(ref_path(cachedir, project, element_name, cache_key)))
        if "files" not in roots:
            rows[element_name] = {"files_bytes": None, "buildtree_bytes": None,
                                  "source": "ref_absent"}
            continue
        row = {"files_bytes": None, "buildtree_bytes": None, "source": "cas_walk"}
        marginal = 0
        for key in ("files", "buildtree"):
            if key not in roots:
                continue
            own, new, read = walk_tree(casdir, roots[key], shared, deadline)
            dirs += read
            if own is None:
                row["source"] = ("budget_exceeded"
                                 if time.monotonic() > deadline else "incomplete")
                row["files_bytes"] = row["buildtree_bytes"] = None
                marginal = 0
                break
            row[f"{key}_bytes"] = own
            marginal += new
        rows[element_name] = row
        unique += marginal
    return {
        "cachedir": cachedir,
        "project": project,
        "elements": rows,
        # One seen-set across every element, so a blob two artifacts
        # share counts once here and once *each* above: the rows sum to
        # more than this by whatever the artifacts share.
        "run_unique_bytes": unique,
        "walk_dirs_read": dirs,
    }
