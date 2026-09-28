"""UX-1084: a short numeric credential still exports verbatim.

`_value()` used to keep every digit-only value up to six characters, so
`--otp=123456`/`--pin=1234` rode through pseudonymized only by name. The
default inverts: a numeric value pseudonymizes unless its flag is on
`_MAKE_SAFE_FLAGS` *and* argv[0] is a make-like binary, or its `-D`/env
name is on `_MACRO_SAFE_NAMES` (any binary). A first cut keyed safety on
the flag name alone; the verifier found `gcc -l1234` (a linker library)
and `curl -O 12345` (an output filename, via positional inheritance)
both kept verbatim - `-l`/`-O` mean different things off `make`/`gcc`.
Mutation: drop the binary check in `_argument`'s flag/glued-value safety
so any binary's `-l`/`-j` counts as safe, and `gcc -l1234` keeps `1234`.
"""
from bga import anonymize as anon

KEY = bytes(range(32))


def _pmap(tmp_path):
    return anon.PseudonymMap(str(tmp_path / "map.json"))


def _originals(pmap):
    return {v.partition("\0")[2] for v in pmap._forward.values()}


def test_an_otp_value_pseudonymizes_not_kept(tmp_path):
    """Pseudonymized, not dropped: the archive carries no trace, but the
    map (reversible by design) resolves the token back to `123456`."""
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("curl --otp=123456", KEY, pmap, frozenset())
    assert "123456" not in rebuilt
    assert "123456" in _originals(pmap)


def test_a_pin_value_pseudonymizes_not_kept(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("curl --pin=1234", KEY, pmap, frozenset())
    assert "1234" not in rebuilt
    assert "1234" in _originals(pmap)


def test_a_glued_jobs_flag_keeps_its_value(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("make -j8", KEY, pmap, frozenset())
    assert rebuilt.endswith("-j8")


def test_a_long_jobs_flag_keeps_its_value(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("ninja --jobs=4", KEY, pmap, frozenset())
    assert rebuilt.endswith("--jobs=4")


def test_an_optimization_flag_keeps_its_value(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("gcc -O2 a.c", KEY, pmap, frozenset())
    assert "-O2" in rebuilt.split()


def test_a_space_form_jobs_value_follows_its_flag(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("make -j 8", KEY, pmap, frozenset())
    assert rebuilt.endswith("-j 8")


def test_a_parallel_level_macro_keeps_its_value(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command(
        "cmake -DCMAKE_BUILD_PARALLEL_LEVEL=8", KEY, pmap, frozenset())
    assert rebuilt.endswith("=8")


def test_a_compilers_glued_library_count_is_not_a_load_average(tmp_path):
    """`-l1234` links `lib1234`; only `make`'s `-l` is a load average."""
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("gcc -l1234 a.c", KEY, pmap, frozenset())
    assert "1234" not in rebuilt
    assert "-l1234" not in rebuilt


def test_an_output_filename_off_the_o_flag_is_not_a_level(tmp_path):
    """`curl -O 12345` writes to a file literally named `12345`; `-O`
    never grants its positional value safety, on any binary."""
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("curl -O 12345", KEY, pmap, frozenset())
    assert "12345" not in rebuilt


def test_a_space_form_load_average_value_follows_make(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("make -l 4", KEY, pmap, frozenset())
    assert rebuilt.endswith("-l 4")
