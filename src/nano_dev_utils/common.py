from pathlib import Path
from typing import AnyStr


def update(obj: object, attrs: dict) -> None:
    """Updates an object's attributes from a dictionary.
    Uses direct __dict__ modification if possible for performance,
    otherwise falls back to setattr for objects without __dict__ (e.g., __slots__).

    Args:
        obj: The object whose attributes will be updated.
        attrs: Dictionary of attribute names and values.

    Raises:
        AttributeError: If an attribute cannot be set (optional, see notes).
    """
    if hasattr(obj, '__dict__'):
        obj.__dict__.update(attrs)
    else:
        for key, value in attrs.items():
            try:
                setattr(obj, key, value)
            except AttributeError as e:
                raise AttributeError(
                    f"Cannot set attribute '{key}' on object '{obj}': {e}"
                )


def encode_dict(input_dict: dict) -> bytes:
    """
    Encodes the values of a dictionary into a single bytes object.

    Each value in the dictionary is converted to its string representation, encoded as bytes,
    and concatenated together with a single space (b' ') separator.

    Parameters:
        input_dict (dict): The dictionary whose values are to be encoded.

    Returns:
        bytes: A single bytes object containing all values, separated by spaces.

    Example:
        >>> encode_dict({"a": 1, "b": "test"})
        b'1 test'

    Raises:
        TypeError: If input_dict is not a dictionary.
    """
    if not isinstance(input_dict, dict):
        raise TypeError('input_dict must be a dictionary.')
    return b' '.join(str(v).encode() for v in input_dict.values())


def str2file(content: AnyStr, filepath: str, mode: str = 'w', enc: str = 'utf-8') -> None:
    """Simply save file directly from any string content.

    Args:
        content (AnyStr): String or bytes to write. Must match the mode type ,e.g. bytes for binary.
        filepath (str): Full file path to write to.
        mode (str): see doc for Path.open. Defaults to 'w'.
        enc (str): Encoding used in text modes; ignored in binary modes. Defaults to 'utf-8'.
    """
    out_file_path = Path(filepath)
    try:
        if 'b' in mode:
            with out_file_path.open(mode) as f:
                f.write(content)
        else:
            with out_file_path.open(mode, encoding=enc) as f:
                f.write(content)

    except PermissionError as e:
        raise PermissionError(f"Cannot write to '{out_file_path}': {e}")
    except OSError as e:
        raise OSError(f"Error writing file '{out_file_path}': {e}")
