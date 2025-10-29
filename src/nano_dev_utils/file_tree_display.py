import os
from collections.abc import Generator
from pathlib import Path
import fnmatch

DEFAULT_SFX = '_filetree.txt'


class FileTreeDisplay:
    """Generate and display a visual file tree of a directory.

    This class builds a directory tree structure using `os.scandir()`
    and yields formatted visual representations of directories and files.
    Supports exclusion lists, configurable indentation, and custom prefix styles.
    """

    def __init__(
        self,
        root_dir: str | None = None,
        filepath: str | None = None,
        ignore_dirs: list[str] | set[str] | None = None,
        ignore_files: list[str] | set[str] | None = None,
        style: str = "-",
        indent: int = 1,
        save2file: bool = True,
        printout: bool = False,
    ) -> None:
        """Initialize the FileTreeDisplay instance.

        Args:
            root_dir (str): Root directory to traverse.
            filepath: str | None: full output file path.
            ignore_dirs (list[str] | set[str] | None): Directory names or patterns to ignore.
            ignore_files (list[str] | set[str] | None): File names or patterns to ignore.
            style (str): Character(s) used to represent hierarchy levels. Defaults to "-".
            indent (int): Number of style characters used per hierarchy level. Defaults to 2.
            save2file (bool): save file tree info to a file.
            printout (bool): print file tree info
        """
        self.root_path = Path(root_dir) if root_dir else Path.cwd()
        self.filepath = filepath
        self.ignore_dirs = set(ignore_dirs or [])
        self.ignore_files = set(ignore_files or [])
        self.style = style
        self.indent = indent
        self.save2file = save2file
        self.printout = printout

    def update(self, attrs: dict) -> None:
        self.__dict__.update(attrs)

    def file_tree_display(self) -> str:
        """Generate and save the directory tree to a text file.

        Returns:
            Either a str: Path to the saved output file containing the directory tree.
            or the whole built tree, as a string of CRLF-separated lines.
        """
        root_path_str = str(self.root_path)
        if not self.root_path.is_dir():
            raise NotADirectoryError(f"The path '{root_path_str}' is not a directory.")

        iterator = self.build_tree(root_path_str, "")

        tree_info = self.get_tree_info(iterator)

        if self.save2file:
            return self.buffer2file(tree_info)

        if self.printout:
            print(tree_info)

        return tree_info

    def get_tree_info(self, iterator: Generator[str, None, None]) -> str:
        lines = [f'{self.root_path.name}/']
        lines.extend(list(iterator))
        return '\n'.join(lines)

    def build_tree(self, dir_path: str, prefix: str = '') -> Generator[str, None, None]:
        """Recursively yield formatted directory tree lines.
        Intended order of appearance is with a preference to subdirectories first.

        Args:
            dir_path (str): The directory path currently being traversed.
            prefix (str): Hierarchical prefix applied to each level.

        Yields:
            str: A formatted string representing either a directory or a file.
        """
        try:
            with os.scandir(dir_path) as entries:
                dirs, files = [], []
                for entry in entries:
                    if entry.is_dir(follow_symlinks=False):
                        if self.should_ignore(entry.name, True):
                            continue
                        dirs.append(entry)
                    elif not self.should_ignore(entry.name, False):
                        files.append(entry)
        except PermissionError:
            yield f'{prefix}{self.style * self.indent}[Permission Denied]'
            return
        except OSError:
            yield f'{prefix}{self.style * self.indent}[Error reading directory]'
            return

        dirs.sort(key=lambda e: e.name)
        files.sort(key=lambda e: e.name)

        for d in dirs:
            yield f'{prefix}{self.style * self.indent}{d.name}/'
            yield from self.build_tree(d.path, prefix + self.style * self.indent)

        for f in files:
            yield f'{prefix}{self.style * self.indent}{f.name}'

    def should_ignore(self, name: str, is_dir: bool) -> bool:
        """Return True if a name matches ignore patterns.

        Args:
            name (str): The file or directory name to check.
            is_dir (bool): Whether the name refers to a directory.

        Returns:
            bool: True if the name matches any ignore pattern, else False.
        """
        ignore_set = self.ignore_dirs if is_dir else self.ignore_files
        if name in ignore_set:
            return True
        return any(fnmatch.fnmatch(name, pattern) for pattern in ignore_set)

    def buffer2file(self, buffer: str) -> str:
        """Save the formatted file directly from a string buffer.

        Args:
            buffer (str): a string of CRLF-separated lines.

        Returns:
            str: Path to the saved output file.
        """
        out_file = self.format_out_path()
        try:
            with out_file.open("w", encoding="utf-8") as f:
                f.write(buffer)

        except PermissionError as e:
            raise PermissionError(f"Cannot write to '{out_file}': {e}")
        except OSError as e:
            raise OSError(f"Error writing file '{out_file}': {e}")

        return str(out_file)

    def format_out_path(self) -> Path:
        alt_file_name = f'{self.root_path.name}{DEFAULT_SFX}'
        out_file = Path(self.filepath) if self.filepath \
            else (self.root_path / alt_file_name)
        return out_file
