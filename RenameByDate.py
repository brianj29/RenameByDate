#!/usr/bin/env python3
"""Rename image files based on their embedded capture timestamp."""

import argparse
import os
import struct
import sys
from datetime import datetime
from pathlib import Path

VALID_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "gif",
    "bmp",
    "tif",
    "tiff",
    "heic",
    "heif",
}

DATE_TIME_TAGS = (306, 36867, 36868)


def parse_args():
    """Create and parse the command-line arguments."""
    parser = argparse.ArgumentParser(
        description=(
            "Rename image files in a directory tree using the capture date stored in "
            "their embedded metadata."
        )
    )
    parser.add_argument("directory", help="Directory tree to scan for image files.")
    return parser.parse_args()


def normalize_extension(path):
    """Return the file extension in lowercase without the leading dot."""
    return path.suffix.lower().lstrip(".")


def read_u16(data, offset, little_endian):
    """Read a 16-bit unsigned integer from a byte buffer."""
    if offset + 2 > len(data):
        raise ValueError("Unexpected end of data while reading UINT16")
    fmt = "<H" if little_endian else ">H"
    return struct.unpack_from(fmt, data, offset)[0]


def read_u32(data, offset, little_endian):
    """Read a 32-bit unsigned integer from a byte buffer."""
    if offset + 4 > len(data):
        raise ValueError("Unexpected end of data while reading UINT32")
    fmt = "<I" if little_endian else ">I"
    return struct.unpack_from(fmt, data, offset)[0]


def decode_tiff_value(data, entry_offset, data_type, count, value_or_offset, little_endian):
    """Decode a TIFF/EXIF tag value from the field data."""
    type_sizes = {
        1: 1,
        2: 1,
        3: 2,
        4: 4,
        5: 8,
        7: 1,
        9: 4,
        10: 8,
    }

    size = type_sizes.get(data_type)
    if size is None:
        return None

    total_size = count * size
    if total_size <= 4:
        raw = data[entry_offset + 8 : entry_offset + 8 + total_size]
        if len(raw) < total_size:
            raw = raw.ljust(total_size, b"\x00")
    else:
        if value_or_offset + total_size > len(data):
            return None
        raw = data[value_or_offset : value_or_offset + total_size]

    if data_type == 2:
        return raw.split(b"\x00", 1)[0].decode("utf-8", errors="replace").strip()

    if data_type == 3:
        values = [read_u16(raw, idx * 2, little_endian) for idx in range(count)]
        return values[0] if count == 1 else values

    if data_type == 4:
        values = [read_u32(raw, idx * 4, little_endian) for idx in range(count)]
        return values[0] if count == 1 else values

    if data_type == 5:
        values = []
        for idx in range(count):
            pos = idx * 8
            numerator = read_u32(raw, pos, little_endian)
            denominator = read_u32(raw, pos + 4, little_endian)
            values.append((numerator, denominator))
        return values[0] if count == 1 else values

    if data_type in (1, 7):
        return raw[:count] if count == 1 else raw

    return None


def parse_ifd(data, ifd_offset, little_endian):
    """Parse a TIFF IFD and return a dictionary of tag values."""
    if ifd_offset < 0 or ifd_offset + 2 > len(data):
        return {}

    entry_count = read_u16(data, ifd_offset, little_endian)
    tags = {}

    for i in range(entry_count):
        entry_offset = ifd_offset + 2 + (i * 12)
        if entry_offset + 12 > len(data):
            break

        tag = read_u16(data, entry_offset, little_endian)
        data_type = read_u16(data, entry_offset + 2, little_endian)
        count = read_u32(data, entry_offset + 4, little_endian)
        value_or_offset = read_u32(data, entry_offset + 8, little_endian)
        value = decode_tiff_value(data, entry_offset, data_type, count, value_or_offset, little_endian)
        tags[tag] = value

    next_ifd_offset = ifd_offset + 2 + (entry_count * 12)
    if next_ifd_offset + 4 <= len(data):
        next_ifd = read_u32(data, next_ifd_offset, little_endian)
        if next_ifd != 0:
            tags["__next_ifd__"] = next_ifd

    return tags


def normalize_capture_value(value):
    """Normalize EXIF date strings into a standard datetime string."""
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        if not value:
            return None
        value = value[0]

    if not isinstance(value, str):
        value = str(value)

    cleaned = value.strip().replace("\x00", "").strip()
    if not cleaned:
        return None

    for fmt in (
        "%Y:%m:%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
    ):
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue

    return None


def parse_exif_from_tiff(data):
    """Read EXIF date tags from TIFF-derived EXIF data."""
    if len(data) < 8:
        return None

    byte_order = data[:2]
    if byte_order == b"II":
        little_endian = True
    elif byte_order == b"MM":
        little_endian = False
    else:
        return None

    try:
        if read_u16(data, 2, little_endian) != 42:
            return None
    except ValueError:
        return None

    try:
        first_ifd_offset = read_u32(data, 4, little_endian)
    except ValueError:
        return None

    if first_ifd_offset < 8 or first_ifd_offset >= len(data):
        return None

    first_ifd = parse_ifd(data, first_ifd_offset, little_endian)
    if not first_ifd:
        return None

    candidate_values = []
    for tag in DATE_TIME_TAGS:
        if tag in first_ifd:
            candidate_values.append(normalize_capture_value(first_ifd[tag]))

    exif_ifd_offset = first_ifd.get(0x8769)
    if isinstance(exif_ifd_offset, (int, float)):
        exif_ifd = parse_ifd(data, int(exif_ifd_offset), little_endian)
        for tag in DATE_TIME_TAGS:
            if tag in exif_ifd:
                candidate_values.append(normalize_capture_value(exif_ifd[tag]))

    for value in candidate_values:
        if value is not None:
            return value

    return None


def extract_capture_datetime(path):
    """Extract the image capture datetime from embedded metadata if available."""
    try:
        with open(path, "rb") as handle:
            content = handle.read()
    except OSError:
        return None

    if not content:
        return None

    # JPEG files store EXIF data in APP1 segments after the SOI marker.
    if content.startswith(b"\xFF\xD8"):
        offset = 2
        while offset + 4 <= len(content):
            if content[offset] != 0xFF:
                break
            marker = content[offset + 1]
            if marker == 0xD9:
                break
            if marker == 0xDA:
                break

            if offset + 4 > len(content):
                break
            segment_length = (content[offset + 2] << 8) | content[offset + 3]
            if segment_length < 2:
                break

            segment_start = offset + 4
            segment_end = segment_start + segment_length - 2
            if segment_end > len(content):
                break

            if marker == 0xE1 and content[segment_start : segment_start + 6] == b"Exif\x00\x00":
                exif_data = content[segment_start + 6 : segment_end]
                dt = parse_exif_from_tiff(exif_data)
                if dt is not None:
                    return dt

            offset = segment_end + 2

        return None

    # PNG EXIF data is stored in an eXIf chunk.
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        offset = 8
        while offset + 8 <= len(content):
            chunk_length = struct.unpack(">I", content[offset : offset + 4])[0]
            chunk_type = content[offset + 4 : offset + 8]
            chunk_data_start = offset + 8
            chunk_data_end = chunk_data_start + chunk_length
            if chunk_data_end + 4 > len(content):
                break

            if chunk_type == b"eXIf":
                dt = parse_exif_from_tiff(content[chunk_data_start : chunk_data_end])
                if dt is not None:
                    return dt

            offset = chunk_data_end + 4

        return None

    # TIFF and TIFF-based formats store tags directly in the file header.
    if content[:2] in (b"II", b"MM"):
        return parse_exif_from_tiff(content)

    return None


def iter_image_files(root_path):
    """Yield valid image files under the provided directory tree."""
    for current, _, files in os.walk(root_path, topdown=True):
        for name in files:
            file_path = Path(current) / name
            if normalize_extension(file_path) in VALID_EXTENSIONS:
                yield file_path


def build_target_name(capture_datetime, original_path):
    """Generate a timestamp-based filename while preserving the original extension."""
    extension = original_path.suffix.lower()
    timestamp = capture_datetime.strftime("%Y-%m-%d-%H-%M-%S")
    return f"{timestamp}{extension}"


def main(argv):
    """Run the CLI program."""
    args = parse_args()
    directory = Path(args.directory)

    if not directory.exists() or not directory.is_dir():
        print(f"Error: directory does not exist or is not a directory: {directory}", file=sys.stderr)
        return 1

    if not os.access(directory, os.R_OK):
        print(f"Error: directory is not readable: {directory}", file=sys.stderr)
        return 1

    print(f"Scanning directory: {directory}")

    total_image_files = 0
    renamed_count = 0
    metadata_missing_count = 0
    collision_count = 0
    reserved_targets = set()

    for image_path in iter_image_files(directory):
        total_image_files += 1
        capture_datetime = extract_capture_datetime(image_path)

        if capture_datetime is None:
            print(f"Skipping file with missing or unreadable metadata: {image_path}")
            metadata_missing_count += 1
            continue

        target_name = build_target_name(capture_datetime, image_path)
        target_path = image_path.with_name(target_name)
        target_key = os.path.normcase(os.path.normpath(str(target_path)))

        if target_path == image_path:
            print(f"No rename needed for file: {image_path}")
            continue

        if target_path.exists() or target_key in reserved_targets:
            print(f"Collision detected; skipping file: {image_path} -> {target_path}")
            collision_count += 1
            continue

        reserved_targets.add(target_key)
        try:
            os.rename(image_path, target_path)
        except OSError:
            print(f"Collision detected; skipping file: {image_path} -> {target_path}")
            collision_count += 1
            reserved_targets.discard(target_key)
            continue

        print(f"Renamed: {image_path} -> {target_path}")
        renamed_count += 1

    print(
        "Summary: "
        f"total image files found={total_image_files}, "
        f"successfully renamed={renamed_count}, "
        f"skipped missing metadata={metadata_missing_count}, "
        f"skipped collisions={collision_count}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main(sys.argv))
    except KeyboardInterrupt:
        print("Interrupted by user.", file=sys.stderr)
        raise SystemExit(1)
