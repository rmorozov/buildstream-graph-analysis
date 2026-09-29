"""UX-1068: a command-line credential is dropped, not kept.

`-D`, `--flag=`/`-flag=` and environment-style `NAME=value` assignments
whose name reads as a credential lose their value to a fixed marker,
never the pseudonym map; a safe-listed numeric assignment (`JOBS`
below) is unaffected, an unsafe one drops too (UX-1088). A verifier
pass on the first close (7eb7e817) found three
further leaks and one regression, closed here: an unlisted name
(`pat`) with a shaped value (`ghp_...`), a space-separated flag+value,
a mixed-case flag name, and a lowercase `a=b` wrongly eaten as an env
prefix. Mutation: drop the credential check and the numeric token
travels.
"""

import collections

from bga import anonymize as anon

KEY = bytes(range(32))


def _pmap(tmp_path):
    return anon.PseudonymMap(str(tmp_path / "map.json"))


def _values(pmap):
    return {v.partition("\0")[2] for v in pmap._forward.values()}


def test_a_dash_d_macro_credential_drops_its_numeric_value(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("cmake -DAPI_TOKEN=12345678", KEY, pmap, frozenset())
    assert "12345678" not in rebuilt
    assert "<dropped>" in rebuilt
    assert "12345678" not in _values(pmap)


def test_a_dash_d_macro_credential_drops_its_text_value(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("cmake -DAPI_TOKEN=s3cr3t", KEY, pmap, frozenset())
    assert "s3cr3t" not in rebuilt
    assert "<dropped>" in rebuilt
    assert "s3cr3t" not in _values(pmap)


def test_a_long_flag_credential_drops_its_value(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("curl --token=12345678", KEY, pmap, frozenset())
    assert "12345678" not in rebuilt
    assert "<dropped>" in rebuilt
    assert "12345678" not in _values(pmap)


def test_a_hyphenated_flag_credential_drops_its_value(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("curl --auth-key=abc", KEY, pmap, frozenset())
    assert "abc" not in rebuilt
    assert "<dropped>" in rebuilt
    assert "abc" not in _values(pmap)


def test_an_environment_style_credential_drops_its_value(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("PASSWORD=hunter2 make", KEY, pmap, frozenset())
    assert "hunter2" not in rebuilt
    assert "<dropped>" in rebuilt
    assert "hunter2" not in _values(pmap)


def test_a_non_credential_numeric_macro_keeps_its_value(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("cmake -DJOBS=4", KEY, pmap, frozenset())
    assert rebuilt.endswith("=4")


def test_the_review_counts_each_credential_drop(tmp_path):
    pmap = _pmap(tmp_path)
    counts = collections.Counter()
    anon.rebuild_command("cmake -DAPI_TOKEN=12345678 --token=x PASSWORD=hunter2", KEY, pmap, frozenset(), counts)
    assert counts["F credential"] == 3


def test_a_shaped_value_drops_even_off_the_name_list(tmp_path):
    """`BUILD_FLAG` is not a credential name; the value's own shape (a
    known GitHub token prefix) is the only reason to drop it."""
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("git -DBUILD_FLAG=ghp_abcdefghijklmnop", KEY, pmap, frozenset())
    assert "ghp_abcdefghijklmnop" not in rebuilt
    assert "<dropped>" in rebuilt
    assert "ghp_abcdefghijklmnop" not in _values(pmap)


def test_a_space_separated_credential_flag_drops_the_next_word(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("curl --api-key 12345678", KEY, pmap, frozenset())
    assert "12345678" not in rebuilt
    assert "<dropped>" in rebuilt
    assert "12345678" not in _values(pmap)


def test_a_mixed_case_flag_name_and_its_continuation_both_drop(tmp_path):
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("curl --Authorization=Bearer abc", KEY, pmap, frozenset())
    assert "Bearer" not in rebuilt
    assert "abc" not in rebuilt
    assert rebuilt.count("<dropped>") == 2
    assert "Bearer" not in _values(pmap) and "abc" not in _values(pmap)


def test_a_lowercase_leading_word_is_the_binary_not_an_env_prefix(tmp_path):
    """Regression: `a=b` is not `[A-Z_][A-Z0-9_]*=`, so it is `argv[0]`
    (position 0 in the rebuilt output), not a consumed env assignment -
    `--flag` stays a flag (dashes kept) at position 1, rather than
    itself becoming a dash-less `b-` binary pseudonym."""
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("a=b --flag x", KEY, pmap, frozenset())
    words = rebuilt.split()
    assert len(words) == 3
    assert words[1].startswith("--")


def test_over_dropping_a_non_credential_named_value_is_accepted(tmp_path):
    """`--sessions=2` is not a secret, but `session` is on the name
    list; over-dropping a plain count is the accepted tradeoff (1068
    verifier), not a false negative on a real credential."""
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("curl --sessions=2", KEY, pmap, frozenset())
    assert rebuilt.endswith("=<dropped>")


def test_a_long_digit_only_value_is_dropped_not_kept(tmp_path):
    """A digit run (a card number's shape) drops like any other
    unsafe numeric value (UX-1088), never entering the map."""
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("cmake -DBUILD=123456789", KEY, pmap, frozenset())
    assert "123456789" not in rebuilt
    assert "<dropped>" in rebuilt
    assert "123456789" not in _values(pmap)


def test_a_short_digit_only_value_off_the_safe_list_is_dropped(tmp_path):
    """UX-1088: a numeric value not on a named safe pair (like `JOBS`
    above) drops rather than pseudonymizes - never reversible in the map."""
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("cmake -DPORT=8080", KEY, pmap, frozenset())
    assert "8080" not in rebuilt
    assert "<dropped>" in rebuilt
    assert "8080" not in _values(pmap)


def test_the_signing_name_alone_drops_a_value_too_short_to_be_shaped(tmp_path):
    """`signing` shares no substring with the original name list: `1234`
    is neither a known token prefix nor high-entropy, so only the added
    name catches it (unlike `apikey`/`private_key`, already covered by
    `key`)."""
    pmap = _pmap(tmp_path)
    rebuilt = anon.rebuild_command("cmake -DSIGNINGNONCE=1234", KEY, pmap, frozenset())
    assert rebuilt.endswith("=<dropped>")
