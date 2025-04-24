from types import ModuleType
from typing import Any

import importlib


class Importer:
    def __init__(self):
        self.imported_modules = {}

    def import_mod_from_lib(self, library: str, module_name: str) -> ModuleType | Any:
        """Lazily imports and caches a specific submodule from a given library.
        :param library: The name of the library.
        :param module_name: The name of the module to import.
        :return: The imported module.
        """
        if module_name in self.imported_modules:
            return self.imported_modules[module_name]

        try:
            module = importlib.import_module(f"{library}.{module_name}")
            self.imported_modules[module_name] = module
            return module
        except ModuleNotFoundError as e:
            raise ImportError(f"Could not import {library}.{module_name}") from e



