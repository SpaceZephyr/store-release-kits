#!/usr/bin/env python3
"""Dependency-free PNG/JPEG metadata reader."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import struct


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
JPEG_SOF_MARKERS = {
    0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
    0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF,
}


@dataclass(frozen=True)
class ImageInfo:
    format: str
    width: int
    height: int
    has_alpha: bool
    bit_depth: int | None = None
    color_type: int | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def read_image_info(path: str | Path) -> ImageInfo:
    image_path = Path(path)
    data = image_path.read_bytes()
    if data.startswith(PNG_SIGNATURE):
        return _read_png(data, image_path)
    if data.startswith(b"\xff\xd8"):
        return _read_jpeg(data, image_path)
    raise ValueError(f"Unsupported image format: {image_path}")


def _read_png(data: bytes, path: Path) -> ImageInfo:
    if len(data) < 33 or data[12:16] != b"IHDR":
        raise ValueError(f"Invalid PNG header: {path}")
    width, height, bit_depth, color_type, _, _, _ = struct.unpack(
        ">IIBBBBB", data[16:29]
    )
    return ImageInfo(
        format="PNG",
        width=width,
        height=height,
        has_alpha=color_type in {4, 6} or b"tRNS" in data,
        bit_depth=bit_depth,
        color_type=color_type,
    )


def _read_jpeg(data: bytes, path: Path) -> ImageInfo:
    offset = 2
    while offset + 3 < len(data):
        if data[offset] != 0xFF:
            offset += 1
            continue
        while offset < len(data) and data[offset] == 0xFF:
            offset += 1
        if offset >= len(data):
            break
        marker = data[offset]
        offset += 1
        if marker in {0x01, 0xD8, 0xD9} or 0xD0 <= marker <= 0xD7:
            continue
        if offset + 2 > len(data):
            break
        segment_length = struct.unpack(">H", data[offset : offset + 2])[0]
        if segment_length < 2 or offset + segment_length > len(data):
            break
        if marker in JPEG_SOF_MARKERS:
            if segment_length < 7:
                break
            bit_depth = data[offset + 2]
            height, width = struct.unpack(">HH", data[offset + 3 : offset + 7])
            return ImageInfo("JPEG", width, height, False, bit_depth)
        offset += segment_length
    raise ValueError(f"Could not find JPEG dimensions: {path}")

