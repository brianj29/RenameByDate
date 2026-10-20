1. Write a Python command-line script named "RenameByDate.py" in this repository. The script should rename image files in a directory tree based on the date and time the image was captured, as stored in the image metadata.

2. Command-line interface:
   - Accept exactly one required argument: the path to a directory to scan.
   - Support the standard help flags: -h and --help.
   - If the wrong number of arguments is supplied, print a usage message to stderr and exit with a non-zero status.
   - If the supplied directory does not exist or is not readable, print an error to stderr and exit with a non-zero status.

3. Directory scan:
   - Recursively scan the given directory tree.
   - Process only image files.
   - Ignore files that are not images and ignore directories.
   - Treat common image file extensions such as .jpg, .jpeg, .png, .gif, .bmp, .tif, .tiff, .heic, .heif as valid image types.
   - Do not use file modification time or directory timestamps as the source of the date; use the embedded image metadata only.

4. Metadata handling:
   - Extract the capture date/time from the image metadata, not from the filesystem timestamp.
   - Prefer EXIF fields such as DateTimeOriginal or DateTimeDigitized when available.
   - If those are absent, fall back to other valid EXIF date metadata if available.
   - If readable capture date/time metadata is not present, skip that file without renaming it.
   - Ignore files whose metadata is unreadable or malformed.

5. Renaming behavior:
   - For each eligible image file, rename it to a filename that sorts chronologically when listed lexicographically.
   - Use a format similar to: YYYY-MM-DD-HH-MM-SS.ext
   - Preserve the original file extension, but normalize the extension to lowercase if appropriate.
   - Example: IMG_1234.jpg -> 2024-05-12-14-32-18.jpg
   - If the image file already has a name matching the target format, leave it unchanged unless it still needs to be renamed for consistency (this case should be handled conservatively and predictably).
   - The script should operate in place; it should not create temporary copies or move files outside the source directory tree.

6. Collision handling:
   - Before renaming any file, check whether the target filename already exists in the target directory or would conflict with another file being renamed in the same run.
   - If a collision would occur, print a clear error message to stderr and skip that file without renaming it.
   - Do not overwrite existing files.
   - If multiple source files would resolve to the same target name, only one may be renamed; the rest must be skipped with a collision error.

7. Output:
   - Print a message indicating which directory is being scanned.
   - At the end, print a summary line reporting:
     - the total number of image files found
     - the number of files successfully renamed
     - the number of files skipped due to missing metadata or collisions
   - Use concise but informative messages for both success and error cases.

8. Portability:
   - The script must run on both Linux and Windows.
   - Use only standard Python libraries.
   - Avoid platform-specific assumptions about path separators or filename handling.

9. Code quality:
   - Include concise but clear comments for each function and for any non-trivial logic.
   - Write readable, maintainable, and well-factored code.
   - Keep logic explicit and avoid unnecessary temporary variables or unnecessary abstraction.

10. Acceptance criteria:
   - The script is executable as a Python CLI script.
   - It scans the directory tree recursively.
   - It reads capture metadata rather than filesystem timestamps.
   - It renames valid files into a sortable chronological naming scheme.
   - It skips unreadable or non-image files.
   - It handles collisions safely.
   - It prints clear status and summary output.
   - It exits with the correct status codes for valid and invalid inputs.
