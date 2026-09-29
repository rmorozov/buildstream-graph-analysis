"""UX-1061: a pseudonym is keyed, stable, and keeps the name's shape.

Acceptance test: same key+value across two runs match, a forced
collision grows `k`, the map round-trips, and the key/map files are
0600. Mutation: drop the class from the HMAC input and an element and
a directory of the same name stop being distinguishable.
"""

import hmac as hmac_module
import stat

from bga import anonymize as anon


def test_same_key_and_value_give_the_same_pseudonym_across_two_runs(tmp_path):
    key = anon.load_or_create_key(str(tmp_path))
    pmap1 = anon.PseudonymMap.for_project(str(tmp_path))
    first = anon.pseudonymize("gtk3", "element", key, pmap1)
    pmap1.save()

    # A second "run": fresh key load, fresh map load from disk.
    key2 = anon.load_or_create_key(str(tmp_path))
    pmap2 = anon.PseudonymMap.for_project(str(tmp_path))
    second = anon.pseudonymize("gtk3", "element", key2, pmap2)

    assert first == second
    assert first.startswith("e-")


def test_a_forced_collision_grows_k(tmp_path, monkeypatch):
    key = anon.load_or_create_key(str(tmp_path))
    pmap = anon.PseudonymMap.for_project(str(tmp_path))

    real_token = anon._token

    # Same-band values ("alpha", "delta": both length 5, band 8) so both
    # start at the same k; force every request up to the band's width to
    # the same value, so the second distinct input must grow past the
    # band to stay injective.
    def collide(key, cls, value, alphabet, length):
        band = anon._length_band(len(value))
        base = real_token(key, cls, "forced-collision", alphabet, min(length, band))
        if length <= band:
            return base
        return (base + real_token(key, cls, value, alphabet, length - band))[:length]

    monkeypatch.setattr(anon, "_token", collide)

    first = anon.pseudonymize("alpha", "element", key, pmap)
    second = anon.pseudonymize("delta", "element", key, pmap)

    assert first != second
    assert len(second) > len(first)


def test_the_token_keeps_the_original_length_band(tmp_path):
    """Guard: a `min(band, 4)` regression caps every first-attempt token
    at 4 chars, so a 2-char name and a 90-char one produce the same
    length and the band is not kept (design §6.1)."""
    key = anon.load_or_create_key(str(tmp_path))
    pmap = anon.PseudonymMap.for_project(str(tmp_path))
    prefix_len = len(anon.CLASS_PREFIXES["element"])

    short_token = anon.pseudonymize("ab", "element", key, pmap)
    long_value = "a" * 40
    long_token = anon.pseudonymize(long_value, "element", key, pmap)

    assert len(short_token) - prefix_len == anon._length_band(len("ab"))
    assert len(long_token) - prefix_len == anon._length_band(len(long_value))
    assert len(long_token) > len(short_token)


def test_the_map_round_trips(tmp_path):
    key = anon.load_or_create_key(str(tmp_path))
    pmap = anon.PseudonymMap.for_project(str(tmp_path))
    token = anon.pseudonymize("libfoo", "directory", key, pmap)
    pmap.save()

    reloaded = anon.PseudonymMap.for_project(str(tmp_path))
    assert reloaded.resolve(token) == "directory\0libfoo"


def test_the_key_and_map_files_are_0600(tmp_path):
    key = anon.load_or_create_key(str(tmp_path))
    pmap = anon.PseudonymMap.for_project(str(tmp_path))
    anon.pseudonymize("libfoo", "directory", key, pmap)
    pmap.save()

    key_path = tmp_path / ".bga" / "anon" / "key"
    map_path = tmp_path / ".bga" / "anon" / "map.json"
    assert stat.S_IMODE(key_path.stat().st_mode) == 0o600
    assert stat.S_IMODE(map_path.stat().st_mode) == 0o600


def test_the_path_shape_survives(tmp_path):
    key = anon.load_or_create_key(str(tmp_path))
    pmap = anon.PseudonymMap.for_project(str(tmp_path))
    out = anon.pseudonymize_element_path("base.bst:components/gtk/gtk3.bst", key, pmap)

    junction, _, rest = out.partition(":")
    parts = rest.split("/")
    assert junction.startswith("j-") and junction.endswith(".bst")
    assert len(parts) == 3
    assert parts[0].startswith("d-")
    assert parts[1].startswith("d-")
    assert parts[2].startswith("e-") and parts[2].endswith(".bst")


def test_the_class_salts_the_hmac_so_an_element_and_a_directory_differ(tmp_path):
    """Guard for the named mutation: drop `cls` from the HMAC input and
    an element and a directory of the same name become the same token
    under their prefix, so a reader can link the two namespaces."""
    key = anon.load_or_create_key(str(tmp_path))
    pmap_a = anon.PseudonymMap.for_project(str(tmp_path))
    pmap_a.path = str(tmp_path / "a.json")
    pmap_b = anon.PseudonymMap(str(tmp_path / "b.json"))

    element_token = anon.pseudonymize("gtk3", "element", key, pmap_a)[2:]
    directory_token = anon.pseudonymize("gtk3", "directory", key, pmap_b)[2:]

    assert element_token != directory_token


def test_digest_input_includes_the_class(tmp_path):
    """Direct check on the HMAC input itself, independent of prefix
    collisions: `_digest` must fold `cls` into the message it signs."""
    key = anon.load_or_create_key(str(tmp_path))
    element_digest = anon._digest(key, "element", "gtk3", 0)
    directory_digest = anon._digest(key, "directory", "gtk3", 0)
    assert element_digest != directory_digest
    assert element_digest == hmac_module.new(key, b"element\0gtk3", "sha256").digest()
