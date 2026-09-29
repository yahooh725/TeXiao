"""Dependency-light preview renderer used by the engineering MVP."""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def write_png(path: Path, width: int = 512, height: int = 512) -> None:
    pixels = bytearray(width * height * 3)

    def pixel(x: int, y: int, color: tuple[int, int, int]) -> None:
        if 0 <= x < width and 0 <= y < height:
            i = (y * width + x) * 3
            pixels[i:i + 3] = bytes(color)

    def ellipse(cx: float, cy: float, rx: float, ry: float, color: tuple[int, int, int], border: tuple[int, int, int] | None = None, bw: int = 0) -> None:
        for y in range(max(0, int(cy - ry - bw)), min(height, int(cy + ry + bw + 1))):
            for x in range(max(0, int(cx - rx - bw)), min(width, int(cx + rx + bw + 1))):
                d = ((x - cx) / max(rx, 1)) ** 2 + ((y - cy) / max(ry, 1)) ** 2
                if d <= 1:
                    pixel(x, y, color)
                elif border and d <= ((rx + bw) / max(rx, 1)) ** 2:
                    pixel(x, y, border)

    def line(x0: int, y0: int, x1: int, y1: int, color: tuple[int, int, int], width: int = 2) -> None:
        steps = max(abs(x1 - x0), abs(y1 - y0), 1)
        for n in range(steps + 1):
            x = round(x0 + (x1 - x0) * n / steps)
            y = round(y0 + (y1 - y0) * n / steps)
            ellipse(x, y, width, width, color)

    # Background.
    for y in range(height):
        c = (220 - y // 8, 238 - y // 16, 255)
        for x in range(width):
            pixel(x, y, c)
    # Bunny ears behind the face.
    ellipse(188, 130, 48, 128, (247, 200, 213), (123, 75, 82), 5)
    ellipse(324, 130, 48, 128, (247, 200, 213), (123, 75, 82), 5)
    ellipse(188, 130, 20, 92, (255, 240, 245))
    ellipse(324, 130, 20, 92, (255, 240, 245))
    # Face and simple light beauty treatment.
    ellipse(256, 270, 146, 146, (248, 205, 171), (87, 61, 58), 6)
    ellipse(205, 272, 13, 13, (51, 43, 42))
    ellipse(307, 272, 13, 13, (51, 43, 42))
    ellipse(256, 334, 28, 18, (239, 158, 175), (123, 75, 82), 3)
    line(256, 347, 256, 366, (123, 75, 82), 2)
    # Whiskers.
    for side in (-1, 1):
        for dy in (-22, 0, 22):
            line(256 + side * 15, 340, 110 if side < 0 else 402, 340 + dy, (123, 75, 82), 2)
    raw = b"".join(b"\x00" + bytes(pixels[y * width * 3:(y + 1) * width * 3]) for y in range(height))
    png = b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b"")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
