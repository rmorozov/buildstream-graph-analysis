"""UX-1089: a single-dash flag glued to = goes through the numeric rule.

Verifier finding on 1a498516: `_flag_argument`'s glued fallback passes
the literal `"=value"` (equals sign included) to `_value`, whose
`.isdigit()` fails on it - `-j=123456` fell all the way to
`pseudonymize_identifier`, mapping `=123456` verbatim. A short flag
(`-j`, `-l`, `-O`) is too narrow for `_NAMED_FLAG`'s three-char
lookahead to catch glued with `=`, so it never reached the
(binary, option) safety check `--flag=value` already gets. `-X=value`
now splits at the first `=` like every long-form flag, before the
plain-glued fallback.
Mutation: drop the `if equals:` branch, and `-j=123456` maps again.
"""

from bga import anonymize as anon

KEY = bytes(range(32))


def _pmap(tmp_path):
    return anon.PseudonymMap(str(tmp_path / "map.json"))


def _originals(pmap):
    return {v.partition("\0")[2] for v in pmap._forward.values()}


def test_curls_glued_equals_jobs_value_drops_not_maps(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("curl -j=123456", KEY, pmap, frozenset())
    assert "123456" not in rebuilt
    assert "<dropped>" in rebuilt
    assert "123456" not in _originals(pmap)
    assert "=123456" not in _originals(pmap)


def test_a_private_tools_glued_equals_load_average_drops(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("acme -l=4321", KEY, pmap, frozenset())
    assert "4321" not in rebuilt
    assert "4321" not in _originals(pmap)


def test_a_glued_equals_o_value_drops_off_a_compiler(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("tool -O=99", KEY, pmap, frozenset())
    assert "99" not in rebuilt
    assert "99" not in _originals(pmap)


def test_makes_glued_equals_jobs_value_is_kept(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("make -j=8", KEY, pmap, frozenset())
    assert rebuilt.endswith("-j=8")
