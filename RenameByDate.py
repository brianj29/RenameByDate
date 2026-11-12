#!/usr/bin/env python3
"""Rename image files in a directory tree using embedded capture timestamps."""

import argparse
import os
import re
import sys
from datetime import datetime
from pathlib import Path

try:
    import exifread
except ImportError:  # Report a useful error when the command is run.
    exifread = None


VALID_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".bmp",
    ".tif",
    ".tiff",
    ".heic",
    ".heif",
}

# Check the most specific and reliable EXIF capture fields before generic dates.
DATE_TAG_PRIORITY = (
    "EXIF DateTimeOriginal",
    "EXIF DateTimeDigitized",
    "Image DateTime",
)
DATE_FORMATS = (
    "%Y:%m:%d %H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y/%m/%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
)


def parse_capture_datetime(value):
    """Parse a metadata date value without consulting filesystem timestamps."""
    if value is None:
        return None

    # EXIF values can contain null padding, fractional seconds, or a UTC offset.
    text = str(value).strip().replace("\x00", "").strip()
    if not text:
        return None

    for candidate in (text, re.split(r"[+-]\d{2}:?\d{2}$", text)[0].strip()):
        for date_format in DATE_FORMATS:
            try:
                return datetime.strptime(candidate, date_format)
            except ValueError:
                pass

    # EXIF subsecond and offset tags are sometimes appended to the base timestamp.
    match = re.match(r"^(\d{4}[:/-]\d{2}[:/-]\d{2} \d{2}:\d{2}:\d{2})", text)
    if match:
        for date_format in DATE_FORMATS[:3]:
            try:
                return datetime.strptime(match.group(1), date_format)
            except ValueError:
                pass
    return None


def read_capture_datetime(file_path):
    """Read an embedded capture date from EXIF or other date/time metadata."""
    if exifread is None:
        return None

    try:
        with file_path.open("rb") as image_file:
            tags = exifread.process_file(image_file, details=False)
    except (OSError, ValueError, TypeError, struct_error()):
        # The EXIF reader can reject truncated or malformed image metadata.
        return None
    except Exception:
        # Metadata parser exceptions are treated as unreadable metadata, not fatal.
        return None

    for tag_name in DATE_TAG_PRIORITY:
        value = tags.get(tag_name)
        capture_time = parse_capture_datetime(value)
        if capture_time is not None:
            return capture_time

    # Some formats expose capture dates under other names. Only accept tags
    # explicitly suggesting a date/time, and never inspect file timestamps.
    for tag_name, value in tags.items():
        name = str(tag_name).lower()
        if "date" not in name and "time" not in name:
            continue
        capture_time = parse_capture_datetime(value)
        if capture_time is not None:
            return capture_time

    return None


def struct_error():
    """Return a harmless exception class tuple member for parser compatibility."""
    # Kept as a helper to avoid making the optional metadata dependency mandatory.
    return OSError


def is_image_file(file_path):
    """Return whether the path is a regular file with a supported extension."""
    try:
        return file_path.is_file() and file_path.suffix.lower() in VALID_EXTENSIONS
    except OSError:
        return False


def find_image_files(directory):
    """Recursively list supported image files, in a stable traversal order."""
    image_files = []

    def report_walk_error(error):
        print(f"Error: cannot read directory {error.filename}: {error}", file=sys.stderr)

    for current, dirs, filenames in os.walk(directory, onerror=report_walk_error):
        dirs.sort()
        for filename in sorted(filenames):
            path = Path(current) / filename
            if is_image_file(path):
                image_files.append(path)
    return image_files


def build_target_path(source_path, capture_time):
    """Create a chronological target filename in the source file's directory."""
    timestamp = capture_time.strftime("%Y-%m-%d-%H-%M-%S")
    return source_path.with_name(timestamp + source_path.suffix.lower())


def normalized_path(path):
    """Return a platform-normalized absolute path for collision comparisons."""
    return os.path.normcase(os.path.abspath(os.fspath(path)))


def plan_renames(image_files, verbose):
    """Build rename candidates and classify files without changing the filesystem."""
    candidates = []
    missing_metadata = 0
    collisions = 0
    reserved_targets = set()

    for source_path in image_files:
        if verbose:
            print(f"Processing: {source_path}")

        capture_time = read_capture_datetime(source_path)
        if capture_time is None:
            missing_metadata += 1
            if verbose:
                print("  Skipped: missing or unreadable capture metadata")
            continue

        target_path = build_target_path(source_path, capture_time)
        source_key = normalized_path(source_path)
        target_key = normalized_path(target_path)

        if source_key == target_key:
            if verbose:
                print("  No change: filename already matches the capture timestamp")
            continue

        # Treat both existing files and destinations already claimed in this run
        # as collisions; never overwrite a file, even if it is also being scanned.
        if target_path.exists() or target_key in reserved_targets:
            collisions += 1
            if verbose:
                print(f"  Skipped: collision at {target_path}")
            continue

        reserved_targets.add(target_key)
        candidates.append((source_path, target_path))

    return candidates, missing_metadata, collisions


def perform_renames(candidates, dry_run, verbose):
    """Execute the rename plan or display it in dry-run mode."""
    renamed = 0

    for source_path, target_path in candidates:
        if dry_run:
            renamed += 1
            if verbose:
                print(f"  Would rename: {source_path} -> {target_path}")
            continue

        try:
            # Recheck immediately before the operation to reduce the chance of
            # replacing a file created after planning. os.rename is same-directory.
            if target_path.exists():
                raise FileExistsError(f"target already exists: {target_path}")
            os.rename(source_path, target_path)
        except OSError as error:
            print(f"Error: collision; could not rename {source_path} to {target_path}: {error}", file=sys.stderr)
        else:
            renamed += 1
            if verbose:
                print(f"  Renamed: {source_path} -> {target_path}")

    return renamed


def parse_args(argv=None):
    """Define and parse the command-line options."""
    parser = argparse.ArgumentParser(
        description="Rename images using their embedded capture date and time."
    )
    parser.add_argument("directory", help="directory tree to scan recursively")
    parser.add_argument(
        "-n", "--dry-run", action="store_true",
        help="show planned renames without changing files (implies --verbose)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="show the result for each image file",
    )
    return parser.parse_args(argv)


def main(argv=None):
    """Validate arguments and run the recursive image renamer."""
    args = parse_args(argv)
    verbose = args.verbose or args.dry_run
    directory = Path(args.directory).expanduser()

    if not directory.exists() or not directory.is_dir():
        print(f"Error: directory does not exist or is not a directory: {directory}", file=sys.stderr)
        return 1
    if not os.access(directory, os.R_OK):
        print(f"Error: directory is not readable: {directory}", file=sys.stderr)
        return 1
    if exifread is None:
        print("Error: install the required metadata reader with: pip install exifread", file=sys.stderr)
        return 1

    print(f"Scanning directory: {directory}")
    image_files = find_image_files(directory)
    candidates, missing_metadata, collisions = plan_renames(image_files, verbose)
    renamed = perform_renames(candidates, args.dry_run, verbose)

    print(
        "Summary: total image files found={}, successfully renamed={}, "
        "skipped missing metadata={}, skipped due to collisions={}".format(
            len(image_files), renamed, missing_metadata, collisions
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
