"""Keep pytest's collection to this repository's own tests.

`dev/fixtures/` holds whole sample projects that the tests copy and run. One
of them declares `pytest_plugins` in its own `conftest.py`, which pytest
refuses to load from below the root directory, so collecting that tree stops
the session before a single test runs. Nothing under `dev/fixtures/` is a test
of this repository, so collection never descends into it.

This file is also what framework detection reads pytest off, so the framework
this repository proves itself with is named by the same file that keeps the
session collectable.

Under mutmut this file is copied into `mutants/`, and it names each module
under `scripts/` by its path. The tests import `scripts/run/records.py` as
`records`, through a `sys.path` entry, while mutmut names a break by the path,
`scripts.run.records`, and switches a break on only when a function's
`__module__` matches that name. Without the rename no break is ever switched
on and mutmut stops before running one. Outside `mutants/` nothing is renamed.
"""

import importlib.abc
import importlib.machinery
import os
import sys

collect_ignore = ['dev/fixtures']

_ROOT = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.join(_ROOT, 'scripts') + os.sep


def _path_name(origin):
    """`scripts.run.records` for `<root>/scripts/run/records.py`."""
    relative = os.path.relpath(origin, _ROOT)[:-len('.py')]
    name = relative.replace(os.sep, '.')
    if name.endswith('.__init__'):
        name = name[:-len('.__init__')]
    return name


class _PathNamedLoader(importlib.abc.Loader):
    """Runs a module's code with the path name as its `__name__`."""

    def __init__(self, loader, fullname, path_name):
        self.loader = loader
        self.fullname = fullname
        self.path_name = path_name

    def create_module(self, spec):
        return None

    def exec_module(self, module):
        code = self.loader.get_code(self.fullname)
        sys.modules.setdefault(self.path_name, module)
        module.__name__ = self.path_name
        exec(code, module.__dict__)


class _PathNamedFinder(importlib.abc.MetaPathFinder):
    """Finds a module the usual way and renames it when it lives in `scripts/`."""

    def find_spec(self, fullname, path=None, target=None):
        spec = importlib.machinery.PathFinder.find_spec(fullname, path)
        if spec is None or not spec.origin or not spec.origin.endswith('.py'):
            return spec
        if not os.path.abspath(spec.origin).startswith(_SCRIPTS):
            return spec
        name = _path_name(os.path.abspath(spec.origin))
        if name != fullname:
            spec.loader = _PathNamedLoader(spec.loader, fullname, name)
        return spec


_UNDER_MUTMUT = os.path.basename(_ROOT) == 'mutants'

if _UNDER_MUTMUT and not any(
        isinstance(finder, _PathNamedFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, _PathNamedFinder())


def pytest_runtest_setup(item):
    """Keep mutmut's switch out of the processes a test starts.

    mutmut keeps the active break both in `MUTANT_UNDER_TEST` and in its own
    process, and reads its own copy when the variable is gone. A test that
    runs a script in a subprocess would otherwise hand the variable on, and
    the script's mutmut hook then reads a config from the test's temporary
    project and exits 1. The subprocess could not switch a break on anyway:
    its modules are not renamed.
    """
    if _UNDER_MUTMUT:
        os.environ.pop('MUTANT_UNDER_TEST', None)
