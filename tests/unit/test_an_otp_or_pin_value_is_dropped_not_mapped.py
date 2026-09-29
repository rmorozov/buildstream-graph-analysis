"""UX-1088: an unrecognized numeric value is dropped, not mapped.

UX-1084 made a numeric value default to pseudonymize; the #298
re-review found that still put a real secret (`--otp=123456`,
`--pin=1234`) in `PseudonymMap`, reversible by design. `otp`/`pin`
(and `passcode`/`mfa`/`totp`) join `_CREDENTIAL_NAME`, and `_value`'s
default for an unsafe digit-only value is now drop, matching the
credential path: `<dropped>`, never the map. A safe (binary, option)
pair - make-like `-j`/`-l`, a compiler's glued `-O<digit>`,
`JOBS`/`CMAKE_BUILD_PARALLEL_LEVEL` - still keeps its value.
Mutation: restore `_value`'s digit branch to
`pseudonymize_identifier` unconditionally, and an unsafe numeric
value re-enters the map.
"""

from bga import anonymize as anon

KEY = bytes(range(32))


def _pmap(tmp_path):
    return anon.PseudonymMap(str(tmp_path / "map.json"))


def _originals(pmap):
    return {v.partition("\0")[2] for v in pmap._forward.values()}


def test_an_otp_value_is_dropped_not_mapped(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("curl --otp=123456", KEY, pmap, frozenset())
    assert "123456" not in rebuilt
    assert "<dropped>" in rebuilt
    assert "123456" not in _originals(pmap)


def test_a_pin_value_is_dropped_not_mapped(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("curl --pin=1234", KEY, pmap, frozenset())
    assert "1234" not in rebuilt
    assert "<dropped>" in rebuilt
    assert "1234" not in _originals(pmap)


def test_a_non_numeric_otp_value_drops_on_its_name_not_its_shape(tmp_path):
    """`abc12` is neither digit-only nor high-entropy (too short for
    `_HIGH_ENTROPY`); only `otp` on `_CREDENTIAL_NAME` catches it."""
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("curl --otp=abc12", KEY, pmap, frozenset())
    assert "abc12" not in rebuilt
    assert "<dropped>" in rebuilt
    assert "abc12" not in _originals(pmap)


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
    rebuilt = anon.rebuild_command("cmake -DCMAKE_BUILD_PARALLEL_LEVEL=8", KEY, pmap, frozenset())
    assert rebuilt.endswith("=8")


def test_a_compilers_glued_library_count_is_dropped_not_a_load_average(tmp_path):
    """`-l1234` links `lib1234`; only `make`'s `-l` is a load average -
    off `make`, the digits drop, never reaching the map."""
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("gcc -l1234 a.c", KEY, pmap, frozenset())
    assert "1234" not in rebuilt
    assert "-l1234" not in rebuilt
    assert "1234" not in _originals(pmap)


def test_an_output_filename_off_the_o_flag_is_dropped_not_a_level(tmp_path):
    """`curl -O 12345` writes to a file literally named `12345`; `-O`
    never grants its positional value safety, on any binary."""
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("curl -O 12345", KEY, pmap, frozenset())
    assert "12345" not in rebuilt
    assert "12345" not in _originals(pmap)


def test_a_space_form_load_average_value_follows_make(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("make -l 4", KEY, pmap, frozenset())
    assert rebuilt.endswith("-l 4")
