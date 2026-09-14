#!/usr/bin/env python3
"""Drive the Purlin QA tool once, by hand, against this checkout.

A person runs this. It is not in `dev/run_tests.sh` and never will be: it calls
the real `claude` CLI, so it costs money and its answer is a model's, not a
fixture's. One prompt per run, one hard timeout, one transcript on disk.

`tools/QA/purlin-qa-report.md` is the tool a QA person installs in Claude
Desktop. This check hands the CLI that text and the rollup
`scripts/report/scan.py` prints for this checkout, and asks for the triage
report the tool describes.

Exit codes: 0 the CLI ran and every check passed, 1 a check failed, 2 `claude`
is not on PATH.

Usage:
    python3 dev/manual/check_qa_tool.py [--repo DIR] [--keep] [--timeout 600]
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
sys.path.insert(0, HERE)

from check_spec import (TMP_BASE, call_claude, report, run)  # noqa: E402

TOOL = os.path.join(PLUGIN_ROOT, 'tools', 'QA', 'purlin-qa-report.md')
SCAN = os.path.join(PLUGIN_ROOT, 'scripts', 'report', 'scan.py')
RISKS = ('high', 'medium', 'low')
ASK = ('The rollup below is what `scan.py --repo %s` printed. The scan has '
       'already run, so do not run it again and do not open a repository. '
       'Read the rollup and print the triage report: the review list, ordered '
       'by risk, and the closing counts.\n\n%s')


def tool_text():
    """The tool's instructions, without the front matter a reader never sees."""
    with open(TOOL, encoding='utf-8') as handle:
        text = handle.read()
    if text.startswith('---'):
        text = text.split('\n---\n', 1)[-1]
    return text.strip()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--repo', default=PLUGIN_ROOT,
                        help='the repository to scan (default: this checkout)')
    parser.add_argument('--keep', action='store_true',
                        help='leave the temporary directory on disk')
    parser.add_argument('--timeout', type=int, default=600,
                        help='seconds the claude CLI may take (default 600)')
    args = parser.parse_args(argv)

    if shutil.which('claude') is None:
        print('claude is not on PATH, so there is nothing to drive.')
        return 2

    root = os.path.join(TMP_BASE, 'check_qa_tool-%s' % time.strftime('%H%M%S'))
    os.makedirs(root, exist_ok=True)
    try:
        _code, rollup = run([sys.executable, SCAN, '--repo', args.repo],
                            root, timeout=300)
    except subprocess.TimeoutExpired:
        rollup = 'scan.py did not finish inside 300 s'
    print('scan of %s:\n%s' % (args.repo, rollup.strip()))
    total = re.search(r'(\d+)\s+rules', rollup)
    total = int(total.group(1)) if total else 0
    gate = re.search(r'gate\s+(tested|recorded|approved)', rollup)
    gate = gate.group(1) if gate else ''

    reply, transcript = call_claude(
        root, ASK % (args.repo, rollup.strip()), args.timeout,
        extra=['--append-system-prompt', tool_text()])
    print('\ntranscript: %s\n' % transcript)
    print('report:\n%s\n' % reply.strip())

    seen = [RISKS.index(w.lower()) for w in re.findall(
        r'\b(high|medium|low)\b', reply, re.IGNORECASE)]
    ordered = all(a <= b for a, b in zip(seen, seen[1:]))
    named = sorted(set(re.findall(r'\bRULE-\d+\b', reply)))

    code = report([
        ('the CLI answered', bool(reply.strip()), '%d characters' % len(reply.strip())),
        ('the gate is named', bool(gate) and gate in reply,
         'gate %s' % (gate or 'not read from the scan')),
        ('ordered by risk', ordered,
         'risk words in order: %s' % (', '.join(RISKS[i] for i in seen) or 'none')),
        ('the review list only', total and len(named) < total,
         '%d rule id(s) named of %d in the project' % (len(named), total)),
        ('the review list is named', 'review list' in reply.lower(),
         'the phrase "review list" is %spresent'
         % ('' if 'review list' in reply.lower() else 'not ')),
    ])
    if args.keep:
        print('kept: %s' % root)
    else:
        shutil.rmtree(root, ignore_errors=True)
        print('removed: %s (pass --keep to inspect it)' % root)
    return code


if __name__ == '__main__':
    sys.exit(main())
