"""Write, render and commit the test results `purlin:test` produces.

A run of the tagged tests leaves two tracked files:

    .purlin/tests/<feature>.json   what the run saw, one file per feature
    .purlin/tests.md              one table for the whole project

`references/formats/tests_format.md` is the contract both sides read.

**The run commits them itself and never pushes.** They are the person's own
evidence of their own run, so they go in under the person's git identity with
the subject `purlin: tests at <sha7>`. A push is a person's act: nothing here
reaches a remote. A `--feature` run writes the features it ran and leaves
every other row of the table as it was, so the table is always the whole
project even when the run was not.

These results count at `passed` and nowhere above it. `strong` and `signed`
read a record CI wrote, which is a different file written by a different run.
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

_RUN_DIR = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(os.path.dirname(_RUN_DIR))
_MCP_DIR = os.path.join(_ROOT, 'scripts', 'mcp')
if _MCP_DIR not in sys.path:
    sys.path.insert(0, _MCP_DIR)

from purlin import results as reader  # noqa: E402

SCHEMA = reader.SCHEMA
TESTS_DIR = reader.TESTS_DIR
TABLE_PATH = reader.TABLE_PATH
# What git is handed. A pathspec takes `/` on every operating system.
TESTS_PATHSPEC = '.purlin/tests'
TABLE_PATHSPEC = '.purlin/tests.md'

COMMIT_SUBJECT = 'purlin: tests at %s'
COMMITTED = 'Test results committed.'
UNCHANGED = 'Test results unchanged.'
NO_REPOSITORY = ('Test results written; there is no git repository to commit '
                 'them to.')

TABLE_HEADING = '# Test results at %s'
TABLE_COLUMNS = ('Feature', 'Rules', 'Passed', 'Failing', 'No test',
                 'Last run')
TABLE_NOTE = ('These are the last local run of each feature, and they count '
              'only at the gate `passed`.')
TABLE_EMPTY = 'No feature has been run yet.'


def _now_iso():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def rule_word(proof_ids, proofs, observed, host_os):
    """The passed cell's word for one rule, read off this run alone.

    A `@manual` proof declares that no test is written for it, so it is read
    out here exactly as the passed cell reads it out: a rule whose proofs are
    all manual has nothing for a run to observe and is not counted as
    untested. A proof another operating system owns was not run here, so the
    rule reads `not run` rather than claiming there is no test.
    """
    written = list(proof_ids or ())
    if not written:
        return 'no test'
    runnable = [pid for pid in written
                if (proofs.get(pid) or {}).get('tier') != 'manual']
    if not runnable:
        return 'passed'
    if any(observed.get(pid) == 'fail' for pid in runnable):
        return 'failed'
    foreign = [pid for pid in runnable
               if (proofs.get(pid) or {}).get('env')
               and (proofs.get(pid) or {}).get('env') != host_os]
    here = [pid for pid in runnable if pid not in foreign]
    if here and all(observed.get(pid) == 'pass' for pid in here):
        return 'passed' if not foreign else 'not run'
    if any(observed.get(pid) for pid in runnable):
        return 'not run'
    return 'no test'


def build_results(feature, info, observed, tests, commit, host_os, when=None):
    """The `purlin-tests/1` dict for one feature this run covered.

    `observed` is `{proof_id: 'pass' | 'fail'}` from the run, and `tests` is
    `{proof_id: '<file>::<name>'}` naming what observed each proof.
    """
    proofs = info.get('proofs') or {}
    by_rule = info.get('proofs_by_rule') or {}
    rules = {}
    for rule_id in info.get('rule_order') or ():
        rules[rule_id] = rule_word(by_rule.get(rule_id) or [], proofs,
                                   observed, host_os)
    entries = []
    for rule_id in info.get('rule_order') or ():
        for proof_id in by_rule.get(rule_id) or ():
            proof = proofs.get(proof_id) or {}
            entries.append({
                'id': proof_id,
                'rule': rule_id,
                'result': observed.get(proof_id) or 'missing',
                'tier': proof.get('tier') or '',
                'env': proof.get('env'),
                'test': tests.get(proof_id) or '',
            })
    return {
        'schema': SCHEMA,
        'feature': feature,
        'commit': commit or '',
        'at': when or _now_iso(),
        'os': host_os,
        'rules': rules,
        'proofs': entries,
    }


def same_run(project_root, one, other):
    """True when two results say the same thing about the same code.

    `at` is when the run happened rather than what it saw, so it never makes
    two runs different. `commit` moves on its own: committing the results
    leaves HEAD one commit further on, and the very next run would otherwise
    have something to commit for ever. Two commits count as the same code
    when nothing outside the test results differs between them.
    """
    def observations(results):
        return {key: value for key, value in (results or {}).items()
                if key not in ('at', 'commit')}

    if observations(one) != observations(other):
        return False
    if (one or {}).get('commit') == (other or {}).get('commit'):
        return True
    return only_results_changed(project_root, (one or {}).get('commit'),
                                (other or {}).get('commit'))


def only_results_changed(project_root, one, other):
    """True when two commits differ in the test results and nothing else."""
    if not one or not other:
        return False
    listed = _git(project_root,
                  ['diff', '--name-only', '%s..%s' % (one, other), '--', '.',
                   ':(exclude)%s' % TESTS_PATHSPEC,
                   ':(exclude)%s' % TABLE_PATHSPEC])
    return listed is not None and not listed.strip()


def write_results(project_root, results):
    """Write one feature's results and return the path, project-relative.

    A file already saying this is left exactly as it is, so a second run that
    saw the same thing has nothing to commit.
    """
    directory = reader.tests_dir(project_root)
    if not os.path.isdir(directory):
        os.makedirs(directory)
    path = os.path.join(directory, '%s.json' % results.get('feature'))
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            existing = json.load(handle)
    except (json.JSONDecodeError, IOError, OSError, UnicodeDecodeError):
        existing = None
    if isinstance(existing, dict) and same_run(project_root, existing,
                                               results):
        return os.path.relpath(path, project_root).replace(os.sep, '/')
    with open(path, 'w', encoding='utf-8') as handle:
        json.dump(results, handle, indent=2, sort_keys=True)
        handle.write('\n')
    return os.path.relpath(path, project_root).replace(os.sep, '/')


def counts(results):
    """`(rules, passed, failing, no_test)` for one feature's results.

    `No test` is every rule that is neither `passed` nor `failed`, so a rule
    waiting on another operating system is counted there rather than silently
    dropped from the row.
    """
    words = list((results.get('rules') or {}).values())
    passed = sum(1 for word in words if word == 'passed')
    failing = sum(1 for word in words if word == 'failed')
    return len(words), passed, failing, len(words) - passed - failing


def newest_commit(all_results):
    """The commit of the most recent run in the table, as seven characters.

    The heading names the results rather than the working tree, so a run that
    saw nothing new leaves the table byte for byte as it was. Naming HEAD
    instead would change the heading on every run, because committing the
    results is itself a commit.
    """
    newest = None
    for results in (all_results or {}).values():
        if newest is None or str(results.get('at') or '') > str(
                newest.get('at') or ''):
            newest = results
    return str((newest or {}).get('commit') or '')[:7]


def render_table(all_results):
    """`.purlin/tests.md` for every feature that has results on disk."""
    lines = [TABLE_HEADING % (newest_commit(all_results)
                              or 'an unknown commit'), '']
    if not all_results:
        lines.append(TABLE_EMPTY)
        lines.append('')
        lines.append(TABLE_NOTE)
        return '\n'.join(lines) + '\n'
    lines.append('| %s |' % ' | '.join(TABLE_COLUMNS))
    lines.append('|%s|' % '|'.join('---' for _ in TABLE_COLUMNS))
    for feature in sorted(all_results):
        results = all_results[feature]
        rules, passed, failing, no_test = counts(results)
        last = ' · '.join([str(results.get('commit') or '')[:7] or '-',
                           str(results.get('at') or '-'),
                           str(results.get('os') or '-')])
        lines.append('| %s | %d | %d | %d | %d | %s |'
                     % (feature, rules, passed, failing, no_test, last))
    lines.append('')
    lines.append(TABLE_NOTE)
    return '\n'.join(lines) + '\n'


def write_table(project_root):
    """Render the whole table from what is on disk. The path it wrote.

    Every file under `.purlin/tests/` is read, so a `--feature` run leaves the
    rows it did not run exactly as they were.
    """
    path = reader.table_path(project_root)
    parent = os.path.dirname(path)
    if parent and not os.path.isdir(parent):
        os.makedirs(parent)
    text = render_table(reader.load_results(project_root))
    try:
        with open(path, 'r', encoding='utf-8') as handle:
            if handle.read() == text:
                return TABLE_PATHSPEC
    except (IOError, OSError, UnicodeDecodeError):
        pass
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)
    return TABLE_PATHSPEC


def project_totals(project_root, features=None):
    """`(passed, rules)` over the whole project, not over this run.

    The gate is a question about the project, so a `--feature` run answers it
    for every rule under `specs/` and not only for the features it ran: a
    feature with no results yet has passed nothing. `features` is the spec
    scan, which is what says how many rules a feature writes; without it the
    files on disk are all there is to count.
    """
    all_results = reader.load_results(project_root)
    names = sorted(features) if features is not None else sorted(all_results)
    passed = rules = 0
    for name in names:
        results = all_results.get(name) or {}
        feature_rules, feature_passed, _failing, _none = counts(results)
        if features is None:
            rules += feature_rules
        else:
            rules += len((features.get(name) or {}).get('rule_order') or ())
        passed += feature_passed
    return passed, rules


def gate_line(passed, rules):
    """The one line a person reads at `passed`, and the exit code with it."""
    if rules and passed == rules:
        return 'gate passed: %d of %d' % (passed, rules), 0
    return 'gate not met: %d of %d' % (passed, rules), 1


def commit_results(project_root, commit):
    """Commit the two files under the person's identity. The line to print.

    Nothing here pushes. The results are the person's own evidence of their
    own run, so the commit is theirs; a push is a separate act they make
    themselves.
    """
    paths = [TESTS_PATHSPEC, TABLE_PATHSPEC]
    listed = _git(project_root, ['status', '--porcelain', '--'] + paths)
    if listed is None:
        return NO_REPOSITORY
    if not listed.strip():
        return UNCHANGED
    if _git(project_root, ['add', '--'] + paths) is None:
        return NO_REPOSITORY
    message = COMMIT_SUBJECT % (str(commit or '')[:7] or 'an unknown commit')
    if _git(project_root, ['commit', '-m', message, '--'] + paths) is None:
        return NO_REPOSITORY
    return COMMITTED


def _git(project_root, args):
    """One git command's stdout, or None when git could not do it."""
    try:
        result = subprocess.run(['git'] + list(args), capture_output=True,
                                text=True, cwd=project_root, timeout=60)
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout if result.returncode == 0 else None
