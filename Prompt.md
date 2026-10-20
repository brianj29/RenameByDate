Write a python script called "RenameByDate.pl" in this repo which performs the functions described below.

Input:
* A single directory name, supplied on the command line
* Standard -h/--help argument is supported
* Exits with error if given the wrong number of arguments, or the directory is not readable.

Operation:
* Print a message indicating which directory is being scanned.
* Scan the given directory recursively, looking for common image file types (eg. ".jpg").
* For each file found, extract the the date and time it was taken from the embedded metadata (not the file's creation date).
* Ignore non-image files, and files without readable image metadata.
* Rename each file according to its date, so that the filenames will sort lexicographically in temporal order.  Use a format similar to "YYYY-MM-DD-HH-MM-SS.extension."
* Detect file name collisions.  If a file's new name would conflict with an existing file, print an error and skip that file.
* When finished, print a line summarizing the number of files found, and the number renamed.

Other considerations:
* Make it portable across Linux and Windows
* Use standard python libraries for directory traversal, metadata extraction, etc.
* Include concise but informative comments on every subroutine, and on non-trivial steps in the code.
* Use good software engineering practices.  Make the code readable, well factored, and maintainable.  Don't generate temporaries which aren't necessary for correctness or readability.
