import json

import pytest

from app import config as C
from app.rag import manifest as M


@pytest.fixture
def data_dir(tmp_path, monkeypatch):
    d = tmp_path / "data"
    d.mkdir()
    monkeypatch.setattr(C, "DATA_PATH", d)
    return d


@pytest.fixture
def manifest_path(tmp_path, monkeypatch):
    p = tmp_path / "persist" / "manifest.json"
    monkeypatch.setattr(C, "MANIFEST_PATH", p)
    monkeypatch.setattr(C, "PERSIST_DIR", p.parent)
    return p


def test_file_hash_same_content_same_hash(tmp_path):
    a = tmp_path / "a.txt"
    b = tmp_path / "b.txt"
    a.write_bytes(b"hello world")
    b.write_bytes(b"hello world")
    assert M.file_hash(a) == M.file_hash(b)


def test_scan_files_only_supported_exts(data_dir, monkeypatch):
    monkeypatch.setattr(C, "SUPPORTED_EXTS", [".txt", ".md"])
    (data_dir / "keep.txt").write_text("a")
    (data_dir / "keep.md").write_text("b")
    (data_dir / "skip.pdf").write_text("c")

    result = M.scan_files()

    assert set(result.keys()) == {"keep.txt", "keep.md"}


def test_scan_files_uses_forward_slashes(data_dir, monkeypatch):
    monkeypatch.setattr(C, "SUPPORTED_EXTS", [".txt"])
    nested = data_dir / "sub" / "dir"
    nested.mkdir(parents=True)
    (nested / "file.txt").write_text("x")

    result = M.scan_files()

    assert "sub/dir/file.txt" in result
    assert all("\\" not in k for k in result)


def test_load_manifest_missing_file_returns_empty(manifest_path):
    assert not manifest_path.exists()
    assert M.load_manifest() == {}


def test_load_manifest_corrupted_json_returns_empty(manifest_path):
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text("{ this is not valid json", encoding="utf-8")

    assert M.load_manifest() == {}


def test_save_and_load_manifest_roundtrip(manifest_path):
    payload = {"a.txt": "beef", "nested/b.md": "cafebabe"}
    M.save_manifest(payload)

    assert manifest_path.exists()
    assert json.loads(manifest_path.read_text(encoding="utf-8")) == payload
    assert M.load_manifest() == payload