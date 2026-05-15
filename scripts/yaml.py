"""Compatibility loader for PyYAML in constrained test environments.

This file intentionally shadows the top-level `yaml` import only to delegate
to the real PyYAML package. The project keeps system package paths out of
pytest.ini, but some container images install PyYAML only in distro-managed
locations that are not on the interpreter's default sys.path. Because pytest
adds `scripts` to pythonpath, this delegating shim is found first and then
loads PyYAML from normal or distro package locations. Do not add YAML parsing
logic here.
"""

from __future__ import annotations

import importlib.machinery
import importlib.util
import pathlib
import sys

_CURRENT_DIR = pathlib.Path(__file__).resolve().parent
_SEARCH_PATHS = [
    path
    for path in sys.path
    if path and pathlib.Path(path).resolve() != _CURRENT_DIR
]
for distro_path in ("/usr/lib/python3/dist-packages", "/usr/local/lib/python3/dist-packages"):
    if distro_path not in _SEARCH_PATHS:
        _SEARCH_PATHS.append(distro_path)

sys.modules.pop(__name__, None)
_SPEC = importlib.machinery.PathFinder.find_spec(__name__, _SEARCH_PATHS)
if _SPEC is None or _SPEC.loader is None:
    raise ModuleNotFoundError(
        "PyYAML is required; install it or make the distro package path available."
    )

_MODULE = importlib.util.module_from_spec(_SPEC)
sys.modules[__name__] = _MODULE
_SPEC.loader.exec_module(_MODULE)
globals().update(_MODULE.__dict__)
