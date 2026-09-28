"""The source of the test that backs a proof, read out of its file.

The AI audit sets a proof against the test that backs it, so it needs that
test's own source. This module finds it: it reads the marker comments in the
test file, the way the run reads them (`scripts/mcp/purlin/markers.py`),
finds the test each marker of the proof is tied to, and returns that test's
source text. It judges nothing about the test.

A test declared in Python, JavaScript, TypeScript, C# or Go is read from its
declaration to the end of its body. A file of an `exit` suite, a shell or SQL
script, is one test, and its source is the whole file.
"""

import os
import re
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
_MCP_DIR = os.path.join(os.path.dirname(_HERE), 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import markers as markers_module                  # noqa: E402


def _file_text(path):
    with open(path, encoding='utf-8') as handle:
        return handle.read()


def _format_of(project_root, test_file):
    """The format of the suite the file belongs to.

    A file no suite names is read by its language: one with a test reader is
    read test by test, and any other file is one test.
    """
    suites, _problems = markers_module.read_suites(project_root)
    suite = markers_module.suite_of(test_file, suites)
    if suite is not None:
        return suite.format
    ext = os.path.splitext(test_file)[1].lower()
    return 'junit' if markers_module.declared_tests('', ext) is not None \
        else 'exit'


def _test_bodies(project_root, test_file, feature, proof_id):
    """`[(name, source)]` for each test the marker `feature proof_id` is tied to."""
    path = os.path.join(project_root, *test_file.split('/'))
    try:
        text = _file_text(path)
    except (OSError, UnicodeDecodeError):
        return []
    fmt = _format_of(project_root, test_file)
    found = markers_module.read_text(test_file, text, fmt)
    wanted = (feature, proof_id)
    if found.whole:
        if any(marker.key() == wanted for marker in found.markers):
            return [(test_file.rsplit('/', 1)[-1], text)]
        return []
    bodies = []
    for test in found.tests:
        if any(marker.key() == wanted for marker in test.markers):
            source_text = _python_or_span(text, test, test_file)
            bodies.append((markers_module.test_name(test_file, test),
                           source_text))
    return bodies


def _python_or_span(text, test, test_file):
    if test_file.endswith('.py'):
        lines = text.splitlines(True)
        end = test.end or test.line
        return ''.join(lines[test.line - 1:end])
    if test.start is None:
        return None
    return text[test.start:test.end] if test.end else text[test.start:]


# A name the evidence carries may hold what the runner added to the name in
# the source: a pytest parameter id or an xUnit theory's arguments.
_NAME_ARGS_RE = re.compile(r'(?:\[.*\]|\(.*\))\s*$')


def _key(name):
    return ' '.join(str(name or '').split())


def name_matches(test_name, names):
    """The indexes in `names` that are the test the evidence names `test_name`.

    An exact name wins, then the name without its arguments, then a name the
    written one ends with after a class, namespace or describe prefix. Empty
    when none is that test.
    """
    wanted = _key(test_name)
    bare = _NAME_ARGS_RE.sub('', wanted).strip()
    keys = [_key(name) for name in names]
    for key in (wanted, bare):
        found = [i for i, name in enumerate(keys) if key and name == key]
        if found:
            return found
    return [i for i, name in enumerate(keys)
            if name and any(bare.endswith(sep + name)
                            for sep in ('::', '.', ' > ', ' '))]


def _pick_test_body(candidates, test_name):
    """The source in `candidates` whose name is `test_name`, or None.

    With no name asked for, the first. A name that matches nothing still finds
    the one test when the proof has only one in the file; among several it
    finds none, because showing another test's source under this name
    misleads.
    """
    if not candidates:
        return None
    if test_name is None:
        return candidates[0][1]
    found = name_matches(test_name, [name for name, _body in candidates])
    if found:
        return candidates[found[0]][1]
    return candidates[0][1] if len(candidates) == 1 else None


def source(project_root, feature, proof_id, test_file, test_name=None):
    """The source of the test named `test_name` backing `proof_id`, or None."""
    if not test_file:
        return None
    path = os.path.join(project_root, *test_file.split('/'))
    if not os.path.isfile(path):
        return None
    return _pick_test_body(
        _test_bodies(project_root, test_file, feature, proof_id), test_name)
