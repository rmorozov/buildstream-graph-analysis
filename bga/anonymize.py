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

    Character class and length band of `value` are kept - the token
    (prefix excluded) starts at the band's own width, not a fixed
    floor, so a 90-char name does not collapse to the same length as a
    9-char one. `cls` picks the prefix and salts the HMAC so the same
    string in two classes never shares a token. `k` (the token length)
    grows past the band on collision until the result is injective in
    `pmap`.
    """
    if cls not in CLASS_PREFIXES:
        raise ValueError(f"unknown pseudonym class: {cls!r}")
    prefix = CLASS_PREFIXES[cls]
    _, alphabet = _charset_for(value)
    band = _length_band(len(value))
    k = band
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


_TASK_WORD = re.compile(r"[A-Z_]+|\d+")
_URL = re.compile(r"([A-Za-z][A-Za-z0-9+.-]*)://(?:[^@/]*@)?([^/]*)(.*)", re.S)
_SCP_USER = re.compile(r"^[^@/:\s]+@(?=[^/]*:)")
_PUBLIC_SCHEMES = frozenset({"http", "https", "git", "ssh", "file", "ftp", "git+ssh", "git+https"})
_EXTENSION = re.compile(r"(.+?)(\.[A-Za-z0-9]{1,5})")


def pseudonymize_identifier(value, key, pmap):
    """The one place a class A value's pseudonym is decided.

    A task key `uid|ACTION|...|n` keeps its public words; a `.bst` name
    keeps its junction and depth; anything else is a path or URL, whose
    userinfo (class G) is dropped before a segment reaches the map.
    """
    if not isinstance(value, str) or not value:
        return value
    if "|" in value:
        head, *rest = value.split("|")
        return "|".join([pseudonymize_identifier(head, key, pmap)] + [
            part if _TASK_WORD.fullmatch(part) else pseudonymize_identifier(part, key, pmap)
            for part in rest])
    if value.endswith(_BST_SUFFIX) or f"{_BST_SUFFIX}{_JUNCTION_SEP}" in value:
        return pseudonymize_element_path(value, key, pmap)
    url = _URL.fullmatch(value)
    if url:
        scheme, host, rest = url.groups()
        if scheme.lower() not in _PUBLIC_SCHEMES:
            scheme = pseudonymize(scheme, "source", key, pmap)
        host = pseudonymize(host, "source", key, pmap) if host else host
        return f"{scheme}://{host}{_path(rest, key, pmap)}"
    return _path(_SCP_USER.sub("", value), key, pmap)


def _path(value, key, pmap):
    segments = value.split(_PATH_SEP)
    last = len(segments) - 1
    return _PATH_SEP.join(_segment(seg, "file" if i == last else "directory", key, pmap)
                          for i, seg in enumerate(segments))


def _segment(segment, cls, key, pmap):
    lead = "." if segment.startswith(".") else ""
    stem, ext = segment[len(lead):], ""
    shaped = _EXTENSION.fullmatch(stem) if cls == "file" else None
    if shaped:
        stem, ext = shaped.groups()
    if not stem or stem == ".":
        return segment
    return lead + pseudonymize(stem, cls, key, pmap) + ext


def rekey_hash(value, key, pmap):
    """A class E hash re-keyed by HMAC: equal stays equal, same length, hex."""
    if not isinstance(value, str) or not value:
        return value
    out, extend = "", 0
    while len(out) < len(value):
        out += _digest(key, "hash", value, extend).hex()
        extend += 1
    out = out[:len(value)]
    pmap.add(out, f"hash\0{value}")
    return out


def pseudonymize_toolchain(value, key, pmap):
    """A toolchain string off its allowlist: the tool pseudonymized, the version kept."""
    shaped = re.fullmatch(r"(.+?) (\d[\w.~+-]*)", value)
    if shaped is None:
        return pseudonymize(value, "binary", key, pmap)
    return f"{pseudonymize(shaped.group(1), 'binary', key, pmap)} {shaped.group(2)}"


_PUBLIC_MACRO = re.compile(r"CMAKE_[A-Z0-9_]+|BUILD_SHARED_LIBS|BUILD_TESTING|NDEBUG|_GNU_SOURCE|_FORTIFY_SOURCE")
_CMAKE_TYPES = frozenset({"PATH", "FILEPATH", "STRING", "BOOL", "INTERNAL"})
_PUBLIC_VALUES = frozenset({"ON", "OFF", "TRUE", "FALSE", "YES", "NO", "Release", "Debug", "RelWithDebInfo", "MinSizeRel"})
_KEPT_FLAG = re.compile(r"-(?:g[0-3]?|j\d*|[cESvwsP]|shared|static|pipe|pthread|rdynamic)")
#: `-O<n>` is its own check (below): only a compiler driver keeps it, and
#: only glued - `wget -O2`'s `2` is a filename, not an optimization level.
_OPT_LEVEL = re.compile(r"-O[0-3sgz]?|-Ofast")
#: `-lfoo`, `-ofoo` carry a value glued to the letter; any other lowercase word is a flag name.
_NAMED_FLAG = re.compile(r"(--|-[fmW]|-std|-(?=[a-km-np-z][a-z0-9-]{2}))([a-z][a-z0-9+-]*)?(=.*)?", re.S)
_MACRO = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)(?::([A-Z]+))?(=.*)?", re.S)
_ENV_ASSIGNMENT = re.compile(r"([A-Za-z_][A-Za-z0-9_]*)=(.*)", re.S)
#: Only an all-caps word is an env-var prefix ahead of `argv[0]`; a
#: lowercase `a=b` is the binary itself (the UX-1068 verifier regression).
_LEADING_ENV = re.compile(r"[A-Z_][A-Z0-9_]*=.*", re.S)
#: A name that reads as a credential, any case, any separator (1068, class G).
_CREDENTIAL_NAME = re.compile(
    r"token|secret|password|passwd|key|auth|credential|cookie|session"
    r"|pat|bearer|apikey|private_key|signing", re.I)
#: A numeric value pseudonymizes by default (UX-1084: a six-digit OTP is
#: not a jobs count). Two things can keep one: a `-D`/env name on
#: `_MACRO_SAFE_NAMES` (any binary), or a flag on `_MAKE_SAFE_FLAGS`
#: *and* argv[0] a make-like binary - `gcc -l1234` is a linker library,
#: not a load average, and `curl -O 12345` an output filename, not a
#: level (UX-1084 verifier).
_MACRO_SAFE_NAMES = frozenset({"JOBS", "CMAKE_BUILD_PARALLEL_LEVEL"})
_MAKE_SAFE_FLAGS = frozenset({"-j", "--jobs", "-l", "--load-average"})
_MAKE_LIKE_BINARIES = frozenset({"make", "gmake", "ninja", "samu", "bst"})
#: `ld` is deliberately absent: `-l`/`-O` there name libraries/output, never counts.
_COMPILER_BINARIES = frozenset({"cc", "c++", "gcc", "g++", "clang", "clang++", "cc1", "cc1plus"})
#: A value shaped like a credential regardless of its name: a known
#: token prefix, an auth scheme with its value on the next word, or a
#: long run mixing letters and digits (1068 verifier findings).
_TOKEN_PREFIX = re.compile(r"^(?:ghp_|gho_|ghu_|ghs_|ghr_|github_pat_|glpat-|xox[abp]-|AKIA|sk-)")
_AUTH_SCHEME = re.compile(r"^(?:bearer|basic)$", re.I)
_HIGH_ENTROPY = re.compile(r"^(?=.*[A-Za-z])(?=.*[0-9])[A-Za-z0-9_+/=-]{20,}$")
_DROPPED = "<dropped>"


def _credential_shaped(value):
    return bool(value) and bool(
        _TOKEN_PREFIX.match(value) or _AUTH_SCHEME.fullmatch(value) or _HIGH_ENTROPY.fullmatch(value))

#: The only flag names a rebuilt command keeps verbatim, on any `argv[0]`;
#: any other name becomes an `m-` pseudonym behind its dashes (6.6, 6.11).
PUBLIC_FLAGS = frozenset([
    # long options: cmake, make, ninja, meson, configure, the GNU toolchain
    "--build", "--install", "--target", "--config", "--parallel", "--prefix", "--libdir",
    "--bindir", "--includedir", "--datadir", "--sysconfdir", "--localstatedir", "--host",
    "--help", "--version", "--verbose", "--quiet", "--silent", "--jobs", "--keep-going",
    "--output", "--sysroot", "--as-needed", "--no-as-needed", "--whole-archive",
    "--no-whole-archive", "--start-group", "--end-group", "--gc-sections", "--build-id",
    "--hash-style", "--eh-frame-hdr", "--enable-shared", "--disable-shared",
    "--enable-static", "--disable-static", "--with-pic", "--buildtype", "--wrap-mode",
    "--switch", "--cyan", "--green", "--red", "--blue", "--magenta", "--bold",
    "--progress-dir", "--progress-num", "--mode", "--tag", "--preserve-dup-deps",
    # single-dash words: gcc, cc1, collect2, ld
    "-std", "-quiet", "-version", "-dumpdir", "-dumpbase", "-dumpbase-ext", "-imultiarch",
    "-isystem", "-iquote", "-idirafter", "-include", "-print-sysroot", "-nostdlib",
    "-nostdinc", "-nostartfiles", "-pie", "-no-pie", "-plugin", "-plugin-opt", "-soname",
    "-rpath", "-dynamic-linker", "-export-dynamic", "-auxbase", "-auxbase-strip",
    # -f, -m, -W families
    "-fPIC", "-fpic", "-fPIE", "-fpie", "-flto", "-fno-lto", "-fcommon", "-fno-common",
    "-fexceptions", "-fno-exceptions", "-frtti", "-fno-rtti", "-fopenmp", "-fvisibility",
    "-fdiagnostics-color", "-fasynchronous-unwind-tables", "-fcf-protection",
    "-fstack-clash-protection", "-fstack-protector", "-fstack-protector-strong",
    "-fstack-protector-all", "-fno-omit-frame-pointer", "-fomit-frame-pointer",
    "-fno-plt", "-fdebug-prefix-map", "-ffile-prefix-map", "-fmacro-prefix-map",
    "-ffunction-sections", "-fdata-sections", "-fno-strict-aliasing", "-fwrapv",
    "-march", "-mtune", "-mcpu", "-m32", "-m64", "-mfpu", "-mfloat-abi", "-mabi",
    "-Wall", "-Wextra", "-Werror", "-Wpedantic", "-Wformat", "-Wformat-security",
    "-Wno-error", "-Wshadow", "-Wconversion", "-Wno-unused-parameter",
    "-Wno-unused-variable", "-Wno-deprecated-declarations", "-Wunused",
])


def rebuild_command(cmd, key, pmap, public_binaries, counts=None):
    """A class F command line rebuilt from its grammar (`anonymized-bundle.md` 6.6).

    A leading run of `NAME=value` env words (uppercase name, never the
    last word) sits ahead of `argv[0]`; `argv[0]`'s basename is kept
    when public, else a `b-` pseudonym; a flag keeps its name only from
    `PUBLIC_FLAGS`; every value slot, argument, private flag and
    private macro is a pseudonym. A credential-named or credential-
    shaped assignment (1068) is classified before that grammar: its
    value is dropped, never pseudonymized, never mapped; a bare
    credential flag or an auth-scheme value also drops the argv word
    that carries it. `counts`, when given, is incremented once per drop.
    """
    if not isinstance(cmd, str):
        return cmd
    words = cmd.split()
    if not words:
        return ""
    lead = 0
    while lead < len(words) - 1 and _LEADING_ENV.fullmatch(words[lead]):
        lead += 1
    binary = words[lead].rsplit(_PATH_SEP, 1)[-1]
    ctx = (counts, binary)
    out = [_argument(word, key, pmap, ctx) for word in words[:lead]]
    out.append(binary if binary in public_binaries else pseudonymize(binary, "binary", key, pmap))
    i = lead + 1
    pending_safe = False
    while i < len(words):
        word, following = words[i], words[i + 1] if i + 1 < len(words) else None
        if _space_credential(word, following):
            out.append(word if word in PUBLIC_FLAGS else _pseudonymize_flag(word, key, pmap))
            out.append(_DROPPED)
            if counts is not None:
                counts["F credential"] += 1
            pending_safe = False
            i += 2
            continue
        out.append(_argument(word, key, pmap, ctx, pending_safe if not word.startswith("-") else False))
        if following is not None and not following.startswith("-") and _continues_scheme(word):
            out.append(_DROPPED)
            if counts is not None:
                counts["F credential"] += 1
            pending_safe = False
            i += 2
            continue
        pending_safe = binary in _MAKE_LIKE_BINARIES and word in _MAKE_SAFE_FLAGS
        i += 1
    return " ".join(out)


def _pseudonymize_flag(flag, key, pmap):
    dashes = "--" if flag.startswith("--") else "-"
    return dashes + pseudonymize(flag[len(dashes):], "macro", key, pmap)


def _space_credential(word, following):
    """A bare (no `=`) credential flag, its value the next argv word."""
    if following is None or following.startswith("-"):
        return False
    if not word.startswith("-") or word == "-" or "=" in word or word.startswith("-D"):
        return False
    if _KEPT_FLAG.fullmatch(word):
        return False
    return bool(_CREDENTIAL_NAME.search(word))


def _continues_scheme(word):
    """An `Authorization=Bearer`-shaped word: the token is the next word."""
    _, _, assigned = word.partition("=")
    return bool(assigned) and bool(_AUTH_SCHEME.fullmatch(assigned))


_CREDENTIAL_MODE = "credential"


def _argument(word, key, pmap, ctx, safe=False):
    """`ctx` is `(counts, binary)` - argv[0]'s basename, needed to key a
    safe numeric flag (UX-1084 verifier: `-l`/`-O` mean different things
    on `make` than on `gcc` or `curl`). `safe` is a digit value's safety
    already resolved by the caller (a preceding flag's classification)."""
    counts, binary = ctx
    if not word.startswith("-") or word == "-":
        return _positional(word, key, pmap, counts, safe)
    if binary in _COMPILER_BINARIES and _OPT_LEVEL.fullmatch(word):
        return word
    if _KEPT_FLAG.fullmatch(word):
        return word
    if word.startswith("-D") and not word.startswith("--"):
        return _dash_d_argument(word, key, pmap, counts)
    return _flag_argument(word, key, pmap, counts, binary)


def _positional(word, key, pmap, counts, safe):
    env = _ENV_ASSIGNMENT.fullmatch(word)
    if env and (_CREDENTIAL_NAME.search(env.group(1)) or _credential_shaped(env.group(2))):
        return _drop(env.group(1), key, pmap, counts)
    return _value(word, key, pmap, counts, safe)


def _dash_d_argument(word, key, pmap, counts):
    macro = _MACRO.fullmatch(word[2:])
    if macro is None:
        return "-D" + _value(word[2:], key, pmap, counts)
    name, kind, assigned = macro.groups()
    credential = bool(_CREDENTIAL_NAME.search(name))
    macro_safe = name in _MACRO_SAFE_NAMES
    name = name if _PUBLIC_MACRO.fullmatch(name) else pseudonymize(name, "macro", key, pmap)
    if kind is not None:
        kind = kind if kind in _CMAKE_TYPES else pseudonymize(kind, "macro", key, pmap)
    mode = _CREDENTIAL_MODE if credential else macro_safe
    return (f"-D{name}{'' if kind is None else ':' + kind}"
            f"{_assigned(assigned, key, pmap, counts, mode)}")


def _flag_argument(word, key, pmap, counts, binary):
    flag, equals, assigned = word.partition("=")
    credential = bool(_CREDENTIAL_NAME.search(flag))
    flag_safe = binary in _MAKE_LIKE_BINARIES and flag in _MAKE_SAFE_FLAGS
    if flag in PUBLIC_FLAGS and not credential:
        return flag + _assigned(equals + assigned, key, pmap, counts, flag_safe)
    if credential:
        rendered = flag if flag in PUBLIC_FLAGS else _pseudonymize_flag(flag, key, pmap)
        return rendered + _assigned(equals + assigned, key, pmap, counts, _CREDENTIAL_MODE)
    named = _NAMED_FLAG.fullmatch(word)
    if named and named.group(2):
        return (named.group(1) + pseudonymize(named.group(2), "macro", key, pmap)
                + _assigned(named.group(3), key, pmap, counts))
    glued_safe = binary in _MAKE_LIKE_BINARIES and word[:2] in _MAKE_SAFE_FLAGS
    return word[:2] + _value(word[2:], key, pmap, counts, glued_safe)


def _drop(name, key, pmap, counts):
    """A credential name pseudonymized, its value replaced, never mapped."""
    if counts is not None:
        counts["F credential"] += 1
    return f"{pseudonymize(name, 'macro', key, pmap)}={_DROPPED}"


def _assigned(assigned, key, pmap, counts=None, mode=None):
    """`mode` is `_CREDENTIAL_MODE` for a credential drop, `True`/`False`
    for a numeric value's safety already resolved by the caller, or
    `None` for the ordinary pseudonymize path (a non-numeric value)."""
    if not assigned:
        return ""
    if mode == _CREDENTIAL_MODE:
        if counts is not None:
            counts["F credential"] += 1
        return f"={_DROPPED}"
    return "=" + _value(assigned[1:], key, pmap, counts, bool(mode))


def _value(value, key, pmap, counts=None, safe=False):
    if not value or value in _PUBLIC_VALUES:
        return value
    if value.isdigit():
        return value if safe else pseudonymize_identifier(value, key, pmap)
    if _credential_shaped(value):
        if counts is not None:
            counts["F credential"] += 1
        return _DROPPED
    return pseudonymize_identifier(value, key, pmap)


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
