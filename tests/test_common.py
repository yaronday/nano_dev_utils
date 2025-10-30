import pytest
import os
import tempfile

from types import SimpleNamespace
from pathlib import Path
from typing import AnyStr

from nano_dev_utils.common import encode_dict, update, str2file


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


def str2file_basic_test(content: AnyStr, filepath: str, mode: str = 'w', enc: str = 'utf-8') -> None:
    out_file_path = Path(filepath)
    try:
        with out_file_path.open(mode, encoding=enc) as f:
            f.write(content)
    except PermissionError as e:
        raise PermissionError(f"Cannot write to '{out_file_path}': {e}")
    except OSError as e:
        raise OSError(f"Error writing file '{out_file_path}': {e}")


@pytest.fixture
def temp_file():
    # Creates a named temporary file and deletes it after use
    fd, path = tempfile.mkstemp()
    os.close(fd)
    yield path
    if os.path.exists(path):
        os.unlink(path)


def test_write_text_default(temp_file):
    content = "Hello, world!"
    str2file(content, temp_file)
    with open(temp_file, encoding='utf-8') as f:
        assert f.read() == content


def test_write_text_with_encoding(temp_file):
    content = "Café Münster"
    str2file(content, temp_file, enc='utf-8')
    with open(temp_file, encoding='utf-8') as f:
        assert f.read() == content


def test_write_bytes_binary_mode(temp_file):
    content = b"\x00\xFFbinarydata"
    str2file(content, temp_file, mode='wb')
    with open(temp_file, 'rb') as f:
        assert f.read() == content


def test_overwrite_contents(temp_file):
    initial = "first"
    updated = "second"
    str2file(initial, temp_file)
    str2file(updated, temp_file)  # Should overwrite
    with open(temp_file, encoding='utf-8') as f:
        assert f.read() == updated


def test_permission_error(monkeypatch, temp_file):
    # Simulate permission error by patching Path.open
    def raise_perm(*a, **kw): raise PermissionError("Simulated")
    monkeypatch.setattr(Path, "open", raise_perm)
    with pytest.raises(PermissionError, match="Cannot write"):
        str2file("fail", temp_file)


def test_oserror(monkeypatch, temp_file):
    # Simulate OSError by patching Path.open
    def raise_oserr(*a, **kw): raise OSError("Simulated")
    monkeypatch.setattr(Path, "open", raise_oserr)
    with pytest.raises(OSError, match="Error writing"):
        str2file("fail", temp_file)


@pytest.mark.parametrize("mode,content", [
    ("w", b"bytes"),     # bytes in text mode—should fail at runtime
    ("wb", "string"),    # str in binary mode—should fail at runtime
])
def test_type_error_on_wrong_content_mode(temp_file, mode, content):
    with pytest.raises(TypeError):
        str2file(content, temp_file, mode=mode)
