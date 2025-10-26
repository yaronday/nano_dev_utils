import os
from collections.abc import Generator
from pathlib import Path
import fnmatch
from .ftd_consts import (
    TITLE,
    DEFAULT_SFX,
    TREE_SAVED,
    NOT_A_DIR,
    PERMISSION_DENIED,
    READ_ERR,
    WR_PERMISSION_DENIED,
    FILE_WR_ERR,
    t_msg,
)


class FileTreeDisplay:
    """Generate and display a visual file tree of a directory.

    This class builds a directory tree structure using `os.scandir()`
    and yields formatted visual representations of directories and files.
    Supports exclusion lists, configurable indentation, and custom prefix styles.
    """

    def __init__(
        self,
        root_dir: str,
        filepath: str | None = None,
        ignore_dirs: list[str] | set[str] | None = None,
        ignore_files: list[str] | set[str] | None = None,
        style: str = '-',
        indent: int = 1,
        title: str = TITLE,
        default_suffix: str = DEFAULT_SFX,
    ) -> None:
        """Initialize the FileTreeDisplay instance.

        Args:
            root_dir (str): Root directory to traverse.
            ignore_dirs (list[str] | set[str] | None): Directory names or patterns to ignore.
            ignore_files (list[str] | set[str] | None): File names or patterns to ignore.
            style (str): Character(s) used to represent hierarchy levels. Defaults to "-".
            indent (int): Number of style characters used per hierarchy level. Defaults to 2.
        """
        self.root_dir = root_dir
        self.filepath = filepath
        self.ignore_dirs = set(ignore_dirs or [])
        self.ignore_files = set(ignore_files or [])
        self.style = style
        self.indent = indent
        self.title = title
        self.default_suffix = default_suffix

    def file_tree_display(self, save2file: bool = True) -> str | None:
        """Generate and save the directory tree to a text file.

        Returns:
            str: Path to the saved output file containing the directory tree.
        """
        root_path = Path(self.root_dir)
        if not root_path.is_dir():
            raise NotADirectoryError(t_msg(NOT_A_DIR, path=self.root_dir))

        root_path_str = f'{root_path.name}/'
        header = [self.title, root_path_str] if self.title else [root_path_str]

        iterator = self.build_tree(str(root_path), '')

        if save2file:
            file_path = self.save2file(header, iterator, self.filepath)
            print(t_msg(TREE_SAVED, filepath=file_path))
            return file_path
        else:
            print('\n'.join(header))
            for line in iterator:
                print(line)

    def build_tree(self, dir_path: str, prefix: str = '') -> Generator[str, None, None]:
        """Recursively yield formatted directory tree lines.

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
            yield f'{prefix}{self.style * self.indent}{PERMISSION_DENIED}'
            return
        except OSError:
            yield f'{prefix}{self.style * self.indent}{READ_ERR}'
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

    def save2file(
        self,
        header: list[str],
        iterator: Generator[str, None, None],
        filepath: str | None = None,
    ) -> str:
        """Save the formatted file tree to a text file.

        Args:
            header (list[str]): Header lines to write at the beginning of the file.
            iterator (Generator[str, None, None]): The yielded directory/file tree lines.
            filepath (str | None): Optional output file path. Defaults to
                "<root_dir>/<root_name>_file_tree.txt".

        Returns:
            str: Path to the saved output file.
        """
        root_path = Path(self.root_dir)
        out_file = (
            Path(filepath)
            if filepath
            else root_path / f'{root_path.name}{self.default_suffix}'
        )

        try:
            with out_file.open('w', encoding='utf-8') as f:
                f.write('\n'.join(header) + '\n')
                for line in iterator:
                    f.write(line + '\n')
        except PermissionError as e:
            raise PermissionError(
                t_msg(WR_PERMISSION_DENIED, filepath=out_file, error=e)
            )
        except OSError as e:
            raise OSError(t_msg(FILE_WR_ERR, filepath=out_file, error=e))

        return str(out_file)
