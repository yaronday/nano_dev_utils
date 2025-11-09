import fnmatch
import re
import sys
import json

from pathlib import Path
from typing import AnyStr, Any

from collections.abc import Callable
from functools import partial
from typing import TypeAlias


FilterSet: TypeAlias = list[str] | set[str] | None


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


def str2file(
    content: AnyStr, filepath: str, mode: str = 'w', enc: str = 'utf-8'
) -> None:
    """Simply save file directly from any string content.

    Args:
        content (AnyStr): String or bytes to write. Must match the mode type ,e.g. bytes for binary.
        filepath (str): Full file path to write to.
        mode (str): see doc for Path.open. Defaults to 'w'.
        enc (str): Encoding used in text modes; ignored in binary modes. Defaults to 'utf-8'.
    """
    out_file_path = Path(filepath)

    if not out_file_path.parent.exists():
        out_file_path.parent.mkdir(parents=True, exist_ok=True)

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


class PredicateBuilder:
    def build_predicate(
        self, allow: FilterSet, block: FilterSet
    ) -> Callable[[str], bool]:
        """Build a memory-efficient predicate function."""
        compile_patts = self.compile_patts

        allow_lits, allow_patts = compile_patts(allow)
        block_lits, block_patts = compile_patts(block)

        flag = (
            1 if allow_lits or allow_patts else 0,
            1 if block_lits or block_patts else 0,
        )

        match flag:  # (allow, block)
            case (0, 0):
                return lambda name: True

            case (0, 1):
                return partial(
                    self._match_patt_with_lits,
                    name_patts=block_patts,
                    name_lits=block_lits,
                    negate=True,
                )

            case (1, 0):
                return partial(
                    self._match_patt_with_lits,
                    name_patts=allow_patts,
                    name_lits=allow_lits,
                    negate=False,
                )

            case (1, 1):
                return partial(
                    self._allow_block_predicate,
                    allow_lits=allow_lits,
                    allow_patts=allow_patts,
                    block_lits=block_lits,
                    block_patts=block_patts,
                )

    @staticmethod
    def compile_patts(fs: FilterSet) -> tuple[set[str], list[re.Pattern]]:
        if not fs:
            return set(), []
        literals, patterns = set(), []
        for item in fs:
            if '*' in item or '?' in item or '[' in item:
                patterns.append(re.compile(fnmatch.translate(item)))
            else:
                literals.add(item)
        return literals, patterns

    @staticmethod
    def _match_patts(name: str, patterns: list[re.Pattern]) -> bool:
        """Return True if name matches any compiled regex pattern."""
        return any(pat.fullmatch(name) for pat in patterns)

    def _match_patt_with_lits(
        self,
        name: str,
        *,
        name_lits: set[str],
        name_patts: list[re.Pattern],
        negate: bool = False,
    ) -> bool:
        """Return True if name is in literals or matches any pattern."""
        res = name in name_lits or self._match_patts(name, name_patts)
        return not res if negate else res

    def _allow_block_predicate(
        self,
        name: str,
        *,
        allow_lits: set[str],
        allow_patts: list[re.Pattern],
        block_lits: set[str],
        block_patts: list[re.Pattern],
    ) -> bool:
        """Return True if name is allowed and not blocked (block takes precedence)."""
        if name in block_lits or self._match_patts(name, block_patts):
            return False
        if name in allow_lits or self._match_patts(name, allow_patts):
            return True
        return False


def load_cfg_file(path: str | None) -> dict[str, Any]:
    """Load configuration from JSON file."""
    if not path:
        return {}
    cfg_path = Path(path)
    if not cfg_path.exists():
        sys.exit(f"Error: config file '{cfg_path}' not found.")
    try:
        if cfg_path.suffix == '.json':
            with open(cfg_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            sys.exit('Error: config file must .json')
    except Exception as e:
        sys.exit(f'Error reading config file: {e}')
