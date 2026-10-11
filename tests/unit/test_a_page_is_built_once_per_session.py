"""`UX-1349`: a browser page is built once per test session and shared."""

import os
import pathlib
import uuid

import pages
import pytest

import tools.bga_view as view

SHAPE = ("--layers", "2", "--width", "3")


@pytest.fixture
def exports(monkeypatch, tmp_path):
    monkeypatch.setenv("PYTEST_XDIST_TESTRUNUID", f"guard-{uuid.uuid4().hex}")
    monkeypatch.setattr("tempfile.tempdir", str(tmp_path))
    calls = []
    real = view.export

    def counted(*args, **kwargs):
        calls.append(args)
        return real(*args, **kwargs)

    monkeypatch.setattr(view, "export", counted)
    return calls


def test_one_fixture_is_exported_once(exports, tmp_path):
    first = pages.export_uri(pages.FIXTURES["golden"], tmp_path / "d1")
    second = pages.export_uri(pages.FIXTURES["golden"], tmp_path / "d2")
    assert (first, len(exports)) == (second, 1)
    assert not (tmp_path / "d1").exists()


def test_one_shape_is_exported_once(exports):
    assert pages.two_plane_uri(SHAPE) == pages.two_plane_uri(SHAPE)
    assert len(exports) == 1


def test_another_fixture_or_shape_is_another_page(exports):
    assert pages.export_uri(pages.FIXTURES["golden"], "x") != pages.export_uri(pages.FIXTURES["macro_micro"], "x")
    assert len(exports) == 2
    assert pages.two_plane_uri(SHAPE) != pages.two_plane_uri(("--layers", "2", "--width", "4"))
    assert len(exports) == 4


@pytest.mark.parametrize("label", sorted(pages.FIXTURES))
def test_the_shared_page_is_the_fresh_page(exports, tmp_path, label):
    shared = pathlib.Path(pages.export_uri(pages.FIXTURES[label], tmp_path).removeprefix("file://"))
    fresh = pages.export_page(pages.FIXTURES[label], tmp_path / "fresh")
    built = shared.parent.with_name(f".tmp-{os.getpid()}-{shared.parent.name}")  # where `_shared` built it
    swap = (str(built), str(fresh.parent))
    assert shared.read_text(encoding="utf-8").replace(*swap) == fresh.read_text(encoding="utf-8")
