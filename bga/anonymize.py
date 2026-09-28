"""UX-1061: keyed, stable pseudonyms that keep a name's shape.

`pseudonym = prefix + base32(HMAC-SHA256(key, class || value))[:k]`,
`k` grown on collision so the map stays injective (`anonymized-bundle.md`
§4). The class salts the HMAC input so two classes never share a token
for the same string - dropping it is exactly the mutation this task's
guard catches. One key per project lives under `.bga/anon/key`, the
`pseudonym -> original` map beside it at `.bga/anon/map.json`, both
0600. UX-1062 walks a capture with this; UX-1064 resolves free text.
"""

import hashlib
import hmac
import json
import os
import re

ANON_DIRNAME = "anon"
KEY_FILENAME = "key"
MAP_FILENAME = "map.json"
KEY_BYTES = 32

#: `anonymized-bundle.md` §4: the class a value belongs to names the
#: prefix a reader sees, so a pseudonym also says what kind of thing it is.
CLASS_PREFIXES = {
    "element": "e-",
    "junction": "j-",
    "directory": "d-",
    "file": "f-",
    "source": "s-",
    "host": "h-",
    "macro": "m-",
    "binary": "b-",
}

#: Character classes a token can keep, widest match wins, checked in order.
_CHARSETS = [
    ("digit", re.compile(r"^[0-9]+$"), "0123456789"),
    ("lower-alpha", re.compile(r"^[a-z]+$"), "abcdefghijklmnopqrstuvwxyz"),
    ("lower-alnum", re.compile(r"^[a-z0-9]+$"), "abcdefghijklmnopqrstuvwxyz0123456789"),
    ("mixed", re.compile(r"^[A-Za-z0-9_-]+$"), "abcdefghijklmnopqrstuvwxyz0123456789_-"),
]
_DEFAULT_CHARSET = _CHARSETS[-1]

#: Length bands: exact length is not kept, only which band it falls in,
#: represented by the band's own width so page layout stays plausible.
_LENGTH_BANDS = [2, 4, 8, 16, 32, 64, 128]


def _charset_for(token):
    for name, pattern, alphabet in _CHARSETS:
        if pattern.match(token):
            return name, alphabet
    return _DEFAULT_CHARSET[0], _DEFAULT_CHARSET[2]


def _length_band(n):
    for band in _LENGTH_BANDS:
        if n <= band:
            return band
    return _LENGTH_BANDS[-1]


def _anon_dir(project_root):
    return os.path.join(project_root, ".bga", ANON_DIRNAME)


def _write_0600(path, data):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.write(fd, data)
    finally:
        os.close(fd)
    os.chmod(path, 0o600)


def load_or_create_key(project_root):
    """The project's HMAC key at `.bga/anon/key`, created 0600 on first use."""
    anon_dir = _anon_dir(project_root)
    key_path = os.path.join(anon_dir, KEY_FILENAME)
    if os.path.exists(key_path):
        with open(key_path, "rb") as fh:
            return fh.read()
    os.makedirs(anon_dir, exist_ok=True)
    key = os.urandom(KEY_BYTES)
    _write_0600(key_path, key)
    return key


def key_fingerprint(key):
    """A non-secret fingerprint for the bundle manifest: sha256(key)[:16]."""
    return hashlib.sha256(key).hexdigest()[:16]


class PseudonymMap:
    """`pseudonym -> original`, persisted 0600 beside the key; UX-1064 reads it."""

    def __init__(self, path):
        self.path = path
        self._forward = {}
        if os.path.exists(path):
            with open(path, encoding="utf-8") as fh:
                self._forward = json.load(fh)

    def resolve(self, pseudonym):
        return self._forward.get(pseudonym)

    def has(self, pseudonym):
        return pseudonym in self._forward

    def add(self, pseudonym, original):
        self._forward[pseudonym] = original

    def save(self):
        data = json.dumps(self._forward, indent=2, sort_keys=True).encode("utf-8")
        _write_0600(self.path, data)

    @classmethod
    def for_project(cls, project_root):
        return cls(os.path.join(_anon_dir(project_root), MAP_FILENAME))


def _digest(key, cls, value, extend):
    """HMAC-SHA256 over `class || value`, extended with a counter past 32 chars."""
    msg = cls.encode("utf-8") + b"\0" + value.encode("utf-8")
    if extend:
        msg += b"\0" + str(extend).encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).digest()


def _token(key, cls, value, alphabet, length):
    """`length` characters drawn from `alphabet` (base32's digest, mapped
    into the original's character class rather than always a-z2-7, so a
    digit-only or letter-only token keeps looking like one)."""
    out = []
    extend = 0
    while len(out) < length:
        digest = _digest(key, cls, value, extend)
        for byte in digest:
            out.append(alphabet[byte % len(alphabet)])
            if len(out) == length:
                break
        extend += 1
    return "".join(out)


def pseudonymize(value, cls, key, pmap):
    """A shape-preserving pseudonym for one atomic token (no path structure).

    Character class and length band of `value` are kept; `cls` picks the
    prefix and salts the HMAC so the same string in two classes never
    shares a token. `k` (the token length) grows on collision until the
    result is injective in `pmap`.
    """
    if cls not in CLASS_PREFIXES:
        raise ValueError(f"unknown pseudonym class: {cls!r}")
    prefix = CLASS_PREFIXES[cls]
    _, alphabet = _charset_for(value)
    band = _length_band(len(value))
    k = min(band, 4)
    while True:
        token = _token(key, cls, value, alphabet, k)
        candidate = f"{prefix}{token}"
        existing = pmap.resolve(candidate)
        if existing is None or existing == f"{cls}\0{value}":
            break
        k += 1
        if k > band + 8:
            raise RuntimeError(f"pseudonym map exhausted for class {cls!r}")
    pmap.add(candidate, f"{cls}\0{value}")
    return candidate


_JUNCTION_SEP = ":"
_PATH_SEP = "/"
_BST_SUFFIX = ".bst"


def pseudonymize_element_path(value, key, pmap):
    """Shape-preserving pseudonym for a `.bst` path, junction included.

    `base.bst:components/gtk/gtk3.bst` becomes `j-4fne.bst:d-2k7a/d-x9p3/e-q7rk.bst`:
    the junction separator, directory depth and `.bst` extension all
    survive; every path segment is pseudonymized in its own class so a
    directory and an element of the same name never share a token.
    """
    junction, _, rest = value.partition(_JUNCTION_SEP)
    if not rest:
        rest = junction
        junction = None
    parts = rest.split(_PATH_SEP)
    out_parts = []
    for i, part in enumerate(parts):
        is_last = i == len(parts) - 1
        stem, ext = os.path.splitext(part) if part.endswith(_BST_SUFFIX) else (part, "")
        cls = "element" if is_last else "directory"
        token = pseudonymize(stem, cls, key, pmap)
        out_parts.append(token + ext)
    out = _PATH_SEP.join(out_parts)
    if junction is not None:
        j_stem, j_ext = os.path.splitext(junction) if junction.endswith(_BST_SUFFIX) else (junction, "")
        j_token = pseudonymize(j_stem, "junction", key, pmap) + j_ext
        return f"{j_token}{_JUNCTION_SEP}{out}"
    return out


class FingerprintMismatch(Exception):
    """A map's key does not match the fingerprint the bundle carries
    (`anonymized-bundle.md` §4): resolving through it would print the
    wrong project's names, so UX-1064 refuses rather than guessing."""


def check_fingerprint(key, expected_fingerprint):
    actual = key_fingerprint(key)
    if actual != expected_fingerprint:
        raise FingerprintMismatch(
            f"map key fingerprint {actual} does not match the bundle's "
            f"{expected_fingerprint}; this map belongs to a different project")


#: Any prefix a pseudonym-shaped token can start with, longest run of its
#: own alphabet kept greedily - free text has no other delimiter to lean on.
_TOKEN_RE = re.compile(
    "(?<![A-Za-z0-9_])(?:"
    + "|".join(re.escape(p) for p in CLASS_PREFIXES.values())
    + ")[A-Za-z0-9_-]+"
)


def resolve_text(text, pmap):
    """Rewrite every pseudonym in `text` back to its original.

    Returns `(resolved, unknown)`; `unknown` lists, in first-seen order,
    every pseudonym-shaped token `pmap` has no entry for - UX-1064 must
    never drop one silently.
    """
    unknown = []
    seen = set()

    def _replace(match):
        token = match.group(0)
        tagged = pmap.resolve(token)
        if tagged is None:
            if token not in seen:
                seen.add(token)
                unknown.append(token)
            return token
        _, _, original = tagged.partition("\0")
        return original

    resolved = _TOKEN_RE.sub(_replace, text)
    return resolved, unknown
