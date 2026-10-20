# RenameByDate

Rename image files in a directory tree based on the date and time the image was captured, using the embedded metadata stored in the image file itself.

This script scans a directory recursively, inspects supported image files, extracts the capture timestamp from EXIF metadata, and renames each valid file to a sortable name in the format:

`YYYY-MM-DD-HH-MM-SS.ext`

It intentionally ignores filesystem timestamps and only uses the image's embedded metadata as the source of truth.

## Features

- Recursively scans a supplied directory tree
- Accepts exactly one required directory argument
- Supports standard help flags: `-h` and `--help`
- Recognizes common image formats such as `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tif`, `.tiff`, `.heic`, and `.heif`
- Uses EXIF metadata fields like `DateTimeOriginal` and `DateTimeDigitized` when available
- Falls back to other valid capture-time metadata when needed
- Skips files with missing, malformed, or unreadable metadata
- Avoids overwriting files and skips files that would collide with existing names
- Prints a scan message and final summary
- Works on both Linux and Windows without platform-specific assumptions

## Usage

```bash
python RenameByDate.py /path/to/photos
```

Example:

```bash
python RenameByDate.py "C:/Users/Example/Pictures"
```

## Behavior

For each eligible image file, the script tries to find the capture timestamp from embedded metadata. If it can read a valid date/time, it renames the file to a lexicographically sortable timestamp-based name while preserving the original extension.

Example:

```text
IMG_1234.jpg  ->  2024-05-12-14-32-18.jpg
```

If a file has no usable capture metadata, or if the metadata is unreadable or malformed, it is skipped without being renamed.

If a new name would collide with either:
- an existing file, or
- another file being renamed in the same run,

then the script prints a clear collision message and skips that file without overwriting anything.

## Output

The script prints progress messages while scanning and then ends with a summary such as:

```text
Summary: total image files found=42, successfully renamed=31, skipped missing metadata=8, skipped collisions=3
```

## Notes

- The script uses embedded metadata only; it does not rely on file modification or creation dates.
- It only renames files inside the scanned directory tree.
- It modifies the files in place.
- It exits with a non-zero status for invalid CLI usage or unreadable directories.

## Requirements

- Python 3
- Standard library only
