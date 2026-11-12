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
    """Return (capture datetime, parser error) from the image's embedded metadata."""
    if exifread is None:
        return None, "the exifread package is not installed"

    try:
        with file_path.open("rb") as image_file:
            tags = exifread.process_file(image_file, details=False)
    except Exception as error:
        return None, str(error) or error.__class__.__name__

    for tag_name in DATE_TAG_PRIORITY:
        capture_time = parse_capture_datetime(tags.get(tag_name))
        if capture_time is not None:
            return capture_time, None

    # Some formats expose capture dates under other names. Only accept tags
    # explicitly suggesting a date/time, and never inspect file timestamps.
    for tag_name, value in tags.items():
        name = str(tag_name).lower()
        if "date" not in name and "time" not in name:
            continue
        capture_time = parse_capture_datetime(value)
        if capture_time is not None:
            return capture_time, None

    return None, None


def is_image_file(file_path):
    """Return whether the path is a regular file with a supported extension."""
    try:
        return file_path.is_file() and file_path.suffix.lower() in VALID_EXTENSIONS
    except OSError:
        return False


def find_files(directory, verbose=False):
    """Collect files and image files; in verbose mode report every file encountered."""
    all_files = []
    image_files = []

    def report_walk_error(error):
        failed_path = error.filename or directory
        print(f"Error: cannot read directory {failed_path}: {error}", file=sys.stderr)

    for current, dirs, filenames in os.walk(directory, onerror=report_walk_error):
        dirs.sort()
        for filename in sorted(filenames):
            path = Path(current) / filename
            all_files.append(path)
            if is_image_file(path):
                image_files.append(path)
                if verbose:
                    print(f"Found image file: {path}")
            elif verbose:
                print(f"Ignoring non-image file: {path}")

    return all_files, image_files


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
            print(f"Processing image: {source_path}")

        capture_time, metadata_error = read_capture_datetime(source_path)
        if metadata_error is not None:
            print(f"Error: could not read metadata for {source_path}: {metadata_error}", file=sys.stderr)
            missing_metadata += 1
            continue
        if capture_time is None:
            missing_metadata += 1
            if verbose:
                print(f"  Skipped: no usable capture metadata in {source_path}")
            continue

        target_path = build_target_path(source_path, capture_time)
        source_key = normalized_path(source_path)
        target_key = normalized_path(target_path)

        if source_key == target_key:
            if verbose:
                print(f"  No change: {source_path} already matches the capture timestamp")
            continue

        # Treat existing files and destinations already claimed in this run as
        # collisions; never overwrite a file.
        if target_path.exists() or target_key in reserved_targets:
            collisions += 1
            print(f"Error: collision for file {source_path}: target already exists or is reserved: {target_path}", file=sys.stderr)
            continue

        reserved_targets.add(target_key)
        candidates.append((source_path, target_path))

    return candidates, missing_metadata, collisions


def perform_renames(candidates, dry_run, verbose):
    """Execute the rename plan or display it in dry-run mode."""
    renamed = 0
    collisions = 0

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
            collisions += 1
            print(
                f"Error: could not rename file {source_path} to {target_path}: {error}",
                file=sys.stderr,
            )
        else:
            renamed += 1
            if verbose:
                print(f"  Renamed: {source_path} -> {target_path}")

    return renamed, collisions


def print_summary(total_files, total_images, renamed, missing_metadata, collisions):
    """Print a compact two-column summary table for the completed scan."""
    rows = (
        ("Total files found", total_files),
        ("Image files found", total_images),
        ("Successfully renamed", renamed),
        ("Skipped: missing metadata", missing_metadata),
        ("Skipped: collisions", collisions),
    )
    label_width = max(len(label) for label, _ in rows)
    count_width = max(len("Count"), max(len(str(count)) for _, count in rows))
    separator = f"+{'-' * (label_width + 2)}+{'-' * (count_width + 2)}+"

    print("Summary:")
    print(separator)
    print(f"| {'Item':<{label_width}} | {'Count':>{count_width}} |")
    print(separator)
    for label, count in rows:
        print(f"| {label:<{label_width}} | {count:>{count_width}} |")
    print(separator)


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
        help="show a status line for every file encountered",
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
    all_files, image_files = find_files(directory, verbose=verbose)
    candidates, missing_metadata, planned_collisions = plan_renames(image_files, verbose)
    renamed, runtime_collisions = perform_renames(candidates, args.dry_run, verbose)
    print_summary(
        total_files=len(all_files),
        total_images=len(image_files),
        renamed=renamed,
        missing_metadata=missing_metadata,
        collisions=planned_collisions + runtime_collisions,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
