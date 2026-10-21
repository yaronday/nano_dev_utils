import pytest
import os
import tempfile
import json

from pytest import MonkeyPatch
from types import SimpleNamespace
from pathlib import Path
from typing import Generator, AnyStr


from nano_dev_utils.common import encode_dict, update, str2file, PredicateBuilder, load_cfg_file


@pytest.fixture
def temp_file() -> Generator[str, None, None]:
    # Creates a named temporary file and deletes it after use
    fd, path = tempfile.mkstemp()
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)

@pytest.fixture
def builder():
    return PredicateBuilder()


def test_encode_dict_basic() -> None:
    assert encode_dict({'a': 1, 'b': 'test'}) == b'1 test'


def test_encode_dict_empty() -> None:
    assert encode_dict({}) == b''


def test_encode_dict_all_str() -> None:
    d = {'a': 'foo', 'b': 'bar'}
    assert encode_dict(d) == b'foo bar'


def test_encode_dict_mixed_types() -> None:
    d = {'x': 42, 'y': 3.14, 'z': False}
    result = encode_dict(d)
    assert result == b'42 3.14 False'


def test_encode_dict_order() -> None:
    d = {'first': 'A', 'second': 'B', 'third': 'C'}
    assert encode_dict(d) == b'A B C'


def test_encode_dict_non_dict_raises() -> None:
    with pytest.raises(TypeError):
        encode_dict(['not', 'a', 'dict'])  # type: ignore


def test_encode_dict_nested_dicts() -> None:
    d = {'d': {'x': 1}, 'e': [2, 3]}
    expected = b"{'x': 1} [2, 3]"
    assert encode_dict(d) == expected


def test_update_regular_object() -> None:
    class Regular:
        pass

    obj = Regular()
    update(obj, {'a': 1, 'b': 'hello'})
    assert obj.a == 1  # type: ignore[attr-defined]
    assert obj.b == 'hello'  # type: ignore[attr-defined]


def test_update_simple_namespace() -> None:
    obj = SimpleNamespace()
    update(obj, {'foo': 42})
    assert obj.foo == 42


def test_update_slots_object() -> None:
    class SlotsOnly:
        __slots__ = ('x', 'y')

    obj = SlotsOnly()
    update(obj, {'x': 10, 'y': 20})
    assert obj.x == 10
    assert obj.y == 20


def test_update_slots_and_dict_object() -> None:
    class SlotsAndDict:
        __slots__ = ('x',)

    obj = SlotsAndDict()
    update(obj, {'x': 123})
    assert obj.x == 123


def test_update_invalid_attribute_raises() -> None:
    class SlotsOnly:
        __slots__ = ('a',)

    obj = SlotsOnly()
    with pytest.raises(AttributeError):
        update(obj, {'b': 'not allowed'})


def test_update_many_attributes() -> None:
    class Many:
        pass

    obj = Many()
    attrs = {f'attr{i}': i for i in range(10)}
    update(obj, attrs)
    for i in range(10):
        assert getattr(obj, f'attr{i}') == i


def test_update_overwrites_existing() -> None:
    class Demo:
        pass

    obj = Demo()

    obj.val = 33  # pyright: ignore[reportAttributeAccessIssue]
    update(obj, {'val': 44})
    assert obj.val == 44  # pyright: ignore[reportAttributeAccessIssue]


def test_write_text_default(temp_file: str) -> None:
    content = 'Hello, world!'
    str2file(content, temp_file)
    with open(temp_file, encoding='utf-8') as f:
        assert f.read() == content


def test_write_text_with_encoding(temp_file: str) -> None:
    content = 'Café Münster'
    str2file(content, temp_file, enc='utf-8')
    with open(temp_file, encoding='utf-8') as f:
        assert f.read() == content


def test_write_bytes_binary_mode(temp_file: str) -> None:
    content = b'\x00\xffbinarydata'
    str2file(content, temp_file, mode='wb')
    with open(temp_file, 'rb') as f:
        assert f.read() == content


def test_overwrite_contents(temp_file: str) -> None:
    initial = 'first'
    updated = 'second'
    str2file(initial, temp_file)
    str2file(updated, temp_file)  # Should overwrite
    with open(temp_file, encoding='utf-8') as f:
        assert f.read() == updated


def test_permission_error(monkeypatch: MonkeyPatch, temp_file: str) -> None:
    def raise_perm(*args, **kwargs):
        raise PermissionError('Simulated')

    monkeypatch.setattr(Path, 'open', raise_perm)
    with pytest.raises(PermissionError, match='Cannot write'):
        str2file('fail', temp_file)


def test_os_error(monkeypatch: MonkeyPatch, temp_file) -> None:
    # Simulate OSError by patching Path.open
    def raise_os_err(*args, **kwargs):
        raise OSError('Simulated')

    monkeypatch.setattr(Path, 'open', raise_os_err)
    with pytest.raises(OSError, match='Error writing'):
        str2file('fail', temp_file)


@pytest.mark.parametrize(
    'mode,content',
    [
        ('w', b'bytes'),  # bytes in text mode—should fail at runtime
        ('wb', 'string'),  # str in binary mode—should fail at runtime
    ],
)
def test_type_error_on_wrong_content_mode(
    temp_file: str, mode: str, content: AnyStr
) -> None:
    with pytest.raises(TypeError):
        str2file(content, temp_file, mode=mode)


def test_str2file_creates_nested_dirs(tmp_path: str):
    temp_file = Path(tmp_path) / 'nested' / 'dir' / 'testfile.txt'
    content = 'Nested content'
    str2file(content, str(temp_file))
    assert temp_file.exists()
    assert temp_file.read_text(encoding='utf-8') == content


class TestCompilePatts:
    @pytest.mark.parametrize(
        "fs,expected_lits,expected_patt_count",
        [
            ([], set(), 0),
            (None, set(), 0),
            (["foo", "bar"], {"foo", "bar"}, 0),
            (["FILE_*.txt", "data?.csv"], set(), 2),
            (["exact", "wild*card"], {"exact"}, 1),
        ],
    )
    def an_empty_or_varied_filter_set(self, builder, fs, expected_lits, expected_patt_count):
        literals, patterns = builder.compile_patts(fs)
        assert literals == expected_lits
        assert len(patterns) == expected_patt_count


class TestPredicateBuilderMatrix:
    # State (0, 0): No allow, no block -> Allow everything
    def test_no_filters_allows_all(self, builder):
        predicate = builder.build_predicate([], [])
        assert predicate("anything.txt") is True
        assert predicate("FOO") is True

    # State (0, 1): No allow, has block -> Block matches, allow rest
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("secret.txt", False),
            ("temp.log", False),
            ("public.txt", True),
        ],
    )
    def test_block_only_predicate(self, builder, name, expected):
        block_set = ["secret.txt", "*.log"]
        predicate = builder.build_predicate([], block_set)
        assert predicate(name) == expected

    # State (1, 0): Has allow, no block -> Allow matches, block rest
    @pytest.mark.parametrize(
        "name,expected",
        [
            ("report.pdf", True),
            ("data.csv", True),
            ("other.txt", False),
        ],
    )
    def test_allow_only_predicate(self, builder, name, expected):
        allow_set = ["report.pdf", "data.*"]
        predicate = builder.build_predicate(allow_set, [])
        assert predicate(name) == expected

    # State (1, 1): Has allow, has block -> Block takes precedence
    @pytest.mark.parametrize(
        "name, expected",
        [
            ("allowed.txt", True),
            ("blocked_allowed.txt", False),  # Matches both allow & block -> blocked
            ("random.log", False),           # Matches neither -> falls through to False
        ],
    )
    def test_allow_and_block_with_precedence(self, builder, name, expected):
        allow_set = ["*.txt"]
        block_set = ["blocked_allowed.txt"]
        predicate = builder.build_predicate(allow_set, block_set)
        assert predicate(name) == expected


class TestWildcardsAndCaseInsensitivity:
    @pytest.mark.parametrize(
        "pattern,target,expected",
        [
            ("file_?.txt", "file_1.txt", True),
            ("file_?.txt", "file_12.txt", False),
            ("data[0-9].csv", "data5.csv", True),
            ("data[0-9].csv", "dataX.csv", False),
        ],
    )
    def test_complex_wildcards(self, builder, pattern, target, expected):
        predicate = builder.build_predicate([pattern], [])
        assert predicate(target) == expected

    def test_case_insensitivity_handling(self, builder):
        allow_set = ["Important-File.TXT"]
        block_set = ["EXCLUDE-ME.log"]

        predicate = builder.build_predicate(allow_set, block_set)

        # Test casefolded literal matches
        assert predicate("important-file.txt") is True
        assert predicate("IMPORTANT-FILE.TXT") is True

        # Test block case-insensitivity precedence
        predicate_with_block = builder.build_predicate(["*.log"], ["exclude-me.log"])
        assert predicate_with_block("EXCLUDE-ME.LOG") is False



@pytest.mark.parametrize("path_input", [None, ""])
def test_load_cfg_file_empty_path(path_input):
    """Test that a missing or empty path returns an empty dictionary."""
    assert load_cfg_file(path_input) == {}


def test_load_cfg_file_not_found(tmp_path):
    """Test that a non-existent file path triggers a system exit."""
    missing_file = tmp_path / "missing.json"

    with pytest.raises(SystemExit) as exc_info:
        load_cfg_file(str(missing_file))

    assert "not found" in str(exc_info.value)


def test_load_cfg_file_invalid_extension(tmp_path):
    """Test that non-json files trigger a system exit."""
    txt_file = tmp_path / "config.txt"
    txt_file.write_text("key = value", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        load_cfg_file(str(txt_file))

    assert "must .json" in str(exc_info.value)


def test_load_cfg_file_invalid_json_content(tmp_path):
    """Test that malformed JSON triggers a system exit during parsing."""
    json_file = tmp_path / "config.json"
    json_file.write_text("{ malformed json ...", encoding="utf-8")

    with pytest.raises(SystemExit) as exc_info:
        load_cfg_file(str(json_file))

    assert "Error reading config file" in str(exc_info.value)


def test_load_cfg_file_success(tmp_path):
    """Test successful loading and parsing of a valid JSON config file."""
    json_file = tmp_path / "config.json"
    expected_data = {"host": "localhost", "port": 5432, "debug": True}
    json_file.write_text(json.dumps(expected_data), encoding="utf-8")

    result = load_cfg_file(str(json_file))

    assert result == expected_data
