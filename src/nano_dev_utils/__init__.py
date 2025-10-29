"""nano-dev-utils - A collection of small Python utilities for developers.
Copyright (c) 2025 Yaron Dayan
"""

from pathlib import Path
from importlib.metadata import version
from .dynamic_importer import Importer
from .timers import Timer
from .release_ports import PortsRelease, PROXY_SERVER, INSPECTOR_CLIENT
from .common import update
from .file_tree_display import FileTreeDisplay, DEFAULT_SFX

timer = Timer()
ports_release = PortsRelease()
importer = Importer()
filetree_display = FileTreeDisplay(root_dir=str(Path.cwd()))


__version__ = version('nano-dev-utils')

__all__ = [
    'Importer',
    'Timer',
    'PortsRelease',
    'PROXY_SERVER',
    'INSPECTOR_CLIENT',
    'update',
    'timer',
    'ports_release',
    'importer',
    'filetree_display',
    'DEFAULT_SFX',
]
