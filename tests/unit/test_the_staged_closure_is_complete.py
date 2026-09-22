"""UX-927: a staged closure carries every path it names, or says so.

Hermetic, like the pure half of `test_the_staged_make_is_the_pinned_one`:
the suite does not reach the network (`tests/conftest.py`), so the NARs
and narinfos here are synthesized and served over `file://`.

The claim under test is the one `UX-925` asks for and a green build
cannot make: that the tree is complete *by its own account*, rather than
complete enough to link on a host that happens to have Nix. So the
interesting clauses are the negative ones - a closure walk that stops
early, a digest that disagrees, a reference nothing staged.
"""
import hashlib
import os
import struct

import pytest

from tools import nix_closure, nix_store_fetch

ALPHABET = nix_closure.ALPHABET


def _nix32(raw):
    """The inverse of `nix_closure.nix32_decode`, so a fixture can write
    a narinfo the way `cache.nixos.org` does."""
    length = (len(raw) * 8 + 4) // 5
    out = []
    for n in range(length - 1, -1, -1):
        bit = n * 5
        i, j = divmod(bit, 8)
        digit = raw[i] >> j
        if i + 1 < len(raw):
            digit |= raw[i + 1] << (8 - j)
        out.append(ALPHABET[digit & 0x1F])
    return "".join(out)


def _word(value):
    raw = value if isinstance(value, bytes) else value.encode("utf-8")
    return struct.pack("<Q", len(raw)) + raw + b"\x00" * (-len(raw) % 8)


def _regular(contents, executable=False):
    node = _word("(") + _word("type") + _word("regular")
    if executable:
        node += _word("executable") + _word("")
    return node + _word("contents") + _word(contents) + _word(")")


def _one_file_nar(name, contents):
    """A NAR whose root is a directory holding one regular file."""
    entry = (_word("entry") + _word("(") + _word("name") + _word(name)
             + _word("node") + _regular(contents) + _word(")"))
    return (_word("nix-archive-1") + _word("(") + _word("type")
            + _word("directory") + entry + _word(")"))


class _Cache:
    """A `file://` binary cache: narinfos and NARs on disk, written the
    way the real one serves them."""

    def __init__(self, root):
        self.root = root
        os.makedirs(os.path.join(root, "nar"), exist_ok=True)

    @property
    def base(self):
        return "file://" + self.root + "/"

    def add(self, digest, name, contents=b"x", references=(),
            compression="none", file_hash=None):
        raw = _one_file_nar("payload", contents)
        body = raw
        if compression == "xz":
            import lzma
            body = lzma.compress(raw)
        elif compression == "zstd":
            body = _zstd_compress(raw)
        url = f"nar/{digest}.nar.{compression}" if compression != "none" \
            else f"nar/{digest}.nar"
        with open(os.path.join(self.root, url), "wb") as handle:
            handle.write(body)
        store_path = f"/nix/store/{digest}-{name}"
        refs = " ".join(references) or f"{digest}-{name}"
        fields = [
            f"StorePath: {store_path}",
            f"URL: {url}",
            f"Compression: {compression}",
            "FileHash: sha256:" + (file_hash or _nix32(hashlib.sha256(body).digest())),
            f"FileSize: {len(body)}",
            "NarHash: sha256:" + _nix32(hashlib.sha256(raw).digest()),
            f"NarSize: {len(raw)}",
            f"References: {refs}",
        ]
        with open(os.path.join(self.root, digest + ".narinfo"), "w",
                  encoding="utf-8") as handle:
            handle.write("\n".join(fields) + "\n")
        return store_path


def _zstd_compress(raw):
    """`zstandard` is a `[dev]`/`[nix]` dependency (UX-927): a closure
    off `cache.nixos.org` is `zstd` and stdlib `lzma` stages none of it,
    so a suite that could not compress one could not test the path
    that matters."""
    import zstandard
    return zstandard.ZstdCompressor().compress(raw)


#: 32 nix-base32 characters, the shape a store hash has.
def _digest(seed):
    return (hashlib.sha256(seed.encode()).hexdigest()
            .translate(str.maketrans("etou", "kmpq"))[:32])


class TestNixBase32:
    """The decoder is checked against digests this repository already
    typed as hex, so the two spellings of the same pin have to agree."""

    @pytest.mark.parametrize("name", sorted(nix_store_fetch.PINS["x86_64"]["paths"]))
    def test_a_pins_hex_digest_is_its_narinfo_spelling(self, name):
        pin = nix_store_fetch.PINS["x86_64"]["paths"][name]
        # The `nar/<nix32>.nar.xz` URL carries the same digest the pin
        # states as hex - UX-915 typed one and UX-927 reads the other.
        nix32 = pin["url"].rsplit("/", 1)[1].split(".", 1)[0]
        assert nix_closure.nix32_decode(nix32).hex() == pin["sha256"]

    def test_the_encoder_in_this_file_inverts_the_decoder(self):
        raw = hashlib.sha256(b"UX-927").digest()
        assert nix_closure.nix32_decode(_nix32(raw)) == raw

    def test_a_hex_digest_is_passed_through(self):
        hex_digest = "0" * 64
        assert nix_closure.digest_hex("sha256:" + hex_digest) == hex_digest

    def test_an_unknown_algorithm_is_named(self):
        with pytest.raises(ValueError, match="sha512"):
            nix_closure.digest_hex("sha512:deadbeef")


class TestTheClosureWalkIsTransitive:
    def test_a_reference_two_hops_out_is_reached(self, tmp_path):
        """The whole point of the row: `make`'s closure is one hop and a
        compiler's is not, so a walk that stops at the root's own
        `References` stages a sysroot that reaches outside itself."""
        cache = _Cache(str(tmp_path / "cache"))
        c = _digest("c")
        b = _digest("b")
        a = _digest("a")
        cache.add(c, "leaf")
        cache.add(b, "middle", references=[f"{b}-middle", f"{c}-leaf"])
        cache.add(a, "root", references=[f"{a}-root", f"{b}-middle"])
        found = nix_closure.closure([a], str(tmp_path / "dl"), cache.base)
        assert sorted(found) == sorted([a, b, c])

    def test_a_reference_cycle_terminates(self, tmp_path):
        """Every real narinfo lists its own path, and store paths may
        reference each other; a walk that did not remember would not
        return."""
        cache = _Cache(str(tmp_path / "cache"))
        x, y = _digest("x"), _digest("y")
        cache.add(x, "x", references=[f"{x}-x", f"{y}-y"])
        cache.add(y, "y", references=[f"{y}-y", f"{x}-x"])
        assert sorted(nix_closure.closure([x], str(tmp_path / "dl"),
                                          cache.base)) == sorted([x, y])

    def test_the_order_is_stable(self, tmp_path):
        cache = _Cache(str(tmp_path / "cache"))
        for seed in "abcdef":
            cache.add(_digest(seed), seed)
        roots = [_digest(seed) for seed in "abcdef"]
        first = list(nix_closure.closure(roots, str(tmp_path / "dl"), cache.base))
        second = list(nix_closure.closure(reversed(roots),
                                          str(tmp_path / "dl2"), cache.base))
        assert first == second == sorted(roots)


class TestTheDigestGate:
    def test_narhash_decides(self, tmp_path):
        """A NAR whose content does not hash to its `NarHash` is refused,
        whatever the wrapper says."""
        cache = _Cache(str(tmp_path / "cache"))
        digest = _digest("bad")
        cache.add(digest, "bad")
        path = os.path.join(cache.root, digest + ".narinfo")
        text = open(path, encoding="utf-8").read().replace(
            "NarHash: sha256:", "NarHash: sha256:" + "0" * 0)
        fields = nix_closure.parse_narinfo(text)
        fields["NarHash"] = "sha256:" + "0" * 64
        with pytest.raises(SystemExit, match="NarHash"):
            nix_closure.fetch_nar(fields, str(tmp_path / "dl"), cache.base)

    def test_a_recompressed_body_is_a_warning_not_a_refusal(self, tmp_path, capsys):
        """Measured 2026-09-22: `glibc-2.40-224` arrives 9,099,653 bytes
        against a declared 9,096,823 with `FileHash` disagreeing, while
        `NarHash` and `NarSize` are exact. `FileHash` describes one
        compression of the path; `NarHash` is the path. Refusing on the
        wrapper would refuse a correct store path."""
        cache = _Cache(str(tmp_path / "cache"))
        digest = _digest("recompressed")
        cache.add(digest, "recompressed", compression="xz",
                  file_hash=_nix32(b"\x00" * 32))
        fields = nix_closure.narinfo(digest, str(tmp_path / "dl"), cache.base)
        raw = nix_closure.fetch_nar(fields, str(tmp_path / "dl"), cache.base)
        assert hashlib.sha256(raw).hexdigest() == \
            nix_closure.digest_hex(fields["NarHash"])
        assert "NarHash decides" in capsys.readouterr().err

    def test_a_narinfo_naming_another_path_is_refused(self, tmp_path):
        """The one field a narinfo cannot attest to is which path it is
        for, so it is checked against the hash that was asked for."""
        cache = _Cache(str(tmp_path / "cache"))
        digest = _digest("real")
        cache.add(digest, "real")
        other = _digest("other")
        os.rename(os.path.join(cache.root, digest + ".narinfo"),
                  os.path.join(cache.root, other + ".narinfo"))
        with pytest.raises(SystemExit, match=other):
            nix_closure.narinfo(other, str(tmp_path / "dl"), cache.base)


class TestTheDecompressorIsDeclared:
    def test_an_unknown_compression_is_named_not_passed_through(self):
        """A NAR handed to the reader still compressed reads as a
        malformed NAR, which names the wrong thing."""
        with pytest.raises(SystemExit, match="brotli"):
            nix_closure.decompress("brotli", b"")

    @pytest.mark.parametrize("compression", ("none", "xz", "zstd"))
    def test_each_declared_compression_round_trips(self, compression, tmp_path):
        cache = _Cache(str(tmp_path / "cache"))
        digest = _digest(compression)
        cache.add(digest, compression, contents=b"UX-927" * 64,
                  compression=compression)
        fields = nix_closure.narinfo(digest, str(tmp_path / "dl"), cache.base)
        raw = nix_closure.fetch_nar(fields, str(tmp_path / "dl"), cache.base)
        assert raw.startswith(struct.pack("<Q", len("nix-archive-1")))

    def test_the_zstd_backend_is_named(self):
        """`--check` prints it, so a staged tree says what read it -
        UX-914's rule, one layer down."""
        assert nix_closure.zstd_backend() in \
            [name for name, _ in nix_closure._zstd_backends()]


class TestTheStagedTreeIsCheckedAgainstItself:
    def _stage(self, tmp_path, contents):
        cache = _Cache(str(tmp_path / "cache"))
        leaf = _digest("leaf")
        root = _digest("root")
        cache.add(leaf, "leaf")
        cache.add(root, "root", contents=contents,
                  references=[f"{root}-root", f"{leaf}-leaf"])
        dest = str(tmp_path / "sysroot")
        nix_closure.stage_closure(dest, [root], str(tmp_path / "dl"), cache.base)
        return dest, root, leaf

    def test_every_closure_member_lands_at_its_own_store_path(self, tmp_path):
        dest, root, leaf = self._stage(tmp_path, b"x")
        for digest in (root, leaf):
            assert os.path.isdir(f"{dest}/nix/store/{digest}-"
                                 + ("root" if digest == root else "leaf"))
        assert nix_closure.missing_from(dest, [root, leaf]) == []

    def test_a_complete_tree_has_no_dangling_reference(self, tmp_path):
        """A staged file naming a path the tree does carry is not a
        finding - almost every real store path names its own."""
        dest, root, _leaf = self._stage(tmp_path, b"self /nix/store/PLACEHOLDER")
        path = f"{dest}/nix/store/{root}-root/payload"
        os.chmod(path, 0o644)
        with open(path, "wb") as handle:
            handle.write(b"self /nix/store/" + f"{root}-root".encode())
        assert nix_closure.dangling_store_refs(dest) == []

    def test_a_reference_nothing_staged_is_reported(self, tmp_path):
        """The defect the row exists for: a tree that names a store path
        it does not carry resolved that path on the staging host."""
        absent = _digest("absent")
        dest, _root, _leaf = self._stage(
            tmp_path, b"needs /nix/store/" + f"{absent}-absent".encode())
        dangling = nix_closure.dangling_store_refs(dest)
        assert [ref for _file, ref in dangling] == \
            [f"/nix/store/{absent}-absent"]

    def test_dropping_a_closure_member_reddens_the_check(self, tmp_path):
        """The mutation, run as a clause: the staged tree is complete,
        then one member is removed and the same call names it."""
        import shutil
        leaf = _digest("leaf")
        dest, root, staged_leaf = self._stage(
            tmp_path, b"needs /nix/store/" + f"{leaf}-leaf".encode())
        assert staged_leaf == leaf
        assert nix_closure.dangling_store_refs(dest) == []
        shutil.rmtree(f"{dest}/nix/store/{leaf}-leaf",
                      onerror=lambda f, path, _e: (os.chmod(path, 0o755), f(path)))
        assert [ref for _file, ref in nix_closure.dangling_store_refs(dest)] == \
            [f"/nix/store/{leaf}-leaf"]
        assert nix_closure.missing_from(dest, [root, leaf]) == [leaf]
