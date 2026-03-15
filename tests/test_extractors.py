from pathlib import Path

from app.extractors.registry import ExtractorRegistry


def test_extractor_registry_text(tmp_path: Path) -> None:
    f = tmp_path / "note.txt"
    f.write_text("hello extractor", encoding="utf-8")

    result = ExtractorRegistry().extract(f, "text/plain")
    assert result.strategy == "plain_text"
    assert "extractor" in result.text


def test_extractor_registry_fallback(tmp_path: Path) -> None:
    f = tmp_path / "bin.bin"
    f.write_bytes(b"\x00\x01\x02")

    result = ExtractorRegistry().extract(f, "application/octet-stream")
    assert result.strategy == "metadata_only"
    assert result.text == ""
