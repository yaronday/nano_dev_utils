import unittest
from unittest.mock import patch
from types import ModuleType
from src.nano_utils_yaronday.dynamic_importer import Importer


class TestImporter(unittest.TestCase):

    def setUp(self):
        self.importer = Importer()
        self.mock_module = ModuleType('mock_module')
        self.mock_module.attribute = "test_value"

    def test_import_mod_from_lib_success_new_import(self):
        with patch("importlib.import_module",
                   return_value=self.mock_module) as mock_import:
            module = self.importer.import_mod_from_lib("test_library",
                                                       "test_module")
            self.assertEqual(module, self.mock_module)
            self.assertIn("test_module", self.importer.imported_modules)
            self.assertEqual(self.importer.imported_modules["test_module"], self.mock_module)
            mock_import.assert_called_once_with("test_library.test_module")

    def test_import_mod_from_lib_success_cached_import(self):
        self.importer.imported_modules["cached_module"] = self.mock_module
        with patch("importlib.import_module") as mock_import:
            module = self.importer.import_mod_from_lib("another_library",
                                                       "cached_module")
            self.assertEqual(module, self.mock_module)
            mock_import.assert_not_called()

    def test_import_mod_from_lib_failure(self):
        with patch("importlib.import_module",
                   side_effect=ModuleNotFoundError("No module named "
                                                   "'nonexistent_library.missing_module'")):
            with self.assertRaisesRegex(ImportError, "Could not import "
                                                     "nonexistent_library.missing_module"):
                self.importer.import_mod_from_lib("nonexistent_library",
                                                  "missing_module")
            self.assertNotIn("missing_module", self.importer.imported_modules)

    def test_import_mod_from_lib_returns_any(self):
        # Simulate importing a non-module object (though importlib.import_module typically returns modules)
        mock_object = "not a module"
        with patch.dict("sys.modules",
                        {"yet_another_library.some_object": mock_object}):
            result = self.importer.import_mod_from_lib("yet_another_library",
                                                       "some_object")
            self.assertEqual(result, mock_object)
            self.assertIn("some_object", self.importer.imported_modules)
            self.assertEqual(self.importer.imported_modules["some_object"], mock_object)


if __name__ == '__main__':
    unittest.main()
