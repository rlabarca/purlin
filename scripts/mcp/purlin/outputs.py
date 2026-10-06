"""The outputs a run keeps, and the ones a sign-off commits with the package.

An output is a file a run left that a result was read from: a test suite's
report, as the suite wrote it. The evidence names each by the sha256 of its
bytes, and two places hold the bytes:

    .purlin/runtime/kept/<sha256><extension>
        on the machine that ran the tests, which git ignores. A run puts
        each report it read there, and removes the files no evidence file
        on disk names any longer.

    .purlin/evidence/package/<version>.outputs/<kind>s/<sha256><extension>
        beside the evidence package, committed with the first sign-off of
        the version: the outputs the package lists that this machine still
        holds. `<kind>` is `report` for a test suite's report.

A file is found by its sha256 alone, and its bytes are hashed again before
they are copied or counted, so a file changed after it was kept is not kept
as the one the evidence names.

`references/formats/evidence_format.md` and `package_format.md` hold the
fields that name an output.
"""

import hashlib
import os
import pathlib
import re

from . import evidence as evidence_module
from . import signatures as signatures_module

# Where a run keeps the outputs its results were read from.
KEPT_DIR = '.purlin/runtime/kept'

# The one kind of output there is: a test suite's report.
REPORT = 'report'

# The file that keeps git from rewriting a line end in a kept output, and
# what it holds.
ATTRIBUTES = '.gitattributes'
ATTRIBUTES_TEXT = '* -text\n'

# What a kept copy of a command's standard output is named with beside the
# package.
STDOUT_EXTENSION = '.txt'

_SHA = re.compile(r'[0-9a-f]{64}')
_SHA_NAME = re.compile(r'^([0-9a-f]{64})(\.[A-Za-z0-9]+)?$')


def sha256_of(data):
    return hashlib.sha256(data).hexdigest()


def _full(project_root, rel):
    return os.path.join(project_root, *rel.split('/'))


def _read(path):
    try:
        return pathlib.Path(path).read_bytes()
    except (IOError, OSError):
        return None


# ---------------------------------------------------------------------------
# On the machine that ran the tests
# ---------------------------------------------------------------------------

def keep(project_root, data, extension=''):
    """Keep `data` under its sha256. The sha256.

    The file is `.purlin/runtime/kept/<sha256><extension>`; one already
    there is left as it is.
    """
    sha = sha256_of(data)
    folder = _full(project_root, KEPT_DIR)
    path = os.path.join(folder, sha + (extension or ''))
    if not os.path.isfile(path):
        os.makedirs(folder, exist_ok=True)
        pathlib.Path(path).write_bytes(data)
    return sha


def held(project_root, sha):
    """`(file name, bytes)` of the output kept under `sha` whose bytes still
    give that sha256, or None where this machine holds none."""
    folder = _full(project_root, KEPT_DIR)
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return None
    for name in names:
        found = _SHA_NAME.match(name)
        if not found or found.group(1) != sha:
            continue
        data = _read(os.path.join(folder, name))
        if data is not None and sha256_of(data) == sha:
            return name, data
    return None


def named_in_evidence(project_root):
    """Every sha256 the evidence files on disk hold, under either source."""
    found = set()
    for source in evidence_module.SOURCES:
        folder = _full(project_root, '%s/%s' % (evidence_module.EVIDENCE_DIR,
                                                source))
        try:
            names = os.listdir(folder)
        except OSError:
            continue
        for name in names:
            if not name.endswith('.json'):
                continue
            data = _read(os.path.join(folder, name))
            if data:
                found.update(_SHA.findall(data.decode('utf-8', 'replace')))
    return found


def prune(project_root, keep_too=()):
    """Remove each kept output no evidence file on disk names. The names.

    `keep_too` is the sha256s to leave whatever the evidence says.
    """
    folder = _full(project_root, KEPT_DIR)
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        return []
    wanted = named_in_evidence(project_root) | set(keep_too)
    removed = []
    for name in names:
        found = _SHA_NAME.match(name)
        if not found or found.group(1) in wanted:
            continue
        try:
            os.remove(os.path.join(folder, name))
        except OSError:
            continue
        removed.append(name)
    return removed


# ---------------------------------------------------------------------------
# Beside the package
# ---------------------------------------------------------------------------

def outputs_dir(version):
    """`.purlin/evidence/package/<version>.outputs`, `/` separated."""
    return '%s/%s.outputs' % (signatures_module.PACKAGE_DIR, version)


def output_rel(version, kind, sha, extension=''):
    """Where one output of a version is committed, `/` separated."""
    return '%s/%ss/%s%s' % (outputs_dir(version), kind, sha, extension or '')


def extension_of(path):
    """The extension a kept output takes from the file it was read from:
    `.xml` for `reports/pytest.xml`, '' where the name has none, and
    `.txt` for `-`, a command's standard output."""
    if path == '-':
        return STDOUT_EXTENSION
    extension = os.path.splitext(str(path or ''))[1].lower()
    return extension if re.match(r'^\.[a-z0-9]+$', extension) else ''


def copy_kept(project_root, version, listed):
    """Write beside the package each output of `listed` this machine holds.
    The paths written, `/` separated, the attributes file first where one
    output was written.

    `listed` is the package's `outputs`. An output is written at its own
    `file` where the kept bytes give its `sha256`; one this machine does
    not hold is left out.
    """
    written = []
    for item in listed or ():
        found = held(project_root, str(item.get('sha256') or ''))
        if found is None:
            continue
        path = _full(project_root, item['file'])
        os.makedirs(os.path.dirname(path), exist_ok=True)
        pathlib.Path(path).write_bytes(found[1])
        written.append(item['file'])
    if written:
        rel = '%s/%s' % (outputs_dir(version), ATTRIBUTES)
        with open(_full(project_root, rel), 'w', encoding='utf-8',
                  newline='\n') as handle:
            handle.write(ATTRIBUTES_TEXT)
        written.insert(0, rel)
    return written


def on_this_machine(project_root, listed):
    """How many of the package's `outputs` this machine holds."""
    return sum(1 for item in listed or ()
               if held(project_root, str(item.get('sha256') or ''))
               is not None)


def check(listed, read):
    """`(kept, differing)` for the package's `outputs` against the files
    beside it.

    `read(file)` gives one output's bytes, or None where it is not there.
    `kept` counts the outputs whose bytes give the sha256 the package
    records, and `differing` is `[(file, sha256 its bytes give)]` for each
    that is there and gives another. An output that is not there is in
    neither.
    """
    kept, differing = 0, []
    for item in listed or ():
        data = read(item.get('file') or '')
        if data is None:
            continue
        gives = sha256_of(data)
        if gives == item.get('sha256'):
            kept += 1
        else:
            differing.append((item.get('file'), gives))
    return kept, differing
