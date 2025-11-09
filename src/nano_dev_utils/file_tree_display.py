import io
import os
import re

from collections.abc import Generator
from itertools import chain
from pathlib import Path
from typing_extensions import Callable, Any
from typing import Iterable

from .common import str2file, FilterSet, PredicateBuilder


DEFAULT_SFX = '_filetree.txt'


_NUM_SPLIT = re.compile(r'(\d+)').split


class FileTreeDisplay:
    """Generate and display a visual file tree of a directory.

    This class builds a directory tree structure and yields formatted
    visual representations of directories and files.
    Supports exclusion lists, configurable indentation, and custom prefix styles.
    """

    __slots__ = (
        'root_path',
        'filepath',
        'ignore_dirs',
        'ignore_files',
        'include_dirs',
        'include_files',
        'style',
        'indent',
        'files_first',
        'skip_sorting',
        'sort_key_name',
        'reverse',
        'custom_sort',
        'save2file',
        'printout',
        'style_dict',
        'sort_keys',
        'pb',
        'dir_filter',
        'file_filter',
    )

    def __init__(
        self,
        root_dir: str | None = None,
        filepath: str | None = None,
        ignore_dirs: FilterSet = None,
        ignore_files: FilterSet = None,
        include_dirs: FilterSet = None,
        include_files: FilterSet = None,
        style: str = 'classic',
        indent: int = 2,
        files_first: bool = False,
        skip_sorting: bool = False,
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
            skip_sorting (bool): Skip sorting directly, even if configured.
            sort_key_name (str): sorting key name, e.g. 'lex' for lexicographic or 'custom'. Defaults to 'natural'.
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
        self.skip_sorting = skip_sorting
        self.sort_key_name = sort_key_name
        self.reverse = reverse
        self.custom_sort = custom_sort
        self.save2file = save2file
        self.printout = printout

        self.style_dict: dict = {
            'classic': self.connector_styler('├── ', '└── '),
            'dash': self.connector_styler('|-- ', '`-- '),
            'arrow': self.connector_styler('├─> ', '└─> '),
            'plus': self.connector_styler('+--- ', '\\--- '),
        }

        self.sort_keys = {
            'natural': self._nat_key,
            'lex': self._lex_key,
            'custom': self.custom_sort,
        }

        self.pb = PredicateBuilder()
        self.dir_filter = self.pb.build_predicate(self.include_dirs, self.ignore_dirs)
        self.file_filter = self.pb.build_predicate(
            self.include_files, self.ignore_files
        )

    def format_style(self) -> dict:
        style, style_dict = self.style, self.style_dict
        style_keys = list(style_dict.keys())
        if style not in style_keys:
            raise ValueError(f"'{style}' is invalid: must be one of {style_keys}\n")
        return style_dict[style]

    def init(self, *args, **kwargs) -> None:
        self.__init__(*args, **kwargs)

    def update_predicates(self) -> None:
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

    def _resolve_sort_key(self) -> Callable[[str], Any]:
        sort_key_name, sort_keys = self.sort_key_name, self.sort_keys
        key = sort_keys.get(sort_key_name)
        if key is None:
            if self.sort_key_name == 'custom':
                raise ValueError(
                    "custom_sort function must be specified when sort_key_name='custom'"
                )
            raise ValueError(
                f'Invalid sort key name: "{sort_key_name}"! '
                f'Currently defined keys are: {list(sort_keys.keys())}'
            )
        return key

    def file_tree_display(self) -> str:
        """Generates a directory tree and saves it to a text file.

        Returns:
            str: The complete directory tree as a single CRLF-delimited string.
        """
        root_path_str = str(self.root_path)
        filepath = self.filepath

        if not self.root_path.is_dir():
            raise NotADirectoryError(f"The path '{root_path_str}' is not a directory.")

        style = self.format_style()
        sort_key = None if self.skip_sorting else self._resolve_sort_key()
        dir_filter, file_filter = self.dir_filter, self.file_filter
        files_first, reverse = self.files_first, self.reverse
        indent = self.indent

        iterator = self._build_tree(
            root_path_str,
            prefix='',
            style=style,
            sort_key=sort_key,
            files_first=files_first,
            dir_filter=dir_filter,
            file_filter=file_filter,
            reverse=reverse,
            indent=indent,
        )

        tree_info = self.get_tree_info(iterator)

        if self.save2file and filepath:
            str2file(tree_info, filepath)

        if self.printout:
            print(tree_info)

        return tree_info

    def get_tree_info(self, iterator: Generator[str, None, None]) -> str:
        buf = io.StringIO()
        write = buf.write
        write(f'{self.root_path.name}/\n')
        buf.writelines(f'{line}\n' for line in iterator)
        out = buf.getvalue()
        return out[:-1] if out.endswith('\n') else out

    def _build_tree(
        self,
        dir_path: str,
        *,
        prefix: str,
        style: dict,
        sort_key: Callable[[str], Any] | None,
        files_first: bool,
        dir_filter: Callable[[str], bool],
        file_filter: Callable[[str], bool],
        reverse: bool,
        indent: int,
    ) -> Generator[str, None, None]:
        """Yields lines representing a formatted folder structure using a recursive DFS.
        The internal recursive generator has runtime consts threaded through to avoid attrib. lookups.

        Args:
            dir_path (str): The directory path or disk drive currently being traversed.
            prefix (str): Hierarchical prefix applied to each level.

        Yields:
            str: A formatted text representation of the folder structure.
        """
        branch = style['branch']
        end = style['end']
        vertical = style['vertical']
        space = style['space']

        recurse = self._build_tree

        dirs: list[tuple[str, str]] = []
        files: list[str] = []

        try:
            with os.scandir(dir_path) as it:
                append_dir = dirs.append
                append_file = files.append
                for entry in it:
                    name = entry.name
                    try:
                        is_dir = entry.is_dir(follow_symlinks=False)
                    except OSError:
                        continue

                    if is_dir:
                        if dir_filter(name):
                            append_dir((name, entry.path))
                    else:
                        if file_filter(name):
                            append_file(name)

        except (PermissionError, OSError, FileNotFoundError) as e:
            if isinstance(e, PermissionError):
                yield '[Permission Denied]'
            else:
                yield '[Error reading directory]'
            return

        if sort_key:
            dirs.sort(key=lambda d: sort_key(d[0]), reverse=reverse)
            files.sort(key=sort_key, reverse=reverse)

        # Compute combined sequence without extra temporary tuples where possible
        f_iter: Iterable[tuple[str, None, bool]] = ((f, None, False) for f in files)
        d_iter: Iterable[tuple[str, str, bool]] = ((d[0], d[1], True) for d in dirs)
        seq: Iterable[tuple[str, str | None, bool]] = (
            chain(f_iter, d_iter) if files_first else chain(d_iter, f_iter)
        )

        combined = list(seq)
        last_index = len(combined) - 1

        for idx, (name, path, is_dir) in enumerate(combined):
            is_last = idx == last_index
            connector = end if is_last else branch
            formatted_name = f'{name}/' if is_dir else name
            yield f'{prefix}{connector}{formatted_name}'
            extension = space if is_last else vertical

            if is_dir and path:
                yield from recurse(
                    path,
                    prefix=prefix + extension,
                    style=style,
                    sort_key=sort_key,
                    files_first=files_first,
                    dir_filter=dir_filter,
                    file_filter=file_filter,
                    reverse=reverse,
                    indent=indent,
                )

    def connector_styler(self, branch: str, end: str) -> dict:
        indent = self.indent
        return {
            'space': ' ' * indent,
            'vertical': f'│{" " * (indent - 1)}',
            'branch': branch,
            'end': end,
        }
