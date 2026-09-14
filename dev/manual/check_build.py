#!/usr/bin/env python3
"""Drive `purlin:build` once, by hand, against a throwaway project.

A person runs this. It is not in `dev/run_tests.sh` and never will be: it calls
the real `claude` CLI, so it costs money and its answer is a model's, not a
fixture's. One prompt per run, one hard timeout, one transcript on disk.

Run it after `check_spec.py --keep`, whose project it picks up by default, so it
builds the spec that was just written. `--spec <file>` builds a committed
fixture spec in a fresh project instead, and `--project <dir>` names a project
directly.

Exit codes: 0 the CLI ran and every check passed, 1 a check failed, 2 `claude`
is not on PATH.

Usage:
    python3 dev/manual/check_build.py [--spec FILE] [--project DIR]
                                      [--keep] [--timeout 600]
"""

import argparse
import glob
import os
import re
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)

from check_spec import (TMP_BASE, call_claude, new_project,  # noqa: E402
                        read_spec, report, run, write)

# The three sections `references/commit_conventions.md` gives the changeset
# body. Changeset carries no heading of its own: it is the `RULE-N -> file:line`
# lines that open the body, so it is read off those.
SECTIONS = ('Decisions', 'Review')
CHANGESET = re.compile(r'^RULE-\d+\s*\u2192\s*\S+', re.MULTILINE)
MARKER = re.compile(r'proof\s*\(\s*["\']', re.IGNORECASE)
TEST_FILE = re.compile(r'(^|/)(test_[^/]+\.py|[^/]+_test\.py)$')


def newest_kept_project():
    """The newest project `check_spec.py --keep` left behind, if any."""
    found = [p for p in glob.glob(os.path.join(TMP_BASE, 'check_spec-*'))
             if os.path.isdir(p)]
    return max(found, key=os.path.getmtime) if found else None


def project_from_spec(spec_file):
    """A fresh project carrying `spec_file`, committed."""
    root = new_project('check_build')
    with open(spec_file, encoding='utf-8') as handle:
        text = handle.read()
    dest = os.path.join(root, 'specs', 'app', os.path.basename(spec_file))
    write(dest, text)
    run(['git', 'add', '-A'], root)
    run(['git', 'commit', '-qm', 'spec(%s): the fixture spec'
         % os.path.splitext(os.path.basename(spec_file))[0]], root)
    return root


def tracked_files(root):
    _code, out = run(['git', 'ls-files'], root)
    return set(out.split())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--spec', help='a committed fixture spec to build instead')
    parser.add_argument('--project', help='the project to build in')
    parser.add_argument('--keep', action='store_true',
                        help='leave the temporary project on disk')
    parser.add_argument('--timeout', type=int, default=600,
                        help='seconds the claude CLI may take (default 600)')
    args = parser.parse_args(argv)

    if shutil.which('claude') is None:
        print('claude is not on PATH, so there is nothing to drive.')
        return 2

    if args.project:
        root = args.project
    elif args.spec:
        root = project_from_spec(args.spec)
    else:
        root = newest_kept_project()
        if root is None:
            print('No project from check_spec.py --keep under %s, and no '
                  '--spec or --project given.' % TMP_BASE)
            return 1
    rel, _text = read_spec(root)
    if rel is None:
        print('%s carries no spec, so there is nothing to build.' % root)
        return 1
    feature = os.path.splitext(os.path.basename(rel))[0]
    before = tracked_files(root)
    _code, head_before = run(['git', 'rev-parse', 'HEAD'], root)

    prompt = 'purlin:build %s' % feature
    print('project:    %s' % root)
    print('spec:       %s' % rel)
    print('prompt:     %s\n' % prompt)
    reply, transcript = call_claude(root, prompt, args.timeout)
    print('transcript: %s\n' % transcript)

    created = sorted(tracked_files(root) - before)
    print('files created:')
    for path in created or ['  (none)']:
        print('  %s' % path)

    tests = [p for p in created if TEST_FILE.search(p)]
    marked = []
    for path in tests:
        with open(os.path.join(root, path), encoding='utf-8') as handle:
            if MARKER.search(handle.read()):
                marked.append(path)

    env = dict(os.environ)
    try:
        _code, quick = run([sys.executable,
                            os.path.join(PLUGIN_ROOT, 'scripts', 'run',
                                         'purlin_run.py'),
                            '--all', '--quick', '--project-root', root],
                           root, timeout=300, env=env)
    except subprocess.TimeoutExpired:
        quick = 'purlin_run.py did not finish inside 300 s'
    print('\npurlin_run.py --all --quick:\n%s' % quick.strip())

    _code, head_after = run(['git', 'rev-parse', 'HEAD'], root)
    body = ''
    if head_after.strip() != head_before.strip():
        _code, body = run(['git', 'log', '-1', '--format=%B'], root)
    present = (['Changeset'] if CHANGESET.search(body) else []) + [
        s for s in SECTIONS
        if re.search(r'^\**%s\**:\s*$' % s, body, re.MULTILINE | re.IGNORECASE)]
    print('\ncommit body sections: %s' % (', '.join(present) or 'none'))
    print(body.strip() or '(the build committed nothing)')
    print('')

    code = report([
        ('the build created files', bool(created),
         '%d file(s)' % len(created)),
        ('a tagged test was written', bool(tests),
         ', '.join(tests) or 'no test file'),
        ('every test carries a proof marker', bool(tests) and len(marked) == len(tests),
         '%d of %d marked' % (len(marked), len(tests))),
        ('the quick run passed', 'FAIL' not in quick.upper(),
         (quick.strip().splitlines() or ['no output'])[-1][:70]),
        ('the commit body carries Changeset', 'Changeset' in present,
         'sections: %s' % (', '.join(present) or 'none')),
        ('the reply named the next step', 'purlin:' in reply,
         (reply.strip().splitlines() or [''])[-1][-70:]),
    ])
    if args.keep or args.project:
        print('kept: %s' % root)
    else:
        shutil.rmtree(root, ignore_errors=True)
        print('removed: %s (pass --keep to inspect it)' % root)
    return code


if __name__ == '__main__':
    sys.exit(main())
