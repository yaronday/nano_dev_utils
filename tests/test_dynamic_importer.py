import pytest
from types import ModuleType
from nano_dev_utils.dynamic_importer import Importer


@pytest.fixture
def importer():
    return Importer()


@pytest.fixture
def mock_module():
    module = ModuleType('mock_module')
    setattr(module, 'attribute', 'test_value')
    return module


def test_import_mod_from_lib_success_new_import(importer, mock_module, mocker):
    mock_import = mocker.patch('importlib.import_module', return_value=mock_module)
    module = importer.import_mod_from_lib('test_library', 'test_module')

    assert module == mock_module
    assert 'test_module' in importer.imported_modules
    assert importer.imported_modules['test_module'] == mock_module
    mock_import.assert_called_once_with('test_library.test_module')


def test_import_mod_from_lib_success_cached_import(importer, mock_module, mocker):
    importer.imported_modules['cached_module'] = mock_module
    mock_import = mocker.patch('importlib.import_module')

    module = importer.import_mod_from_lib('another_library', 'cached_module')

    assert module == mock_module
    mock_import.assert_not_called()


def test_import_mod_from_lib_failure(importer, mocker):
    mocker.patch(
        'importlib.import_module',
        side_effect=ModuleNotFoundError(
            "No module named 'nonexistent_library.missing_module'"
        ),
    )

    with pytest.raises(
        ImportError, match='Could not import nonexistent_library.missing_module'
    ):
        importer.import_mod_from_lib('nonexistent_library', 'missing_module')

    assert 'missing_module' not in importer.imported_modules


def test_import_mod_from_lib_returns_any(importer, mocker):
    mock_object = 'not a module'
    mocker.patch.dict('sys.modules', {'yet_another_library.some_object': mock_object})

    result = importer.import_mod_from_lib('yet_another_library', 'some_object')

    assert result == mock_object
    assert 'some_object' in importer.imported_modules
    assert importer.imported_modules['some_object'] == mock_object
