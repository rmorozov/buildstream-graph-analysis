"""UX-1089: a glued -j keeps its digits only on a make-like tool.

`_KEPT_FLAG`'s `j\\d*` used to accept `-j<digits>` on any `argv[0]`,
ahead of the make-like binary allowlist `_MAKE_SAFE_FLAGS` already
keys the space-separated and assigned forms on (UX-1084). `curl
-j123456` or a private tool with that argument kept six digits
verbatim. `_GLUED_JOBS` now routes the glued form through the same
(binary, option) safe check as everything else; off a make-like
binary it falls to `_value`'s default drop. `-O\\d`/`-l` were already
keyed this way; `g[0-3]?` stays unkeyed - a bounded 4-way enum, not a
captured value.
Mutation: drop the `binary in _MAKE_LIKE_BINARIES` check in the glued
`-j` branch, and `curl -j123456` keeps its digits again.
"""

from bga import anonymize as anon

KEY = bytes(range(32))


def _pmap(tmp_path):
    return anon.PseudonymMap(str(tmp_path / "map.json"))


def _originals(pmap):
    return {v.partition("\0")[2] for v in pmap._forward.values()}


def test_a_glued_j_on_a_non_make_tool_is_dropped(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("curl -j123456", KEY, pmap, frozenset())
    assert "123456" not in rebuilt
    assert "<dropped>" in rebuilt
    assert "123456" not in _originals(pmap)


def test_a_glued_j_on_a_private_tool_is_dropped(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("acme-gen -j123456", KEY, pmap, frozenset())
    assert "123456" not in rebuilt
    assert "123456" not in _originals(pmap)


def test_make_glued_j_still_keeps_its_digits(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("make -j8", KEY, pmap, frozenset())
    assert rebuilt.endswith("-j8")


def test_ninja_glued_j_still_keeps_its_digits(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("ninja -j12", KEY, pmap, frozenset())
    assert rebuilt.endswith("-j12")


def test_gcc_glued_optimization_level_still_kept(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("gcc -O2 a.c", KEY, pmap, frozenset())
    assert "-O2" in rebuilt.split()


def test_curls_glued_o_with_a_digit_is_dropped_not_a_level(tmp_path):
    """`curl` is not a compiler driver; `-O2`'s `2` is not an
    optimization level there, and drops like any other unsafe digit."""
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("curl -O2", KEY, pmap, frozenset())
    assert "-O2" not in rebuilt
    assert "2" not in _originals(pmap)
