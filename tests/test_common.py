import pytest
from types import SimpleNamespace

from nano_dev_utils.common import encode_dict, update


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
