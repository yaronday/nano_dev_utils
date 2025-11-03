import os
import re

from collections.abc import Generator
from pathlib import Path
from typing_extensions import Callable, Any

from .common import str2file, FilterSet, PredicateBuilder


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
        ignore_dirs: FilterSet = None,
        ignore_files: FilterSet = None,
        include_dirs: FilterSet = None,
        include_files: FilterSet = None,
        style: str = ' ',
        indent: int = 2,
        files_first: bool = False,
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
            include_dirs (list[str] | set[str] | None): Directory names or patterns to include.
            include_files (list[str] | set[str] | None): File names or patterns to include.
            style (str): Character(s) used to represent hierarchy levels. Defaults to " ".
            indent (int): Number of style characters used per hierarchy level. Defaults to 2.
            files_first (bool): Determines whether to list files first. Defaults to False.
            sort_key_name (str): sorting key name, e.g. 'lex' for lexicographic or 'custom'. Defaults to 'natural'.
                                 '' means no sorting.
            reverse (bool): reversed sorting.
            custom_sort (Callable[[str], Any] | None):
            save2file (bool): save file tree info to a file.
            printout (bool): print file tree info.
        """
        self.root_path = Path(root_dir) if root_dir else Path.cwd()
        self.filepath = filepath
        self.ignore_dirs = set(ignore_dirs or [])
        self.ignore_files = set(ignore_files or [])
        self.include_dirs = set(include_dirs or [])
        self.include_files = set(include_files or [])
        self.style = style
        self.indent = indent
        self.files_first = files_first
        self.sort_key_name = sort_key_name
        self.reverse = reverse
        self.custom_sort = custom_sort
        self.save2file = save2file
        self.printout = printout

        self.sort_keys = {
            'natural': self._nat_key,
            'lex': self._lex_key,
            'custom': self.custom_sort,
            '': None,
        }

        self.pb = PredicateBuilder()
        self.dir_filter = self.pb.build_predicate(self.include_dirs, self.ignore_dirs)
        self.file_filter = self.pb.build_predicate(
            self.include_files, self.ignore_files
        )

    def init(self, *args, **kwargs) -> None:
        self.__init__(*args, **kwargs)

    def update(self, attrs: dict) -> None:
        self.__dict__.update(attrs)
        pattern = re.compile(r'^(ign|inc)')
        if any(pattern.match(key) for key in attrs):
            self.update_predicates()

    def update_predicates(self):
        self.dir_filter = self.pb.build_predicate(self.include_dirs, self.ignore_dirs)
        self.file_filter = self.pb.build_predicate(
            self.include_files, self.ignore_files
        )

    @staticmethod
    def _nat_key(name: str) -> list[int | str | Any]:
        """Natural sorting key"""
        return [
            int(part) if part.isdigit() else part.lower() for part in _NUM_SPLIT(name)
        ]

    @staticmethod
    def _lex_key(name: str) -> str:
        """Lexicographic sorting key"""
        return name.lower()

    def file_tree_display(self) -> str:
        """Generates a directory tree and saves it to a text file.

        Returns:
            str: The path to the saved output file containing the directory tree,
                or the complete directory tree as a single CRLF-delimited string.
        """

        root_path_str = str(self.root_path)
        filepath = self.filepath
        if not self.root_path.is_dir():
            raise NotADirectoryError(f"The path '{root_path_str}' is not a directory.")

        if self.style not in STYLES:
            raise ValueError(f"'{self.style}' is invalid: must be one of {STYLES}\n")

        iterator = self.build_tree(root_path_str)

        tree_info = self.get_tree_info(iterator)

        if self.save2file and filepath:
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
        """Yields formatted directory tree lines, using a recursive DFS.
        Intended order of appearance is with a preference to subdirectories first.

        Args:
            dir_path (str): The directory path currently being traversed.
            prefix (str): Hierarchical prefix applied to each level.

        Yields:
            str: A formatted string representing either a directory or a file.
        """
        files_first = self.files_first
        dir_filter, file_filter = self.dir_filter, self.file_filter
        sort_key_name, reverse = self.sort_key_name, self.reverse
        sort_key = self.sort_keys.get(self.sort_key_name)
        curr_indent = self.style * self.indent

        next_prefix = prefix + curr_indent

        if sort_key is None:
            if sort_key_name == 'custom':
                raise ValueError(
                    "custom_sort function must be specified when sort_key_name='custom'"
                )
            raise ValueError(f'Invalid sort key name: {sort_key_name}')

        try:
            with os.scandir(dir_path) as entries:
                dirs, files = [], []
                append_dir, append_file = dirs.append, files.append
                for entry in entries:
                    name = entry.name
                    if entry.is_dir():
                        if dir_filter(name):
                            append_dir((name, entry.path))
                    else:
                        if file_filter(name):
                            append_file(name)

        except (PermissionError, OSError) as e:
            msg = (
                '[Permission Denied]'
                if isinstance(e, PermissionError)
                else '[Error reading directory]'
            )
            yield f'{next_prefix}{msg}'
            return

        if sort_key:
            dirs.sort(key=lambda d: sort_key(d[0]), reverse=reverse)
            files.sort(key=sort_key, reverse=reverse)

        if files_first:
            for name in files:
                yield next_prefix + name

        for name, path in dirs:
            yield f'{next_prefix}{name}/'
            yield from self.build_tree(path, next_prefix)

        if not files_first:
            for name in files:
                yield next_prefix + name

    def format_out_path(self) -> Path:
        alt_file_name = f'{self.root_path.name}{DEFAULT_SFX}'
        out_file = (
            Path(self.filepath) if self.filepath else (self.root_path / alt_file_name)
        )
        return out_file
