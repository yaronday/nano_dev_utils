"""
A wrapper for windows tree command, which graphically displays folder structure.
https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/tree
"""

import subprocess
from pathlib import Path


def tree_wrapper(
    root_path: str | None,
    show_files: bool = True,
    save2file: bool = False,
    filepath: str | None = None,
    use_ascii: bool = True,
) -> None:
    """Wrapper for the MS Windows tree command that graphically displays the folder structure.

    Args:
        root_path (str | None): Root directory for which to display the directory structure.
        show_files (bool): Whether to include file names in each directory.
        save2file (bool): Whether to save the output to a file.
        filepath (str): Path to the output file. Must be specified if `save2file` is True.
        use_ascii (bool): Use text characters instead of graphic characters for the tree links.

    Returns:
        None
    """

    if not root_path:
        root_path = str(Path.cwd())

    elif not Path(root_path).is_dir():
        raise NotADirectoryError(f"The path '{root_path}' is not a directory.")

    cmd: list[str] = ['tree', root_path]
    if show_files:
        cmd.append('/f')
    if use_ascii:
        cmd.append('/a')

    command = ' '.join(cmd)

    if save2file:
        if not filepath:
            raise ValueError('filepath must be provided if save2file is True')
        with open(filepath, 'w', encoding='utf-8') as f:
            subprocess.run(
                command, stdout=f, stderr=subprocess.PIPE, shell=True, check=True
            )
    else:
        subprocess.run(command, shell=True, check=True)
