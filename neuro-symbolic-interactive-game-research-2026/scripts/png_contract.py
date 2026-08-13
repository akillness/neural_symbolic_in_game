"""Small dependency-free PNG inspection helpers for retained render evidence."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True)
class PngStats:
    width: int
    height: int
    color_type: int
    unique_colors: int
    opaque_fraction: float
    min_luma: float
    max_luma: float
    mean_luma: float

    def to_jsonable(self) -> dict[str, int | float]:
        return {
            "unique_colors": self.unique_colors,
            "opaque_fraction": round(self.opaque_fraction, 6),
            "min_luma": round(self.min_luma, 6),
            "max_luma": round(self.max_luma, 6),
            "mean_luma": round(self.mean_luma, 6),
        }


def _paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    distance_left = abs(estimate - left)
    distance_up = abs(estimate - up)
    distance_upper_left = abs(estimate - upper_left)
    if distance_left <= distance_up and distance_left <= distance_upper_left:
        return left
    if distance_up <= distance_upper_left:
        return up
    return upper_left


def inspect_png(path: Path) -> PngStats:
    """Decode an 8-bit non-interlaced RGB/RGBA PNG and return visual sanity metrics."""
    payload = path.read_bytes()
    if not payload.startswith(PNG_SIGNATURE):
        raise ValueError(f"not a PNG: {path}")

    offset = len(PNG_SIGNATURE)
    width = height = bit_depth = color_type = interlace = -1
    compressed = bytearray()
    while offset < len(payload):
        if offset + 12 > len(payload):
            raise ValueError(f"truncated PNG chunk: {path}")
        length = struct.unpack(">I", payload[offset : offset + 4])[0]
        chunk_type = payload[offset + 4 : offset + 8]
        chunk_start = offset + 8
        chunk_end = chunk_start + length
        if chunk_end + 4 > len(payload):
            raise ValueError(f"truncated PNG payload: {path}")
        chunk = payload[chunk_start:chunk_end]
        if chunk_type == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(">IIBBBBB", chunk)
        elif chunk_type == b"IDAT":
            compressed.extend(chunk)
        elif chunk_type == b"IEND":
            break
        offset = chunk_end + 4

    if width <= 0 or height <= 0:
        raise ValueError(f"missing PNG dimensions: {path}")
    if bit_depth != 8 or color_type not in {2, 6} or interlace != 0:
        raise ValueError(
            f"unsupported PNG encoding in {path}: depth={bit_depth}, "
            f"color_type={color_type}, interlace={interlace}"
        )

    channels = 3 if color_type == 2 else 4
    stride = width * channels
    decoded = zlib.decompress(bytes(compressed))
    expected = height * (stride + 1)
    if len(decoded) != expected:
        raise ValueError(f"unexpected decoded PNG size for {path}: {len(decoded)} != {expected}")

    prior = bytearray(stride)
    rows: list[bytearray] = []
    cursor = 0
    for _ in range(height):
        filter_type = decoded[cursor]
        cursor += 1
        raw = decoded[cursor : cursor + stride]
        cursor += stride
        reconstructed = bytearray(stride)
        for index, value in enumerate(raw):
            left = reconstructed[index - channels] if index >= channels else 0
            up = prior[index]
            upper_left = prior[index - channels] if index >= channels else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            elif filter_type == 4:
                predictor = _paeth(left, up, upper_left)
            else:
                raise ValueError(f"unsupported PNG filter {filter_type} in {path}")
            reconstructed[index] = (value + predictor) & 0xFF
        rows.append(reconstructed)
        prior = reconstructed

    colors: set[tuple[int, int, int, int]] = set()
    opaque = 0
    luma_total = 0.0
    min_luma = 1.0
    max_luma = 0.0
    pixels = width * height
    for row in rows:
        for offset in range(0, len(row), channels):
            red, green, blue = row[offset : offset + 3]
            alpha = row[offset + 3] if channels == 4 else 255
            colors.add((red, green, blue, alpha))
            opaque += int(alpha == 255)
            luma = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255.0
            luma_total += luma
            min_luma = min(min_luma, luma)
            max_luma = max(max_luma, luma)

    return PngStats(
        width=width,
        height=height,
        color_type=color_type,
        unique_colors=len(colors),
        opaque_fraction=opaque / pixels,
        min_luma=min_luma,
        max_luma=max_luma,
        mean_luma=luma_total / pixels,
    )


def validate_render_png(path: Path, *, width: int = 1280, height: int = 720) -> PngStats:
    """Fail closed on empty, transparent, black, white, or low-information captures."""
    stats = inspect_png(path)
    if (stats.width, stats.height) != (width, height):
        raise ValueError(
            f"unexpected render dimensions for {path}: "
            f"{stats.width}x{stats.height} != {width}x{height}"
        )
    if stats.unique_colors < 32:
        raise ValueError(f"render capture has too few colors ({stats.unique_colors}): {path}")
    if stats.opaque_fraction < 0.99:
        raise ValueError(
            f"render capture is unexpectedly transparent ({stats.opaque_fraction:.4f}): {path}"
        )
    if stats.min_luma > 0.2 or stats.max_luma < 0.7:
        raise ValueError(
            f"render capture lacks expected tonal range "
            f"({stats.min_luma:.3f}..{stats.max_luma:.3f}): {path}"
        )
    if not 0.03 <= stats.mean_luma <= 0.95:
        raise ValueError(f"render capture appears blank ({stats.mean_luma:.3f}): {path}")
    return stats
