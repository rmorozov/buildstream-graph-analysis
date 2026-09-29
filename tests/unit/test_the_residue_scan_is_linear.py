"""UX-1071: the residue scan reads a large member in linear time.

`bundle.residue` used to test one `re.findall` alternation of every
normalized variant per chunk - O(dictionary size) per byte. This
compares its hits against that alternation, reimplemented here as the
oracle, over generated archives with multi-word names split by a
separator; then bounds scan time by dictionary size, the axis the
architect's own measurement (~800 variants) turns on.
"""

import gzip
import io
import re
import tarfile
import time

import pytest

from bga import bundle

RESIDUE_MIN = bundle.RESIDUE_MIN


def _oracle_pattern(dictionary):
    """`_residue_pattern`, before UX-1071: one alternation regex."""
    variants, public = {}, bundle._public_words()
    for token in dictionary:
        low = token.lower()
        for form in {low, re.sub(r"[-_.]", "", low), *(re.sub(r"[-_.]", sep, low) for sep in "-_.")}:
            if form == low or (len(form) >= RESIDUE_MIN and form not in public):
                variants.setdefault(form, token)
    if not variants:
        return None, variants
    alternation = "|".join(map(re.escape, sorted(variants, key=len, reverse=True)))
    return re.compile(rf"(?<![a-z0-9])(?:{alternation})(?![a-z0-9])"), variants


def _oracle_hits(text: str, dictionary) -> set:
    pattern, variants = _oracle_pattern(dictionary)
    if pattern is None:
        return set()
    return {variants[m.group()] for m in pattern.finditer(text) if m.start()}


def _archive(path, members: dict) -> None:
    with (
        open(path, "wb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed,
        tarfile.open(fileobj=compressed, mode="w", format=tarfile.USTAR_FORMAT) as archive,
    ):
        for name, body in members.items():
            data = body.encode("utf-8")
            archive.addfile(bundle.neutral_tarinfo(name, len(data)), io.BytesIO(data))


DICTIONARY = {"acme-codegen", "libfoo.bst", "lib-a.bst", "acme_lib_1", "core-runner-7"}


def test_hits_match_the_alternation_across_separators_and_squashed_forms(tmp_path):
    text = (
        "\n".join(
            [
                "path is /a/libfoo.bst here",
                "the tool acme_codegen ran",
                "the tool acme.codegen ran",
                "the tool acmecodegen ran",
                "Xeon lib-a.bst edition",
                "acme_lib_1 seen twice acme_lib_1",
                "host core-runner-7 reporting",
                "unrelated cmake -B build",
            ]
        )
        + "\n"
    ) * 40
    path = str(tmp_path / "a.tar.gz")
    _archive(path, {"member": text})
    assert bundle.residue(path, DICTIONARY) == [
        f"member: {t}" for t in sorted(_oracle_hits("\n" + text.lower() + "\n", DICTIONARY))
    ]


def test_a_name_split_across_a_small_chunk_boundary_is_still_caught(tmp_path, monkeypatch):
    monkeypatch.setattr(bundle, "RESIDUE_CHUNK", 8)
    text = "padding " * 5 + "found acme-codegen here" + " more padding" * 5
    path = str(tmp_path / "b.tar.gz")
    _archive(path, {"member": text})
    assert bundle.residue(path, {"acme-codegen"}) == ["member: acme-codegen"]


def _timed(path, dictionary) -> float:
    start = time.perf_counter()
    bundle.residue(path, dictionary)
    return time.perf_counter() - start


@pytest.mark.parametrize("chunk, prefix", [(1, 0), (2, 0), (17, 9)])
def test_a_word_truncated_at_a_chunk_boundary_is_not_its_own_suffix(tmp_path, monkeypatch, chunk, prefix):
    """`_residue_hits` skips a token starting at the buffer's position 0,
    since it may be the tail of a word already scanned whole in the prior
    chunk. `bar` is not `foobar`, so this must stay clean at these
    chunk/prefix pairs, found by sweeping both against the mutant below."""
    monkeypatch.setattr(bundle, "RESIDUE_CHUNK", chunk)
    text = "x" * prefix + " foobar " + "y" * 40
    path = str(tmp_path / "c.tar.gz")
    _archive(path, {"member": text})
    assert bundle.residue(path, {"bar"}) == []


def test_scan_time_does_not_grow_with_dictionary_size(tmp_path):
    """The architect's measurement (`UX-1071`): ~800 variants, an alternation
    over them - the axis the old scan's cost turned on. Fixed text, a
    10-token dictionary against one at that scale; a per-token alternation
    cost would show here (see the task file's Outcome for why text size
    alone cannot)."""
    unit = "gcc -c widget-source-file.c -O2 -DFOO=1 host runner-host-3\n"
    path = str(tmp_path / "n.tar.gz")
    _archive(path, {"member": unit * 6000})
    small = {f"runner-host-{i}" for i in range(10)}
    large = (
        {f"acme-lib-{i}.bst" for i in range(200)}
        | {f"runner-host-{i}" for i in range(200)}
        | {f"binary-tool-{i}" for i in range(200)}
        | {f"flag-value-{i}" for i in range(200)}
    )
    assert len(large) > 700, len(large)
    _timed(path, small)  # warm caches first
    small_time = min(_timed(path, small) for _ in range(3))
    large_time = min(_timed(path, large) for _ in range(3))
    assert large_time < 5 * small_time, (small_time, large_time)
