You are working in the repo root for the project "RenameByDate".

Create a Python command-line script named "RenameByDate.py" in this repository.

Goal:
Rename image files in a directory tree based on the date and time the image was captured, using the embedded metadata in the image file itself rather than filesystem timestamps.

Requirements:
1. The script must accept exactly one required argument: the path to a directory to scan.
2. Support the standard help flags: -h and --help.
3. If the wrong number of arguments is provided, print a usage message to stderr and exit with a non-zero status.
4. If the directory does not exist or cannot be read, print an error to stderr and exit with a non-zero status.
5. Recursively scan the provided directory tree.
6. Process only image files. Ignore non-image files and directories.
7. Treat common image extensions such as .jpg, .jpeg, .png, .gif, .bmp, .tif, .tiff, .heic, and .heif as valid image types.
8. For each eligible image file, extract the capture date/time from embedded image metadata, not from the file's modification time or creation time.
9. Prefer EXIF metadata fields such as DateTimeOriginal and DateTimeDigitized when available.
10. If those fields are absent, fall back to other valid image metadata fields that indicate capture date/time, if available.
11. If the file has no usable capture date/time metadata, skip it without renaming it.
12. Ignore files whose metadata is unreadable, malformed, or missing.
13. Rename each eligible file to a name that sorts chronologically when listed lexicographically.
14. Use a naming format similar to: YYYY-MM-DD-HH-MM-SS.ext
15. Preserve the original file extension, normalized to lowercase if appropriate.
16. Example: IMG_1234.jpg -> 2024-05-12-14-32-18.jpg
17. If a target filename would collide with an existing file, or with another file being renamed in the same run, print a clear error and skip that file without overwriting anything.
18. Do not rename files when a collision would occur.
19. If multiple files would resolve to the same target name, only one may be renamed; the others must be skipped with a collision error.
20. Print a message indicating which directory is being scanned.
21. At the end, print a summary line showing:
    - total image files found
    - number successfully renamed
    - number skipped due to missing metadata
    - number skipped due to collisions
22. The script must be portable across Linux and Windows.
23. Use only standard Python libraries.
24. Avoid platform-specific path assumptions.
25. Keep the code readable, maintainable, and well-factored.
26. Include clear comments for each function and for any non-trivial logic.
27. Do not add unnecessary temporary files or unnecessary abstraction layers.

Behavioral notes:
- Use the embedded image metadata as the source of truth.
- Do not rely on file creation or modification dates.
- Do not rename files outside the scanned directory tree.
- The script should modify files in place.

Validation criteria:
- The script runs successfully in Python on both Linux and Windows.
- It scans directories recursively.
- It renames valid files into a sortable time-based filename format.
- It skips files with missing or unreadable metadata.
- It avoids overwriting files and handles collisions safely.
- It prints clear status and summary output.
- It exits with non-zero status for invalid CLI usage or unreadable directories.

Important:
- Ask for clarification only if a required behavior is genuinely ambiguous.
- Otherwise, proceed with the implementation and make reasonable assumptions that align with the requirements above.
- Favor correctness, clarity, and maintainability over cleverness.
