"""UX-1085: `_WORD` was ASCII-only (`[a-z0-9]+`), so a non-ASCII original
such as `café` could never be indexed or matched, wholly within one
chunk or split across a streamed-chunk boundary (UX-1069). NFC and NFD
forms of the same name must also compare equal on either side.
"""

import gzip
import io
import tarfile
import unicodedata

from bga import bundle

NFC_CAFE = unicodedata.normalize("NFC", "café")
NFD_CAFE = unicodedata.normalize("NFD", "café")
assert NFC_CAFE != NFD_CAFE


def _archive(path, members: dict) -> None:
    with (
        open(path, "wb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed,
        tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive,
    ):
        for name, body in members.items():
            data = body.encode("utf-8")
            archive.addfile(bundle.neutral_tarinfo(name, len(data)), io.BytesIO(data))


def test_a_non_ascii_original_wholly_within_one_chunk_is_caught(tmp_path):
    text = "padding padding built by café padding padding"
    path = str(tmp_path / "a.tar.gz")
    _archive(path, {"member": text})
    assert bundle.residue(path, {"café"}) == ["member: café"]


def test_a_non_ascii_original_wholly_within_one_chunk_is_caught_cyrillic(tmp_path):
    text = "padding padding host иванов padding padding"
    path = str(tmp_path / "a.tar.gz")
    _archive(path, {"member": text})
    assert bundle.residue(path, {"иванов"}) == ["member: иванов"]


def test_a_non_ascii_original_split_across_a_small_chunk_boundary_is_still_caught(tmp_path, monkeypatch):
    # chunk=1: every multi-byte UTF-8 sequence (café's 2-byte é) is split
    # across a chunk boundary, so only an incremental decoder survives it.
    monkeypatch.setattr(bundle, "RESIDUE_CHUNK", 1)
    text = "padding " * 5 + "found café here" + " more padding" * 5
    path = str(tmp_path / "b.tar.gz")
    _archive(path, {"member": text})
    assert bundle.residue(path, {"café"}) == ["member: café"]


def test_a_non_ascii_original_split_across_a_small_chunk_boundary_cyrillic(tmp_path, monkeypatch):
    monkeypatch.setattr(bundle, "RESIDUE_CHUNK", 1)
    text = "padding " * 5 + "found иванов here" + " more padding" * 5
    path = str(tmp_path / "b.tar.gz")
    _archive(path, {"member": text})
    assert bundle.residue(path, {"иванов"}) == ["member: иванов"]


def test_ascii_behaviour_is_unchanged(tmp_path):
    text = "padding padding found acme-codegen padding padding"
    path = str(tmp_path / "c.tar.gz")
    _archive(path, {"member": text})
    assert bundle.residue(path, {"acme-codegen"}) == ["member: acme-codegen"]


def test_an_nfc_original_matches_nfd_text_wholly_within_one_chunk(tmp_path):
    text = "padding padding built by " + NFD_CAFE + " padding padding"
    path = str(tmp_path / "d.tar.gz")
    _archive(path, {"member": text})
    assert bundle.residue(path, {NFC_CAFE}) == [f"member: {NFC_CAFE}"]


def test_an_nfd_original_matches_nfc_text_wholly_within_one_chunk(tmp_path):
    text = "padding padding built by " + NFC_CAFE + " padding padding"
    path = str(tmp_path / "e.tar.gz")
    _archive(path, {"member": text})
    assert bundle.residue(path, {NFD_CAFE}) == [f"member: {NFD_CAFE}"]


def test_an_nfc_original_matches_nfd_text_split_at_the_combining_mark(tmp_path, monkeypatch):
    # chunk=1: the base 'e' and the combining acute decode in separate
    # chunks, so only normalizing carry+new together (not each alone) composes them
    monkeypatch.setattr(bundle, "RESIDUE_CHUNK", 1)
    text = "padding " * 5 + "found " + NFD_CAFE + " here" + " more padding" * 5
    path = str(tmp_path / "f.tar.gz")
    _archive(path, {"member": text})
    assert bundle.residue(path, {NFC_CAFE}) == [f"member: {NFC_CAFE}"]


def test_an_nfd_original_matches_nfc_text_split_at_the_multibyte_boundary(tmp_path, monkeypatch):
    monkeypatch.setattr(bundle, "RESIDUE_CHUNK", 1)
    text = "padding " * 5 + "found " + NFC_CAFE + " here" + " more padding" * 5
    path = str(tmp_path / "g.tar.gz")
    _archive(path, {"member": text})
    assert bundle.residue(path, {NFD_CAFE}) == [f"member: {NFD_CAFE}"]
