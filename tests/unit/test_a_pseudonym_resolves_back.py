"""UX-1064: a pseudonym in any text resolves back to the real name.

Acceptance test: `resolve(anon(text)) == text` on golden fixture uids,
an unknown pseudonym-shaped token is listed rather than dropped, and a
foreign map is refused. Mutation: skip the fingerprint check, and the
foreign map resolves to wrong names.
"""

from bga import anonymize as anon


def test_resolve_round_trips_a_path_embedded_in_free_text(tmp_path):
    key = anon.load_or_create_key(str(tmp_path))
    pmap = anon.PseudonymMap.for_project(str(tmp_path))
    original_path = "base.bst:components/gtk/gtk3.bst"
    token = anon.pseudonymize_element_path(original_path, key, pmap)
    pmap.save()

    text = f"please rebase {token} on main"
    resolved, unknown = anon.resolve_text(text, pmap)

    assert resolved == f"please rebase {original_path} on main"
    assert unknown == []


def test_an_unknown_pseudonym_shaped_token_is_listed_not_dropped(tmp_path):
    key = anon.load_or_create_key(str(tmp_path))
    pmap = anon.PseudonymMap.for_project(str(tmp_path))
    known = anon.pseudonymize("gtk3", "element", key, pmap)
    pmap.save()

    text = f"{known} depends on e-zzzzzz somehow"
    resolved, unknown = anon.resolve_text(text, pmap)

    assert resolved == "gtk3 depends on e-zzzzzz somehow"
    assert unknown == ["e-zzzzzz"]


def test_a_foreign_map_is_refused_on_fingerprint_mismatch(tmp_path):
    project_a = tmp_path / "a"
    project_b = tmp_path / "b"
    project_a.mkdir()
    project_b.mkdir()

    key_a = anon.load_or_create_key(str(project_a))
    key_b = anon.load_or_create_key(str(project_b))
    fingerprint_a = anon.key_fingerprint(key_a)

    pmap_b = anon.PseudonymMap.for_project(str(project_b))
    anon.pseudonymize("gtk3", "element", key_b, pmap_b)
    pmap_b.save()

    import pytest

    with pytest.raises(anon.FingerprintMismatch):
        anon.check_fingerprint(key_b, fingerprint_a)


def test_the_cli_refuses_a_foreign_map_by_fingerprint(tmp_path, monkeypatch, capsys):
    """CLI-level: `bga bundle --resolve` calls `check_fingerprint` before
    ever reading the map. Mutation target - drop that call from
    `_bundle_resolve` and this collision (both projects' first token is
    `e-` plus the HMAC-derived text, made to collide by construction)
    resolves to project B's real name under project A's
    `--key-fingerprint`."""
    from bga import cli

    project_a = tmp_path / "a"
    project_b = tmp_path / "b"
    project_a.mkdir()
    project_b.mkdir()
    (project_b / "project.conf").write_text("name: b\n")

    key_a = anon.load_or_create_key(str(project_a))
    fingerprint_a = anon.key_fingerprint(key_a)

    key_b = anon.load_or_create_key(str(project_b))
    pmap_b = anon.PseudonymMap.for_project(str(project_b))
    token_b = anon.pseudonymize("mesa", "element", key_b, pmap_b)
    pmap_b.save()

    monkeypatch.chdir(project_b)
    monkeypatch.setattr("sys.stdin", __import__("io").StringIO(token_b))
    parser = cli.create_parser()
    args = parser.parse_args(["bundle", "--resolve", "--key-fingerprint", fingerprint_a])

    exit_code = cli.cmd_bundle(args)

    assert exit_code == 2
    assert "does not match" in capsys.readouterr().err
