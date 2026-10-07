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

A second kind of output is what an AI produced for one run of an AI proof's
test, a folder:

    .purlin/runtime/ai/<feature>/<PROOF-N>/<model>/<n>/
        reply.md           the last thing the AI said
        transcript.jsonl   what the session did, one JSON object per line
        files/             every file it wrote or changed in the sample
        purlin.json        the helper's own record of the run (`RECORD`)

The evidence names the folder by `folder_sha256`, which every file in it
but `purlin.json` goes into. `scripts/ai/purlin_ai.py` writes the folder
and the record; the run names the folder through `AI_OUT` and reads the
record back. The folder stays where the run wrote it, found again by its
sha256 (`ai_held`), and a run removes each one no evidence file on disk
names any longer (`prune`).

`references/formats/evidence_format.md` and `package_format.md` hold the
fields that name an output.
"""

import hashlib
import json
import os
import pathlib
import re
import shutil

from . import evidence as evidence_module
from . import signatures as signatures_module

# Where a run keeps the outputs its results were read from.
KEPT_DIR = '.purlin/runtime/kept'

# A test suite's report, the kind of output that is one file.
REPORT = 'report'

# The file that keeps git from rewriting a line end in a kept output, and
# what it holds.
ATTRIBUTES = '.gitattributes'
ATTRIBUTES_TEXT = '* -text\n'

# What a kept copy of a command's standard output is named with beside the
# package.
STDOUT_EXTENSION = '.txt'

# What an AI produced, kept per run of an AI proof's test on one model.
AI_DIR = '.purlin/runtime/ai'
AI_OUTPUT = 'ai-output'
REPLY = 'reply.md'
TRANSCRIPT = 'transcript.jsonl'
FILES = 'files'

# The helper's own record of one run, beside the output and left out of its
# sha256. `made` is `helper` where `purlin_ai.py run` made the output and
# `project` where the project's own test handed it over with `record`;
# `model` is the model asked; `reached` is false where the model gave no
# answer, `why` then saying so in one sentence. `grade`, written by
# `purlin_ai.py grade`, holds the grader's `model`, `accepted` (true, false,
# or None where the grader gave no answer) and its one `reason`.
RECORD = 'purlin.json'
MADE_BY_HELPER = 'helper'
MADE_BY_PROJECT = 'project'

# What the run sets for an AI proof's test. A test reads `AI_HELPER`, the
# path of `scripts/ai/purlin_ai.py`, to start it; the helper reads the other
# three: the model to ask, the folder to write, and a folder holding an
# earlier output to hand back in place of asking any model.
AI_HELPER = 'PURLIN_AI'
AI_MODEL = 'PURLIN_AI_MODEL'
AI_OUT = 'PURLIN_AI_OUT'
AI_REPLAY = 'PURLIN_AI_REPLAY'

# How many times an AI proof's test runs on each model where neither the
# settings' `runs` nor the proof's own `runs=` says.
RUNS = 3

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
    """Remove each kept output no evidence file on disk names. What was
    removed: the name of each report file, then the path of each run
    folder of an AI proof, `/` separated from the project root.

    `keep_too` is the sha256s to leave whatever the evidence says. A folder
    under `AI_DIR` left empty goes with the run folder it held.
    """
    wanted = named_in_evidence(project_root) | set(keep_too)
    removed = []
    folder = _full(project_root, KEPT_DIR)
    try:
        names = sorted(os.listdir(folder))
    except OSError:
        names = []
    for name in names:
        found = _SHA_NAME.match(name)
        if not found or found.group(1) in wanted:
            continue
        try:
            os.remove(os.path.join(folder, name))
        except OSError:
            continue
        removed.append(name)
    for rel in ai_run_dirs(project_root):
        if folder_sha256(_full(project_root, rel)) in wanted:
            continue
        shutil.rmtree(_full(project_root, rel), ignore_errors=True)
        removed.append(rel)
        above = os.path.dirname(_full(project_root, rel))
        for _level in range(_RUN_DEPTH - 1):
            try:
                os.rmdir(above)
            except OSError:
                break
            above = os.path.dirname(above)
    return removed


# ---------------------------------------------------------------------------
# What an AI produced
# ---------------------------------------------------------------------------

def model_slug(model):
    """A model's name as a folder is named: every character but a letter, a
    digit, `.`, `_` and `-` reads `_`."""
    return re.sub(r'[^A-Za-z0-9._-]', '_', str(model or '')) or '_'


def ai_run_dir(feature, proof_id, model, run, test=1):
    """Where one run of an AI proof's test writes, `/` separated:
    `.purlin/runtime/ai/<feature>/<PROOF-N>/<model>/<n>`, `n` from 1. A
    proof's second and later tests, in the order the evidence lists them,
    write to `<n>.<t>`, `t` from 2."""
    last = '%d' % run if test <= 1 else '%d.%d' % (run, test)
    return '%s/%s/%s/%s/%s' % (AI_DIR, feature, proof_id, model_slug(model),
                               last)


# How many folders deep a run folder sits under `AI_DIR`: the feature, the
# proof, the model and the run.
_RUN_DEPTH = 4


def ai_run_dirs(project_root):
    """Every run folder under `AI_DIR`, as `ai_run_dir` names one, sorted."""
    found = []

    def walk(rel, depth):
        try:
            names = sorted(os.listdir(_full(project_root, rel)))
        except OSError:
            return
        for name in names:
            below = '%s/%s' % (rel, name)
            if not os.path.isdir(_full(project_root, below)):
                continue
            if depth == _RUN_DEPTH:
                found.append(below)
            else:
                walk(below, depth + 1)
    walk(AI_DIR, 1)
    return found


def ai_held(project_root, sha):
    """The run folder this machine keeps whose files give the sha256 `sha`
    now, as `ai_run_dir` names it, or None where it keeps none."""
    if not sha:
        return None
    for rel in ai_run_dirs(project_root):
        if folder_sha256(_full(project_root, rel)) == sha:
            return rel
    return None


def runs_asked(proof, setting=None):
    """How many times an AI proof's test runs on each model: the proof's
    own `runs`, else `setting`, the `runs` of the settings file as
    `config_engine.runs` reads it, else `RUNS`."""
    return (proof or {}).get('runs') or setting or RUNS


def runs_setting(project_root):
    """The `runs` of the project's settings file, or None where it sets
    none (`config_engine.runs`)."""
    import config_engine
    from . import markers as markers_module
    return config_engine.runs(markers_module.load_config(project_root))


def asked_runs(info, setting=None):
    """`{proof id: runs}` for each AI proof of one spec, `info` its entry
    in `specs.scan_specs`: what `runs_asked` answers for each."""
    return {proof_id: runs_asked(proof, setting)
            for proof_id, proof in ((info or {}).get('proofs') or {}).items()
            if proof.get('ai')}


def folder_files(folder):
    """The `/` separated paths, sorted, of every file under `folder` but
    the helper's record."""
    found = []
    for dirpath, dirnames, filenames in os.walk(folder):
        dirnames.sort()
        for name in filenames:
            rel = os.path.relpath(os.path.join(dirpath, name),
                                  folder).replace(os.sep, '/')
            if rel != RECORD:
                found.append(rel)
    return sorted(found)


def folder_sha256(folder):
    """The sha256 an output folder is named by, or None where it holds no
    file but the record.

    One line per file, sorted by path, `<sha256 of its bytes>  <path>` and a
    line feed, as `sha256sum` prints them; the sha256 of those lines.
    """
    lines = []
    for rel in folder_files(folder):
        data = _read(os.path.join(folder, *rel.split('/')))
        if data is None:
            continue
        lines.append('%s  %s\n' % (sha256_of(data), rel))
    if not lines:
        return None
    return sha256_of(''.join(lines).encode('utf-8'))


def read_record(folder):
    """The helper's record of the run that wrote `folder`, `{}` where it
    left none that can be read."""
    data = _read(os.path.join(folder, RECORD))
    try:
        found = json.loads(data.decode('utf-8')) if data else {}
    except ValueError:
        found = {}
    return found if isinstance(found, dict) else {}


def write_record(folder, record):
    """Write the helper's record of a run into `folder`."""
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, RECORD), 'w', encoding='utf-8',
              newline='\n') as handle:
        handle.write(json.dumps(record, indent=2, sort_keys=True) + '\n')


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
