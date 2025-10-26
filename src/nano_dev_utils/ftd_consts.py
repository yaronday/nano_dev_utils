from typing import Any

TITLE: str = ''
DEFAULT_SFX: str = '_file_tree.txt'

TREE_SAVED = 'Tree saved to {filepath}'
NOT_A_DIR = "The path '{path}' is not a directory."

PERMISSION_DENIED = '[Permission Denied]'
READ_ERR = '[Error reading directory]'

WR_PERMISSION_DENIED = "Cannot write to '{filepath}': {error}"
FILE_WR_ERR = "Error writing file '{filepath}': {error}"


def t_msg(template: str, /, *args: Any, **kwargs: Any) -> str:
    """Generic message formatter function.
    - Uses str.format() internally to support flexible templates.
    - Can be replaced or extended with Python 3.14+ t-strings later.

    Usage examples:
        t_msg("Tree saved to {file_path}", file_path="/tmp/tree.txt")
        t_msg("Error: '{}' is not a directory.", "/tmp")
    """
    return template.format(*args, **kwargs)
