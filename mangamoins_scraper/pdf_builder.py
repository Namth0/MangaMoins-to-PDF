"""Assemble downloaded page images into a single PDF file."""

from __future__ import annotations

from io import BytesIO
from pathlib import Path

import img2pdf
from PIL import Image


def _normalize_to_pdf_input(data: bytes) -> bytes:
    """img2pdf doesn't support WEBP directly, so re-encode it as PNG."""
    is_webp = data[:4] == b"RIFF" and data[8:12] == b"WEBP"
    if not is_webp:
        return data

    image = Image.open(BytesIO(data)).convert("RGB")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def build_pdf(images: list[bytes], output_path: Path) -> None:
    if not images:
        raise ValueError("Aucune image à assembler en PDF")

    pdf_inputs = [_normalize_to_pdf_input(data) for data in images]
    pdf_bytes = img2pdf.convert(pdf_inputs)
    output_path.write_bytes(pdf_bytes)
