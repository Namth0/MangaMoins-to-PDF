from io import BytesIO

import pytest
from PIL import Image

from mangamoins_scraper.pdf_builder import _normalize_to_pdf_input, build_pdf


def _make_image_bytes(fmt: str, color: str) -> bytes:
    image = Image.new("RGB", (10, 10), color=color)
    buffer = BytesIO()
    image.save(buffer, format=fmt)
    return buffer.getvalue()


class TestNormalizeToPdfInput:
    def test_passes_through_non_webp(self):
        data = _make_image_bytes("PNG", "blue")
        assert _normalize_to_pdf_input(data) == data

    def test_converts_webp_to_png(self):
        data = _make_image_bytes("WEBP", "red")
        result = _normalize_to_pdf_input(data)
        assert result != data
        assert result[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic number

    def test_ignores_data_too_short_to_be_webp(self):
        assert _normalize_to_pdf_input(b"") == b""
        assert _normalize_to_pdf_input(b"\x00\x01") == b"\x00\x01"


class TestBuildPdf:
    def test_raises_on_empty_list(self, tmp_path):
        with pytest.raises(ValueError):
            build_pdf([], tmp_path / "out.pdf")

    def test_builds_pdf_from_single_image(self, tmp_path):
        output = tmp_path / "out.pdf"
        build_pdf([_make_image_bytes("PNG", "green")], output)
        assert output.exists()
        assert output.read_bytes()[:5] == b"%PDF-"

    def test_builds_pdf_from_mixed_formats(self, tmp_path):
        images = [_make_image_bytes("PNG", "blue"), _make_image_bytes("WEBP", "red")]
        output = tmp_path / "out.pdf"
        build_pdf(images, output)
        assert output.exists()
        assert output.read_bytes()[:5] == b"%PDF-"
