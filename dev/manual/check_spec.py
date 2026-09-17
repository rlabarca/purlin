#!/usr/bin/env python3
"""Drive `purlin:spec` once, by hand, against a throwaway project.

A person runs this. It is not in `dev/run_tests.sh` and never will be: it calls
the real `claude` CLI, so it costs money and its answer is a model's, not a
fixture's. One prompt per run, one hard timeout, one transcript on disk.

The project is a fresh git repository set up through
`scripts/init/scaffold.py --gate passed --yes`, which is what `purlin:init`
answers `passed` runs. The prompt is the sentence from the design's solo start,
and the checks read the spec the model wrote.

Exit codes: 0 the CLI ran and every check passed, 1 a check failed, 2 `claude`
is not on PATH.

Usage:
    python3 dev/manual/check_spec.py [--keep] [--timeout 600]
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(os.path.dirname(HERE))
TMP_BASE = os.environ.get(
    'PURLIN_MANUAL_TMP',
    '/private/tmp/claude-501/-Users-richlabarca-LocalCode-purlin'
    '/bdea5a4d-f9c8-4410-904f-32e75781c94b/scratchpad/lane-9H')

SENTENCE = ('Users sign in with email and password. After five failed attempts '
            'the account is locked for fifteen minutes.')
PROMPT = 'purlin:spec "%s"' % SENTENCE
CLOSING = 'Build it now?'

RULE_LINE = re.compile(r'^-\s+(RULE-\d+):')
PROOF_LINE = re.compile(r'^-\s+(PROOF-\d+)\s*\(([^)]*)\):')
TAG = re.compile(r'\[(risk|origin|criterion):\s*([^\]]+)\]')

SEED = {
    'pyproject.toml': '[tool.pytest.ini_options]\ntestpaths = ["tests"]\n',
    'src/__init__.py': '',
    'tests/__init__.py': '',
}


def run(cmd, cwd, timeout=120, env=None):
    """Run `cmd`, returning (returncode, stdout+stderr)."""
    proc = subprocess.run(cmd, cwd=cwd, timeout=timeout, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return proc.returncode, proc.stdout.decode('utf-8', 'replace')


def write(path, text):
    os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
    with open(path, 'w', encoding='utf-8') as handle:
        handle.write(text)


def new_project(label):
    """A fresh git repository with Purlin set up at the `passed` gate."""
    root = os.path.join(TMP_BASE, '%s-%s' % (label, time.strftime('%H%M%S')))
    shutil.rmtree(root, ignore_errors=True)
    os.makedirs(root)
    run(['git', 'init', '-q', '.'], root)
    for key, value in (('user.email', 'manual@example.com'),
                       ('user.name', 'Manual Check'),
                       ('commit.gpgsign', 'false')):
        run(['git', 'config', key, value], root)
    for rel, text in SEED.items():
        write(os.path.join(root, rel), text)
    run(['git', 'add', '-A'], root)
    run(['git', 'commit', '-qm', 'seed'], root)
    code, out = run([sys.executable,
                     os.path.join(PLUGIN_ROOT, 'scripts', 'init', 'scaffold.py'),
                     '--gate', 'passed', '--yes',
                     '--project-root', root, '--plugin-root', PLUGIN_ROOT], root)
    if code != 0:
        sys.stderr.write(out)
        raise SystemExit('scaffold.py exited %d; nothing to check' % code)
    run(['git', 'add', '-A'], root)
    run(['git', 'commit', '-qm', 'purlin: set up at the passed gate'], root)
    return root


def call_claude(root, prompt, timeout, extra=None):
    """One `claude -p` run. Returns (reply, transcript path)."""
    cmd = ['claude', '--plugin-dir', PLUGIN_ROOT,
           '--dangerously-skip-permissions', '-p', prompt] + list(extra or [])
    try:
        _code, out = run(cmd, root, timeout=timeout)
    except subprocess.TimeoutExpired:
        out = 'the claude CLI did not finish inside %d s' % timeout
    # Outside the project, so `--keep` is not what decides whether it survives.
    transcript = os.path.join(TMP_BASE, '%s.transcript.txt' % os.path.basename(root))
    write(transcript, out)
    return out, transcript


def read_spec(root):
    """The newest spec written under `specs/`, outside `specs/_anchors/`."""
    found = []
    for dirpath, dirnames, filenames in os.walk(os.path.join(root, 'specs')):
        dirnames[:] = [d for d in dirnames if d != '_anchors']
        found += [os.path.join(dirpath, n) for n in filenames if n.endswith('.md')]
    if not found:
        return None, ''
    newest = max(found, key=os.path.getmtime)
    with open(newest, encoding='utf-8') as handle:
        return os.path.relpath(newest, root), handle.read()


def report(checks):
    """Print one line per check and return the exit code."""
    for name, passed, detail in checks:
        print('%-38s %-4s %s' % (name, 'ok' if passed else 'FAIL', detail))
    failed = [name for name, passed, _ in checks if not passed]
    print('\n%d of %d checks passed.' % (len(checks) - len(failed), len(checks)))
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--keep', action='store_true',
                        help='leave the temporary project on disk')
    parser.add_argument('--timeout', type=int, default=600,
                        help='seconds the claude CLI may take (default 600)')
    args = parser.parse_args(argv)

    if shutil.which('claude') is None:
        print('claude is not on PATH, so there is nothing to drive.')
        return 2

    root = new_project('check_spec')
    print('project:    %s' % root)
    print('prompt:     %s\n' % PROMPT)
    reply, transcript = call_claude(root, PROMPT, args.timeout)
    print('transcript: %s\n' % transcript)

    rel, text = read_spec(root)
    rules = [m.group(1) for m in (RULE_LINE.match(l) for l in text.splitlines()) if m]
    proved = set()
    for line in text.splitlines():
        match = PROOF_LINE.match(line)
        if match:
            proved.update(re.findall(r'RULE-\d+', match.group(2)))
    tags = {}
    for line in text.splitlines():
        if RULE_LINE.match(line):
            for key, value in TAG.findall(line):
                tags.setdefault(key, []).append(value.strip())
    unproved = [r for r in rules if r not in proved]
    tag_detail = ', '.join('%s on %d of %d' % (k, len(tags.get(k, [])), len(rules))
                           for k in ('risk', 'origin', 'criterion')) or 'none'

    code = report([
        ('a spec file was written', rel is not None, rel or 'nothing under specs/'),
        # The skill splits this sentence into at least the success path, the
        # wrong password and the lockout. A richer split is the model's call.
        ('the sentence became 3 rules or more', len(rules) >= 3,
         '%d rules: %s' % (len(rules), ', '.join(rules) or 'none')),
        ('every rule carries a proof', bool(rules) and not unproved,
         'unproved: %s' % (', '.join(unproved) or 'none')),
        ('the rules carry tags', bool(tags.get('risk')) and bool(tags.get('origin')),
         tag_detail),
        ('the reply ends with the offer', reply.strip().endswith(CLOSING),
         'last line: %s' % (reply.strip().splitlines() or [''])[-1][-60:]),
    ])
    if args.keep:
        print('kept: %s' % root)
    else:
        shutil.rmtree(root, ignore_errors=True)
        print('removed: %s (pass --keep to inspect it)' % root)
    return code


if __name__ == '__main__':
    sys.exit(main())
