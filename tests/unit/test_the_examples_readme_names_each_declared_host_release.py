"""UX-1393: examples/README.md names every release `HOST_RELEASES` declares, and no other."""

import pathlib
import re
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))

from tools import sysroot_manifest

README = REPO / "examples/README.md"


def _warning_sentence() -> str:
    text = " ".join(README.read_text(encoding="utf-8").split())
    match = re.search(r"If you stage on a host outside[^,]*,", text)
    assert match, "examples/README.md has no 'If you stage on a host outside ...' sentence"
    return match.group(0)


def test_the_warning_sentence_names_exactly_the_declared_releases():
    named = set(re.findall(r"\b\d\d\.\d\d\b", _warning_sentence()))
    assert named == set(sysroot_manifest.HOST_RELEASES)


def test_the_pasted_table_is_labelled_with_a_declared_release():
    text = README.read_text(encoding="utf-8")
    label = re.search(r"read on Ubuntu (\d\d\.\d\d)", text)
    assert label, "the pasted table carries no 'read on Ubuntu NN.NN' label"
    assert label.group(1) in sysroot_manifest.HOST_RELEASES


def test_the_pasted_figures_are_the_labelled_releases_own():
    text = README.read_text(encoding="utf-8")
    label = re.search(r"read on Ubuntu (\d\d\.\d\d)", text).group(1)
    block = text[text.index("read on Ubuntu") :].split("```text", 1)[1].split("```", 1)[0]
    pasted = dict(re.findall(r"^\s+(glibc|coreutils)\s+host\s+(\S+)", block, re.M))
    assert pasted == sysroot_manifest.HOST_RELEASES[label]
