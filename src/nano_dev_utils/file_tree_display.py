import os
import re
import fnmatch

from collections.abc import Generator
from pathlib import Path
from typing_extensions import LiteralString, Callable, Any

from .common import str2file


DEFAULT_SFX = '_filetree.txt'

STYLES: list[str] = [' ', '-', '—', '_', '*', '>', '<', '+', '.']

_NUM_SPLIT = re.compile(r'(\d+)').split


class FileTreeDisplay:
    """Generate and display a visual file tree of a directory.

    This class builds a directory tree structure and yields formatted
    visual representations of directories and files.
    Supports exclusion lists, configurable indentation, and custom prefix styles.
    """

    def __init__(
            self,
            root_dir: str | None = None,
            filepath: str | None = None,
            ignore_dirs: list[str] | set[str] | None = None,
            ignore_files: list[str] | set[str] | None = None,
            style: str = ' ',
            indent: int = 1,
            sort_key_name: str = 'natural',
            reverse: bool = False,
            custom_sort: Callable[[str], Any] | None = None,
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
            sort_key_name (str): sorting key name, e.g. 'lex' for lexicographic or 'custom'. Default to 'natural'.
            reverse (bool): reversed sorting
            custom_sort (Callable[[str], Any] | None):
            save2file (bool): save file tree info to a file.
            printout (bool): print file tree info
        """
        self.root_path = Path(root_dir) if root_dir else Path.cwd()
        self.filepath = filepath
        self.ignore_dirs = set(ignore_dirs or [])
        self.ignore_files = set(ignore_files or [])
        self.style = style
        self.indent = indent
        self.sort_key_name = sort_key_name
        self.reverse = reverse
        self.custom_sort = custom_sort
        self.save2file = save2file
        self.printout = printout

        self.sort_keys = {
            'natural': self._nat_key,
            'lex': self._lex_key,
            'custom': None,
        }

    def init(self, *args, **kwargs) -> None:
        self.__init__(*args, **kwargs)

    def update(self, attrs: dict) -> None:
        self.__dict__.update(attrs)

    @staticmethod
    def _nat_key(name: str) -> list[int | LiteralString]:
        """Natural sorting key"""
        return [int(part) if part.isdigit() else part.lower()
                for part in _NUM_SPLIT(name)]

    @staticmethod
    def _lex_key(name: str) -> str:
        """Lexicographic sorting key"""
        return name.lower()

    def file_tree_display(self) -> str:
        """Generate and save the directory tree to a text file.

        Returns:
            Either a str: Path to the saved output file containing the directory tree.
            or the whole built tree, as a string of CRLF-separated lines.
        """
        root_path_str = str(self.root_path)
        filepath = self.filepath
        if not self.root_path.is_dir():
            raise NotADirectoryError(f"The path '{root_path_str}' is not a directory.")

        if self.style not in STYLES:
            raise ValueError(f"'{self.style}' is invalid: must be one of {STYLES}\n")

        iterator = self.build_tree(root_path_str)

        tree_info = self.get_tree_info(iterator)

        if self.save2file:
            str2file(tree_info, filepath)
            return filepath

        if self.printout:
            print(tree_info)

        return tree_info

    def get_tree_info(self, iterator: Generator[str, None, None]) -> str:
        lines = [f'{self.root_path.name}/']
        lines.extend(list(iterator))
        return '\n'.join(lines)

    def build_tree(self, dir_path: str, prefix: str = '') -> Generator[str, None, None]:
        """Recursively yield formatted directory tree lines, using DFS.
        Intended order of appearance is with a preference to subdirectories first.

        Args:
            dir_path (str): The directory path currently being traversed.
            prefix (str): Hierarchical prefix applied to each level.

        Yields:
            str: A formatted string representing either a directory or a file.
        """
        style, indent, should_ignore = self.style, self.indent, self.should_ignore
        join_prefix = ''.join

        sort_key: Callable[[str], Any] | None = None
        reverse = self.reverse
        sort_key_name = self.sort_key_name
        if sort_key_name:
            if sort_key_name == 'custom':
                if not self.custom_sort:
                    raise ValueError("custom_sort function must "
                                     "be specified when sort_key_name='custom'")
                sort_key = self.custom_sort
            else:
                sort_key = self.sort_keys.get(sort_key_name)
                if sort_key is None:
                    raise ValueError(f"Invalid sort key name: {sort_key_name}")

        curr_indent: str = style * indent
        next_prefix = f'{prefix}{curr_indent}'

        try:
            with os.scandir(dir_path) as entries:
                dirs, files = [], []
                append_dir, append_file = dirs.append, files.append

                for entry in entries:
                    name = entry.name
                    if entry.is_dir():
                        if not should_ignore(name, True):
                            append_dir((name, entry.path))
                    else:
                        if not should_ignore(name, False):
                            append_file(name)
        except (PermissionError, OSError) as e:
            msg = '[Permission Denied]' if isinstance(e, PermissionError) else '[Error reading directory]'
            yield f'{prefix}{curr_indent}{msg}'
            return

        if sort_key:
            dirs.sort(key=lambda d: sort_key(d[0]), reverse=reverse)
            files.sort(key=sort_key, reverse=reverse)

        for name, path in dirs:
            yield join_prefix((prefix, curr_indent, name, '/'))
            yield from self.build_tree(path, next_prefix)

        for name in files:
            yield join_prefix((next_prefix, name))

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

    def format_out_path(self) -> Path:
        alt_file_name = f'{self.root_path.name}{DEFAULT_SFX}'
        out_file = (
            Path(self.filepath) if self.filepath else (self.root_path / alt_file_name)
        )
        return out_file
