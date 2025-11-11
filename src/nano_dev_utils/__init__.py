"""nano-dev-utils - A collection of small Python utilities for developers.
Copyright (c) 2025 Yaron Dayan
"""

from importlib.metadata import version
from .dynamic_importer import Importer
from .timers import Timer
from .release_ports import PortsRelease, PROXY_SERVER, INSPECTOR_CLIENT
from .common import (
    update,
    encode_dict,
    str2file,
    PredicateBuilder,
    FilterSet,
    load_cfg_file,
)

from ._constants import PKG_NAME

timer = Timer()
ports_release = PortsRelease()
importer = Importer()
predicate_builder = PredicateBuilder

__version__ = version(PKG_NAME)

__all__ = [
    'Importer',
    'Timer',
    'PortsRelease',
    'PROXY_SERVER',
    'INSPECTOR_CLIENT',
    'update',
    'encode_dict',
    'str2file',
    'PredicateBuilder',
    'predicate_builder',
    'FilterSet',
    'timer',
    'ports_release',
    'importer',
    'load_cfg_file',
]
