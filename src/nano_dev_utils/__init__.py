"""nano-dev-utils - A collection of small Python utilities for developers.
Copyright (c) 2025 - 2026 Yaron Dayan
"""

from importlib.metadata import version

from ._constants import PKG_NAME
from .common import (
    FilterSet,
    PredicateBuilder,
    encode_dict,
    load_cfg_file,
    str2file,
    update,
)
from .dynamic_importer import Importer
from .release_ports import INSPECTOR_CLIENT, PROXY_SERVER, PortsRelease
from .timers import Timer

timer = Timer()
ports_release = PortsRelease()
importer = Importer()
predicate_builder = PredicateBuilder

__version__ = version(PKG_NAME)

__all__ = [
    'INSPECTOR_CLIENT',
    'PROXY_SERVER',
    'FilterSet',
    'Importer',
    'PortsRelease',
    'PredicateBuilder',
    'Timer',
    'encode_dict',
    'importer',
    'load_cfg_file',
    'ports_release',
    'predicate_builder',
    'str2file',
    'timer',
    'update',
]
