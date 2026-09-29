"""The throwaway projects the report tests and the setup tests share.

A helper module, not a test file: it carries no marker and pytest collects
nothing from it. Each test file imports the names it uses from here, so no
test file imports another.
"""

import json
import os
import shutil
import subprocess
import sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUN_SCRIPT = os.path.join(REPO, 'scripts', 'run', 'purlin_run.py')
FIXTURES = os.path.join(REPO, 'dev', 'fixtures', 'reports')


def _write(root, rel, text):
    path = root.joinpath(*rel.split('/'))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


def _run(root, *args):
    done = subprocess.run(
        [sys.executable, RUN_SCRIPT, '--project-root', str(root)]
        + list(args), capture_output=True, encoding='utf-8', cwd=str(root))
    return done.returncode, done.stdout + done.stderr


def _evidence(root, feature='login'):
    path = root / '.purlin' / 'evidence' / 'local' / ('%s.json' % feature)
    data = json.loads(path.read_text(encoding='utf-8'))
    (section,) = data['platforms'].values()
    return section


def _fixture(tmp_path, name):
    target = tmp_path / name
    shutil.copytree(os.path.join(FIXTURES, name), str(target))
    return target


GO_SPECS = {
    'cart': ('# Feature: cart\n\n> Scope: cart/\n\n## Rules\n\n'
             '- RULE-1: Two prices add up\n'
             '- RULE-2: An empty basket is refused\n'
             '- RULE-3: A discount applies\n'
             '- RULE-4: Two and two total five\n\n## Proof\n\n'
             '- PROOF-1 (RULE-1): 2 and 3 total 5\n'
             '- PROOF-2 (RULE-2): an empty basket is refused\n'
             '- PROOF-3 (RULE-3): a discount applies\n'
             '- PROOF-4 (RULE-4): 2 and 2 total 5\n'),
    'tax': ('# Feature: tax\n\n> Scope: tax/\n\n## Rules\n\n'
            '- RULE-1: The uk rate is 0.2\n'
            '- RULE-2: A lookup past the table is refused\n'
            '- RULE-3: A test after a panic is reached\n\n## Proof\n\n'
            '- PROOF-1 (RULE-1): the uk rate reads 0.2\n'
            '- PROOF-2 (RULE-2): a lookup past the table is refused\n'
            '- PROOF-3 (RULE-3): the test after the panic runs\n'),
}
