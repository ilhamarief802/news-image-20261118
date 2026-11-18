#!/usr/bin/env python3
"""make.fun entry news-image-20261118.

Copies the one news image (entry.png, next to this file) into the output
directory and self-checks the result: PNG signature, size <= 1 MiB,
dimensions <= 1024x1024. Standard library only, no network, deterministic.
"""

import os
import struct
import sys
from pathlib import Path

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_BYTES = 1_048_576  # 1 MiB
MAX_DIM = 1024


def fail(message: str):
    """Print a clear error and exit non-zero (the caller never continues)."""
    print("error: " + message, file=sys.stderr)
    sys.exit(1)


def check_png(data: bytes, path: "os.PathLike[str] | str") -> tuple[int, int]:
    """Verify the PNG constraints; exit non-zero with a clear message if not.

    Returns the (width, height) read from IHDR on success.
    """
    if len(data) < 24:
        fail(f"{path}: too small to be a PNG ({len(data)} bytes)")

    if not data.startswith(PNG_SIGNATURE):
        fail(f"{path}: missing PNG signature (first bytes: {data[:8]!r})")

    if len(data) > MAX_BYTES:
        fail(f"{path}: {len(data)} bytes exceeds the {MAX_BYTES}-byte limit")

    # IHDR always starts at offset 8: 4-byte length, 4-byte type, then data.
    length, ihdr_type = struct.unpack(">I4s", data[8:16])
    if ihdr_type != b"IHDR":
        fail(f"{path}: first chunk is {ihdr_type!r}, expected IHDR")
    if length < 13:
        fail(f"{path}: IHDR length {length} is too short")

    width, height = struct.unpack(">II", data[16:24])
    if width > MAX_DIM or height > MAX_DIM:
        fail(f"{path}: dimensions {width}x{height} exceed the {MAX_DIM}x{MAX_DIM} limit")

    # A whole PNG ends with a zero-length IEND chunk (plus its CRC).
    if data[-12:-8] != b"\x00\x00\x00\x00" or data[-8:-4] != b"IEND":
        fail(f"{path}: does not end with an IEND chunk (truncated PNG?)")

    return width, height


def main() -> None:
    source = Path(__file__).resolve().parent / "entry.png"

    try:
        data = source.read_bytes()
    except FileNotFoundError:
        fail(f"entry.png not found next to main.py (looked for {source})")
    except OSError as exc:
        fail(f"cannot read {source}: {exc}")

    check_png(data, source)

    out_dir = Path(os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output")
    try:
        out_dir.mkdir(parents=True, exist_ok=True)
        target = out_dir / "entry.png"
        target.write_bytes(data)
    except OSError as exc:
        fail(f"cannot write to {out_dir}: {exc}")

    # Re-read what landed on disk and check that, not just what we held in memory.
    written = target.read_bytes()
    if written != data:
        fail(f"{target}: content on disk differs from what was written")
    width, height = check_png(written, target)

    print(f"wrote {target} ({len(written)} bytes, {width}x{height})")


if __name__ == "__main__":
    main()
