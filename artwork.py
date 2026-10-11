"""Validate locally generated artwork before opening the native PNG save dialog."""
import base64
import binascii
import struct


def decode_artwork(data_url):
    prefix = "data:image/png;base64,"
    if not isinstance(data_url, str) or not data_url.startswith(prefix):
        raise ValueError("Export card artwork as a PNG.")
    if len(data_url) > 16 * 1024 * 1024:
        raise ValueError("The card artwork is too large.")
    try:
        data = base64.b64decode(data_url[len(prefix):], validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid PNG data.") from exc
    if (len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n"
            or data[8:16] != b"\x00\x00\x00\rIHDR"
            or struct.unpack(">II", data[16:24]) != (1536, 969)):
        raise ValueError("Card artwork must be 1536 × 969 pixels.")
    return data
