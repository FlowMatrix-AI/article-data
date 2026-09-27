import hashlib
from pathlib import Path

import pytest

from article_data import fetch


class FakeResponse:
    def __init__(self, body: bytes):
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def raise_for_status(self):
        pass

    def iter_content(self, chunk: int):
        yield self.body


def source(body: bytes, sha256: str | None = None) -> fetch.Source:
    return fetch.Source(
        name="t",
        url="https://example.invalid/t.bin",
        filename="t.bin",
        sha256=sha256 or hashlib.sha256(body).hexdigest(),
        licence="test",
        group="g",
    )


@pytest.fixture
def served(monkeypatch: pytest.MonkeyPatch):
    calls: list[str] = []

    def fake_get(url: str, **_):
        calls.append(url)
        return FakeResponse(b"payload")

    monkeypatch.setattr(fetch.requests, "get", fake_get)
    return calls


def test_verified_download_lands_under_its_group_and_leaves_no_part_file(tmp_path: Path, served):
    dest = fetch.fetch(source(b"payload"), tmp_path)
    assert dest == tmp_path / "g" / "t.bin"
    assert dest.read_bytes() == b"payload"
    assert not list(tmp_path.glob("**/*.part"))


def test_checksum_mismatch_raises_and_keeps_nothing(tmp_path: Path, served):
    with pytest.raises(fetch.ChecksumMismatch):
        fetch.fetch(source(b"payload", sha256="0" * 64), tmp_path)
    assert not [p for p in tmp_path.glob("**/*") if p.is_file()]


def test_existing_verified_file_is_not_downloaded_again(tmp_path: Path, served):
    src = source(b"payload")
    fetch.fetch(src, tmp_path)
    fetch.fetch(src, tmp_path)
    assert len(served) == 1


def test_existing_file_with_wrong_bytes_is_replaced(tmp_path: Path, served):
    src = source(b"payload")
    dest = src.path(tmp_path)
    dest.parent.mkdir(parents=True)
    dest.write_bytes(b"stale")
    fetch.fetch(src, tmp_path)
    assert dest.read_bytes() == b"payload"
    assert len(served) == 1


def test_groups_expand_and_unknown_names_are_refused():
    assert [s.name for s in fetch.resolve(["acs"])] == fetch.GROUPS["acs"]
    assert [s.name for s in fetch.resolve(["eia861_2024"])] == ["eia861_2024"]
    with pytest.raises(KeyError):
        fetch.resolve(["nope"])


def test_every_source_records_a_url_checksum_and_licence():
    for s in fetch.SOURCES.values():
        assert s.url.startswith("https://")
        assert len(s.sha256) == 64 and int(s.sha256, 16) >= 0
        assert s.licence
